"""SCM HTTP 会话与公共参数。

约定：
- 所有接口 POST + JSON，成功码 `40001`；
- 必带请求头 `provideridm = md5(providerId)`；
- 业务码 → 技能错误码映射见 `_CODE_HINT`。
"""

from __future__ import annotations

from datetime import datetime

try:
    import requests
except ImportError:  # 最小环境/沙箱未安装依赖时，模块仍可导入、--help 仍可用
    requests = None  # type: ignore[assignment]

from .errors import SkillError

BASE = "https://scm.ysbang.cn"
SUCCESS_CODES = {"40001"}
TIMEOUT = (10, 120)

_CODE_HINT = {
    "40000": ("AUTH_EXPIRED", "登录已失效，请重新登录", "运行 `python scm.py login --account <账号>`"),
    "40020": ("AUTH_EXPIRED", "会话缺少 cmsToken 或 token 无效", "重新登录以刷新 cmsToken"),
    "40003": ("RATE_LIMITED", "提交过于频繁（1 分钟 / 10 分钟窗口）", "间隔 ≥75 秒，或等待 10 分钟后重试"),
    "40004": ("PARAM_INVALID", "参数异常", "检查参数名与类型（如 storeType 传数字、日期需成对带时分秒）"),
}

_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"


def public_params(token: str, ex: str = "goodsOnShelves") -> dict:
    """公共参数六件套。"""
    return {
        "token": str(token),
        "platform": "scm-admin",
        "version": "1.0.3",
        "ua": _USER_AGENT,
        "ex": ex,
        "lastBuildTime": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def _require_requests():
    if requests is None:
        raise SkillError("DEPENDENCY_MISSING", "缺少依赖 requests",
                         hint="pip install -r requirements.txt")


def build_session(credential: dict) -> requests.Session:
    _require_requests()
    """按凭证构造会话：Cookie + 请求头（含 provideridm）。"""
    provider_id_m = str(credential.get("provider_id_m") or "")
    if not provider_id_m:
        raise SkillError("CREDENTIALS_INVALID", "凭证缺少 provider_id_m", hint="重新登录")
    session = requests.Session()
    session.trust_env = False
    host = __import__("urllib.parse", fromlist=["urlparse"]).urlparse(BASE).hostname
    for name, value in (credential.get("cookies") or {}).items():
        if name and value:
            # 必须显式设 domain，否则无域 cookie 不会被发给 BASE 主机（上传等接口会因此鉴权失败）
            session.cookies.set(name, str(value), domain=host)
    session.headers.update({
        "User-Agent": _USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "Referer": f"{BASE}/web-scm-admin/web/index.html",
        "Origin": BASE,
        "provideridm": provider_id_m,
    })
    return session


def upload_file(credential: dict, token: str, file_bytes: bytes,
                filename: str = "upload.png", ex: str = "goodsOnShelves") -> object:
    """通用图床上传 `POST /scm-base/common/upload2Local`（multipart 字段 `file`）。

    注意：必须用**干净 session + 显式 `Cookie` 头**，不可在 `build_session` 之后再手动加
    `Cookie` 头（会与 jar 内 cookie 叠加成重复/畸形 Cookie 头 → 40002「服务器开小差」）。
    成功返回直链字符串，失败返回 None。
    """
    from urllib.parse import urlparse
    host = urlparse(BASE).hostname
    cookie_str = "; ".join(f"{k}={v}" for k, v in (credential.get("cookies") or {}).items() if k and v)
    pidm = str(credential.get("provider_id_m") or "")
    s = requests.Session()
    s.trust_env = False
    s.headers.update({
        "User-Agent": _USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Referer": f"{BASE}/web-scm-admin/web/index.html",
        "Origin": BASE,
        "provideridm": pidm,
        "Cookie": cookie_str,
    })
    pp = public_params(token, ex)
    try:
        r = s.post(f"{BASE}/scm-base/common/upload2Local", data=pp,
                   files={"file": (filename, file_bytes, "image/png")}, timeout=60)
        j = r.json()
    except Exception:
        return None
    if str(j.get("code")) == "40001":
        d = j.get("data")
        return d if isinstance(d, str) else None
    return None


def post(session: requests.Session, token: str, path: str, body: dict | None = None,
         *, ex: str = "goodsOnShelves") -> object:
    """调用接口并返回 `data`；失败抛 SkillError。"""
    payload = public_params(token, ex)
    if body:
        payload.update(body)
    try:
        response = session.post(f"{BASE}{path}", json=payload, timeout=TIMEOUT)
    except requests.exceptions.Timeout as exc:
        raise SkillError("UPSTREAM_TIMEOUT", "请求超时", hint="稍后重试或检查网络/VPN") from exc
    except requests.exceptions.RequestException as exc:
        raise SkillError("NETWORK_ERROR", "网络请求失败", hint="检查内网/VPN/DNS") from exc

    if response.status_code != 200:
        raise SkillError("HTTP_ERROR", f"HTTP {response.status_code}", details={"path": path})
    try:
        data = response.json()
    except ValueError as exc:
        raise SkillError("RESPONSE_INVALID", "接口返回不是 JSON", details={"path": path}) from exc

    code = str(data.get("code") or "")
    if code not in SUCCESS_CODES:
        err_code, message, hint = _CODE_HINT.get(
            code, ("BUSINESS_ERROR", str(data.get("message") or "业务处理失败"), "")
        )
        raise SkillError(err_code, f"{message}（code={code}）", hint=hint,
                         details={"path": path, "message": data.get("message")})
    return data.get("data")


def call_endpoint(session, url: str, payload: dict, *, method: str = "post",
                  headers: dict | None = None, out: str | None = None) -> dict:
    """通用端点调用：`scm.py call` 的唯一 HTTP 出口。

    与 `post()` 共享公共参数与业务码口径，另支持 GET（query 传参）、自定义请求头、
    以及同步文件流（xlsx/CSV）直接落盘。返回
    `{"kind": "json", "code", "data"}` 或 `{"kind": "file", "path", "bytes", "contentType"}`。
    """
    from pathlib import Path

    opts: dict = {"timeout": TIMEOUT}
    if headers:
        opts["headers"] = headers
    if method.lower() == "get":
        opts["params"] = payload
    else:
        opts["json"] = payload
    try:
        response = session.request(method.upper(), url, **opts)
    except requests.exceptions.Timeout as exc:
        raise SkillError("UPSTREAM_TIMEOUT", "请求超时", hint="稍后重试或检查网络/VPN") from exc
    except requests.exceptions.RequestException as exc:
        raise SkillError("NETWORK_ERROR", "网络请求失败", hint="检查内网/VPN/DNS") from exc

    if response.status_code != 200:
        raise SkillError("HTTP_ERROR", f"HTTP {response.status_code}", details={"url": url})

    try:
        data = response.json()
    except ValueError:
        if not out:
            raise SkillError("RESPONSE_INVALID", "接口返回文件流（非 JSON）",
                             hint="加 --out <文件路径> 落盘，例如同步 xlsx/CSV 导出接口")
        target = Path(out).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(response.content)
        return {"kind": "file", "path": str(target), "bytes": len(response.content),
                "contentType": response.headers.get("Content-Type", "")}

    if not isinstance(data, dict):
        return {"kind": "json", "code": "", "data": data}
    code = str(data.get("code") or "")
    if code not in SUCCESS_CODES:
        err_code, message, hint = _CODE_HINT.get(
            code, ("BUSINESS_ERROR", str(data.get("message") or "业务处理失败"), ""))
        raise SkillError(err_code, f"{message}（code={code}）", hint=hint,
                         details={"url": url, "message": data.get("message")})
    return {"kind": "json", "code": code, "data": data.get("data")}
