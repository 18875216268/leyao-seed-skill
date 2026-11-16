#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SCM 登录 · 药师帮商家后台登录模块（单文件自包含；依赖 requests；验证码人工识别输入，扫码确认窗用 tkinter 标准库）。

一个文件 = 一个既能独立运行、也能被任何应用 import 的登录组件。
模块只做一件事：账号密码 + 人工输入验证码 → 按账号策略自动分流（免扫码直登 / 企微扫码二次验证）→
拿到「完整 SCM 账户信息」与「完整请求凭证」。

════════════════ 给 AI · Agent 的调用契约（唯一登录入口 · 先读这段） ════════════════
需要 SCM 凭证时：**直接调用本脚本（黑盒使用）；禁止读源码后自写 / 自组装登录流程** ✗。

① 环境自检：python scripts/scm_login.py --check
② 先验证（只读、绝不弹窗）：python scripts/scm_login.py --status --no-remote
   退出码 0 = 已有可用凭证 → 直接使用（stdout 即完整凭证 JSON）。
③ 需要登录（唯一点：原生窗口）——账密可经 --account/--password 参数、
   SCM_ACCOUNT/SCM_PASSWORD 环境变量预填；验证码一律人工看图输入：
     python scripts/scm_login.py --reuse
④ 取凭证：--status 输出（同一份凭证仓库，见凭证文件节）。
用户已指定或提供凭证 / 登录方式 → 按其走。
禁止：自写登录流程 · 自取验证码/二维码 · 自拼鉴权 · 组装内部类（LoginFlow 等）· 绕过本脚本解析凭证。
═══════════════════════════════════════════════════════════════════════════════

登录机制（2026-10-30 实测定谳）：账密通道（登录页会话 → captcha（人工识别输入）→ postLogin，
password=md5(明文)）之后服务端按账号策略分流：
  · info="登录成功" 且 cookies 含 ysbang_adminToken → 免扫码直登（主账号类）；
  · info="请扫码登录" → 企微扫码二次验证（SSO 二维码 → auth_code → postLoginWx）。
凭证装配：getProviderLoginInfo（providerIdM=md5(providerId)）+ indexJava（tokenSY/tokenHP 等）。

直接运行：python scripts/scm_login.py [--status | --check | --reuse | --no-remote |
           --account X --password Y]；退出码 0 成功 / 1 业务错误 / 2 未分类错误。
被调用（四门面）：relogin / verify_credential / get_credential / is_authenticated。
凭证文件（落盘形态）：
  · 当前生效：%LOCALAPPDATA%\\scm-operations-query\\credential.json
  · 按账号归档：%LOCALAPPDATA%\\scm-operations-query\\accounts\\credential_<account>.json
  · 均为明文 JSON，原子写；登录新账号会更新「当前生效」，同时归档该账号，互不覆盖。
安全：主机/端点双白名单，不走系统代理；验证码人工识别输入；全部明文存储依赖用户目录 ACL。
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import tempfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

try:
    import requests
    from requests import Response
except ImportError:  # 沙箱可能未安装 requests
    requests = None  # type: ignore[assignment]
    Response = object  # type: ignore[assignment,misc]

# --------------------------------------------------------------------------- #
# 错误类型
# --------------------------------------------------------------------------- #
class ScmError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        output: dict[str, Any] = {"code": self.code, "message": self.message, "retryable": self.retryable}
        if self.details:
            output["details"] = self.details
        return output


# --------------------------------------------------------------------------- #
# 启动文件名（副本重命名后，运行时提示自动跟随实际文件名）
# --------------------------------------------------------------------------- #
_SELF = Path(sys.argv[0]).name if sys.argv and sys.argv[0] else "scripts/scm_login.py"


# --------------------------------------------------------------------------- #
# 命令行输出工具
# --------------------------------------------------------------------------- #
def configure_stdio() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")


def emit(value: dict[str, Any]) -> None:
    json.dump(value, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.write("\n")


# --------------------------------------------------------------------------- #
# 连接配置（仅登录必需项，硬编码；不含任何账号信息）
# --------------------------------------------------------------------------- #
SCM_BASE = "https://scm.ysbang.cn"
WECOM_BASE = "https://login.work.weixin.qq.com"
LOGIN_PAGE_PATH = "/provider.php/admin/public/login"
CAPTCHA_PATH = "/provider.php/Admin/Public/captcha"
POST_LOGIN_PATH = "/provider.php/Admin/Public/postLogin"
POST_LOGIN_WX_PATH = "/provider.php/Admin/Public/postLoginWx"
PROVIDER_INFO_PATH = "/scm-base/provider/getProviderLoginInfo"
INDEX_JAVA_PATH = "/provider.php/Admin/Index/indexJava"
# 业务探针：验证 cmsToken 是否仍有效（只读，要求 provideridm 请求头）
BUSINESS_PROBE_PATH = "/scm-goods/wholesaleDrug/getProviderInfo4List2"
QR_KEY_PATH = "/wwlogin/monoApi/sso/login/getWebQrCodeKey"
QR_STATUS_PATH = "/wwlogin/monoApi/sso/login/getWebQrCodeStatus"
QR_IMAGE_PATH = "/wwlogin/sso/qrcode"

WECOM_APP_ID = "wx8c9fab123dec4357"
WECOM_AGENT_ID = "1000327"   # SCM 企微应用编号（BI=1000305 / PMS=1000054）
WECOM_REDIRECT_URI = f"{SCM_BASE}/provider.php/admin/public/postLoginWx"
WECOM_VERSION = "2.3.2"

# 验证码：人工看图输入（原始方式）

CONNECT_TIMEOUT = 10.0
READ_TIMEOUT = 130.0
SCAN_POLL_INTERVAL = 1.5
QR_TIMEOUT_SECONDS = 300
CONFIRM_WAIT_SECONDS = 90
CREDENTIAL_EXPIRE_HOURS = 24

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


# --------------------------------------------------------------------------- #
# HTTP 传输层（固定官方主机 + 端点白名单）
# --------------------------------------------------------------------------- #
_ALLOWED_HOSTS = frozenset({urlparse(SCM_BASE).hostname, urlparse(WECOM_BASE).hostname})
_SCM_GET_PATHS = frozenset({LOGIN_PAGE_PATH, CAPTCHA_PATH, INDEX_JAVA_PATH})
_SCM_POST_PATHS = frozenset({POST_LOGIN_PATH, POST_LOGIN_WX_PATH, PROVIDER_INFO_PATH})
_WECOM_GET_PATHS = frozenset({QR_IMAGE_PATH})
_WECOM_POST_PATHS = frozenset({QR_KEY_PATH, QR_STATUS_PATH})


class Transport:
    """登录专用 HTTP 传输层：固定官方主机、端点白名单、不走系统代理。"""

    def __init__(self) -> None:
        self.scm_base = SCM_BASE
        self.wecom_base = WECOM_BASE
        self.timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)
        ca_bundle = os.environ.get("SCM_CA_BUNDLE", "").strip()
        if ca_bundle:
            ca_path = Path(ca_bundle).expanduser().resolve()
            if not ca_path.is_file():
                raise ScmError(
                    "TLS_CA_NOT_FOUND", "SCM_CA_BUNDLE 指向的证书文件不存在。",
                    details={"path": str(ca_path)},
                )
            self.verify: bool | str = str(ca_path)
        else:
            self.verify = True
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update({"User-Agent": _USER_AGENT, "Accept-Language": "zh-CN,zh;q=0.9"})

    def close(self) -> None:
        self.session.close()

    def scm_get(self, path: str, *, params: Any = None, accept: str = "*/*") -> Response:
        if path not in _SCM_GET_PATHS:
            raise ScmError("ENDPOINT_NOT_ALLOWED", "SCM 请求端点不在白名单中。")
        headers: dict[str, str] = {"Accept": accept, "Referer": f"{SCM_BASE}{LOGIN_PAGE_PATH}"}
        if path == INDEX_JAVA_PATH:
            headers.update(
                {
                    "Accept": "application/json, text/plain, */*",
                    "Referer": f"{SCM_BASE}/web-scm-admin/web/index.html",
                    "X-Requested-With": "XMLHttpRequest",
                }
            )
        return self._request("GET", self.scm_base, path, params=params, headers=headers)

    def scm_post(self, path: str, *, form: dict[str, str] | None = None, json_body: Any = None) -> Response:
        if path not in _SCM_POST_PATHS:
            raise ScmError("ENDPOINT_NOT_ALLOWED", "SCM 请求端点不在白名单中。")
        if json_body is not None:
            return self._request(
                "POST", self.scm_base, path, json=json_body,
                headers={"Content-Type": "application/json;charset=UTF-8"},
            )
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{SCM_BASE}{LOGIN_PAGE_PATH}",
            "Origin": SCM_BASE,
        }
        return self._request("POST", self.scm_base, path, data=form, headers=headers)

    def wecom_get(self, path: str, *, params: Any = None,
                  timeout: tuple[float, float] | None = None) -> Response:
        if path not in _WECOM_GET_PATHS:
            raise ScmError("ENDPOINT_NOT_ALLOWED", "企微请求端点不在白名单中。")
        return self._request("GET", self.wecom_base, path, params=params, timeout=timeout)

    def wecom_post(self, path: str, *, params: Any = None, json_body: Any,
                   timeout: tuple[float, float] | None = None) -> Response:
        if path not in _WECOM_POST_PATHS:
            raise ScmError("ENDPOINT_NOT_ALLOWED", "企微请求端点不在白名单中。")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Origin": WECOM_BASE,
            "Referer": f"{WECOM_BASE}/",
        }
        return self._request("POST", self.wecom_base, path, params=params, json=json_body,
                             headers=headers, timeout=timeout)

    def _request(
        self,
        method: str,
        base: str,
        path: str,
        *,
        json: Any = None,
        data: Any = None,
        params: Any = None,
        headers: dict[str, str] | None = None,
        timeout: tuple[float, float] | None = None,
    ) -> Response:
        parsed = urlparse(base)
        if parsed.hostname not in _ALLOWED_HOSTS:
            raise ScmError("ENDPOINT_NOT_ALLOWED", "请求主机不在白名单中。")
        headers = dict(headers or {})
        url = f"{base}{path}"
        try:
            response = self.session.request(
                method, url, headers=headers, json=json, data=data, params=params,
                timeout=timeout or self.timeout, verify=self.verify, allow_redirects=False,
            )
        except requests.exceptions.SSLError as exc:
            raise ScmError("TLS_VALIDATION_FAILED", "HTTPS 证书验证失败，请检查公司 CA 配置。") from exc
        except requests.exceptions.Timeout as exc:
            raise ScmError("UPSTREAM_TIMEOUT", "SCM 或企微请求超时。", retryable=True) from exc
        except requests.exceptions.ConnectionError as exc:
            raise ScmError(
                "SCM_NETWORK_UNREACHABLE",
                "无法连接 SCM 或企微服务，请确认公司内网、VPN 和 DNS。",
                retryable=True,
            ) from exc
        except requests.RequestException as exc:
            raise ScmError("NETWORK_ERROR", "网络请求失败。", retryable=True) from exc

        expected_host = parsed.hostname
        final_host = urlparse(response.url).hostname
        if final_host != expected_host or any(
            urlparse(item.url).hostname != expected_host for item in response.history
        ):
            raise ScmError("REDIRECT_NOT_ALLOWED", "请求离开了固定的官方主机。")
        if 300 <= response.status_code < 400:
            location = response.headers.get("Location") or ""
            redirect_host = urlparse(requests.compat.urljoin(response.url, location)).hostname
            if redirect_host != expected_host:
                raise ScmError("REDIRECT_NOT_ALLOWED", "官方接口返回了未允许的重定向。")
            raise ScmError("AUTH_EXPIRED", "SCM 登录已过期，请重新登录。")
        if response.status_code == 401:
            raise ScmError("AUTH_EXPIRED", "SCM 登录已过期，请重新登录。")
        if response.status_code == 403:
            raise ScmError("AUTH_FORBIDDEN", "当前账号无权执行该请求。")
        if response.status_code == 429:
            raise ScmError("RATE_LIMITED", "请求过于频繁。", retryable=True)
        if response.status_code in (502, 503, 504):
            raise ScmError(
                "UPSTREAM_UNAVAILABLE", f"上游暂时不可用（HTTP {response.status_code}）。", retryable=True
            )
        if response.status_code >= 400:
            raise ScmError(
                "HTTP_ERROR", f"请求失败（HTTP {response.status_code}）。",
                details={"status": response.status_code},
            )
        return response

    @staticmethod
    def json(response: Response) -> dict[str, Any]:
        try:
            data = response.json()
        except ValueError as exc:
            raise ScmError("RESPONSE_INVALID_JSON", "接口返回了无效 JSON。") from exc
        if not isinstance(data, dict):
            raise ScmError("RESPONSE_SCHEMA_CHANGED", "接口返回结构不是 JSON 对象。")
        return data


# --------------------------------------------------------------------------- #
# 本地凭证存储（单文件，全部明文 JSON）
# --------------------------------------------------------------------------- #
def _data_home() -> Path:
    override = os.environ.get("SCM_OPERATIONS_HOME", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "scm-operations-query"
    xdg = os.environ.get("XDG_DATA_HOME", "").strip()
    return (Path(xdg).expanduser() if xdg else Path.home() / ".local" / "share") / "scm-operations-query"


_WRITE_LOCK = threading.Lock()          # 进程内串行化
_LOCK_STALE_SECONDS = 30.0              # 崩溃遗留锁的清理阈值
_LOCK_TIMEOUT_SECONDS = 10.0


def _acquire_file_lock(lock_path: Path) -> int:
    """跨进程文件锁（O_CREAT|O_EXCL）；超时抛 CREDENTIAL_BUSY。"""
    start = time.monotonic()
    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            try:
                os.write(fd, str(os.getpid()).encode("ascii"))
            except OSError:
                pass
            return fd
        except FileExistsError:
            try:
                if time.time() - lock_path.stat().st_mtime > _LOCK_STALE_SECONDS:
                    lock_path.unlink(missing_ok=True)
                    continue
            except OSError:
                pass
            if time.monotonic() - start > _LOCK_TIMEOUT_SECONDS:
                raise ScmError("CREDENTIAL_BUSY", "凭证文件写入繁忙，请稍后重试。")
            time.sleep(0.02)


def _release_file_lock(fd: int, lock_path: Path) -> None:
    try:
        os.close(fd)
    except OSError:
        pass
    try:
        lock_path.unlink(missing_ok=True)
    except OSError:
        pass


def _write_json_once(path: Path, data: dict[str, Any]) -> None:
    """单文件原子写（调用方须已持锁）：临时文件 + fsync + replace（Windows 冲突重试）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.chmod(tmp_name, 0o600)
        except OSError:
            pass
        last_exc: Exception | None = None
        for attempt in range(20):
            try:
                os.replace(tmp_name, path)
                return
            except PermissionError as exc:      # Windows: 目标被短暂占用
                last_exc = exc
                time.sleep(0.01 * (attempt + 1))
        if last_exc:
            raise last_exc
    finally:
        if os.path.exists(tmp_name):
            try:
                os.unlink(tmp_name)
            except OSError:
                pass





__all__ = [
    "get_credential",
    "verify_credential",
    "relogin",
    "is_authenticated",
    "run_login_dialog",
    "LoginFlow",
    "build_credential",
    "login_and_store",
    "load_credential",
    "save_credential",
    "ScmError",
    "data_home",
    "check_credential",
]


# --------------------------------------------------------------------------- #
# 阶段与文案（窗口/回调用）
# --------------------------------------------------------------------------- #
STAGE_SCANNED = "scanned"
STAGE_AUTHENTICATING = "authenticating"

STATUS_CONFIRM = "请确认登录！"
STATUS_LOGGING_IN = "登录中......"

_FONT_FAMILY = "Microsoft YaHei UI"

# 这些错误说明「本地凭证不可用」，才允许弹窗重新登录。
_RECOVERABLE_CODES = frozenset({"AUTH_REQUIRED", "AUTH_EXPIRED", "CREDENTIALS_INVALID"})
# 扫码成功但换取凭证失败时，可靠「重新加载二维码」自救的错误。
_RELOADABLE_AFTER_SCAN = frozenset({"AUTH_EXPIRED", "AUTH_TOKEN_MISSING", "REDIRECT_NOT_ALLOWED"})

_RELOAD = object()  # _poll 的返回值哨兵：表示需要重新加载二维码


def md5_hex(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _public_params(token: str, *, ex: str = "", ua: str = _USER_AGENT) -> dict[str, str]:
    """接口公共参数六件套（登录链路统一构造，避免多处重复）。"""
    return {
        "token": str(token),
        "platform": "scm-admin",
        "version": "1.0.3",
        "ua": ua,
        "ex": ex,
        "lastBuildTime": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def _index_java_params(token: str) -> dict[str, str]:
    """indexJava 的 URL 参数（公共参数 + 时间戳）。"""
    params = _public_params(token)
    params["_t"] = str(int(time.time() * 1000))
    return params


def build_credential(
    credentials: dict[str, Any],
    *,
    source: str,
    reused: bool,
) -> dict[str, Any]:
    """把凭证本体打包成「完整凭证」，任何应用都能直接消费。"""
    token = str(credentials.get("token") or "")
    cookies = dict(credentials.get("cookies") or {})
    cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items() if k and v)
    now_iso = datetime.now().isoformat(timespec="seconds")
    expire_iso = (datetime.now() + timedelta(hours=CREDENTIAL_EXPIRE_HOURS)).isoformat(timespec="seconds")
    result: dict[str, Any] = {
        "ok": True,
        "authenticated": True,
        "source": source,
        "reused": reused,
        "token": token,
        "cookies": cookies,
        "headers": {"Cookie": cookie_str},
        "account": str(credentials.get("account") or ""),
        "provider_id": credentials.get("provider_id"),
        "provider_id_m": credentials.get("provider_id_m"),
        "provider_name": (credentials.get("provider_info") or {}).get("provider_name", ""),
        "token_sy": credentials.get("token_sy"),
        "token_hp": credentials.get("token_hp"),
        "cms_token": credentials.get("cms_token"),
        "provider_info": credentials.get("provider_info") or {},
        "extra_info": credentials.get("extra_info") or {},
        "login_time": credentials.get("login_time") or now_iso,
        "expire_time": credentials.get("expire_time") or expire_iso,
        "createdAt": int(credentials.get("createdAt") or 0),
        "validatedAt": int(credentials.get("validatedAt") or 0),
        "scmBase": SCM_BASE,
        "wecomBase": WECOM_BASE,
        "credentialPath": str(credentials.get("credentialPath") or ""),
    }
    return result


def _validate_token_remote(transport: Transport, credential: dict[str, Any]) -> None:
    """远端校验一份 SCM 凭证（POST getProviderLoginInfo，成功码 '40001'）。

    校验失败统一归 AUTH_EXPIRED（含 token 过期/无效类拒绝）。
    """
    token = str(credential.get("token") or "")
    body = transport.json(
        transport.scm_post(
            PROVIDER_INFO_PATH,
            json_body=_public_params(token, ua="Mozilla/5.0"),
        )
    )
    code = str(body.get("code") or "")
    if code != "40001":
        raise ScmError(
            "AUTH_EXPIRED",
            f"SCM 凭证验证失败，请重新登录（code={code}，{body.get('message') or 'unknown'}）",
        )


def _probe_business(credential: dict[str, Any]) -> tuple[str, str]:
    """业务探针：用已存 Cookie 调只读接口，验证 token 与 cmsToken 是否同时有效。

    返回 (state, detail)：
      ok            业务接口返回 40001
      auth_invalid  40000/40020（token 或 cmsToken 失效）
      unavailable   网络异常 / 服务不可用 / 其他业务码（不据此判定凭证失效）
    """
    token = str(credential.get("token") or "")
    provider_id_m = str(credential.get("provider_id_m") or "")
    cookies = {k: v for k, v in (credential.get("cookies") or {}).items() if k and v}
    body = _public_params(token, ua="Mozilla/5.0")
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "Referer": f"{SCM_BASE}/web-scm-admin/web/index.html",
        "provideridm": provider_id_m,
    }
    ca_bundle = os.environ.get("SCM_CA_BUNDLE", "").strip()
    verify: bool | str = str(Path(ca_bundle).expanduser().resolve()) if ca_bundle else True
    try:
        resp = requests.post(
            f"{SCM_BASE}{BUSINESS_PROBE_PATH}",
            json=body,
            cookies=cookies,
            headers=headers,
            timeout=(CONNECT_TIMEOUT, 30),
            verify=verify,
        )
        data = resp.json()
    except Exception:  # noqa: BLE001
        return "unavailable", "network"
    if not isinstance(data, dict):
        return "unavailable", "schema"
    code = str(data.get("code") or "")
    if code == "40001":
        return "ok", "40001"
    if code in {"40000", "40020"}:
        return "auth_invalid", code
    return "unavailable", code or "unknown"


def data_home() -> Path:
    """公开门面：凭证目录（等价旧 _data_home，供 credential.cred_dir 使用）。"""
    return _data_home()


def check_credential(
    credentials: dict[str, Any] | None,
    *,
    validate_remote: bool,
) -> tuple[str | None, ScmError | None]:
    """公开门面：校验一份凭证（等价旧 _check_credential，供 credential.check 使用）。"""
    return _check_credential(credentials, validate_remote=validate_remote)


def _check_credential(
    credentials: dict[str, Any] | None,
    *,
    validate_remote: bool,
) -> tuple[str | None, ScmError | None]:
    """检查一份凭证是否可用；返回 (reason, error)，两者皆 None 表示有效。"""
    if not credentials or not credentials.get("token"):
        return "missing", ScmError("AUTH_REQUIRED", "尚未登录 SCM，请先执行登录。")
    if credentials.get("expire_time"):
        try:
            if datetime.fromisoformat(str(credentials["expire_time"])) < datetime.now():
                return "expired", ScmError("AUTH_EXPIRED", "SCM 登录已过期（本地 24h 口径），请重新登录。")
        except ValueError:
            pass
    if validate_remote:
        transport = Transport()
        try:
            _validate_token_remote(transport, credentials)
        except ScmError as exc:
            if exc.code in _RECOVERABLE_CODES:
                reason = "expired" if exc.code == "AUTH_EXPIRED" else "invalid"
            else:
                reason = "not_validated"
            return reason, exc
        finally:
            transport.close()
        # token 有效后再验 cmsToken（业务接口对 cmsToken 敏感，缺失会 40020）
        state, detail = _probe_business(credentials)
        if state == "auth_invalid":
            return "expired", ScmError(
                "AUTH_EXPIRED",
                f"业务会话已失效（code={detail}，通常为 cmsToken 过期），请重新登录。",
            )
    return None, None


# --------------------------------------------------------------------------- #
# 登录流程内核（分步驱动：登录窗表单交互逐步调用）
# --------------------------------------------------------------------------- #
class LoginFlow:
    """SCM 登录完整流程。步骤方法由登录窗逐步驱动。

    ⚠ 内部组件：仅供本文件的图形弹窗使用；
    外部 / Agent 取凭证请用门面（relogin / get_credential）——禁止自行组装本流程 ✗。

    回调（均可省略）：on_stage / on_qr / on_notice / is_aborted。
    """

    def __init__(
        self,
        *,
        account: str = "",
        password: str = "",
        on_stage: Callable[[str, str], None] | None = None,
        on_qr: Callable[[bytes], None] | None = None,
        on_notice: Callable[[str], None] | None = None,
        is_aborted: Callable[[], bool] | None = None,
        max_auto_reload: int = 3,
    ) -> None:
        self.account = str(account or "")
        self.password = str(password or "")
        self.on_stage = on_stage or (lambda *_: None)
        self.on_qr = on_qr or (lambda _: None)
        self.on_notice = on_notice or (lambda _: None)
        self.is_aborted = is_aborted or (lambda: False)
        self.max_auto_reload = max(0, int(max_auto_reload))
        self._open_data_sid: str | None = None
        self._qr_web_key = ""
        self.transport = Transport()

    def close(self) -> None:
        self.transport.close()

    # --------------------------- 步骤 0：会话初始化 --------------------------- #
    def begin(self) -> None:
        """建立 SCM 会话（PHPSESSID）。"""
        self.transport.scm_get(LOGIN_PAGE_PATH)

    # --------------------------- 步骤 1：验证码 --------------------------- #
    def captcha_image(self) -> str:
        """取验证码图（DataURI）。失败抛 CAPTCHA_FAILED。"""
        captcha = self.transport.scm_get(CAPTCHA_PATH, params={"_": int(time.time() * 1000)}, accept="image/*")
        magic = captcha.content[:4].hex()
        if magic[:8] == "89504e47":
            mime = "image/png"
        elif magic[:6] == "ffd8ff":
            mime = "image/jpeg"
        else:
            raise ScmError("CAPTCHA_FAILED", "验证码返回了非图片内容。")
        return f"data:{mime};base64,{base64.b64encode(captcha.content).decode('ascii')}"

    # --------------------------- 步骤 2：账密提交 --------------------------- #
    def submit_login(self, captcha_code: str) -> tuple[str, dict[str, str]]:
        """提交账密+验证码。返回 ("direct"|"scan_required", cookies)。

        抛出：CAPTCHA_FAILED（验证码错误，可换码重试）/ LOGIN_FAILED（账密错误，需改输入）。
        """
        if not self.account or not self.password:
            raise ScmError("CREDENTIALS_INVALID", "账号与密码不能为空。")
        body = self.transport.json(
            self.transport.scm_post(
                POST_LOGIN_PATH,
                form={
                    "account": self.account,
                    "password": md5_hex(self.password),
                    "captcha": str(captcha_code or ""),
                    "remember": "1",
                },
            )
        )
        if body.get("status") != 1:
            info = str(body.get("info") or body.get("msg") or "")
            if "验证码" in info:
                raise ScmError("CAPTCHA_FAILED", f"验证码错误：{info or '请重试'}")
            raise ScmError("LOGIN_FAILED", f"账号密码验证失败：{info or '未知原因'}")
        cookies = {k: v for k, v in self.transport.session.cookies.get_dict().items() if k and v}
        if "ysbang_adminToken" in cookies:
            return "direct", cookies
        return "scan_required", cookies   # info=「请扫码登录」：该账号强制企微二次验证

    # --------------------------- 步骤 3：企微二次验证 --------------------------- #
    def qr_create(self) -> tuple[str, bytes]:
        response = self.transport.wecom_post(
            QR_KEY_PATH,
            params={"lang": "zh_CN", "ajax": "1", "f": "json", "random": int(time.time()) % 1000000},
            json_body={
                "login_type": "CorpApp",
                "appid": WECOM_APP_ID,
                "agentid": WECOM_AGENT_ID,
                "redirect_uri": WECOM_REDIRECT_URI,
                "state": self.account,
                "redirect_type": "callback",
                "version": WECOM_VERSION,
                "refresh_key": True,
            },
            timeout=(5, 15),
        )
        body = Transport.json(response)
        data = body.get("data") if isinstance(body.get("data"), dict) else {}
        web_key = str(data.get("web_key") or "")
        if not web_key:
            raise ScmError("QR_CREATE_FAILED", f"获取企微二维码失败：{body.get('errmsg') or 'unknown'}")
        self._qr_web_key = web_key
        image = self.transport.wecom_get(QR_IMAGE_PATH, params={"key": web_key}, timeout=(5, 15))
        png = image.content
        if not png or len(png) < 100:
            raise ScmError("QR_CREATE_FAILED", "二维码图片为空。")
        return web_key, png

    def qr_poll(self) -> Any:
        """轮询扫码状态：返回 auth_code（已确认）或 _RELOAD（换码）。"""
        deadline = time.monotonic() + QR_TIMEOUT_SECONDS
        last_status = "QRCODE_SCAN_NEVER"
        confirmed = False
        confirm_deadline = 0.0

        while time.monotonic() < deadline:
            if self.is_aborted():
                raise self._abort_error()
            try:
                response = self.transport.wecom_post(
                    QR_STATUS_PATH,
                    params={"lang": "zh_CN", "ajax": "1", "f": "json", "random": int(time.time()) % 1000000},
                    json_body={
                        "webKey": self._qr_web_key,
                        "lastStatus": last_status,
                        "openDataSid": self._open_data_sid,
                    },
                    timeout=(3, 6),          # 短超时：保证「返回」能尽快中断轮询
                )
                body = Transport.json(response)
                if self.is_aborted():        # 请求返回后立即响应「返回」
                    raise self._abort_error()
            except ScmError as exc:
                if not exc.retryable:
                    raise
                self._sleep_or_abort(SCAN_POLL_INTERVAL)
                continue

            payload = body.get("data") if isinstance(body.get("data"), dict) else {}
            status = str(body.get("status") or payload.get("status") or "")
            auth_code = str(body.get("auth_code") or payload.get("auth_code") or "")
            open_data_sid = body.get("openDataSid") or payload.get("openDataSid")
            if open_data_sid:
                self._open_data_sid = open_data_sid

            if status == "QRCODE_SCAN_ING" or (status == "QRCODE_SCAN_SUCC" and not auth_code):
                if not confirmed:
                    confirmed = True
                    confirm_deadline = time.monotonic() + CONFIRM_WAIT_SECONDS
                    self.on_stage(STAGE_SCANNED, STATUS_CONFIRM)
                elif time.monotonic() > confirm_deadline:
                    return _RELOAD
                self._sleep_or_abort(SCAN_POLL_INTERVAL)
                continue

            if status == "QRCODE_SCAN_SUCC" and auth_code:
                if not confirmed:
                    self.on_stage(STAGE_SCANNED, STATUS_CONFIRM)
                return auth_code

            if status in {"QRCODE_SCAN_ERR", "QRCODE_SCAN_TIMEOUT", "QRCODE_SCAN_CANCEL"}:
                return _RELOAD
            if confirmed and status:
                return _RELOAD
            if status:
                last_status = status
            self._sleep_or_abort(SCAN_POLL_INTERVAL)

        return _RELOAD

    def qr_finish(self, auth_code: str) -> dict[str, str]:
        """auth_code → postLoginWx → 取得 adminToken 会话。"""
        response = self.transport.scm_post(
            POST_LOGIN_WX_PATH,
            form={"code": auth_code, "account": "", "localAccount": self.account},
        )
        body = Transport.json(response)
        if body.get("status") != 1:
            raise ScmError("LOGIN_FAILED", f"扫码登录未完成：{body.get('info') or 'unknown'}")
        cookies = {k: v for k, v in self.transport.session.cookies.get_dict().items() if k and v}
        if "ysbang_adminToken" not in cookies:
            raise ScmError("AUTH_TOKEN_MISSING", "扫码成功，但会话中未取得登录 Token。")
        return cookies

    # --------------------------- 步骤 4：凭证装配 --------------------------- #
    def assemble(self, cookies: dict[str, str]) -> dict[str, Any]:
        """token + getProviderLoginInfo + indexJava → 完整凭证（build_credential 打包）。"""
        token = cookies.get("ysbang_adminToken") or ""
        credentials: dict[str, Any] = {
            "account": self.account,
            "token": token,
            "cookies": cookies,
            "login_time": datetime.now().isoformat(timespec="seconds"),
            "expire_time": (
                datetime.now() + timedelta(hours=CREDENTIAL_EXPIRE_HOURS)
            ).isoformat(timespec="seconds"),
            "createdAt": int(time.time()),
        }
        info_body = self.transport.json(
            self.transport.scm_post(
                PROVIDER_INFO_PATH,
                json_body=_public_params(token, ua="Mozilla/5.0"),
            )
        )
        if str(info_body.get("code") or "") == "40001" and isinstance(info_body.get("data"), dict):
            data = info_body["data"]
            provider_id = data.get("providerId") or data.get("provider_id") or ""
            credentials["provider_id"] = provider_id
            credentials["provider_id_m"] = md5_hex(str(provider_id)) if provider_id else ""
            credentials["provider_info"] = {
                "provider_id": provider_id,
                "provider_name": data.get("providerName") or "",
                "provider_short_name": data.get("providerShortName") or "",
                "username": data.get("userName") or data.get("username") or "",
                "user_id": data.get("userId") or "",
                "role_name": data.get("roleName") or "",
                "mobile": data.get("mobile") or "",
                "email": data.get("email") or "",
            }
        index_body = self.transport.json(
            self.transport.scm_get(INDEX_JAVA_PATH, params=_index_java_params(token))
        )
        if (index_body.get("code") in (40001, "40001")) and isinstance(index_body.get("data"), dict):
            data = index_body["data"]
            credentials["token_sy"] = data.get("tokenSY")
            credentials["token_hp"] = data.get("tokenHP")
            credentials["cms_token"] = data.get("cmsToken")
            # 关键：cmsToken 是 /scm-goods/ 等 Java 服务的会话令牌，必须并入 Cookie
            if data.get("cmsToken"):
                credentials["cookies"] = dict(
                    credentials.get("cookies") or {},
                    cmsToken=data["cmsToken"],
                    **({"cmsUserName": data["cmsUserName"]} if data.get("cmsUserName") else {}),
                )
            credentials["extra_info"] = {
                "uid_hp": data.get("uidHP"),
                "account_id": data.get("accountId"),
                "nick_name": data.get("nickName"),
                "company_user_id": data.get("companyUserId"),
                "company_id_sy": data.get("companyIdSY"),
                "session_id_hp": data.get("sessionIdHP"),
                "hp_websocket_url": data.get("hpWebSocketURL"),
                "sy_websocket_url": data.get("syWebSocketURL"),
            }
            if not credentials.get("provider_id") and data.get("providerIdHP"):
                credentials["provider_id"] = data.get("providerIdHP")
                credentials["provider_id_m"] = md5_hex(str(data.get("providerIdHP")))
        if not (credentials.get("token") and credentials.get("provider_id_m")):
            raise ScmError("CREDENTIALS_INVALID", "凭证装配不完整（缺 token 或 providerIdM）。")
        return build_credential(credentials, source="login", reused=False)

    # --------------------------- 错误收口 --------------------------- #
    def _sleep_or_abort(self, seconds: float) -> bool:
        deadline = time.monotonic() + max(0.0, float(seconds))
        while time.monotonic() < deadline:
            if self.is_aborted():
                raise self._abort_error()
            time.sleep(min(0.1, deadline - time.monotonic()))
        return True

    def _abort_error(self) -> ScmError:
        return ScmError("LOGIN_CANCELLED", "登录已取消。")

# --------------------------------------------------------------------------- #
# 功能二：读取本地凭证并验证是否有效（绝不弹窗）
# --------------------------------------------------------------------------- #
CREDENTIAL_FILENAME = "credential.json"        # 当前生效凭证（所有消费方读取此文件）
ACCOUNTS_DIRNAME = "accounts"                  # 按账号归档：accounts/credential_<account>.json


def _credential_file() -> Path:
    return _data_home() / CREDENTIAL_FILENAME


def _safe_account(account: str) -> str:
    """账号 → 安全文件名（仅保留字母数字与 ._-）。"""
    return "".join(c if (c.isalnum() or c in "._-") else "_" for c in str(account)) or "unknown"


def _account_file(account: str) -> Path:
    return _data_home() / ACCOUNTS_DIRNAME / f"credential_{_safe_account(account)}.json"


def load_credential(account: str | None = None) -> dict[str, Any]:
    """读取本地凭证；不存在或损坏返回 {}（绝不抛异常）。

    account 为空 → 读当前生效的 credential.json；
    指定 account → 读 accounts/credential_<account>.json 归档。
    """
    path = _account_file(account) if account else _credential_file()
    try:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_credential(credential: dict[str, Any]) -> str:
    """原子写凭证：同时写「当前生效」credential.json 与「按账号归档」accounts/credential_<account>.json。

    两处写入在**同一把文件锁**内完成，保证并发时「当前生效」与「归档」一致。
    """
    _data_home().mkdir(parents=True, exist_ok=True)
    active = _credential_file()
    lock_path = active.with_name(active.name + ".lock")
    account = str(credential.get("account") or "").strip()
    payload = {**credential, "credentialPath": str(active)}
    with _WRITE_LOCK:
        fd = _acquire_file_lock(lock_path)
        try:
            _write_json_once(active, payload)
            if account:
                _write_json_once(_account_file(account), payload)
        finally:
            _release_file_lock(fd, lock_path)
    return str(active)


def verify_credential(
    *,
    validate_remote: bool = True,
    raise_on_invalid: bool = False,
) -> dict[str, Any]:
    """验证本地凭证文件里的凭证。**绝不会弹窗。**

    reason 取值：missing / expired / invalid / not_validated（网络类未通过，不代表凭证失效）。
    """
    cred_path = _credential_file()
    credential = load_credential()

    def _invalid(reason: str, exc: ScmError) -> dict[str, Any]:
        if raise_on_invalid:
            raise exc
        return {
            "ok": False,
            "authenticated": False,
            "source": "local",
            "reused": True,
            "reason": reason,
            "error": exc.to_dict(),
            "credentialPath": str(cred_path),
        }

    reason, error = _check_credential(credential, validate_remote=validate_remote)
    if reason:
        return _invalid(reason, error or ScmError("AUTH_REQUIRED", "本地凭证不可用。"))

    credential["validatedAt"] = int(time.time())
    save_credential(credential)
    result = build_credential(credential, source="local", reused=True)
    result["credentialPath"] = str(cred_path)
    return result


def is_authenticated(validate_remote: bool = True) -> bool:
    """快捷判断：本地凭证当前是否可用（绝不会弹窗、绝不会抛异常）。"""
    return bool(verify_credential(validate_remote=validate_remote)["authenticated"])


# --------------------------------------------------------------------------- #
# 功能一：重新登录获取凭证 + 组合入口
# --------------------------------------------------------------------------- #
def _resolve_credentials_input(
    account: str | None, password: str | None, *, interactive: bool
) -> tuple[str, str]:
    """账密解析顺序：参数 > 环境变量（交互模式缺省 → 登录窗表单内填写）。"""
    account = account or os.environ.get("SCM_ACCOUNT", "").strip() or ""
    password = password or os.environ.get("SCM_PASSWORD", "") or ""
    if not interactive and (not account or not password):
        missing = "账号" if not account else "密码"
        raise ScmError(
            "AUTH_REQUIRED",
            f"缺少 SCM {missing}（非交互模式）。请用 --account/--password 或 SCM_ACCOUNT/SCM_PASSWORD 提供。",
        )
    return account, password


def login_and_store(
    *,
    account: str | None = None,
    password: str | None = None,
    interactive: bool = True,
    parent: Any = None,
) -> dict[str, Any]:
    """登录（账密缺省时在登录窗表单内填写）→ 写「当前生效」并按账号归档 → 返回完整凭证。"""
    account, password = _resolve_credentials_input(account, password, interactive=interactive)
    credential = run_login_dialog(account=account, password=password, parent=parent)
    credential["credentialPath"] = save_credential(credential)
    return credential


def get_credential(
    *,
    force_relogin: bool = True,
    validate_remote: bool = True,
    interactive: bool = True,
    account: str | None = None,
    password: str | None = None,
    parent: Any = None,
) -> dict[str, Any]:
    """拿到一份可用凭证。

    force_relogin=True（默认）与 relogin() 等价：重新走登录流程。
    force_relogin=False：优先复用本地有效凭证，失效才登录。
    interactive=False：绝不弹窗；凭证不可用时直接抛 ScmError。
    """
    if not force_relogin:
        active = load_credential()
        active_account = str(active.get("account") or "")
        want_account = str(account or "").strip()

        # 指定账号且与当前生效账号不同 → 先尝试切换到该账号的归档凭证
        if want_account and active_account != want_account:
            archived = load_credential(want_account)
            reason, _error = (
                _check_credential(archived, validate_remote=validate_remote)
                if archived else ("missing", None)
            )
            if not reason:
                archived["validatedAt"] = int(time.time())
                save_credential(archived)          # 激活为当前生效账号
                result = build_credential(archived, source="archive", reused=True)
                result["credentialPath"] = str(_credential_file())
                return result
            force_relogin = True                   # 归档不可用 → 强制登录该账号
        else:
            result = verify_credential(validate_remote=validate_remote)
            if result["authenticated"]:
                return result
            error = result.get("error") or {}
            code = str(error.get("code") or "")
            message = str(error.get("message") or "本地凭证不可用。")
            if not interactive or code not in _RECOVERABLE_CODES:
                raise ScmError(code or "AUTH_REQUIRED", message)

    if not interactive:
        hint = "指定账号无可用归档凭证" if account else "本地没有可用凭证"
        raise ScmError(
            "AUTH_REQUIRED",
            f"{hint}（非交互模式，绝不弹窗）。需要新登录时请运行："
            f"python {_SELF} --reuse --account <账号>（原生登录窗）。",
        )
    return login_and_store(account=account, password=password, interactive=interactive, parent=parent)


def relogin(
    *,
    account: str | None = None,
    password: str | None = None,
    interactive: bool = True,
    parent: Any = None,
) -> dict[str, Any]:
    """功能一：无论本地是否已有凭证，都重新登录，返回全新凭证（source="login"）。"""
    return login_and_store(
        account=account, password=password, interactive=interactive, parent=parent
    )


# --------------------------------------------------------------------------- #
# 登录窗口（tkinter；表单视图「账号/密码/验证码」+ 二维码视图，风格对齐站点登录页）
# --------------------------------------------------------------------------- #
QR_TTL_SECONDS = 300


def run_login_dialog(
    *,
    account: str = "",
    password: str = "",
    parent: Any = None,
) -> dict[str, Any]:
    """登录窗（tkinter、置顶、同步）。

    表单视图：账号 / 密码 / 验证码（人工看图输入；点图换一张）→ 提交后按账号策略分流：
    免扫码直接取得凭证落盘；需二次验证自动切换二维码视图（下方「返回」可回表单）。
    验证码/账密错误在表单内红字提示。关窗 → LOGIN_CANCELLED。"""
    import queue as _queue
    import threading as _th
    import tkinter as tk
    import tkinter.ttk as ttk

    root = tk.Tk()
    root.title("SCM 登录")
    root.attributes("-topmost", True)
    root.resizable(False, False)
    root.configure(bg="#FFFFFF")
    FONT = (_FONT_FAMILY, 10)
    ACCENT = "#1E6FFF"

    # ttk 输入框样式：白底 + 无边框（灰色边框由外层 holder 环绘制）+ 左内边距 6px；聚焦无颜色反馈
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(
        "Gray.TEntry",
        fieldbackground="#FFFFFF",
        background="#FFFFFF",
        foreground="#333333",
        bordercolor="#FFFFFF",
        lightcolor="#FFFFFF",
        darkcolor="#FFFFFF",
        insertcolor="#333333",
        padding=(6, 3),
    )
    style.configure(
        "GrayEye.TEntry",
        fieldbackground="#FFFFFF",
        background="#FFFFFF",
        foreground="#333333",
        bordercolor="#FFFFFF",
        lightcolor="#FFFFFF",
        darkcolor="#FFFFFF",
        insertcolor="#333333",
        padding=(6, 3, 26, 3),  # 右侧预留 26px 给小眼睛图标
    )

    # ---------------- 表单视图 ----------------
    form = tk.Frame(root, bg="#FFFFFF")
    form.pack(padx=20, pady=(14, 12), fill="both", expand=True)
    form.columnconfigure(0, weight=1)
    ENTRY_FONT = (_FONT_FAMILY, 11)
    ENTRY_IPADY = 5
    ENTRY_PADY = (1, 5)

    def _entry(parent, show: str | None = None, eye: bool = False):
        holder = tk.Frame(
            parent, bg="#FFFFFF", highlightthickness=1,
            highlightbackground="#D9D9D9", highlightcolor="#D9D9D9",
        )
        entry = ttk.Entry(holder, style="GrayEye.TEntry" if eye else "Gray.TEntry",
                          font=ENTRY_FONT)
        if show:
            entry.configure(show=show)
        entry.pack(fill="both", expand=True)
        if eye:
            # 内嵌小眼睛：统一使用 Segoe MDL2 Assets 的 RedEye 字形（E7B3，本机实测存在）；
            # 掩码态叠加斜线（与 Ant Design EyeInvisibleOutlined 同构）；点击切换明文/掩码。
            eye_state = {"visible": False}
            icon = tk.Canvas(holder, width=26, height=22, bg="#FFFFFF",
                             highlightthickness=0, cursor="hand2")

            def _draw_eye():
                icon.delete("all")
                icon.create_text(13, 11, text="\uE7B3",
                                 font=("Segoe MDL2 Assets", 13), fill="#8A8F99")
                if not eye_state["visible"]:
                    icon.create_line(6, 17, 20, 4, fill="#8A8F99", width=1.4,
                                     capstyle=tk.ROUND)

            def _toggle_eye(_event=None):
                eye_state["visible"] = not eye_state["visible"]
                entry.configure(show="" if eye_state["visible"] else show or "*")
                _draw_eye()

            icon.bind("<Button-1>", _toggle_eye)
            _draw_eye()
            icon.place(relx=1.0, x=-5, rely=0.5, anchor="e")
        holder.entry = entry
        return holder

    tk.Label(form, text="1. 账号", font=FONT, bg="#FFFFFF", fg="#333333").grid(
        row=0, column=0, sticky="w", padx=0, pady=ENTRY_PADY
    )
    ent_account = _entry(form)
    ent_account.grid(row=1, column=0, sticky="ew", ipady=ENTRY_IPADY, pady=ENTRY_PADY)
    if account:
        ent_account.entry.insert(0, account)

    tk.Label(form, text="2. 密码", font=FONT, bg="#FFFFFF", fg="#333333").grid(
        row=2, column=0, sticky="w", padx=0, pady=ENTRY_PADY
    )
    ent_password = _entry(form, show="*", eye=True)
    ent_password.grid(row=3, column=0, sticky="ew", ipady=ENTRY_IPADY, pady=ENTRY_PADY)
    if password:
        ent_password.entry.insert(0, password)

    # 验证码行：输入框 + 图片（图片高度与输入框完全一致）
    tk.Label(form, text="3. 验证码（看图输入）", font=FONT, bg="#FFFFFF", fg="#333333").grid(
        row=4, column=0, sticky="w", padx=0, pady=ENTRY_PADY
    )
    cap_row = tk.Frame(form, bg="#FFFFFF")
    cap_row.grid(row=5, column=0, sticky="w", pady=ENTRY_PADY)
    ent_captcha = _entry(cap_row)
    ent_captcha.configure(width=14)
    ent_captcha.grid(row=0, column=0, sticky="w", ipady=ENTRY_IPADY, pady=0)
    cap_box = tk.Frame(
        cap_row, bg="#F5F6F8", width=110,
        highlightthickness=1, highlightbackground="#D9D9D9",
        highlightcolor="#D9D9D9",
    )
    cap_box.pack_propagate(False)  # 容器尺寸恒定（像素），加载中/图片模式不跳变
    cap_box.grid(row=0, column=1, sticky="ns", padx=(8, 0))
    cap_label = tk.Label(cap_box, text="加载中…", bg="#F5F6F8", fg="#999999",
                         cursor="hand2")
    cap_label.place(relx=0.5, rely=0.5, anchor="center")

    def _primary_button(parent: tk.Misc, text: str) -> tk.Button:
        """主按钮套件（登录 / 返回共用）：蓝底白字、扁平无边框、禁用态白字。"""
        return tk.Button(
            parent, text=text, font=(_FONT_FAMILY, 11, "bold"),
            bg=ACCENT, fg="#FFFFFF", activebackground="#155BD4",
            activeforeground="#FFFFFF", disabledforeground="#FFFFFF",
            relief="flat", bd=0, cursor="hand2", state="disabled",
        )

    btn = _primary_button(form, "登 录")
    btn.grid(row=6, column=0, sticky="ew", ipady=4, pady=(6, 0))

    root.update_idletasks()  # 网格布局完成后：cap_box 随行高自动等于输入框高度

    # ---------------- 二维码视图（隐藏） ----------------
    qr_frame = tk.Frame(root, bg="#FFFFFF")
    canvas = tk.Canvas(qr_frame, width=300, height=300, highlightthickness=0, bg="#FFFFFF")
    canvas.pack(padx=12, pady=(6, 6))
    img_item = canvas.create_image(150, 150)
    mask = canvas.create_rectangle(0, 0, 300, 300, fill="#000000", stipple="gray50",
                                   outline="", state="hidden")
    r = int(300 * 0.25)
    cx = cy = 150
    tick_circle = canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                     fill="#00A651", outline="", state="hidden")
    lw = max(6, int(r * 0.3))
    tick_l1 = canvas.create_line(cx - r * 0.46, cy + r * 0.02, cx - r * 0.12, cy + r * 0.36,
                                 width=lw, fill="#FFFFFF", capstyle=tk.ROUND, state="hidden")
    tick_l2 = canvas.create_line(cx - r * 0.12, cy + r * 0.36, cx + r * 0.48, cy - r * 0.34,
                                 width=lw, fill="#FFFFFF", capstyle=tk.ROUND, state="hidden")
    qr_tip = tk.Label(qr_frame, text="请使用企业微信扫码", font=FONT, bg="#FFFFFF", fg="#333333")
    qr_tip.pack(padx=12, pady=(0, 8))
    btn_back = _primary_button(qr_frame, "返 回")
    btn_back.configure(state="normal")
    btn_back.pack(fill="x", padx=12, pady=(0, 12), ipady=4)

    # ---------------- 公共状态与助手 ----------------
    evt_q: _queue.Queue = _queue.Queue()
    cmd_q: _queue.Queue = _queue.Queue()
    result: dict[str, Any] = {"cred": None, "error": None}
    cancel = {"v": False}
    back = {"v": False}
    deadline = {"v": 0.0}
    scanned = {"v": False}

    def _hide_tick() -> None:
        for it in (mask, tick_circle, tick_l1, tick_l2):
            canvas.itemconfig(it, state="hidden")

    def show_form() -> None:
        """切回表单视图（扫码阶段点「返回」）。"""
        qr_frame.pack_forget()
        form.pack(padx=20, pady=(14, 12), fill="both", expand=True)

    def show_qr_view() -> None:
        _hide_tick()
        scanned["v"] = False
        qr_tip.configure(text="请使用企业微信扫码", fg="#333333", font=FONT)
        form.pack_forget()
        qr_frame.pack(padx=12, pady=(12, 12), fill="both", expand=True)

    def set_captcha(data_uri: str) -> None:
        """渲染验证码图：Pillow 精确缩放填满容器（容器固定像素，高=输入框高）；
        无 Pillow 时回退为整数倍缩放。"""
        payload = str(data_uri).split(",", 1)[-1]
        try:
            cap_w, cap_h = max(cap_box.winfo_width() - 2, 60), max(cap_box.winfo_height() - 2, 22)
            photo = None
            try:
                from PIL import Image, ImageTk
                from io import BytesIO
                im = Image.open(BytesIO(base64.b64decode(payload))).convert("RGB")
                im = im.resize((cap_w, cap_h))
                photo = ImageTk.PhotoImage(im, master=root)
            except ImportError:
                p = tk.PhotoImage(data=payload)
                s = max(1, -(-p.height() // cap_h))
                photo = p.subsample(s, s) if s > 1 else p
            cap_label.configure(text="", image=photo)
            cap_label._img = photo  # 防 GC
        except Exception:
            cap_label.configure(text="图片无法显示\n请点此换一张", image="")
    def set_qr(png: bytes) -> None:
        try:
            photo = tk.PhotoImage(data=png)
            w = max(photo.width(), photo.height())
            if w > 300:
                photo = photo.subsample(max(1, -(-w // 300)))
            d = max(photo.width(), photo.height())
            canvas.config(width=d, height=d)
            canvas.coords(img_item, d // 2, d // 2)
            canvas.coords(mask, 0, 0, d, d)
            r2 = int(d * 0.25)
            cx2 = cy2 = d // 2
            canvas.coords(tick_circle, cx2 - r2, cy2 - r2, cx2 + r2, cy2 + r2)
            lw2 = max(6, int(r2 * 0.3))
            canvas.coords(tick_l1, cx2 - r2 * 0.46, cy2 + r2 * 0.02, cx2 - r2 * 0.12, cy2 + r2 * 0.36)
            canvas.coords(tick_l2, cx2 - r2 * 0.12, cy2 + r2 * 0.36, cx2 + r2 * 0.48, cy2 - r2 * 0.34)
            canvas.itemconfig(tick_l1, width=lw2)
            canvas.itemconfig(tick_l2, width=lw2)
            canvas.itemconfig(img_item, image=photo)
            canvas._qr_img = photo  # 防 GC
            _hide_tick()
            scanned["v"] = False
            deadline["v"] = time.time() + QR_TTL_SECONDS
            qr_tip.configure(text="请使用企业微信扫码", fg="#333333", font=FONT)
        except Exception as exc:
            qr_tip.configure(text=f"二维码渲染失败：{exc}", fg="#C0392B")

    def show_scanned() -> None:
        _hide_tick()
        canvas.itemconfig(mask, state="normal")
        canvas.itemconfig(tick_circle, state="normal")
        canvas.itemconfig(tick_l1, state="normal")
        canvas.itemconfig(tick_l2, state="normal")
        scanned["v"] = True
        qr_tip.configure(text="扫码成功！请确认~", fg="#00A651", font=(_FONT_FAMILY, 10, "bold"))

    def on_submit_click() -> None:
        cmd_q.put(("submit", (
            ent_account.entry.get().strip(),
            ent_password.entry.get().strip(),
            ent_captcha.entry.get().strip(),
        )))

    def on_back_click() -> None:
        if back["v"]:
            return
        back["v"] = True
        cmd_q.put(("back", None))
        # 立即切回表单（零延迟反馈）；工作线程会在下次中断检查时真正退出扫码
        show_form()
        btn.configure(text="登 录", state="disabled")

    def wait_cmd() -> tuple[str, Any]:
        """等待用户操作（登录 / 换一张），期间响应取消。"""
        while True:
            if cancel["v"]:
                raise ScmError("LOGIN_CANCELLED", "登录已取消。")
            try:
                return cmd_q.get_nowait()
            except _queue.Empty:
                time.sleep(0.1)

    def worker() -> None:
        core = LoginFlow(
            on_qr=lambda png: evt_q.put(("qr", png)),
            on_stage=lambda stage, message: evt_q.put(("stage", (stage, message))),
            is_aborted=lambda: cancel["v"] or back["v"],
        )
        try:
            core.begin()
            while True:
                if cancel["v"]:
                    raise ScmError("LOGIN_CANCELLED", "登录已取消。")
                # ---- 表单阶段：载入验证码 → 等用户提交 ----
                evt_q.put(("captcha", core.captcha_image()))
                evt_q.put(("btn_state", "normal"))
                cmd = wait_cmd()
                if cmd[0] in ("refresh", "back"):
                    continue
                acct, pwd, cap_text = cmd[1]
                if not acct or not pwd or not cap_text:
                    continue  # 空提交：静默忽略
                core.account, core.password = acct, pwd
                evt_q.put(("btn_state", "busy"))
                try:
                    kind, cookies = core.submit_login(cap_text)
                except ScmError as exc:
                    # 界面不显示任何错误提示：仅刷新验证码并恢复按钮，静默重试
                    print(f"[scm-login] {exc.code}: {exc.message}", file=sys.stderr)
                    evt_q.put(("captcha", core.captcha_image()))
                    evt_q.put(("btn_state", "normal"))
                    continue
                if cancel["v"]:
                    raise ScmError("LOGIN_CANCELLED", "登录已取消。")

                if kind == "direct":
                    # 免扫码：直接取得凭证落盘
                    evt_q.put(("btn_state", "logging"))
                    result["cred"] = core.assemble(cookies)
                    break

                # ---- 企微二次验证：二维码视图（「返回」可回表单重走流程） ----
                evt_q.put(("show_qr", None))
                reloads = 0
                qr_done = False
                while not qr_done:
                    if cancel["v"]:
                        raise ScmError("LOGIN_CANCELLED", "登录已取消。")
                    try:
                        _, png = core.qr_create()
                        evt_q.put(("qr", png))
                        outcome = core.qr_poll()
                    except ScmError as exc:
                        # 「返回」按钮：中断扫码阶段，回表单重走账密流程（会话保持）
                        if exc.code == "LOGIN_CANCELLED" and back["v"]:
                            back["v"] = False
                            break
                        raise
                    if outcome is _RELOAD:
                        reloads += 1
                        if reloads > core.max_auto_reload:
                            raise ScmError("QR_EXPIRED", "二维码多次失效，请重试。")
                        evt_q.put(("notice", "二维码已失效，正在重新加载"))
                        continue
                    evt_q.put(("stage", (STAGE_AUTHENTICATING, STATUS_LOGGING_IN)))
                    result["cred"] = core.assemble(core.qr_finish(str(outcome)))
                    qr_done = True
                if qr_done:
                    break
                evt_q.put(("show_form", None))  # 返回表单（外层循环重载验证码）
        except BaseException as exc:  # noqa: BLE001 —— 线程内异常回传主线程
            result["error"] = exc
        finally:
            core.close()
            evt_q.put(("done", None))

    btn.configure(command=on_submit_click)
    cap_label.bind("<Button-1>", lambda _e: cmd_q.put(("refresh", None)))
    ent_captcha.entry.bind("<Return>", lambda _e: on_submit_click())
    btn_back.configure(command=on_back_click)

    def pump() -> None:
        try:
            while True:
                kind, payload = evt_q.get_nowait()
                if kind == "captcha":
                    set_captcha(payload)
                elif kind == "qr":
                    set_qr(payload)
                elif kind == "show_qr":
                    show_qr_view()
                elif kind == "show_form":
                    show_form()
                elif kind == "btn_state":
                    btn.configure(
                        text={"busy": "登录中…", "logging": "获取凭证…"}.get(str(payload), "登 录"),
                        state="disabled" if str(payload) != "normal" else "normal",
                    )
                elif kind == "notice":
                    qr_tip.configure(text=str(payload), fg="#B7791F")
                elif kind == "stage":
                    stage, message = payload
                    if stage == STAGE_SCANNED:
                        show_scanned()
                    elif stage == STAGE_AUTHENTICATING and qr_frame.winfo_ismapped():
                        qr_tip.configure(text=str(message), fg="#333333")
                elif kind == "done":
                    root.after(900, root.destroy)
                    return
        except _queue.Empty:
            pass
        if qr_frame.winfo_ismapped() and deadline["v"] and not scanned["v"]:
            left = int(deadline["v"] - time.time())
            if left > 0:
                qr_tip.configure(text=f"请使用企业微信扫码【剩余 {left}s】", fg="#333333", font=FONT)
            else:
                qr_tip.configure(text="二维码已过期，正在重新加载…", fg="#C0392B", font=FONT)
        root.after(150, pump)

    def on_close() -> None:
        cancel["v"] = True
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    pump()
    _th.Thread(target=worker, daemon=True).start()
    root.mainloop()

    if result["error"]:
        raise result["error"]
    if not result["cred"]:
        raise ScmError("LOGIN_CANCELLED", "用户取消了登录。")
    return result["cred"]

# --------------------------------------------------------------------------- #
# 命令行入口
# --------------------------------------------------------------------------- #
def check_env() -> dict[str, Any]:
    """环境自检：登录器可调用性（tkinter / 凭证仓库可写）与下一步指引；绝不弹窗。"""
    out: dict[str, Any] = {
        "ok": True,
        "python": sys.version.split()[0],
        "gui": None,
        "credentialDir": str(_data_home()),
        "fix": None,
        "next": f"python {_SELF} --reuse（登录）｜--status（只验证）",
    }
    try:
        import tkinter  # noqa: F401
        out["gui"] = "tkinter（标准库，已可用）"
    except ImportError:
        out.update(
            ok=False,
            gui=None,
            fix="当前 Python 缺少 tkinter：请重装 / 修复 Python（安装时勾选 tcl/tk 与 IDLE）",
            next="修复后重新运行 --check 或直接 --reuse 登录",
        )
    try:
        _data_home().mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        out.update(ok=False, fix="检查用户数据目录写入权限",
                   next=f"凭证仓库目录不可写：{exc!r}"[:200])
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="SCM 登录 · 药师帮商家后台（账密+人工验证码，免扫码/企微二次验证自动分流；也可只验证已有凭证）",
        epilog=(
            "给 AI · Agent 的调用契约（唯一登录入口 → 直接调用本登录器（黑盒）；禁止读源码后自写登录）：\n"
            "  1) 自检：--check\n"
            "  2) 验证：--status（退出码 0 = 已有可用凭证，直接用）\n"
            "  3) 登录：--reuse（有效复用、失效才登录；账密用 --account/--password 或环境变量或交互输入）\n"
            "  4) 取凭证：--status 输出（另：Python 门面 relogin / verify_credential /\n"
            "     get_credential / is_authenticated）\n"
            "  禁止：自写登录流程 / 自取验证码/二维码 / 自拼鉴权 / 组装内部类（LoginFlow 等）。\n"
            "  用户已指定或提供凭证 / 登录方式 → 按其走。\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--check", action="store_true", help="环境自检")
    parser.add_argument("--status", action="store_true", help="只验证已有凭证是否有效，绝不弹窗")
    parser.add_argument("--reuse", action="store_true", help="优先复用本地有效凭证，仅在失效时才登录")
    parser.add_argument("--no-remote", action="store_true", help="跳过远端校验")
    parser.add_argument(
        "--account",
        help="SCM 账号（亦可 SCM_ACCOUNT 环境变量 / 交互输入）；配合 --reuse 可切换到该账号的归档凭证",
    )
    parser.add_argument("--password", help="SCM 密码（亦可 SCM_PASSWORD 环境变量 / 交互输入）")
    configure_stdio()
    args = parser.parse_args(argv)
    try:
        if args.check:
            result = check_env()
            emit(result)
            return 0 if result.get("ok") else 1

        if args.status:
            result = verify_credential(validate_remote=not args.no_remote)
            print(
                "[scm-login] "
                + ("凭证有效" if result["authenticated"] else f"凭证无效：{result.get('reason')}"),
                file=sys.stderr,
            )
            emit(result)
            return 0 if result["authenticated"] else 1

        credential = get_credential(
            force_relogin=not args.reuse,
            validate_remote=not args.no_remote,
            interactive=True,
            account=args.account,
            password=args.password,
        )
    except ScmError as exc:
        emit({"ok": False, "authenticated": False, "error": exc.to_dict()})
        return 1
    except Exception:  # noqa: BLE001
        emit(
            {
                "ok": False,
                "authenticated": False,
                "error": ScmError("INTERNAL_ERROR", "SCM 登录发生未分类错误。").to_dict(),
            }
        )
        return 2

    print(
        f"[scm-login] 登录成功（{credential['source']}），账户 {credential.get('account', '')}",
        file=sys.stderr,
    )
    emit(credential)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
