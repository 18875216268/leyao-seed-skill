#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PMS 登录 · 企微扫码登录模块（单文件自包含；依赖 requests；二维码窗口用 tkinter 标准库，零额外依赖）。

一个文件 = 一个既能独立运行、也能被任何应用 import 的登录组件。
模块只做一件事：企微扫码 → 拿到「完整 PMS 账户信息」与「完整请求凭证」。

════════════════ 给 AI · Agent 的调用契约（唯一登录入口 · 先读这段） ════════════════
需要 PMS 凭证时：**直接调用本脚本（黑盒使用）；禁止读源码后自写 / 自组装登录流程** ✗。

① 环境自检（首次使用 / 弹窗异常时）：
     python pms_login.py --check
     ——依赖：tkinter（Python 标准库，弹二维码窗口用）；缺失时按输出的 fix 命令修复。

② 先验证（只读、绝不弹窗）：
     python pms_login.py --status --no-remote
     退出码 0 = 已有可用凭证 → 直接使用（stdout 即完整凭证 JSON，含 token）。
③ 需要登录（唯一点：原生扫码窗）——即直接调起登录器原生弹窗：
     python pms_login.py --reuse                      # 独立登录器完整功能.真正全自动.用户体验优先首选！
                                                      # 确保依赖能够支持，环境有问题自动修复环境；
④ 取凭证：--status 输出（同一份凭证仓库，见第五节）。
用户已指定或提供凭证 / 登录方式 → 按其走（不受上列限制）。

禁止：自写登录流程 · 自取二维码 · 自拼鉴权请求 · 组装内部类（LoginFlow 等）·
     绕过本脚本解析凭证。
提示：不要用"文件时间戳"判断登录完成（--status 成功时也会刷新）；
     以本脚本的结果为准。
═══════════════════════════════════════════════════════════════════════════════

登录所需的全部连接配置（PMS 地址、鉴权服务地址、企微应用参数、固定请求头）
已硬编码为文件内的模块常量（PMS_BASE / AUTH_BASE / WECOM_BASE / OAUTH / PMS_HEADERS），
**不读取任何外部配置文件，不含任何固定账号信息**，可直接整体拷走、独立运行。

=========================== 一、直接运行 ===========================
    python pms_login.py                 # 默认：弹出扫码窗，重新登录获取新凭证（需桌面）
    python pms_login.py --status        # 只验证已有凭证是否有效（绝不弹窗）
    python pms_login.py --check         # 环境自检（依赖 tkinter；缺失给出修复指引）
    python pms_login.py --reuse         # 直接调起原生扫码窗：有效复用、失效才弹窗（首选）
                                        # 确保依赖能够支持，环境有问题自动修复环境；
    python pms_login.py --no-remote     # 跳过远端 index 校验

    成功时把「完整凭证 JSON」打印到 stdout，可直接被上游程序解析；扫码成功均自动落库（见第五节）。
    退出码：0 成功 / 1 业务错误 / 2 未分类错误。

=========================== 二、被其它应用调用 ===========================
    from pms_login import (
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
      "token": "...",                  // PMS Token 明文
      "headers": {...},                // PMS 固定请求头 + token，开箱即用
      "validatedAt": ..., "createdAt": ...,
      "pmsBase": "...", "authBase": "...", "wecomBase": "...",
      "credentialPath": "...",         // 本地明文凭证文件
      "user": {"userId":..., "userName":"张三", "accountNo":"LY000123",
               "roleId":..., "roleName":..., "roleType":...,
               "phone":..., "account":...},
      "providers": [{"id": 3364, "name": "重庆央拓"}],   // 账户可见公司（登录时自动带出）
      "provider_id": 3364,           // 公司口径：单公司账号自动确定；多公司时留空
      "provider_name": "重庆央拓",
      "warehouses": [{"providerId": 3364,               // 发货仓清单（登录时自动带出）
                      "warehouseList": [{"warehouseId": 123, "warehouseName": "央拓重庆仓"}]}]
    }

=========================== 四、二维码窗口（tkinter 标准库） ===========================
    窗口标题：PMS · 扫码登录；置顶显示；260px 二维码区。
    ① 打开 → "正在获取二维码……" → 二维码 + "请使用企业微信扫码【剩余 Ns】"（实时倒计时）
    ② 扫码 → 半透明蒙版 + 绿色大√ + "扫码成功！请确认~"
    ③ 手机确认成功 → 保持绿√约 0.9s → 窗口自动关闭 → 凭证落盘
    ④ 二维码失效 / 手机取消 / 超时 → 窗口内自动重载新码（≤3 次）+ "二维码已失效，正在重新加载"；
       扫码后 90 秒未确认同样换码；超过 3 次 → 窗口关闭并抛 QR_EXPIRED
    ⑤ 用户关闭窗口 → LOGIN_CANCELLED

=========================== 五、凭证文件（唯一落盘形态：单账户） ===========================
    所有登录入口（relogin / login_and_store / CLI / 二维码窗口）落盘到同一处：
        %LOCALAPPDATA%\\pms-operations-query\\credential.json
    **一个文件、一份凭证**；明文 JSON 直接落盘（无加解密开销）；原子写入。

    登录即取全「登录信息」：token + 身份（userId / accountNo）+ 公司口径 + 发货仓清单。
    迁移：旧版 accounts/<accountNo>.json 会在首次运行时自动取最近登录的那份迁移过来
          （原目录保留不删）。

    from pms_login import (
        login_and_store,       # 扫码登录 + 按真实身份落盘
        load_credential,       # 读本地凭证（不存在返回 {}）
        save_credential,       # 写本地凭证（原子写）
    )

    cred = login_and_store()          # 扫码，按扫码人身份落盘
    cred["user"]  # {"userId":..., "accountNo":"LY000123", "userName":"张三", ...}

安全说明：
    · 网络侧：使用内置的主机白名单与端点白名单，不引入任何本地服务、
      代理或第三方端点。
    · 存储侧：**全部明文存储，不做任何加解密**（统一落盘为 credential.json
      单文件，无其它形态），
      依赖 %LOCALAPPDATA% 目录的用户级 ACL 保护，请勿外传或纳入整机备份。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterator
from urllib.parse import quote, urljoin, urlparse

import requests
from requests import Response

# --------------------------------------------------------------------------- #
# 错误类型
# --------------------------------------------------------------------------- #
class PmsError(Exception):
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
PMS_BASE = "https://pms.ysbang.cn"
AUTH_BASE = "https://auth.leyopharm.com"
WECOM_BASE = "https://login.work.weixin.qq.com"
DATA_BASE = "https://pms.leyopharm.com"   # 集团数据中心官方主机（发货仓清单接口所在主机）
ORIGIN = "https://pms.ysbang.cn"

APP_VERSION = "14.30.1"
MODULE = "promo_profit_monitor"
USER_AGENT = "pms-cxml/1.08"
WECOM_APP_ID = "wx8c9fab123dec4357"
WECOM_AGENT_ID = "1000054"
WECOM_REDIRECT_URI = "https://auth.leyopharm.com"
# 企微 state：对固定目标地址做双重 quote（与真实客户端一致）
WECOM_STATE_TARGET = "dGVzdGh0dHBzOi8vcG1zLnlzYmFuZy5jbi8jLw=="
WECOM_STATE = quote(quote(WECOM_STATE_TARGET, safe=""), safe="")
WECOM_VERSION = "2.3.2"
PMS_SUBSYSTEM_ID = 200  # PMS 在鉴权服务中的子系统编号
SUCCESS_CODE = "40001"   # 各 PMS / 鉴权接口的成功码（HTTP 始终 200）

CONNECT_TIMEOUT = 10.0   # 秒
READ_TIMEOUT = 130.0     # 秒

# 企微 OAuth 扫码参数（appId / agentId 是公司企微应用标识，扫码登录必需）
OAUTH: dict[str, Any] = {
    "corpId": WECOM_APP_ID,
    "agentId": WECOM_AGENT_ID,
    "redirectUri": WECOM_REDIRECT_URI,
    "state": WECOM_STATE,
    "pollIntervalSeconds": 1.5,
    "qrTimeoutSeconds": 300,
}

# PMS 接口固定请求头（不含任何账号信息；请求者身份由 `token` 请求头决定）
PMS_HEADERS: dict[str, str] = {
    "accept": "application/json, text/plain, */*",
    "appversion": APP_VERSION,
    "platform": "web",
    "module": MODULE,
    "origin": ORIGIN,
    "referer": f"{ORIGIN}/",
    "user-agent": USER_AGENT,
}


# --------------------------------------------------------------------------- #
# HTTP 传输层（固定官方主机 + 端点白名单）
# --------------------------------------------------------------------------- #
_ALLOWED_HOSTS = frozenset(
    {
        urlparse(PMS_BASE).hostname,
        urlparse(AUTH_BASE).hostname,
        urlparse(WECOM_BASE).hostname,
        urlparse(DATA_BASE).hostname,
    }
)
_WECOM_GET_PATHS = frozenset({"/wwlogin/sso/login", "/wwlogin/sso/qrcode"})
_WECOM_POST_PATHS = frozenset({"/wwlogin/monoApi/sso/login/getWebQrCodeStatus"})
_AUTH_POST_PATHS = frozenset(
    {
        "/auth-service/auth/loginByWorkWeChat/v100",
        "/auth-service/auth/index/v100",
    }
)
_PMS_POST_PATHS = frozenset(
    {
        "/api/Index/loginViaLeyoKeyToken/v1170",
        "/api/Index/index/v423",
        "/pms-main/merpUser/getSubProviderList/v2050",
    }
)
# 集团数据中心（官方主机 pms.leyopharm.com）端点白名单：发货仓清单
_DATA_POST_PATHS = frozenset({"/datacenter_pms/web/search/providerWarehouseOption/pv9210"})

CHINA_TZ = timezone(timedelta(hours=8))


def _build_time() -> str:
    """登录接口需要的 buildTime 字段（本地时区时间戳字符串）。"""
    return datetime.now(CHINA_TZ).strftime("%Y-%m-%d %H:%M:%S")


def _pms_form(token: str, *, with_is_auth8: bool = False) -> dict[str, str]:
    """构造 PMS 表单请求体（token 既放在表单也放在请求头）。"""
    form: dict[str, str] = {
        "token": str(token),
        "appVersion": APP_VERSION,
        "platform": "web",
        "timestamp": str(int(time.time())),
        "buildTime": _build_time(),
    }
    if with_is_auth8:
        form["isAuth8"] = "0"
    return form


def _pms_headers(token: str) -> dict[str, str]:
    """PMS 固定请求头 + token（开箱即用的凭证头就是这个）。"""
    headers = dict(PMS_HEADERS)
    headers["token"] = str(token)
    headers["timestamp"] = str(int(time.time()))
    headers["content-type"] = "application/x-www-form-urlencoded"
    return headers


def _pms_ok(body: dict[str, Any]) -> dict[str, Any]:
    """校验 PMS / 鉴权接口的成功码；返回 data 部分。"""
    code = str(body.get("code") or "")
    if code != SUCCESS_CODE:
        raise PmsError(
            "PMS_REQUEST_FAILED",
            f"PMS 接口返回 {code}：{body.get('message') or body.get('msg')}",
        )
    payload = body.get("data")
    return payload if isinstance(payload, dict) else {}


class Transport:
    """登录专用 HTTP 传输层：固定官方主机、端点白名单、不走系统代理。"""

    def __init__(self) -> None:
        self.pms_base = PMS_BASE
        self.auth_base = AUTH_BASE
        self.wecom_base = WECOM_BASE
        self.data_base = DATA_BASE
        self.timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)
        ca_bundle = os.environ.get("PMS_CA_BUNDLE", "").strip()
        if ca_bundle:
            ca_path = Path(ca_bundle).expanduser().resolve()
            if not ca_path.is_file():
                raise PmsError(
                    "TLS_CA_NOT_FOUND",
                    "PMS_CA_BUNDLE 指向的证书文件不存在。",
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

    def close(self) -> None:
        self.session.close()

    def wecom_get(self, path: str, **kwargs: Any) -> Response:
        if path not in _WECOM_GET_PATHS:
            raise PmsError("ENDPOINT_NOT_ALLOWED", "企微请求端点不在白名单中。")
        return self._request("GET", self.wecom_base, path, **kwargs)

    def wecom_post(
        self,
        path: str,
        *,
        params: Any = None,
        json_body: Any,
        headers: dict[str, str],
    ) -> Response:
        if path not in _WECOM_POST_PATHS:
            raise PmsError("ENDPOINT_NOT_ALLOWED", "企微请求端点不在白名单中。")
        return self._request(
            "POST", self.wecom_base, path, params=params, json=json_body, headers=headers
        )

    def auth_post(self, path: str, *, json_body: Any, token: str | None = None) -> Response:
        if path not in _AUTH_POST_PATHS:
            raise PmsError("ENDPOINT_NOT_ALLOWED", "鉴权请求端点不在白名单中。")
        headers = {
            "content-type": "application/json",
            "Authorization": f"Bearer {token}" if token else "Bearer",
            "Referer": f"{self.auth_base}/",
            "Web-Version": "2.8.2",
        }
        return self._request("POST", self.auth_base, path, json=json_body, headers=headers)

    def pms_post(self, path: str, *, token: str, form: dict[str, str]) -> Response:
        if path not in _PMS_POST_PATHS:
            raise PmsError("ENDPOINT_NOT_ALLOWED", "PMS 请求端点不在白名单中。")
        return self._request(
            "POST", self.pms_base, path, data=form, headers=_pms_headers(token)
        )

    def datacenter_post(
        self, path: str, *, token: str, json_body: dict[str, Any]
    ) -> Response:
        """集团数据中心（官方主机）JSON 请求：发货仓清单用。"""
        if path not in _DATA_POST_PATHS:
            raise PmsError("ENDPOINT_NOT_ALLOWED", "数据中心请求端点不在白名单中。")
        headers = _pms_headers(token)
        headers["content-type"] = "application/json"
        return self._request("POST", self.data_base, path, json=json_body, headers=headers)

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
    ) -> Response:
        parsed = urlparse(base)
        if parsed.hostname not in _ALLOWED_HOSTS:
            raise PmsError("ENDPOINT_NOT_ALLOWED", "请求主机不在白名单中。")
        headers = dict(headers or {})
        url = f"{base}{path}"
        try:
            response = self.session.request(
                method,
                url,
                headers=headers,
                json=json,
                data=data,
                params=params,
                timeout=self.timeout,
                verify=self.verify,
                allow_redirects=False,
            )
        except requests.exceptions.SSLError as exc:
            raise PmsError("TLS_VALIDATION_FAILED", "HTTPS 证书验证失败，请检查公司 CA 配置。") from exc
        except requests.exceptions.Timeout as exc:
            raise PmsError("UPSTREAM_TIMEOUT", "PMS 或企微请求超时。", retryable=True) from exc
        except requests.exceptions.ConnectionError as exc:
            raise PmsError(
                "PMS_NETWORK_UNREACHABLE",
                "无法连接 PMS / 企微 / 鉴权服务，请确认公司内网、VPN 和 DNS。",
                retryable=True,
            ) from exc
        except requests.RequestException as exc:
            raise PmsError("NETWORK_ERROR", "网络请求失败。", retryable=True) from exc

        expected_host = parsed.hostname
        final_host = urlparse(response.url).hostname
        if final_host != expected_host or any(
            urlparse(item.url).hostname != expected_host for item in response.history
        ):
            raise PmsError("REDIRECT_NOT_ALLOWED", "请求离开了固定的官方主机。")
        if 300 <= response.status_code < 400:
            location = response.headers.get("Location") or ""
            redirect_host = urlparse(urljoin(response.url, location)).hostname
            if redirect_host != expected_host:
                raise PmsError("REDIRECT_NOT_ALLOWED", "官方接口返回了未允许的重定向。")
            raise PmsError("AUTH_EXPIRED", "PMS 登录已过期，请重新扫码登录。")

        if response.status_code == 401:
            raise PmsError("AUTH_EXPIRED", "PMS 登录已过期，请重新扫码登录。")
        if response.status_code == 403:
            raise PmsError("AUTH_FORBIDDEN", "当前账号无权执行该请求。")
        if response.status_code == 429:
            raise PmsError("RATE_LIMITED", "请求过于频繁。", retryable=True)
        if response.status_code in (502, 503, 504):
            raise PmsError(
                "UPSTREAM_UNAVAILABLE",
                f"上游暂时不可用（HTTP {response.status_code}）。",
                retryable=True,
            )
        if response.status_code >= 400:
            raise PmsError(
                "HTTP_ERROR",
                f"请求失败（HTTP {response.status_code}）。",
                details={"status": response.status_code},
            )
        return response

    @staticmethod
    def json(response: Response) -> dict[str, Any]:
        try:
            data = response.json()
        except ValueError as exc:
            raise PmsError("RESPONSE_INVALID_JSON", "接口返回了无效 JSON。") from exc
        if not isinstance(data, dict):
            raise PmsError("RESPONSE_SCHEMA_CHANGED", "接口返回结构不是 JSON 对象。")
        return data


# --------------------------------------------------------------------------- #
# 本地凭证存储（单文件，全部明文 JSON）
# --------------------------------------------------------------------------- #
def _data_home() -> Path:
    override = os.environ.get("PMS_OPERATIONS_HOME", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "pms-operations-query"
    xdg = os.environ.get("XDG_DATA_HOME", "").strip()
    return (Path(xdg).expanduser() if xdg else Path.home() / ".local" / "share") / "pms-operations-query"


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
    "PmsError",
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
    {"AUTH_EXPIRED", "AUTH_TOKEN_MISSING", "REDIRECT_NOT_ALLOWED"}
)

# 换取 PMS Token 的响应直接携带身份字段；只保留身份相关字段存进凭证。
_USER_INFO_FIELDS = (
    "userId",
    "userName",
    "accountNo",
    "roleId",
    "roleName",
    "roleType",
)

_QR_PATTERN = re.compile(r"wwlogin/sso/qrcode\?key=([a-f0-9]{16})")
_RELOAD = object()  # _poll 的返回值哨兵：表示需要重新加载二维码
CONFIRM_WAIT_SECONDS = 90   # 已扫码后的等待确认上限（秒）：超过即视为拒绝/无响应 → 换码重扫


# --------------------------------------------------------------------------- #
# 基础工具
# --------------------------------------------------------------------------- #
def _extract_qr_key(html: str) -> str:
    match = _QR_PATTERN.search(html or "")
    if not match:
        raise PmsError("QR_CREATE_FAILED", "企微登录页中没有找到二维码 key。")
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


def _safe_user(data: dict[str, Any]) -> dict[str, Any]:
    """从换取 PMS Token 的响应里只挑身份字段（避免把无关数据存进来）。"""
    slim: dict[str, Any] = {}
    for key in _USER_INFO_FIELDS:
        value = data.get(key)
        if value in (None, "", [], {}):
            continue
        slim[key] = value
    return slim


def _identity_of(user_info: dict[str, Any]) -> str:
    """取账号标识：优先 accountNo（可读、与 PMS 账号一致），退化到 userName / userId。"""
    for key in ("accountNo", "userName", "userId"):
        value = str(user_info.get(key) or "").strip()
        if value:
            return value
    raise PmsError("ACCOUNT_INVALID", "用户信息中没有可用的账号标识。")


def _validate_token_remote(transport: Transport, token: str) -> None:
    """远端校验一份 PMS 凭证（POST /api/Index/index/v423）。

    校验接口（index）的失败即「凭证不可用」——统一归 AUTH_EXPIRED
    （与 BI 版同源；含服务器「无权限或者token已经过期」40007 一类的拒绝）。
    """
    try:
        _pms_ok(
            transport.json(
                transport.pms_post(INDEX_PATH, token=token, form=_pms_form(token))
            )
        )
    except PmsError as exc:
        if exc.code == "PMS_REQUEST_FAILED":
            raise PmsError(
                "AUTH_EXPIRED", f"PMS 凭证验证失败，请重新扫码登录（{exc.message}）"
            ) from exc
        raise


def collect_login_scope(token: str) -> dict[str, Any]:
    """取账户可见的 PMS 数据口径（**登录信息的一部分**）：公司列表 + 发货仓清单。

    为什么在这里取：扫码只回答「你是谁」，不回答「你能看哪些公司 / 哪些仓」——这两项来自
    PMS 官方接口（都已在传输层主机/端点白名单内，均为集团官方主机）：
      · 公司列表   `getSubProviderList`（pms.ysbang.cn，与登录同一主机）
      · 发货仓清单 `providerWarehouseOption`（pms.leyopharm.com，集团数据中心主机）

    并入凭证后，Agent 在**同一处**即可取到全部登录信息（token + 身份 + 公司 + 仓库），
    使用任何子 skill 时直接传参即可（见 vendor/SUBSKILL_ROUTING.md §3 第 6 条）。

    单公司账号 → 直接给出 `provider_id` / `provider_name`；多公司 → `provider_id` 留空、列候选。
    `warehouses` 落盘供查询时选择；**不自动收窄** `warehouse_ids`（默认 = 全部发货仓，
    需要收敛时由调用方显式传 `--warehouse-id`）。任一接口失败都只损失该部分，不阻断登录。
    """
    transport = Transport()
    try:
        scope: dict[str, Any] = {}
        try:
            pbody = transport.json(
                transport.pms_post(PROVIDERS_PATH, token=str(token), form=_pms_form(str(token)))
            )
        except Exception:  # noqa: BLE001 —— 取不到不影响登录与取数
            pbody = {}
        options = [
            {"id": item.get("id"), "name": item.get("name")}
            for item in (pbody.get("data") if isinstance(pbody.get("data"), list) else [])
            if isinstance(item, dict) and item.get("id") is not None
        ]
        if options:
            scope["providers"] = options
            if len(options) == 1:
                scope["provider_id"] = options[0]["id"]
                scope["provider_name"] = options[0].get("name") or ""
        try:
            wbody = transport.json(
                transport.datacenter_post(
                    WAREHOUSES_PATH,
                    token=str(token),
                    json_body={"token": str(token), "buildTime": _build_time()},
                )
            )
        except Exception:  # noqa: BLE001
            wbody = {}
        warehouses = []
        for item in (wbody.get("data") if isinstance(wbody.get("data"), list) else []):
            if not isinstance(item, dict):
                continue
            warehouses.append({
                "providerId": item.get("providerId"),
                "warehouseList": [
                    {"warehouseId": wh.get("warehouseId"),
                     "warehouseName": wh.get("warehouseName") or wh.get("name")}
                    for wh in (item.get("warehouseList") or [])
                    if isinstance(wh, dict) and wh.get("warehouseId") is not None
                ],
            })
        if warehouses:
            scope["warehouses"] = warehouses
        return scope
    finally:
        transport.close()


def fetch_user_info(credential: dict[str, Any]) -> dict[str, Any]:
    """查询某份凭证**实际属于哪个用户**。

    PMS 与 BI 不同：扫码换取 PMS Token 的响应本身就携带 userId / userName /
    accountNo / 角色 等身份字段（无需再调单独的 profile 接口），因此这里的
    「账户信息」是在登录时一并取回、随凭证保存的，本函数直接返回它。

    参数：
        credential  登录得到的完整凭证（需含 user）

    返回：身份信息字典，例如
        {"userId": "…", "userName": "张三", "accountNo": "LY000123",
         "roleId": …, "roleName": …, "roleType": …, "phone": …, "account": …}

    抛出：PmsError —— 凭证中没有账户信息（USER_INFO_FAILED）
    """
    user = credential.get("user")
    if not isinstance(user, dict) or not user:
        raise PmsError("USER_INFO_FAILED", "凭证中没有账户信息，请重新登录。")
    return user


def _check_credential(
    credentials: dict[str, Any] | None,
    *,
    validate_remote: bool,
) -> tuple[str | None, PmsError | None]:
    """检查一份凭证是否可用；返回 (reason, error)，两者皆 None 表示有效。

    reason 取值：missing / expired / invalid / not_validated（网络类未通过，不代表凭证失效）；
    reason 与 error.code 同源（凭证类错误给出明确的 expired / invalid）。
    凭证校验共用这一套判定。
    """
    if not credentials:
        return "missing", PmsError("AUTH_REQUIRED", "尚未登录 PMS，请先执行登录。")
    if validate_remote:
        transport = Transport()
        try:
            _validate_token_remote(transport, str(credentials.get("token") or ""))
        except PmsError as exc:
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
        credentials  凭证本体，至少含 token；可选 createdAt / validatedAt / user
        source       "local"（复用本地凭证）或 "qr"（本次新扫码）
        reused       本次结果是否为复用旧凭证

    返回：完整凭证字典（字段见模块文档「三、返回的完整凭证」）。

    说明：一般不必直接调用，verify_credential() / relogin() 已返回同样结构。
    """
    token = str(credentials.get("token") or "")

    headers = _pms_headers(token)
    result: dict[str, Any] = {
        "ok": True,
        "authenticated": True,
        "source": source,
        "reused": reused,
        "token": token,
        "headers": headers,
        "createdAt": int(credentials.get("createdAt") or 0),
        "validatedAt": int(credentials.get("validatedAt") or 0),
        "pmsBase": PMS_BASE,
        "authBase": AUTH_BASE,
        "wecomBase": WECOM_BASE,
        "credentialPath": str(credentials.get("credentialPath") or ""),
    }
    user = credentials.get("user")
    if user:
        result["user"] = user
    return result


# --------------------------------------------------------------------------- #
# 登录流程内核（弹窗内部组件：不依赖 Qt，但不对外暴露）
# --------------------------------------------------------------------------- #
QR_LOGIN_PATH = "/wwlogin/sso/login"
QR_IMAGE_PATH = "/wwlogin/sso/qrcode"
QR_STATUS_PATH = "/wwlogin/monoApi/sso/login/getWebQrCodeStatus"
AUTH_LOGIN_PATH = "/auth-service/auth/loginByWorkWeChat/v100"
AUTH_INDEX_PATH = "/auth-service/auth/index/v100"
LOGIN_TOKEN_PATH = "/api/Index/loginViaLeyoKeyToken/v1170"
INDEX_PATH = "/api/Index/index/v423"
PROVIDERS_PATH = "/pms-main/merpUser/getSubProviderList/v2050"
WAREHOUSES_PATH = "/datacenter_pms/web/search/providerWarehouseOption/pv9210"


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
        run()  执行一次完整登录，返回完整凭证字典；失败抛 PmsError。
               内部会在二维码失效 / 被取消 / 超时时自动重新加载。

    属性：
        last_error  最近一次错误（PmsError 或 None）

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
        self.last_error: PmsError | None = None
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
                except PmsError as exc:
                    raise self._fail(exc)

                self.on_qr(png)
                self.on_stage(STAGE_QR_READY, STATUS_SCAN)

                # ---- 第二步：轮询扫码与确认 ---- #
                outcome = self._poll(transport, qr_key, sso_url)
                if outcome is _RELOAD:
                    reloads += 1
                    if reloads > self.max_auto_reload:
                        raise self._fail(
                            PmsError("QR_EXPIRED", "二维码多次失效，请点击重试。")
                        )
                    self.on_notice("二维码已失效，正在重新加载")
                    continue
                if self.is_aborted():
                    raise self._abort_error()

                # ---- 第三步：换取并校验凭证 ---- #
                self.on_stage(STAGE_AUTHENTICATING, STATUS_LOGGING_IN)
                try:
                    return self._finish(transport, str(outcome))
                except PmsError as exc:
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
            QR_LOGIN_PATH,
            params={
                "login_type": "CorpApp",
                "appid": oauth["corpId"],
                "agentid": oauth["agentId"],
                "redirect_uri": oauth["redirectUri"],
                "state": oauth["state"],
                "redirect_type": "callback",
                "panel_size": "small",
                "lang": "zh",
                "version": WECOM_VERSION,
            },
        )
        qr_key = _extract_qr_key(response.text)
        image = transport.wecom_get(QR_IMAGE_PATH, params={"key": qr_key})
        png = image.content
        if not png:
            raise PmsError("QR_CREATE_FAILED", "二维码图片为空。")
        return qr_key, png, response.url

    def _poll(self, transport: Transport, qr_key: str, sso_url: str) -> Any:
        """轮询扫码状态。

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
                    QR_STATUS_PATH,
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
                body = Transport.json(response)
            except PmsError as exc:
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
        # 1) 用授权码向鉴权服务换取 Leyo Token
        data = _pms_ok(
            transport.json(
                transport.auth_post(AUTH_LOGIN_PATH, json_body={"code": auth_code})
            )
        )
        leyo_token = str(data.get("token") or "")
        if not leyo_token:
            raise PmsError("AUTH_TOKEN_MISSING", "扫码成功，但鉴权服务未返回 Token。")

        # 2) 校验该企微账号是否拥有 PMS 子系统（200）权限
        index = _pms_ok(
            transport.json(
                transport.auth_post(AUTH_INDEX_PATH, json_body={}, token=leyo_token)
            )
        )
        subsystems = {str(v) for v in (index.get("subsystems") or [])}
        if str(PMS_SUBSYSTEM_ID) not in subsystems:
            raise PmsError(
                "PMS_SUBSYSTEM_UNAUTHORIZED",
                "该企微账号无权访问 PMS 系统（缺少子系统 200）。",
            )

        # 3) 用 Leyo Token 换取 PMS Token（响应携带账户信息）
        pms = _pms_ok(
            transport.json(
                transport.pms_post(
                    LOGIN_TOKEN_PATH,
                    token=leyo_token,
                    form=_pms_form(leyo_token, with_is_auth8=True),
                )
            )
        )
        pms_token = str(pms.get("token") or "")
        if not pms_token:
            raise PmsError("AUTH_TOKEN_MISSING", "PMS 登录未返回 Token。")
        user = _safe_user(pms)

        # 4) 激活会话（用 PMS Token 再走一次登录接口）
        _pms_ok(
            transport.json(
                transport.pms_post(
                    LOGIN_TOKEN_PATH,
                    token=pms_token,
                    form=_pms_form(pms_token, with_is_auth8=True),
                )
            )
        )

        # 5) 远端校验 PMS Token，并取回 userInfo（phone / account）
        validated = _pms_ok(
            transport.json(
                transport.pms_post(INDEX_PATH, token=pms_token, form=_pms_form(pms_token))
            )
        )
        profile = validated.get("userInfo")
        info = profile if isinstance(profile, dict) else {}
        for key in ("phone", "account"):
            value = info.get(key)
            if value not in (None, "", [], {}):
                user[key] = value

        return build_credential(
            {
                "pmsBase": PMS_BASE,
                "token": pms_token,
                "createdAt": int(time.time()),
                "validatedAt": int(time.time()),
                "user": user,
            },
            source="qr",
            reused=False,
        )

    # --------------------------- 错误收口 --------------------------- #
    def _sleep_or_abort(self, seconds: float) -> bool:
        if not _interruptible_sleep(seconds, self.is_aborted):
            raise self._abort_error()
        return True

    def _abort_error(self) -> PmsError:
        exc = PmsError("LOGIN_CANCELLED", "登录已取消。")
        self.last_error = exc
        return exc

    def _fail(self, exc: PmsError) -> PmsError:
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
        validate_remote  True  → 额外请求 /api/Index/index/v423 做远端校验（默认）
                        False → 只做本地检查，不发网络请求
        raise_on_invalid True  → 凭证无效时直接抛出 PmsError
                        False → 不抛异常，返回 ok=False 的结果字典（默认）

    返回：
        有效 → 完整凭证（authenticated=True，source="local"）
        无效 → {"ok": False, "authenticated": False, "reason": ..., "error": {...}}

    reason 取值：missing（本地没有任何账号）/ invalid（凭证损坏或字段缺失）
                / expired（远端判定登录已过期）
                / not_validated（远端校验未通过：网络 / 限流类，不代表凭证失效）
    """
    _migrate_legacy_accounts()
    cred_path = _credential_file()

    def _invalid(reason: str, exc: PmsError) -> dict[str, Any]:
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

    credential = load_credential()
    if not credential:
        return _invalid("missing", PmsError("AUTH_REQUIRED", "尚未登录 PMS，请先执行登录。"))

    reason, error = _check_credential(credential, validate_remote=validate_remote)
    if reason or credential is None:
        return _invalid(
            reason or "invalid",
            error or PmsError("AUTH_REQUIRED", "本地凭证不可用。"),
        )

    credential["validatedAt"] = int(time.time())
    if validate_remote and not (credential.get("providers") and credential.get("warehouses")):
        # 自愈：为老凭证补「公司 + 仓库口径」（登录信息的一部分）——补齐一次后长期复用
        credential.update(collect_login_scope(str(credential.get("token") or "")))
    save_credential(credential)
    result = dict(credential)
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
        validate_remote  True  → 额外做远端 /api/Index/index/v423 校验（默认）
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
        validate_remote True  → 复用时额外请求 /api/Index/index/v423（默认）
                        False → 复用时只做本地检查，不发网络请求
        interactive     True  → 允许弹窗扫码（默认）
                        False → 非交互（调用方保证不弹窗）；凭证不可用时不弹窗，直接抛 PmsError
        parent          兼容保留参数（不使用）

    返回：完整凭证字典（同 build_credential()）；新扫码成功后自动落库并补齐公司/仓口径（与 relogin() 一致）。

    抛出：
        PmsError —— 非交互模式下凭证不可用，或遇到网络/权限类不可恢复错误。
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
            raise PmsError(code or "AUTH_REQUIRED", message)

    if not interactive:
        raise PmsError(
            "AUTH_REQUIRED",
            "本地没有可用凭证（非交互模式，绝不弹窗）。"
            "需要新登录时请运行：python pms_login.py --reuse（原生扫码窗）。",
        )
    # 新扫码成功即补全登录信息并落库（与 relogin() / login_and_store 同源 ✓）
    return _store_scanned_credential(run_login_dialog(parent=parent))


def relogin(*, parent: Any = None) -> dict[str, Any]:
    """功能一：无论本地是否已有凭证，都弹出扫码窗重新登录，返回全新凭证。

    登录成功后按扫码人身份落入本地凭证文件（credential.json）。

    参数：
        parent   兼容保留参数（不使用）

    返回：完整凭证字典（source="qr"、reused=False）。

    抛出：PmsError —— 用户取消（LOGIN_CANCELLED）、二维码多次失效或网络类错误。
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
    """一次性迁移：旧版 accounts/ 多账号文件 → 单文件凭证（取最近登录的那份）。"""
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
    """校验扫码人身份 → 补齐公司 / 仓口径 → 写入本地凭证文件（单账户）。"""
    fetch_user_info(credential)      # 查不到「刚才是谁扫的」→ USER_INFO_FAILED
    # 登录即取全「登录信息」：token + 身份 + 公司口径 + 发货仓清单（取不到不影响登录）
    credential.update(collect_login_scope(str(credential.get("token") or "")))
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
        用户关窗 → PmsError(LOGIN_CANCELLED)。

    参数：
        parent   兼容保留参数（不使用）

    返回：成功 → 完整凭证字典（source="qr"、reused=False）。
    抛出：PmsError —— LOGIN_CANCELLED（用户取消）/ QR_EXPIRED（二维码多次失效）
                    / 网络、限流、权限等不可恢复错误。
    """
    import queue as _queue
    import threading as _th
    import tkinter as tk

    root = tk.Tk()
    root.title("PMS · 扫码登录")
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

    tip = tk.Label(root, text="正在获取二维码……", font=(_FONT_FAMILY, 10),
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
                          font=(_FONT_FAMILY, 10))
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
                      font=(_FONT_FAMILY, 10, "bold"))

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
        raise PmsError("LOGIN_CANCELLED", "用户取消了登录。")
    return result["cred"]


def check_env() -> dict[str, Any]:
    """环境自检：登录器可调用性（tkinter / 凭证仓库可写）与下一步指引；绝不弹窗。"""
    out: dict[str, Any] = {
        "ok": True,
        "python": sys.version.split()[0],
        "gui": None,
        "credentialDir": str(_data_home()),
        "fix": None,
        "next": "python pms_login.py --reuse（弹窗登录）｜--status（只验证）",
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="PMS 登录 · 企微扫码登录（默认弹出扫码窗重新登录；也可只验证已有凭证）",
        epilog=(
            "给 AI · Agent 的调用契约（唯一登录入口 → 直接调用本登录器（黑盒）；禁止读源码后自写登录）：\n"
            "  1) 自检：--check（依赖 tkinter；缺失给出修复指引）\n"
            "  2) 验证：--status（退出码 0 = 已有可用凭证，直接用）\n"
            "  3) 登录：--reuse（唯一点：直接调起原生扫码窗；有效复用、失效才弹窗；依赖缺失自动修复环境）\n"
            "  4) 取凭证：--status 输出（另：Python 门面 relogin / verify_credential /\n"
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
        help="功能二：只验证已有凭证是否有效，绝不弹窗",
    )
    parser.add_argument(
        "--reuse",
        action="store_true",
        help="优先复用本地有效凭证，仅在失效时才弹窗（默认总是重新扫码）",
    )
    parser.add_argument("--no-remote", action="store_true", help="跳过远端 index 校验")
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
                "[pms-login] "
                + ("凭证有效" if result["authenticated"] else f"凭证无效：{result.get('reason')}"),
                file=sys.stderr,
            )
            emit(result)
            return 0 if result["authenticated"] else 1

        # 默认：无论本地是否已有凭证，都弹窗重新扫码获取新凭证。
        credential = get_credential(
            force_relogin=not args.reuse,
            validate_remote=not args.no_remote,
            interactive=True,
        )
    except PmsError as exc:
        emit({"ok": False, "authenticated": False, "error": exc.to_dict()})
        return 1
    except Exception:  # noqa: BLE001
        emit(
            {
                "ok": False,
                "authenticated": False,
                "error": PmsError("INTERNAL_ERROR", "PMS 登录发生未分类错误。").to_dict(),
            }
        )
        return 2

    print(
        f"[pms-login] 登录成功（{credential['source']}），账户 {credential.get('user', {}).get('accountNo', '')}",
        file=sys.stderr,
    )
    emit(credential)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
