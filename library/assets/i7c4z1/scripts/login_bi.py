#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BI 登录 · 企微扫码登录模块（单文件自包含；依赖 requests；二维码窗口用 tkinter 标准库，零额外依赖）。

一个文件 = 一个既能独立运行、也能被任何应用 import 的登录组件。
模块只做一件事：企微扫码 → 拿到「完整用户信息」与「完整请求凭证」。

════════════════ 给 AI · Agent 的调用契约（唯一登录入口 · 先读这段） ════════════════
需要 BI 凭证时：**直接调用本脚本（黑盒使用）；禁止读源码后自写 / 自组装登录流程** ✗。

① 环境自检（首次使用 / 弹窗异常时）：
     python login_bi.py --check
     ——依赖：tkinter（Python 标准库，弹二维码窗口用）；缺失时按输出的 fix 命令修复。

② 先验证（只读、绝不弹窗）：
     python login_bi.py --status --no-remote
     退出码 0 = 已有可用凭证 → 直接使用。
③ 需要登录（唯一点：原生扫码窗）——即直接调起登录器原生弹窗：
     python login_bi.py --reuse                      # 独立登录器完整功能.真正全自动.用户体验优先首选！
                                                     # 确保依赖能够支持，环境有问题自动修复环境；
④ 取凭证：--status --show-token（或门面 API：relogin / verify_credential /
     get_credential / is_authenticated）；正常输出默认不含令牌明文。
用户已指定或提供凭证 / 登录方式 → 按其走（不受上列限制）。

禁止：自写登录流程 · 自取二维码 · 自拼鉴权请求 · 组装内部类（LoginFlow 等）·
     绕过本脚本解析凭证。
提示：不要用"文件时间戳"判断登录完成（--status 成功时也会刷新）；
     以本脚本的结果为准。
═══════════════════════════════════════════════════════════════════════════════

登录所需的全部连接配置（BI 地址、企微应用参数、固定请求头）已硬编码为
文件内的模块常量（BI_BASE / WECOM_BASE / OAUTH / BI_HEADERS），
**不读取任何外部配置文件，不含任何固定账号信息**，可直接整体拷走、独立运行。

=========================== 一、直接运行 ===========================
    python login_bi.py                 # 默认：弹出扫码窗，重新登录获取新凭证（需桌面）
    python login_bi.py --status        # 只验证已有凭证是否有效（绝不弹窗）
    python login_bi.py --check         # 环境自检（依赖 tkinter；缺失给出修复指引）
    python login_bi.py --reuse         # 直接调起原生扫码窗：有效复用、失效才弹窗（首选）
                                       # 确保依赖能够支持，环境有问题自动修复环境；
    python login_bi.py --no-remote     # 跳过远端 validate-token 校验

    成功时把「完整凭证 JSON」打印到 stdout，可直接被上游程序解析；
    `--status` 默认只输出元信息（不含令牌明文），加 `--show-token` 才输出完整凭证。
    退出码：0 成功 / 1 业务错误 / 2 未分类错误。

=========================== 二、被其它应用调用 ===========================
    from login_bi import (
        relogin,             # 功能一：弹出扫码窗重新登录，返回全新凭证
        verify_credential,   # 功能二：只验证已有凭证是否有效（绝不弹窗）
        get_credential,      # 组合：可指定强制重登 / 复用
        is_authenticated,    # 快捷：只想知道"现在能不能用"
    )

    # 功能一：每次都重新扫码，拿全新凭证
    cred = relogin()

    # 功能二：只验证，绝不弹窗
    result = verify_credential()
    if result["authenticated"]:
        token = result["token"]

    # 快捷：只要一个布尔值
    if not is_authenticated():
        cred = relogin()

    # 组合
    cred = get_credential(force_relogin=True)   # 等价 relogin()
    cred = get_credential(force_relogin=False)  # 有效则复用，失效才弹窗

=========================== 三、返回的「完整凭证」 ===========================
    {
      "ok": true, "authenticated": true,
      "source": "local" | "qr",        // 复用还是新扫码
      "reused": bool,
      "token": "...",                  // uIdToken 明文
      "tokenSig": "...",               // uIdToken.sig 明文
      "cookies": {...},                // 可直接塞进任何 HTTP 客户端
      "cookieHeader": "uIdToken=...; uIdToken.sig=...",
      "headers": {...},                // BI 固定请求头 + Cookie，开箱即用
      "exp": 1789465698, "expireAt": "2026-09-15 13:48:16",
      "validatedAt": ..., "createdAt": ...,
      "biBase": "...", "wecomBase": "...",
      "credentialPath": "...",         // 本地明文凭证文件
    }

=========================== 四、二维码窗口（tkinter 标准库） ===========================
    窗口标题：观远 BI · 扫码登录；置顶显示；260px 二维码区。
    ① 打开 → "正在获取二维码……" → 二维码 + "请使用企业微信扫码【剩余 Ns】"（实时倒计时）
    ② 扫码 → 半透明蒙版 + 绿色大√ + "扫码成功！请确认~"
    ③ 手机确认成功 → 保持绿√约 0.9s → 窗口自动关闭 → 凭证落盘
    ④ 二维码失效 / 手机取消 / 超时 → 窗口内自动重载新码（≤3 次）+ "二维码已失效，正在重新加载"；
       扫码后 90 秒未确认同样换码；超过 3 次 → 窗口关闭并抛 QR_EXPIRED
    ⑤ 用户关闭窗口 → LOGIN_CANCELLED

=========================== 五、凭证文件（唯一落盘形态：单账户） ===========================
    所有登录入口（relogin / login_and_store / CLI / 二维码窗口）落盘到同一处：
        %LOCALAPPDATA%\\bi-operations-query\\credential.json
    **一个文件、一份凭证**；明文 JSON 直接落盘（无加解密开销）；原子写入。

    身份识别：扫码后 token 里没有账号字段，模块会自动调 `/api/user/profile`
              查出「刚才是谁扫的」（loginId / uId / 姓名 / 邮箱 / 角色）并写进凭证。
    迁移：旧版 accounts/<loginId>.json 会在首次运行时自动取最近登录的那份迁移过来
          （原目录保留不删）。

    from login_bi import (
        login_and_store,       # 扫码登录 + 按真实身份落盘
        fetch_user_info,       # 查某份凭证属于哪个用户
        load_credential,       # 读本地凭证（不存在返回 {}）
        save_credential,       # 写本地凭证（原子写）
    )

    cred = login_and_store()          # 扫码，按扫码人身份落盘
    cred["user"]  # {"uId":..., "loginId":"LY000123", "name":"张三", ...}

安全说明：
    · 网络侧：使用内置的主机白名单与端点白名单，不引入任何本地服务、
      代理或第三方端点。
    · 存储侧：**全部明文存储，不做任何加解密**（统一落盘为 credential.json
      单文件，无其它形态），
      依赖 %LOCALAPPDATA% 目录的用户级 ACL 保护，请勿外传或纳入整机备份。
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import re
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Iterator
from urllib.parse import urljoin, urlparse

import requests
from requests import Response

# --------------------------------------------------------------------------- #
# 错误类型
# --------------------------------------------------------------------------- #
class BiError(Exception):
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
        output: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
        }
        if self.details:
            output["details"] = self.details
        return output


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
BI_BASE = "https://bi.leyopharm.com"
WECOM_BASE = "https://login.work.weixin.qq.com"
WECOM_VERSION = "2.3.2"

# 企微 OAuth 扫码参数（corpId / agentId 是公司企微应用标识，扫码登录必需）
OAUTH: dict[str, Any] = {
    "corpId": "wx8c9fab123dec4357",
    "agentId": "1000305",
    "redirectUri": "https://bi.leyopharm.com/?provider=wechatwork&agentId=1000305&corpId=wx8c9fab123dec4357&domain=guanbi",
    "domain": "guanbi",
    "state": "loginState",
    "pollIntervalSeconds": 1.5,
    "qrTimeoutSeconds": 300,
}

# BI 接口固定请求头（不含任何账号信息；请求者身份完全由 Cookie 决定）
BI_HEADERS: dict[str, str] = {
    "x-dom-id": "Z3VhbmJp",
    "raw-backend-response": "TRUE",
    "cache-control": "no-cache",
    "Accept": "application/json",
}

CONNECT_TIMEOUT = 10.0  # 秒
READ_TIMEOUT = 130.0    # 秒


# --------------------------------------------------------------------------- #
# HTTP 传输层（固定官方主机 + 端点白名单）
# --------------------------------------------------------------------------- #
_WECOM_GET_PATHS = frozenset(
    {
        "/wwlogin/sso/login",
        "/wwlogin/sso/qrcode",
    }
)
_WECOM_POST_PATHS = frozenset(
    {
        "/wwlogin/monoApi/sso/login/getWebQrCodeStatus",
    }
)
_BI_EXACT_GET_PATHS = frozenset({"/api/validate-token", "/api/user/profile"})


class Transport:
    """登录专用 HTTP 传输层：固定官方主机、端点白名单、不走系统代理。"""

    def __init__(self, credentials: dict[str, Any] | None = None) -> None:
        self.bi_base = BI_BASE
        self.wecom_base = WECOM_BASE
        self.host = urlparse(self.bi_base).hostname or ""
        self.timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)
        ca_bundle = os.environ.get("BI_CA_BUNDLE", "").strip()
        if ca_bundle:
            ca_path = Path(ca_bundle).expanduser().resolve()
            if not ca_path.is_file():
                raise BiError(
                    "TLS_CA_NOT_FOUND",
                    "BI_CA_BUNDLE 指向的证书文件不存在。",
                    details={"path": str(ca_path)},
                )
            self.verify: bool | str = str(ca_path)
        else:
            self.verify = True
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
        )
        if credentials:
            self._install_credentials(credentials)

    def _install_credentials(self, credentials: dict[str, Any]) -> None:
        """把 token / tokenSig 预置为 BI 会话 Cookie（复用本地凭证时使用）。"""
        token = str(credentials.get("token") or "")
        token_sig = str(credentials.get("tokenSig") or "")
        if token:
            self.session.cookies.set("uIdToken", token, domain=self.host, path="/")
        if token_sig:
            self.session.cookies.set("uIdToken.sig", token_sig, domain=self.host, path="/")

    def close(self) -> None:
        self.session.close()

    def cookie_value(self, name: str) -> str:
        matches = [
            cookie.value or ""
            for cookie in self.session.cookies
            if cookie.name == name
            and (not cookie.domain or self.host.endswith(cookie.domain.lstrip(".")))
        ]
        return matches[-1] if matches else ""

    def wecom_get(self, path: str, **kwargs: Any) -> Response:
        if path not in _WECOM_GET_PATHS:
            raise BiError("ENDPOINT_NOT_ALLOWED", "企微请求端点不在白名单中。")
        return self._request("GET", self.wecom_base, path, bi=False, **kwargs)

    def wecom_post(
        self,
        path: str,
        *,
        params: Any = None,
        json_body: Any,
        headers: dict[str, str],
    ) -> Response:
        if path not in _WECOM_POST_PATHS:
            raise BiError("ENDPOINT_NOT_ALLOWED", "企微请求端点不在白名单中。")
        return self._request(
            "POST", self.wecom_base, path, params=params, json=json_body, headers=headers, bi=False
        )

    def bi_get(self, path: str, **kwargs: Any) -> Response:
        allowed = path in _BI_EXACT_GET_PATHS
        if not allowed:
            raise BiError("ENDPOINT_NOT_ALLOWED", "BI GET 端点不在白名单中。")
        return self._request("GET", self.bi_base, path, bi=True, **kwargs)

    def bi_callback(self, auth_code: str) -> Response:
        """访问 BI 的企微回调首页，以 code/state 建立 BI 会话。"""
        return self._request(
            "GET",
            self.bi_base,
            "/",
            bi=True,
            params={
                "provider": "wechatwork",
                "agentId": OAUTH["agentId"],
                "corpId": OAUTH["corpId"],
                "domain": OAUTH.get("domain") or "guanbi",
                "code": auth_code,
                "state": OAUTH.get("state") or "loginState",
            },
            allow_redirects=True,
        )

    def _request(
        self,
        method: str,
        base: str,
        path: str,
        *,
        bi: bool,
        **kwargs: Any,
    ) -> Response:
        headers = dict(kwargs.pop("headers", {}) or {})
        if bi:
            headers.update(BI_HEADERS)
            headers.setdefault("Origin", self.bi_base)
            headers.setdefault("Referer", f"{self.bi_base}/")
        url = f"{base}{path}"
        allow_redirects = bool(kwargs.pop("allow_redirects", False))
        try:
            response = self.session.request(
                method,
                url,
                headers=headers,
                timeout=self.timeout,
                verify=self.verify,
                allow_redirects=allow_redirects,
                **kwargs,
            )
        except requests.exceptions.SSLError as exc:
            raise BiError("TLS_VALIDATION_FAILED", "HTTPS 证书验证失败，请检查公司 CA 配置。") from exc
        except requests.exceptions.Timeout as exc:
            raise BiError("UPSTREAM_TIMEOUT", "BI 或企微请求超时。", retryable=True) from exc
        except requests.exceptions.ConnectionError as exc:
            raise BiError(
                "BI_NETWORK_UNREACHABLE",
                "无法连接 BI 或企微，请确认公司内网、VPN 和 DNS。",
                retryable=True,
            ) from exc
        except requests.RequestException as exc:
            raise BiError("NETWORK_ERROR", "BI 网络请求失败。", retryable=True) from exc

        expected_host = urlparse(base).hostname
        final_host = urlparse(response.url).hostname
        if final_host != expected_host or any(
            urlparse(item.url).hostname != expected_host for item in response.history
        ):
            raise BiError("REDIRECT_NOT_ALLOWED", "请求离开了固定的官方主机。")
        if 300 <= response.status_code < 400:
            location = response.headers.get("Location") or ""
            redirect_host = urlparse(urljoin(response.url, location)).hostname
            if redirect_host != expected_host:
                raise BiError("REDIRECT_NOT_ALLOWED", "官方接口返回了未允许的重定向。")
            if bi:
                raise BiError("AUTH_EXPIRED", "BI 登录已过期，请重新扫码登录。")
            raise BiError("REDIRECT_NOT_ALLOWED", "官方接口返回了未允许的重定向。")

        if response.status_code == 401:
            raise BiError("AUTH_EXPIRED", "BI 登录已过期，请重新扫码登录。")
        if response.status_code == 403:
            raise BiError("AUTH_FORBIDDEN", "当前 BI 账号无权执行该请求。")
        if response.status_code == 429:
            raise BiError("RATE_LIMITED", "BI 请求过于频繁。", retryable=True)
        if response.status_code in (502, 503, 504):
            raise BiError(
                "UPSTREAM_UNAVAILABLE",
                f"BI 上游暂时不可用（HTTP {response.status_code}）。",
                retryable=True,
            )
        if response.status_code >= 400:
            raise BiError(
                "HTTP_ERROR",
                f"BI 请求失败（HTTP {response.status_code}）。",
                details={"status": response.status_code},
            )
        return response

    @staticmethod
    def json(response: Response) -> dict[str, Any]:
        try:
            data = response.json()
        except ValueError as exc:
            raise BiError("RESPONSE_INVALID_JSON", "BI 返回了无效 JSON。") from exc
        if not isinstance(data, dict):
            raise BiError("RESPONSE_SCHEMA_CHANGED", "BI 返回结构不是 JSON 对象。")
        return data


# --------------------------------------------------------------------------- #
# 本地凭证存储（单文件，全部明文 JSON）
# --------------------------------------------------------------------------- #
def _data_home() -> Path:
    override = os.environ.get("BI_OPERATIONS_HOME", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "bi-operations-query"
    xdg = os.environ.get("XDG_DATA_HOME", "").strip()
    return (Path(xdg).expanduser() if xdg else Path.home() / ".local" / "share") / "bi-operations-query"


def decode_jwt_payload(token: str) -> dict[str, Any]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload.encode("ascii")))
        return data if isinstance(data, dict) else {}
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeError):
        return {}


def decode_jwt_exp(token: str) -> int:
    try:
        return int(decode_jwt_payload(token).get("exp") or 0)
    except (ValueError, TypeError):
        return 0


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """原子 JSON 写入：临时文件 + fsync + `os.replace` 原子替换，权限 600。

    保证磁盘上的文件永远是完整写入的（原子替换，不会写坏旧凭证）。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
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
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def local_expired(credentials: dict[str, Any], skew_seconds: int = 60) -> bool:
    exp = int(credentials.get("exp") or 0)
    return bool(exp and exp <= int(time.time()) + skew_seconds)


__all__ = [
    "get_credential",
    "verify_credential",
    "relogin",
    "is_authenticated",
    "run_login_dialog",
    "LoginFlow",
    "build_credential",
    # 凭证文件（唯一落盘形态：单账户）
    "login_and_store",
    "fetch_user_info",
    "load_credential",
    "save_credential",
    "USER_PROFILE_PATH",
    "BiError",
    "STAGE_LOADING",
    "STAGE_QR_READY",
    "STAGE_SCANNED",
    "STAGE_AUTHENTICATING",
    "STAGE_FAILED",
    "STATUS_LOADING",
    "STATUS_SCAN",
    "STATUS_CONFIRM",
    "STATUS_LOGGING_IN",
    "STATUS_RETRY",
]

# --------------------------------------------------------------------------- #
# 阶段与文案
# --------------------------------------------------------------------------- #
STAGE_LOADING = "loading"
STAGE_QR_READY = "qr_ready"
STAGE_SCANNED = "scanned"
STAGE_AUTHENTICATING = "authenticating"
STAGE_FAILED = "failed"

STATUS_LOADING = "加载中......"
STATUS_SCAN = "请企微扫码......"
STATUS_CONFIRM = "请确认登录！"
STATUS_LOGGING_IN = "登录中......"
STATUS_RETRY = "请点击重试！"

# 二维码就绪时的倒计时文案模板，{0} 为剩余时间（mm:ss）
STATUS_SCAN_COUNTDOWN = "请企微扫码（{0}）......"

# 界面配色（十六进制，避免与 Qt 产生耦合）
_FONT_FAMILY = "Microsoft YaHei UI"
# 这些错误说明「本地凭证不可用」，才允许弹窗重新登录。
# 网络、限流、权限、参数类错误一律不触发登录界面。
_RECOVERABLE_CODES = frozenset(
    {"AUTH_REQUIRED", "AUTH_EXPIRED", "CREDENTIALS_INVALID"}
)

# 扫码成功但换取/校验凭证失败时，可以靠「重新加载二维码」自救的错误。
_RELOADABLE_AFTER_SCAN = frozenset(
    {"AUTH_EXPIRED", "CREDENTIALS_INVALID", "AUTH_TOKEN_MISSING", "REDIRECT_NOT_ALLOWED"}
)

# 当前登录用户的身份信息端点（返回 loginId / uId / name / email / role 等）。
# 扫码登录后调它，才能知道「刚才是谁扫的」——token 本身不含账号字段。
USER_PROFILE_PATH = "/api/user/profile"

# /api/user/profile 返回体很大（含 features、字体、导出限制等），
# 只保留身份相关字段存进凭证，避免仓库膨胀。
_USER_INFO_FIELDS = ("uId", "loginId", "name", "email", "domId", "domainName", "role")

_QR_PATTERN = re.compile(r"wwlogin/sso/qrcode\?key=([a-f0-9]{16})")

_RELOAD = object()  # _poll 的返回值哨兵：表示需要重新加载二维码
CONFIRM_WAIT_SECONDS = 90   # 已扫码后的等待确认上限（秒）：超过即视为拒绝/无响应 → 换码重扫


# --------------------------------------------------------------------------- #
# 基础工具
# --------------------------------------------------------------------------- #
def _extract_qr_key(html: str) -> str:
    match = _QR_PATTERN.search(html or "")
    if not match:
        raise BiError("QR_CREATE_FAILED", "企微登录页中没有找到二维码 key。")
    return match.group(1)


def _interruptible_sleep(seconds: float, is_aborted: Callable[[], bool]) -> bool:
    """可中断的 sleep；被打断返回 False。"""
    deadline = time.monotonic() + max(0.0, float(seconds))
    while True:
        if is_aborted():
            return False
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return True
        time.sleep(min(0.1, remaining))


def _format_timestamp(value: int) -> str:
    if not value:
        return ""
    return dt.datetime.fromtimestamp(int(value)).strftime("%Y-%m-%d %H:%M:%S")


def _validate_token_remote(transport: Transport) -> None:
    data = transport.json(transport.bi_get("/api/validate-token"))
    if data.get("response") != "success":
        raise BiError("AUTH_EXPIRED", "BI 凭证验证失败，请重新扫码登录。")


def fetch_user_info(credential: dict[str, Any]) -> dict[str, Any]:
    """查询某份凭证**实际属于哪个用户**（BI `/api/user/profile`）。

    扫码后拿到的 token 里没有账号字段，只有调这个接口才能知道「刚才是谁扫的」。
    按真实客户端的方式调用：POST 空 JSON 体，并用 `token` 请求头携带 JWT。

    参数：
        credential  登录得到的完整凭证（需含 token）

    返回：身份信息字典，例如
        {"uId": "xf727d90…", "loginId": "LY000123", "name": "张三",
         "email": "…@company.com", "domId": "guanbi", "role": [...]}

    抛出：BiError —— 凭证失效（AUTH_EXPIRED）或接口返回异常（USER_INFO_FAILED）
    """
    transport = Transport(credential)
    try:
        data = transport.json(transport.bi_get(USER_PROFILE_PATH))
    finally:
        transport.close()
    # 带 raw-backend-response 时是信封 {"result":"ok","response":{...}}，拆一层；
    # 否则直接就是用户对象。两种形态都兼容。
    if isinstance(data, dict) and isinstance(data.get("response"), dict):
        data = data["response"]
    if not isinstance(data, dict) or not data:
        raise BiError("USER_INFO_FAILED", "未能获取用户信息，请重新登录。")
    return data


def _slim_user(user_info: dict[str, Any]) -> dict[str, Any]:
    """从 /api/user/profile 的完整响应里只挑身份字段（避免把 features/字体等存进来）。"""
    slim: dict[str, Any] = {}
    for key in _USER_INFO_FIELDS:
        value = user_info.get(key)
        if value in (None, "", [], {}):
            continue
        slim[key] = value
    return slim


def _identity_of(user_info: dict[str, Any]) -> str:
    """取账号标识：优先 loginId（可读、与 BI 账号一致），退化到 uId / id。"""
    for key in ("loginId", "uId", "id"):
        value = str(user_info.get(key) or "").strip()
        if value:
            return value
    raise BiError("ACCOUNT_INVALID", "用户信息中没有可用的账号标识。")


def _check_credential(
    credentials: dict[str, Any] | None,
    *,
    validate_remote: bool,
) -> tuple[str | None, BiError | None]:
    """检查一份凭证是否可用；返回 (reason, error)，两者皆 None 表示有效。

    reason 取值：missing / expired / invalid / not_validated（网络类未通过，不代表凭证失效）；
    reason 与 error.code 同源（凭证类错误给出明确的 expired / invalid）。
    凭证校验共用这一套判定。
    """
    if not credentials:
        return "missing", BiError("AUTH_REQUIRED", "尚未登录 BI，请先执行登录。")
    if local_expired(credentials):
        return "expired", BiError("AUTH_EXPIRED", "本地 BI 凭证已过期，请重新扫码登录。")
    if validate_remote:
        transport = Transport(credentials)
        try:
            _validate_token_remote(transport)
        except BiError as exc:
            # reason 与错误码同源：凭证类错误（AUTH_EXPIRED / CREDENTIALS_INVALID）→
            # 明确的 expired / invalid；网络、限流等非凭证类才归 not_validated（不代表凭证失效）。
            if exc.code in _RECOVERABLE_CODES:
                reason = "expired" if exc.code == "AUTH_EXPIRED" else "invalid"
            else:
                reason = "not_validated"
            return reason, exc
        finally:
            transport.close()
    return None, None


# --------------------------------------------------------------------------- #
# 凭证打包
# --------------------------------------------------------------------------- #
def build_credential(
    credentials: dict[str, Any],
    *,
    source: str,
    reused: bool,
) -> dict[str, Any]:
    """把本地或新获取的凭证打包成「完整凭证」，任何应用都能直接消费。

    参数：
        credentials  凭证本体，至少含 token；可选 tokenSig / exp / createdAt / validatedAt
        source       "local"（复用本地凭证）或 "qr"（本次新扫码）
        reused       本次结果是否为复用旧凭证

    返回：完整凭证字典（字段见模块文档「三、返回的完整凭证」）。

    说明：一般不必直接调用，verify_credential() / relogin() 已返回同样结构。
    """
    token = str(credentials.get("token") or "")
    token_sig = str(credentials.get("tokenSig") or "")
    cookies: dict[str, str] = {"uIdToken": token}
    if token_sig:
        cookies["uIdToken.sig"] = token_sig

    headers = dict(BI_HEADERS)
    headers["Cookie"] = "; ".join(f"{name}={value}" for name, value in cookies.items())
    headers.setdefault("Origin", BI_BASE)
    headers.setdefault("Referer", f"{BI_BASE}/")

    exp = int(credentials.get("exp") or decode_jwt_exp(token) or 0)
    return {
        "ok": True,
        "authenticated": True,
        "source": source,
        "reused": reused,
        "token": token,
        "tokenSig": token_sig,
        "cookies": cookies,
        "cookieHeader": headers["Cookie"],
        "headers": headers,
        "exp": exp,
        "expireAt": _format_timestamp(exp),
        "createdAt": int(credentials.get("createdAt") or 0),
        "validatedAt": int(credentials.get("validatedAt") or 0),
        "biBase": BI_BASE,
        "wecomBase": WECOM_BASE,
        "credentialPath": str(credentials.get("credentialPath") or ""),
    }


# --------------------------------------------------------------------------- #
# 登录流程内核（弹窗内部组件：不依赖 Qt，但不对外暴露）
# --------------------------------------------------------------------------- #
class LoginFlow:
    """企微扫码登录的完整流程，通过回调把阶段抛给上层（UI 或 CLI）。

    本类不依赖 Qt（界面框架由上层提供），但**不是对外的无界面登录方式**：
    本登录器只提供原生弹窗登录，外部请用门面（relogin / get_credential）。

    ⚠ 内部组件：仅供本文件的图形弹窗使用；
    外部 / Agent 取凭证请用门面（relogin / get_credential）——
    禁止自行组装本流程 ✗。

    参数（构造）：
        max_auto_reload  二维码失效时最多自动重载几次（默认 3）；超出则抛 QR_EXPIRED

    回调（构造，均可省略，省略后为空实现）：
        on_stage(stage, message)  UI 阶段切换
        on_qr(png_bytes)          二维码图片字节
        on_notice(text)           非阻塞提示（例如"二维码已失效，正在重新加载"）
        is_aborted()              返回 True 立即中止（用于取消 / 关窗）

    方法：
        run()  执行一次完整登录，返回完整凭证字典；失败抛 BiError。
               内部会在二维码失效 / 被取消 / 超时时自动重新加载。

    属性：
        last_error  最近一次错误（BiError 或 None）

    典型用法（后台线程 + 回调）：
        flow = LoginFlow(on_stage=..., on_qr=..., is_aborted=...)
        cred = flow.run()   # 阻塞直到拿到凭证或被中止
    """

    def __init__(
        self,
        *,
        on_stage: Callable[[str, str], None] | None = None,
        on_qr: Callable[[bytes], None] | None = None,
        on_notice: Callable[[str], None] | None = None,
        is_aborted: Callable[[], bool] | None = None,
        max_auto_reload: int = 3,
    ) -> None:
        self.on_stage = on_stage or (lambda *_: None)
        self.on_qr = on_qr or (lambda _: None)
        self.on_notice = on_notice or (lambda _: None)
        self.is_aborted = is_aborted or (lambda: False)
        self.max_auto_reload = max(0, int(max_auto_reload))
        self.last_error: BiError | None = None
        self._open_data_sid: str | None = None

    # --------------------------- 主循环 --------------------------- #
    def run(self) -> dict[str, Any]:
        """执行一次登录；内部会在二维码失效/被取消时自动重新加载。"""
        transport = Transport()
        reloads = 0
        try:
            while True:
                if self.is_aborted():
                    raise self._abort_error()

                # ---- 第一步：加载二维码 ---- #
                self.on_stage(STAGE_LOADING, STATUS_LOADING)
                try:
                    qr_key, png, sso_url = self._create_qr(transport)
                except BiError as exc:
                    raise self._fail(exc)

                self.on_qr(png)
                self.on_stage(STAGE_QR_READY, STATUS_SCAN)

                # ---- 第二步：轮询扫码与确认 ---- #
                outcome = self._poll(transport, qr_key, sso_url)
                if outcome is _RELOAD:
                    reloads += 1
                    if reloads > self.max_auto_reload:
                        raise self._fail(
                            BiError("QR_EXPIRED", "二维码多次失效，请点击重试。")
                        )
                    self.on_notice("二维码已失效，正在重新加载")
                    continue
                if self.is_aborted():
                    raise self._abort_error()

                # ---- 第三步：换取并校验凭证 ---- #
                self.on_stage(STAGE_AUTHENTICATING, STATUS_LOGGING_IN)
                try:
                    return self._finish(transport, str(outcome))
                except BiError as exc:
                    reloads += 1
                    if exc.code not in _RELOADABLE_AFTER_SCAN:
                        raise self._fail(exc)
                    if reloads > self.max_auto_reload:
                        raise self._fail(exc)
                    self.on_notice(f"{exc.message} 正在重新加载二维码")
        finally:
            transport.close()

    # --------------------------- 各环节 --------------------------- #
    def _create_qr(self, transport: Transport) -> tuple[str, bytes, str]:
        oauth = OAUTH
        response = transport.wecom_get(
            "/wwlogin/sso/login",
            params={
                "login_type": "CorpApp",
                "appid": oauth["corpId"],
                "agentid": oauth["agentId"],
                "redirect_uri": oauth["redirectUri"],
                "state": oauth.get("state") or "loginState",
                "redirect_type": "top",
                "panel_size": "small",
                "lang": "zh",
                "version": WECOM_VERSION,
            },
        )
        qr_key = _extract_qr_key(response.text)
        image = transport.wecom_get("/wwlogin/sso/qrcode", params={"key": qr_key})
        png = image.content
        if not png:
            raise BiError("QR_CREATE_FAILED", "二维码图片为空。")
        return qr_key, png, response.url

    def _poll(self, transport: Transport, qr_key: str, sso_url: str) -> Any:
        """轮询扫码状态（wwlogin monoApi）。

        返回 auth_code（已确认）、_RELOAD（需重新加载二维码），或抛出异常。
        """
        oauth = OAUTH
        interval = float(oauth.get("pollIntervalSeconds") or 1.5)
        deadline = time.monotonic() + float(oauth.get("qrTimeoutSeconds") or 300)
        # 企微状态机要求首拍 lastStatus 为固定初始值，服务端据此推进状态
        last_status = "QRCODE_SCAN_NEVER"
        confirmed = False
        confirm_deadline = 0.0      # 已扫码后的确认等待截止（手机"拒绝"的兜底）

        while time.monotonic() < deadline:
            if self.is_aborted():
                raise self._abort_error()
            poll_headers = {
                "content-type": "application/json",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "referer": sso_url,
                "x-wecom-client": f"ww-sso-login:{int(time.time() * 1000)}:master",
            }
            try:
                response = transport.wecom_post(
                    "/wwlogin/monoApi/sso/login/getWebQrCodeStatus",
                    params={
                        "lang": "zh_CN",
                        "ajax": "1",
                        "f": "json",
                        "random": str(time.time()),
                    },
                    json_body={
                        "webKey": qr_key,
                        "lastStatus": last_status,
                        "openDataSid": self._open_data_sid,
                    },
                    headers=poll_headers,
                )
                body = transport.json(response)
            except BiError as exc:
                if not exc.retryable:
                    raise
                self._sleep_or_abort(interval)
                continue

            payload = body.get("data")
            data = payload if isinstance(payload, dict) else {}
            status = str(body.get("status") or data.get("status") or "")
            auth_code = str(body.get("auth_code") or data.get("auth_code") or "")
            open_data_sid = body.get("openDataSid") or data.get("openDataSid")
            if open_data_sid:
                self._open_data_sid = open_data_sid

            # 已扫码、等待手机端确认
            if status == "QRCODE_SCAN_ING" or (
                status == "QRCODE_SCAN_SUCC" and not auth_code
            ):
                if not confirmed:
                    confirmed = True
                    confirm_deadline = time.monotonic() + CONFIRM_WAIT_SECONDS
                    self.on_stage(STAGE_SCANNED, STATUS_CONFIRM)
                elif time.monotonic() > confirm_deadline:
                    return _RELOAD      # 扫了但迟迟不确认（含手机"拒绝"）→ 换码重扫
                self._sleep_or_abort(interval)
                continue

            # 已确认
            if status == "QRCODE_SCAN_SUCC" and auth_code:
                if not confirmed:
                    self.on_stage(STAGE_SCANNED, STATUS_CONFIRM)
                return auth_code

            # 取消 / 失效 / 超时 → 回到第一步重新加载二维码
            if status in {"QRCODE_SCAN_ERR", "QRCODE_SCAN_TIMEOUT", "QRCODE_SCAN_CANCEL"}:
                return _RELOAD

            # 已扫码后出现其它状态（手机"拒绝"、状态回退到未扫、未知值）→ 同样重载，
            # 避免窗口卡在绿√直到整体超时（实测反馈 2026-09-19：拒绝后不恢复）
            if confirmed and status:
                return _RELOAD

            if status:
                last_status = status
            self._sleep_or_abort(interval)

        return _RELOAD  # 轮询整体超时 → 重新加载

    def _finish(
        self,
        transport: Transport,
        auth_code: str,
    ) -> dict[str, Any]:
        # BI 成功链：先带 code/state 访问回调首页，服务器会通过 Set-Cookie 直接下发
        # uIdToken 与 uIdToken.sig。无需再调用 /api/user/token（本账号对该端点 1004 无权限）。
        transport.bi_callback(auth_code)
        token = transport.cookie_value("uIdToken")
        token_sig = transport.cookie_value("uIdToken.sig")
        if not token:
            raise BiError("AUTH_TOKEN_MISSING", "扫码成功，但 BI 回调未返回 Token。")
        _validate_token_remote(transport)

        return build_credential(
            {
                "biBase": BI_BASE,
                "token": token,
                "tokenSig": token_sig,
                "exp": decode_jwt_exp(token),
                "createdAt": int(time.time()),
                "validatedAt": int(time.time()),
            },
            source="qr",
            reused=False,
        )

    # --------------------------- 错误收口 --------------------------- #
    def _sleep_or_abort(self, seconds: float) -> bool:
        if not _interruptible_sleep(seconds, self.is_aborted):
            raise self._abort_error()
        return True

    def _abort_error(self) -> BiError:
        exc = BiError("LOGIN_CANCELLED", "登录已取消。")
        self.last_error = exc
        return exc

    def _fail(self, exc: BiError) -> BiError:
        """进入失败态（静止加载圈 + 请点击重试），并记录错误。"""
        self.last_error = exc
        self.on_stage(STAGE_FAILED, STATUS_RETRY)
        return exc


# --------------------------------------------------------------------------- #
# 功能二：读取本地凭证并验证是否有效（绝不弹窗）
# --------------------------------------------------------------------------- #
def verify_credential(
    *,
    validate_remote: bool = True,
    raise_on_invalid: bool = False,
) -> dict[str, Any]:
    """验证本地凭证文件里的凭证。**绝不会弹窗。**

    参数：
        validate_remote  True  → 额外请求 /api/validate-token 做远端校验（默认）
                        False → 只做本地检查（过期时间），不发网络请求
        raise_on_invalid True  → 凭证无效时直接抛出 BiError
                        False → 不抛异常，返回 ok=False 的结果字典（默认）

    返回：
        有效 → 完整凭证（authenticated=True，source="local"）
        无效 → {"ok": False, "authenticated": False, "reason": ..., "error": {...}}

    reason 取值：missing（本地没有任何账号）/ expired（已过期）
                / invalid（凭证损坏、字段缺失或远端判定失效）
                / not_validated（远端校验未通过：网络 / 限流类，不代表凭证失效）
    """
    _migrate_legacy_accounts()
    cred_path = _credential_file()

    def _invalid(reason: str, exc: BiError) -> dict[str, Any]:
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

    credentials = load_credential()
    if not credentials:
        return _invalid("missing", BiError("AUTH_REQUIRED", "尚未登录 BI，请先执行登录。"))

    reason, error = _check_credential(credentials, validate_remote=validate_remote)
    if reason or credentials is None:
        return _invalid(
            reason or "invalid",
            error or BiError("AUTH_REQUIRED", "本地凭证不可用。"),
        )

    credentials["validatedAt"] = int(time.time())
    save_credential(credentials)
    result = dict(credentials)
    # 验证通过即视为已认证，保证调用方读 authenticated 恒有布尔值。
    result.setdefault("ok", True)
    result.setdefault("authenticated", True)
    result["source"] = "local"
    result["reused"] = True
    result["credentialPath"] = str(cred_path)
    return result


def is_authenticated(validate_remote: bool = True) -> bool:
    """快捷判断：本地凭证当前是否可用（等价于 verify_credential()["authenticated"]）。

    参数：
        validate_remote  True  → 额外做远端 /api/validate-token 校验（默认）
                        False → 只做本地检查，不发网络请求

    返回：True 可用 / False 不可用（绝不会弹窗、绝不会抛异常）。
    """
    return bool(verify_credential(validate_remote=validate_remote)["authenticated"])


# --------------------------------------------------------------------------- #
# 功能一：重新登录获取凭证 + 组合入口
# --------------------------------------------------------------------------- #
def get_credential(
    *,
    force_relogin: bool = True,
    validate_remote: bool = True,
    interactive: bool = True,
    parent: Any = None,
) -> dict[str, Any]:
    """拿到一份可用凭证。

    默认（force_relogin=True）与 relogin() 等价：每次都弹窗重新扫码，
    保证拿到全新凭证。需要"优先复用本地凭证、失效才弹窗"时传 force_relogin=False。

    参数：
        force_relogin   True  → 总是弹窗重新扫码（默认）
                        False → 优先复用本地有效凭证，失效才弹窗
        validate_remote True  → 复用时额外请求 /api/validate-token（默认）
                        False → 复用时只做本地检查，不发网络请求
        interactive     True  → 允许弹窗扫码（默认）
                        False → 非交互（调用方保证不弹窗）；凭证不可用时不弹窗，直接抛 BiError
        parent          兼容保留参数（不使用）

    返回：完整凭证字典（同 build_credential()）。

    抛出：
        BiError —— 非交互模式下凭证不可用，或遇到网络/权限类不可恢复错误。
    """
    if not force_relogin:
        result = verify_credential(validate_remote=validate_remote)
        if result["authenticated"]:
            return result
        error = result.get("error") or {}
        code = str(error.get("code") or "")
        message = str(error.get("message") or "本地凭证不可用。")
        # 只有「凭证本身不可用」才允许弹窗；网络/限流/权限错误直接抛出。
        if not interactive or code not in _RECOVERABLE_CODES:
            raise BiError(code or "AUTH_REQUIRED", message)

    if not interactive:
        raise BiError(
            "AUTH_REQUIRED",
            "本地没有可用凭证（非交互模式，绝不弹窗）。"
            "需要新登录时请运行：python login_bi.py --reuse（原生扫码窗）。",
        )
    # 重新扫码必须走 login_and_store：取扫码人身份并落入 credential.json。
    # 直接调用 run_login_dialog 只会拿到内存凭证，不会落盘（--status 会一直失败）。
    return login_and_store(parent=parent)


def relogin(*, parent: Any = None) -> dict[str, Any]:
    """功能一：无论本地是否已有凭证，都弹出扫码窗重新登录，返回全新凭证。

    登录成功后按扫码人身份落入本地凭证文件（credential.json）。

    参数：
        parent   兼容保留参数（不使用）

    返回：完整凭证字典（source="qr"、reused=False）。

    抛出：BiError —— 用户取消（LOGIN_CANCELLED）、二维码多次失效或网络类错误。
    """
    return login_and_store(parent=parent)


# 凭证仓库（唯一落盘形态：按账号名存取完整凭证）
# --------------------------------------------------------------------------- #
CREDENTIAL_FILENAME = "credential.json"        # 唯一落盘形态：单账户单文件


def _credential_file() -> Path:
    """本地凭证文件路径（单文件）。"""
    return _data_home() / CREDENTIAL_FILENAME


def load_credential() -> dict[str, Any]:
    """读取本地凭证；不存在或损坏返回 {}（绝不抛异常）。"""
    try:
        with open(_credential_file(), encoding="utf-8-sig") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_credential(credential: dict[str, Any]) -> str:
    """原子写本地凭证，返回文件路径。"""
    _data_home().mkdir(parents=True, exist_ok=True)
    _atomic_write_json(_credential_file(), credential)
    return str(_credential_file())


def _migrate_legacy_accounts() -> None:
    """一次性迁移：旧版 accounts/ 多账号文件 → 单文件凭证（取最近登录的那份）。

    原目录保留不删；迁移失败也无副作用（最坏情况重新扫码一次）。
    """
    if _credential_file().is_file():
        return
    legacy = _data_home() / "accounts"
    if not legacy.is_dir():
        return
    for path in sorted(legacy.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        cred = entry.get("credential") if isinstance(entry, dict) else None
        if not isinstance(cred, dict) or not cred.get("token"):
            cred = entry if (isinstance(entry, dict) and entry.get("token")) else None
        if cred:
            save_credential(cred)
            return


def _persist_credential(credential: dict[str, Any]) -> dict[str, Any]:
    """查「刚才是谁扫的」→ 写入本地凭证文件（单账户）。"""
    user_info = fetch_user_info(credential)
    credential["user"] = _slim_user(user_info)
    credential["credentialPath"] = save_credential(credential)
    return credential


def login_and_store(*, parent: Any = None) -> dict[str, Any]:
    """调起二维码窗口扫码，按扫码人身份落库并返回完整凭证。"""
    credential = run_login_dialog(parent=parent)
    return _persist_credential(credential)


# --------------------------------------------------------------------------- #
# 命令行入口
# --------------------------------------------------------------------------- #
QR_TTL_SECONDS = 300          # 二维码有效期（秒；与企微扫码超时一致，仅用于窗口倒计时）


def run_login_dialog(
    *,
    parent: Any = None,
) -> dict[str, Any]:
    """弹出**二维码窗口**（tkinter 标准库、置顶）并等待完成（同步用法）。

    窗口行为：
        显示二维码 → 用户扫码后盖**半透明蒙版 + 绿色大√**并提示"请确认" →
        确认成功自动关闭窗口并返回凭证；失效在窗口内自动重载（≤3 次，由 LoginFlow 控制）；
        用户关窗 → BiError(LOGIN_CANCELLED)。

    参数：
        parent   兼容保留参数（不使用）

    返回：成功 → 完整凭证字典（source="qr"、reused=False）。
    抛出：BiError —— LOGIN_CANCELLED（用户取消）/ QR_EXPIRED（二维码多次失效）
                    / 网络、限流、权限等不可恢复错误。
    """
    import queue as _queue
    import threading as _th
    import tkinter as tk

    root = tk.Tk()
    root.title("观远 BI · 扫码登录")
    root.attributes("-topmost", True)              # 置顶：二维码直达用户桌面
    root.resizable(False, False)

    QR = 260                                        # 二维码显示尺寸（px）
    canvas = tk.Canvas(root, width=QR, height=QR, highlightthickness=0, bg="#FFFFFF")
    canvas.pack(padx=12, pady=(12, 6))
    img_item = canvas.create_image(QR // 2, QR // 2)
    mask = canvas.create_rectangle(0, 0, QR, QR, fill="#000000", stipple="gray50",
                                   outline="", state="hidden")
    # 绿色大√：绿圆 + 两段白勾（Canvas 原生绘制，零依赖）
    r = int(QR * 0.25)
    cx = cy = QR // 2
    tick_circle = canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                     fill="#00A651", outline="", state="hidden")
    lw = max(6, int(r * 0.3))
    tick_l1 = canvas.create_line(cx - r * 0.46, cy + r * 0.02,
                                 cx - r * 0.12, cy + r * 0.36,
                                 width=lw, fill="#FFFFFF", capstyle=tk.ROUND, state="hidden")
    tick_l2 = canvas.create_line(cx - r * 0.12, cy + r * 0.36,
                                 cx + r * 0.48, cy - r * 0.34,
                                 width=lw, fill="#FFFFFF", capstyle=tk.ROUND, state="hidden")

    tip = tk.Label(root, text="正在获取二维码……", font=("Microsoft YaHei UI", 10),
                   wraplength=300, justify="center")
    tip.pack(padx=12, pady=(0, 12))

    evt_q: _queue.Queue = _queue.Queue()
    result: dict[str, Any] = {"cred": None, "error": None}
    cancel = {"v": False}
    deadline = {"v": 0.0}
    scanned = {"v": False}

    def _hide_tick() -> None:
        for it in (mask, tick_circle, tick_l1, tick_l2):
            canvas.itemconfig(it, state="hidden")

    def set_qr(png: bytes) -> None:
        """（重新）载入二维码——失效重载时复用同一窗口。"""
        try:
            photo = tk.PhotoImage(data=png)
            if photo.width() > QR:
                photo = photo.subsample(max(1, photo.width() // QR))
            canvas.itemconfig(img_item, image=photo)
            canvas._qr_img = photo                  # 保持引用防 GC
            _hide_tick()
            scanned["v"] = False
            deadline["v"] = time.time() + QR_TTL_SECONDS
            tip.configure(text="请使用企业微信扫码", fg="#333333",
                          font=("Microsoft YaHei UI", 10))
        except Exception as exc:                    # 渲染失败如实显示，不静默
            tip.configure(text=f"二维码渲染失败：{exc}", fg="#C0392B")

    def show_scanned() -> None:
        """已扫码待确认：蒙版 + 绿色大√ + 提示切换。"""
        _hide_tick()
        canvas.itemconfig(mask, state="normal")
        canvas.itemconfig(tick_circle, state="normal")
        canvas.itemconfig(tick_l1, state="normal")
        canvas.itemconfig(tick_l2, state="normal")
        scanned["v"] = True
        tip.configure(text="扫码成功！请确认~", fg="#00A651",
                      font=("Microsoft YaHei UI", 10, "bold"))

    def worker() -> None:
        try:
            flow = LoginFlow(
                on_qr=lambda png: evt_q.put(("qr", png)),
                on_notice=lambda text: evt_q.put(("notice", text)),
                on_stage=lambda stage, message: evt_q.put(("stage", (stage, message))),
                is_aborted=lambda: cancel["v"],
            )
            result["cred"] = flow.run()
        except BaseException as exc:  # noqa: BLE001 —— 线程内异常回传主线程
            result["error"] = exc
        finally:
            evt_q.put(("done", None))

    def pump() -> None:
        try:
            while True:
                kind, payload = evt_q.get_nowait()
                if kind == "qr":
                    set_qr(payload)
                elif kind == "notice":
                    tip.configure(text=str(payload), fg="#B7791F")
                elif kind == "stage":
                    stage, message = payload
                    if stage == STAGE_SCANNED:
                        show_scanned()
                    elif message:
                        tip.configure(text=str(message), fg="#333333")
                elif kind == "done":
                    root.after(900, root.destroy)   # 让用户看清绿√后再自动关窗
                    return
        except _queue.Empty:
            pass
        if deadline["v"] and not scanned["v"]:
            left = int(deadline["v"] - time.time())
            if left > 0:
                tip.configure(text=f"请使用企业微信扫码【剩余 {left}s】", fg="#333333")
            else:
                tip.configure(text="二维码已过期，正在重新加载…", fg="#C0392B")
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
        raise BiError("LOGIN_CANCELLED", "用户取消了登录。")
    return result["cred"]


def check_env() -> dict[str, Any]:
    """环境自检：登录器可调用性（tkinter / 凭证仓库可写）与下一步指引；绝不弹窗。"""
    out: dict[str, Any] = {
        "ok": True,
        "python": sys.version.split()[0],
        "gui": None,
        "credentialDir": str(_data_home()),
        "fix": None,
        "next": "python login_bi.py --reuse（弹窗登录）｜--status（只验证）",
    }
    try:
        import tkinter  # noqa: F401  —— 标准库：二维码窗口唯一依赖
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


def _emit_credential_result(result: dict[str, Any], show_token: bool) -> None:
    """统一输出：show_token → 完整凭证；否则仅元信息（令牌明文隐藏）。"""
    if show_token:
        emit(result)
        return
    user = result.get("user") if isinstance(result.get("user"), dict) else {}
    out = {
        "ok": result.get("ok"),
        "authenticated": result.get("authenticated"),
        "source": result.get("source"),
        "exp": result.get("exp"),
        "expireAt": result.get("expireAt"),
        "validatedAt": result.get("validatedAt"),
        "biBase": result.get("biBase"),
        "credentialPath": result.get("credentialPath"),
        "user": {
            k: user.get(k)
            for k in ("uId", "loginId", "name", "email", "domId", "role")
            if user.get(k) is not None
        },
        "error": result.get("error"),
        "nextAction": result.get("nextAction"),
    }
    out = {k: v for k, v in out.items() if v is not None}
    emit(out)
    print("[bi-login] 令牌明文已隐藏；需要完整凭证时加 --show-token", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="BI 登录 · 企微扫码登录（默认弹出扫码窗重新登录；也可只验证已有凭证）",
        epilog=(
            "给 AI · Agent 的调用契约（唯一登录入口 → 直接调用本登录器（黑盒）；禁止读源码后自写登录）：\n"
            "  1) 自检：--check（依赖 tkinter；缺失给出修复指引）\n"
            "  2) 验证：--status（退出码 0 = 已有可用凭证，直接用）\n"
            "  3) 登录：--reuse（唯一点：直接调起原生扫码窗；有效复用、失效才弹窗；依赖缺失自动修复环境）\n"
            "  4) 取凭证：--status --show-token（或门面 API：relogin / verify_credential /\n"
            "     get_credential / is_authenticated）\n"
            "  弹窗失败 → --check 修复环境后重试；仍失败 → 询问用户（禁止出码绕路）。\n"
            "  用户已指定或提供凭证 / 登录方式 → 按其走（不受上列限制）。\n"
            "  禁止：自写登录流程 / 出码绕路 / 自取二维码 / 自拼鉴权 / 组装内部类（LoginFlow 等）/ 绕过本脚本解析凭证。\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="环境自检：检查 tkinter 与登录器可调用性；缺失给出修复指引",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="功能二：只验证已有凭证是否有效，绝不弹窗（默认只输出元信息，不含令牌明文）",
    )
    parser.add_argument(
        "--show-token",
        action="store_true",
        help="配合 --status：输出完整凭证（含 token / Cookie 明文），默认隐藏",
    )
    parser.add_argument(
        "--reuse",
        action="store_true",
        help="优先复用本地有效凭证，仅在失效时才弹窗（默认总是重新扫码）",
    )
    parser.add_argument("--no-remote", action="store_true", help="跳过远端 validate-token")
    args = parser.parse_args(argv)

    configure_stdio()
    try:
        if args.check:
            result = check_env()
            emit(result)
            return 0 if result.get("ok") else 1

        if args.status:
            result = verify_credential(validate_remote=not args.no_remote)
            print(
                "[bi-login] "
                + ("凭证有效" if result["authenticated"] else f"凭证无效：{result.get('reason')}"),
                file=sys.stderr,
            )
            _emit_credential_result(result, args.show_token)
            return 0 if result["authenticated"] else 1

        # 默认：无论本地是否已有凭证，都弹窗重新扫码获取新凭证。
        credential = get_credential(
            force_relogin=not args.reuse,
            validate_remote=not args.no_remote,
            interactive=True,
        )
    except BiError as exc:
        emit({"ok": False, "authenticated": False, "error": exc.to_dict()})
        return 1
    except Exception:  # noqa: BLE001
        emit(
            {
                "ok": False,
                "authenticated": False,
                "error": BiError("INTERNAL_ERROR", "BI 登录发生未分类错误。").to_dict(),
            }
        )
        return 2

    print(
        f"[bi-login] 登录成功（{credential['source']}），有效期至 {credential['expireAt']}",
        file=sys.stderr,
    )
    emit(credential)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
