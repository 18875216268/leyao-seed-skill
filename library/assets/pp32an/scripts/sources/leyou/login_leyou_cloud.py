#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
乐药云智库 · 独立登录器（单文件自包含；与 BI / PMS 登录器同构）
模块只做一件事：企微扫码 → 拿到完整凭证并落盘。

════════════════ 给 AI · Agent 的调用契约（唯一登录入口 · 先读这段） ════════════════
需要云智库凭证时：**直接调用本脚本（黑盒使用）；禁止读源码后自写 / 自组装登录流程** ✗。

① 环境自检（首次使用 / 弹窗异常时）：
     python login_leyou_cloud.py --check
     ——依赖：tkinter（Python 标准库，弹二维码窗口用）；缺失时按输出的 fix 命令修复。
② 先验证（只读、绝不弹窗）：
     python login_leyou_cloud.py --status
     退出码 0 = 已有可用凭证 → 直接使用。
③ 需要登录（唯一点：原生扫码窗）：
     python login_leyou_cloud.py --reuse
     弹窗直达用户桌面；有效凭证自动复用、失效才弹窗；扫码成功自动关闭并落盘。
     弹窗失败 → --check 修复环境后重试；仍无法 → 询问用户（**不得绕路出码 / 自写登录** ✗）。
④ 取凭证：--status（或门面 API：relogin / verify_credential / get_credential /
     is_authenticated）。
用户已指定或提供凭证 / 登录方式 → 按其走（不受上列限制）。

禁止：自写登录流程 · 出码绕路 · 自取二维码 · 自拼鉴权请求 · 组装内部类（LoginFlow 等）·
     绕过本脚本解析凭证。
═══════════════════════════════════════════════════════════════════════════════

覆盖能力：
- 扫码登录（企业微信）：取登录 URL → 提取 key/sessionSignature → 二维码 →
  轮询 auth_code → 拼回调换 token → 取 uuid/水印 → 保存凭证 → 自动关闭并删码；
- 凭证复用 / 校验：本地检查 + 远端校验（get-list 实测协议：200/507），**绝不弹窗**；
- 登录内核 `LoginFlow`（弹窗内部组件，不对外）：取码 / 轮询 / 回调全流程，不依赖界面框架；
- 弹窗零额外依赖：tkinter（标准库）；二维码与绿色大√均由 Canvas 原生绘制（**不需要 PIL**）。

两种使用方式（对标 login_bi.py / pms_login.py）：
1) 命令行直接运行（两个接口 + 环境自检；**无出码 / 无界面模式**）：
     python login_leyou_cloud.py                 # 默认：弹窗扫码重新登录，输出全新凭证
     python login_leyou_cloud.py --reuse         # 有效则复用，失效才弹窗（首选）
     python login_leyou_cloud.py --status        # 只验证已有凭证（绝不弹窗）
     python login_leyou_cloud.py --check         # 环境自检（tkinter；异常给修复指引）
     python login_leyou_cloud.py --no-remote     # 跳过远端校验（只做本地检查）
2) Python 调用（只用门面；禁止组装内部类 LoginFlow）：
     from login_leyou_cloud import (
         relogin,             # 弹窗扫码重登，返回全新凭证（并按 token-file 落盘）
         verify_credential,   # 验证凭证（绝不弹窗）
         get_credential,      # 组合入口：强制重登 / 复用
         is_authenticated,    # 快捷：现在能不能用
         build_credential,    # 手工打包凭证
     )

凭证（唯一落盘形态）：JSON 单文件
  `{token, uuid, watermark, login_at, expires_at}`
  默认路径：资产数据区（存在 `scripts/common.py` 时随其权威解析，与桥接同一落点）→
  `$LEYAO_KB_HOME/leyou_token.json` → `~/.leyao-kb/leyou_token.json`（可用 --token-file 覆盖）。
  字段与业务客户端 leyou_cloud.py 完全兼容（同一文件、同一字段）。

安全边界：
- 登录全程只访问固定官方主机（helplook.net 系 + login.work.weixin.qq.com），无本地服务、无代理；
- 凭证为明文 JSON（不做加解密），仅可写入用户数据区（包内零写入）；
- 只有「凭证本身不可用」（missing / expired / invalid）才允许弹窗；
  网络 / 限流类失败一律直接报错，**不会莫名其妙弹登录窗**。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import tempfile
import time
import io as _io
from datetime import datetime

import requests

# ---------------- 站点级常量（勿改） ----------------
TENANT_ID   = "8980"
SITE        = "https://leyohrai.helplook.net"
BASE_GET    = "https://api-get.helplook.net"      # 只读数据域名（校验/水印用）
CALLBACK    = "https://api-sh.helplook.net/oauth/callback-wechat-work-oauth/customer-auth-login"
POLL_URL    = "https://login.work.weixin.qq.com/wwlogin/monoApi/sso/login/getWebQrCodeStatus"
QR_IMG_URL  = "https://login.work.weixin.qq.com/wwlogin/sso/qrcode"
DEFAULT_UUID = "iKMAE54kytaWpL7Z401jh"            # 登录后取不到 hl_uuid 时的兜底（搜索需要）
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

DEFAULT_TIMEOUT = 20          # 常规请求超时（秒）
DEFAULT_MAX_WAIT = 300        # 扫码等待上限（秒）
CONFIRM_WAIT_SECONDS = 90     # 已扫码后的等待确认上限（秒）：超过即视为拒绝/无响应 → 换码重扫

# 登录弹窗窗口图标（笔记本+对勾）；首次渲染后缓存 PNG bytes


# ---------------- 默认 token 文件（与资产数据区对齐；包内零写入） ----------------
def _default_token_file() -> str:
    """默认凭证路径：资产内运行时与数据区对齐；独立拷贝时回落用户区。

    优先级：
      1) 资产在包内运行：复用 `scripts/common.py` 的 `LEYOU_TOKEN_F`（数据区规则的唯一权威，
         含框架挂载 / LEYAO_KB_HOME 判定）——与桥接、人工登录落点完全一致；
      2) 独立单文件运行：`$LEYAO_KB_HOME/leyou_token.json` → `~/.leyao-kb/leyou_token.json`。
    """
    try:  # 1) 资产体系（…/scripts/common.py 存在则用其权威解析）
        _scripts = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if os.path.isfile(os.path.join(_scripts, "common.py")):
            if _scripts not in sys.path:
                sys.path.insert(0, _scripts)
            from common import LEYOU_TOKEN_F   # noqa: PLC0415 —— 延迟导入：独立拷贝时无此模块
            return str(LEYOU_TOKEN_F)
    except Exception:
        pass
    # 2) 独立拷贝：用户区
    env = (os.environ.get("LEYAO_KB_HOME") or "").strip()
    base = os.path.expanduser(env) if env else os.path.join(os.path.expanduser("~"), ".leyao-kb")
    return os.path.join(base, "leyou_token.json")


DEFAULT_TOKEN_FILE = _default_token_file()


# ---------------- 错误体系（统一 code / message / retryable） ----------------
class LeyouLoginError(Exception):
    """统一登录错误：code 机器可读，message 中文说明，retryable 是否可重试。"""

    def __init__(self, code: str, message: str = "", retryable: bool = False):
        super().__init__(message or code)
        self.code = code
        self.message = message or code
        self.retryable = retryable

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "retryable": self.retryable}


# 错误码常量（登录器自有；业务侧 TokenExpired/LoginRequired 为兼容符号）
AUTH_REQUIRED       = "AUTH_REQUIRED"        # 本地无凭证
AUTH_EXPIRED        = "AUTH_EXPIRED"         # 本地凭证已过期（按 expires_at 参考值）
CREDENTIALS_INVALID = "CREDENTIALS_INVALID"  # 凭证文件损坏 / 远端判定失效
NOT_VALIDATED       = "NOT_VALIDATED"        # 远端校验未通过（网络/限流类，不弹窗）
LOGIN_CANCELLED     = "LOGIN_CANCELLED"      # 用户取消 / 关闭窗口
QR_EXPIRED          = "QR_EXPIRED"           # 二维码失效 / 等待扫码超时
QR_CREATE_FAILED    = "QR_CREATE_FAILED"     # 拉取企微登录页 / 二维码失败
NETWORK_ERROR       = "NETWORK_ERROR"        # 网络不可达 / 超时（可重试）
INTERNAL_ERROR      = "INTERNAL_ERROR"       # 未分类异常

# 「凭证本身不可用」→ 复用路径允许弹窗；其余错误一律直接抛出（不弹窗）
_POPUP_REASONS = ("missing", "expired", "invalid")


class TokenExpired(Exception):
    """token 失效（服务端业务码 507）——业务层兼容符号。"""


class LoginRequired(Exception):
    """需要登录但被禁止自动扫码——业务层兼容符号。"""


# ---------------- 凭证文件读写（原子写 + 字段兼容） ----------------
def load_credential(token_file: str | None = None) -> dict:
    """读取凭证文件；不存在或损坏返回 {}（绝不抛异常）。兼容 UTF-8 BOM。"""
    path = token_file or DEFAULT_TOKEN_FILE
    try:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_credential(token_file: str, store: dict) -> str:
    """原子写入凭证文件（临时文件 + os.replace），返回绝对路径。

    唯一落盘格式：{token, uuid, watermark, login_at, expires_at}（与业务客户端兼容）。
    """
    path = os.path.abspath(token_file or DEFAULT_TOKEN_FILE)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


# ---------------- 会话 / 小工具 ----------------
def _new_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": SITE + "/",
    })
    return s


def _http_get(session: requests.Session, url: str, *, params=None, headers=None,
              timeout: float = DEFAULT_TIMEOUT, retries: int = 3):
    """带轻量重试的 GET（网络类异常最多重试 retries 次）；请求异常统一抛 NETWORK_ERROR。"""
    last = None
    for i in range(max(1, retries)):
        try:
            return session.get(url, params=params, headers=headers, timeout=timeout)
        except requests.exceptions.RequestException as e:
            last = e
            time.sleep(0.5 * (i + 1))
    raise LeyouLoginError(NETWORK_ERROR, f"网络请求失败：{last!r}"[:200], retryable=True)


def _local_check(store: dict) -> str:
    """本地检查：ok / missing / expired。expires_at 为登录时的 30 天参考值。"""
    token = store.get("token")
    if not token:
        return "missing"
    exp = str(store.get("expires_at") or "").strip()
    if exp:
        try:
            if datetime.strptime(exp[:10], "%Y-%m-%d").date() < datetime.now().date():
                return "expired"
        except ValueError:
            pass
    return "ok"


def _remote_probe(session: requests.Session, token: str, uuid: str,
                  timeout: float = DEFAULT_TIMEOUT) -> tuple[str, dict]:
    """远端校验（实测协议：get-list 带 token 200 / 无 token 507）。

    返回 (status, info)：status = "ok" | "invalid" | "not_validated"；
    info = {categories, first_category}（ok 时）。
    """
    try:
        r = session.get(f"{BASE_GET}/foreground/content/get-list",
                        params={"tannant_id": TENANT_ID, "data_type": 1},
                        headers={"x-auth-token": token}, timeout=timeout)
    except requests.exceptions.RequestException:
        return "not_validated", {}
    try:
        j = r.json()
    except ValueError:
        return "not_validated", {}
    if isinstance(j, dict) and j.get("code") == 507:
        return "invalid", {}
    lst = ((j.get("data") or {}).get("list") or []) if isinstance(j, dict) else []
    if isinstance(j, dict) and j.get("code") == 200 and lst:
        return "ok", {"categories": len(lst),
                      "first_category": lst[0].get("name", "")}
    return "invalid", {}


# ---------------- 凭证打包 ----------------
def build_credential(store: dict, *, source: str, reused: bool,
                     token_file: str | None = None) -> dict:
    """把凭证存储包装成对外完整凭证（token/cookies/endpoints 开箱即用）。"""
    token = store.get("token") or ""
    uuid = store.get("uuid") or ""
    path = os.path.abspath(token_file or DEFAULT_TOKEN_FILE)
    return {
        "ok": True,
        "authenticated": bool(token),
        "source": source,                 # "qr" = 本次新扫码；"local" = 复用本地
        "reused": reused,
        "token": token,
        "uuid": uuid,
        "watermark": store.get("watermark") or "",
        "login_at": store.get("login_at"),
        "expires_at": store.get("expires_at"),
        "cookies": {                      # 可直接塞进任何 HTTP 客户端
            "hlsdk_token_cp7nb9": token,
            "hl_siteid_8980": token,
            "hl_uuid": uuid,
        },
        "endpoints": {"get": BASE_GET, "site": SITE},
        "credentialPath": path,
    }


class LoginFlow:
    """扫码登录全过程内核（不依赖 tkinter；弹窗为唯一对外形态）。

    注：本类不是"无界面登录方式"——本登录器只提供原生弹窗登录，
    外部取凭证请用门面（relogin / get_credential），禁止组装本类。

    阶段常量（仅供本文件内置窗口使用；禁止外部自建界面）：
      STAGE_LOADING / STAGE_QR_READY / STAGE_SCANNED / STAGE_AUTHENTICATING / STAGE_FAILED
    文案常量：STATUS_LOADING / STATUS_SCAN / STATUS_CONFIRM / STATUS_LOGGING_IN / STATUS_RETRY
    """

    STAGE_LOADING = "loading"
    STAGE_QR_READY = "qr_ready"
    STAGE_SCANNED = "scanned"
    STAGE_AUTHENTICATING = "authenticating"
    STAGE_FAILED = "failed"

    STATUS_LOADING = "加载中......"
    STATUS_SCAN = "请企微扫码（mm:ss）......"
    STATUS_CONFIRM = "请确认登录！"
    STATUS_LOGGING_IN = "登录中......"
    STATUS_RETRY = "请点击重试！"

    def __init__(self, *, token_file: str | None = None, timeout: float = DEFAULT_TIMEOUT,
                 max_wait: float = DEFAULT_MAX_WAIT, quiet: bool = True,
                 max_auto_reload: int = 3,
                 on_stage=None, on_qr=None, on_status=None, on_notice=None,
                 is_aborted=None):
        self.token_file = token_file or DEFAULT_TOKEN_FILE
        self.timeout = timeout
        self.max_wait = max_wait
        self.quiet = quiet
        self.max_auto_reload = max(0, int(max_auto_reload))   # 二维码失效最多自动重载 3 次
        # 回调默认空实现（与 BI / PMS 登录器一致：调用方不必判空）
        self.on_stage = on_stage or (lambda *_: None)
        self.on_qr = on_qr or (lambda *_: None)
        self.on_status = on_status or (lambda *_: None)
        self.on_notice = on_notice or (lambda *_: None)
        self.is_aborted = is_aborted or (lambda: False)
        self.session = _new_session()
        self.last_error: LeyouLoginError | None = None

    # -- 回调小工具 --
    def _stage(self, stage: str):
        if self.on_stage:
            try:
                self.on_stage(stage, {
                    self.STAGE_LOADING: self.STATUS_LOADING,
                    self.STAGE_QR_READY: self.STATUS_SCAN,
                    self.STAGE_SCANNED: self.STATUS_CONFIRM,
                    self.STAGE_AUTHENTICATING: self.STATUS_LOGGING_IN,
                    self.STAGE_FAILED: self.STATUS_RETRY,
                }.get(stage, ""))
            except Exception:
                pass

    def _notice(self, text: str):
        """人类提示 → stderr（stdout 只保留最终 JSON 契约）。"""
        if not self.quiet:
            try:
                sys.stderr.write(text + "\n")
            except Exception:
                pass

    def _aborted(self) -> bool:
        try:
            return bool(self.is_aborted and self.is_aborted())
        except Exception:
            return False

    # -- 步骤 1：取登录 URL + 二维码 --
    def _prepare(self):
        self._stage(self.STAGE_LOADING)
        r = _http_get(self.session, f"{BASE_GET}/foreground/tannant/get-auth-url",
                      params={"tannant_id": TENANT_ID, "redirect_uri": SITE + "/"},
                      timeout=self.timeout)
        try:
            login_url = r.json()["data"]["url"]
        except (ValueError, KeyError, TypeError) as e:
            raise LeyouLoginError(QR_CREATE_FAILED, f"获取登录地址失败：{e!r}"[:200])
        hdr = {"User-Agent": UA}
        html = _http_get(self.session, login_url, headers=hdr, timeout=self.timeout).text
        m_key = re.search(r"qrcode\?key=([0-9a-f]+)", html)
        m_sig = re.search(r'sessionSignature\\?"\s*[:=]\s*"(Bearer [^"]+)"', html) or \
                re.search(r'\"sessionSignature\":\"(Bearer [^\"]+)\"', html)
        if not m_key or not m_sig:
            raise LeyouLoginError(QR_CREATE_FAILED, "无法从登录页提取 key/sessionSignature，请重试")
        key, sig = m_key.group(1), m_sig.group(1)
        qr_png = _http_get(self.session, f"{QR_IMG_URL}?key={key}",
                           headers=hdr, timeout=self.timeout).content
        state = (f'{{"tannant_id":"{TENANT_ID}","source":"work_wechat",'
                 f'"redirect_uri":"{SITE.replace("https://", "https:\\\\/\\\\/")}\\\\/"}}')
        return key, sig, state, login_url, hdr, qr_png

    # -- 步骤 2：轮询扫码状态 → auth_code → 回调换 token --
    def _poll(self, key, sig, state, login_url, hdr, *, cancel=None, on_status=None):
        """轮询企微扫码状态；换到 token 返回字符串，超时返回 None。

        cancel：{"v": bool} 可变字典（弹窗取消标记）；on_status(status) 每次状态变化回调。
        """
        h_poll = {**hdr,
                  "authorization": sig,
                  "x-wecom-client": f"ww-sso-login:{int(time.time()*1000)}:master",
                  "Content-Type": "application/json",
                  "Referer": login_url}
        last, open_sid = "QRCODE_SCAN_NEVER", None
        scanned = False
        confirm_deadline = 0.0
        start = time.time()
        while time.time() - start < self.max_wait:
            if (cancel and cancel.get("v")) or self._aborted():
                return None
            try:
                rr = self.session.post(
                    POLL_URL,
                    params={"lang": "zh_CN", "ajax": 1, "f": "json",
                            "random": str(int(time.time() * 1000))[-6:]},
                    json={"webKey": key, "lastStatus": last, "openDataSid": open_sid},
                    headers=h_poll, timeout=15)
                d = (rr.json() or {}).get("data", {}) or {}
                status = d.get("status")
                if status and status != last:
                    if status == "QRCODE_SCAN_ING":   # 已扫码，等待手机端确认
                        scanned = True
                        confirm_deadline = time.time() + CONFIRM_WAIT_SECONDS
                        self._stage(self.STAGE_SCANNED)
                    for cb in (on_status, self.on_status):
                        if cb:
                            try:
                                cb(status)
                            except Exception:
                                pass
                    last = status
                    # 已扫码后出现其它状态（手机"拒绝"/回退未扫/未知值）→ 交上层重载（防卡绿√），
                    # 实测反馈 2026-09-19：拒绝后窗口不恢复
                    if scanned and status not in ("QRCODE_SCAN_ING", "QRCODE_SCAN_SUCC"):
                        return None
                # 扫了但迟迟不确认（含手机"拒绝"）→ 交上层重载换码
                if scanned and confirm_deadline and time.time() > confirm_deadline:
                    return None
                if d.get("openDataSid"):
                    open_sid = d["openDataSid"]
                ac = d.get("auth_code")
                if ac:   # 关键：auth_code 就是 OAuth code，立即拼回调
                    for cb in (on_status, self.on_status):
                        if cb:
                            try:
                                cb("QRCODE_SCAN_SUCC")   # 保险：确保 UI 显示"扫码成功"
                            except Exception:
                                pass
                    token = self._exchange(ac, state, hdr)
                    if token:
                        return token
                if status in ("QRCODE_SCAN_ERR", "QRCODE_SCAN_TIMEOUT", "QRCODE_SCAN_CANCEL"):
                    # 取消 / 超时 / 出错 → 交上层重载（≤3 次）：窗口换新码、绿√消失、等用户重扫
                    return None
            except LeyouLoginError:
                raise
            except requests.exceptions.RequestException:
                pass     # 轮询偶发超时（企微限流）忽略继续
            time.sleep(0.8)   # 0.8s 轮询，避免错过短暂的"已扫码待确认"状态
        return None

    def _exchange(self, auth_code: str, state: str, hdr: dict) -> str | None:
        """拼回调换 token：GET CALLBACK?code&state → 从落地 URL 提取 token。"""
        try:
            res = self.session.get(CALLBACK, params={"code": auth_code, "state": state},
                                   headers={"User-Agent": hdr["User-Agent"]},
                                   allow_redirects=True, timeout=self.timeout)
        except requests.exceptions.RequestException:
            return None
        m = re.search(r"[?&]token=([0-9A-Za-z_.\-]+)", res.url)
        return m.group(1) if m else None

    # -- 步骤 3：登录收尾（uuid/水印 → 保存 → 凭证） --
    def _finish(self, token: str) -> dict:
        self.session.headers["x-auth-token"] = token
        cj = self.session.cookies.get_dict()
        uuid = cj.get("hl_uuid") or DEFAULT_UUID
        watermark = ""
        try:
            w = self.session.get(f"{BASE_GET}/foreground/tannant/get-watermark",
                                 params={"tannant_id": TENANT_ID}, timeout=self.timeout).json()
            watermark = (w.get("data") or {}).get("text", "")
        except Exception:
            watermark = ""
        store = {
            "token": token,
            "uuid": uuid,
            "login_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "expires_at": time.strftime("%Y-%m-%d", time.localtime(time.time() + 30 * 86400)),
            "watermark": watermark,
        }
        path = save_credential(self.token_file, store)
        return build_credential(store, source="qr", reused=False, token_file=path)

    # -- 总入口（纯内核：不含界面） --
    def run(self) -> dict:
        """执行一次登录：取码 → 轮询 →（失效重载 ≤3 次）→ 换 token → 完整凭证。

        每次取到新二维码都通过 on_qr(png) 通知上层（窗口据此刷新，不重建）。
        """
        reloads = 0
        while True:
            if self._aborted():
                raise LeyouLoginError(LOGIN_CANCELLED, "用户取消了登录")
            key, sig, state, login_url, hdr, qr_png = self._prepare()
            self.on_qr(qr_png)
            self._stage(self.STAGE_QR_READY)
            token = self._poll(key, sig, state, login_url, hdr)
            if token:
                self._stage(self.STAGE_AUTHENTICATING)
                return self._finish(token)
            if self._aborted():
                raise LeyouLoginError(LOGIN_CANCELLED, "用户取消了登录")
            reloads += 1
            if reloads > self.max_auto_reload:
                raise LeyouLoginError(QR_EXPIRED, "二维码多次失效，请重新登录")
            self.on_notice("二维码已失效，正在重新加载")


# 阶段常量（模块级别名，与 BI / PMS 登录器用法一致；值仍由 LoginFlow 定义）
STAGE_LOADING = LoginFlow.STAGE_LOADING
STAGE_QR_READY = LoginFlow.STAGE_QR_READY
STAGE_SCANNED = LoginFlow.STAGE_SCANNED
STAGE_AUTHENTICATING = LoginFlow.STAGE_AUTHENTICATING
STAGE_FAILED = LoginFlow.STAGE_FAILED


# ---------------- 二维码窗口（tkinter 标准库；与 BI / PMS 登录器同款） ----------------
def run_login_dialog(
    *,
    token_file: str | None = None,
    max_wait: float = DEFAULT_MAX_WAIT,
    quiet: bool = False,
) -> dict:
    """弹出**二维码窗口**（tkinter 标准库、置顶）并等待完成（同步用法）。

    窗口行为：显示二维码（含剩余时间）→ 扫码后盖**半透明蒙版 + 绿色大√**并提示"请确认" →
    确认成功自动关闭并返回凭证；失效在窗口内自动重载（≤3 次，由 LoginFlow 控制）；
    用户关窗 → LeyouLoginError(LOGIN_CANCELLED)。

    返回：成功 → 完整凭证字典（已按 token_file 落盘）。
    """
    import queue as _queue
    import threading as _th
    import tkinter as tk

    root = tk.Tk()
    root.title("乐药云智库 · 扫码登录")
    root.attributes("-topmost", True)               # 置顶：二维码直达用户桌面
    root.resizable(False, False)

    QR = 260                                        # 二维码显示尺寸（px）
    canvas = tk.Canvas(root, width=QR, height=QR, highlightthickness=0, bg="#FFFFFF")
    canvas.pack(padx=12, pady=(12, 6))
    img_item = canvas.create_image(QR // 2, QR // 2)
    mask = canvas.create_rectangle(0, 0, QR, QR, fill="#000000", stipple="gray50",
                                   outline="", state="hidden")
    r = int(QR * 0.25)                              # 绿色大√：绿圆 + 两段白勾（Canvas 原生）
    cx = cy = QR // 2
    tick_circle = canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                     fill="#00A651", outline="", state="hidden")
    lw = max(6, int(r * 0.3))
    tick_l1 = canvas.create_line(cx - r * 0.46, cy + r * 0.02, cx - r * 0.12, cy + r * 0.36,
                                 width=lw, fill="#FFFFFF", capstyle=tk.ROUND, state="hidden")
    tick_l2 = canvas.create_line(cx - r * 0.12, cy + r * 0.36, cx + r * 0.48, cy - r * 0.34,
                                 width=lw, fill="#FFFFFF", capstyle=tk.ROUND, state="hidden")

    tip = tk.Label(root, text="正在获取二维码……", font=("Microsoft YaHei UI", 10),
                   wraplength=300, justify="center")
    tip.pack(padx=12, pady=(0, 12))

    evt_q: _queue.Queue = _queue.Queue()
    result: dict = {"cred": None, "error": None}
    cancel = {"v": False}
    deadline = {"v": 0.0}
    scanned = {"v": False}

    def _notice(text: str) -> None:
        if not quiet:
            try:
                sys.stderr.write(text + "\n")
            except Exception:
                pass

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
            canvas._qr_img = photo                      # 保持引用防 GC
            _hide_tick()
            scanned["v"] = False
            deadline["v"] = time.time() + max(5.0, float(max_wait))
            tip.configure(text="请使用企业微信扫码", fg="#333333",
                          font=("Microsoft YaHei UI", 10))
        except Exception as exc:                        # 渲染失败如实显示，不静默
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
                token_file=token_file,
                max_wait=max_wait,
                quiet=True,
                on_qr=lambda png: evt_q.put(("qr", png)),
                on_stage=lambda stage, message: evt_q.put(("stage", (stage, message))),
                on_notice=lambda text: evt_q.put(("notice", text)),
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
                    elif stage == STAGE_FAILED and message:
                        tip.configure(text=str(message), fg="#C0392B")
                elif kind == "done":
                    root.after(900, root.destroy)       # 看清绿√后再自动关窗
                    return
        except _queue.Empty:
            pass
        if deadline["v"] and not scanned["v"]:
            left = int(deadline["v"] - time.time())
            if left > 0:
                tip.configure(text=f"请使用企业微信扫码【剩余 {left}s】", fg="#333333")
            else:
                tip.configure(text="二维码已过期，正在重新加载…", fg="#C0392B")
        root.after(200, pump)

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
        raise LeyouLoginError(LOGIN_CANCELLED, "用户取消了登录")
    _notice("登录成功，凭证已落盘")
    return result["cred"]


def relogin(*, token_file: str | None = None, max_wait: float = DEFAULT_MAX_WAIT,
            quiet: bool = False) -> dict:
    """功能一：扫码登录（原生二维码窗口），按 token_file 落盘，返回全新凭证。

    抛出：LeyouLoginError（LOGIN_CANCELLED / QR_EXPIRED / QR_CREATE_FAILED / NETWORK_ERROR…）
    """
    return run_login_dialog(token_file=token_file, max_wait=max_wait, quiet=quiet)


def verify_credential(*, token: str | None = None, uuid: str | None = None,
                      token_file: str | None = None, validate_remote: bool = True,
                      raise_on_invalid: bool = False, session=None,
                      timeout: float = DEFAULT_TIMEOUT) -> dict:
    """功能二：验证凭证（绝不弹窗）。

    - token 未显式传入时读 token_file（默认用户区）；
    - validate_remote=True 额外发一次远端校验（get-list 200/507）；
    - 返回：有效 → 完整凭证（authenticated=True, source="local", reused=True）；
            无效 → {ok:False, authenticated:False, reason, error, credentialPath}，
            当 raise_on_invalid=True 时抛 LeyouLoginError。
    reason: missing / expired / invalid（远端判定失效）/ not_validated（网络类，可重试）
    """
    path = os.path.abspath(token_file or DEFAULT_TOKEN_FILE)
    store = load_credential(path)
    tok = token or store.get("token")
    uid = uuid or store.get("uuid") or DEFAULT_UUID

    def _fail(reason: str, code: str, message: str, retryable: bool = False) -> dict:
        err = LeyouLoginError(code, message, retryable=retryable)
        if raise_on_invalid:
            raise err
        return {"ok": False, "authenticated": False, "source": "local", "reused": False,
                "reason": reason, "error": err.to_dict(), "credentialPath": path}

    if not tok:
        return _fail("missing", AUTH_REQUIRED, "本地没有任何凭证")

    local = _local_check({**store, "token": tok})
    if local == "expired":
        return _fail("expired", AUTH_EXPIRED, "本地凭证已过期（expires_at 参考值）")

    if validate_remote:
        sess = session or _new_session()
        status, info = _remote_probe(sess, tok, uid, timeout)
        if status == "not_validated":
            return _fail("not_validated", NOT_VALIDATED,
                         "远端校验未通过（网络不通 / 服务端限流），可重试", retryable=True)
        if status == "invalid":
            return _fail("invalid", CREDENTIALS_INVALID, "远端判定凭证已失效")

    cred = build_credential({**store, "token": tok, "uuid": uid},
                            source="local", reused=True, token_file=path)
    if validate_remote and info:
        cred.update(info)     # categories / first_category（业务预检复用）
    return cred


def is_authenticated(*, validate_remote: bool = True, session=None,
                     token_file: str | None = None) -> bool:
    """快捷：现在能不能用（绝不弹窗、绝不抛异常）。"""
    try:
        return bool(verify_credential(validate_remote=validate_remote,
                                      session=session, token_file=token_file)
                    .get("authenticated"))
    except LeyouLoginError:
        return False


def get_credential(*, force_relogin: bool = True, validate_remote: bool = True,
                   interactive: bool = True, token_file: str | None = None,
                   max_wait: float = DEFAULT_MAX_WAIT, quiet: bool = True) -> dict:
    """组合入口：
    - force_relogin=True → 总是重新扫码（等价 relogin）；
    - force_relogin=False → 先验证：有效则复用；失效且 interactive=True 才弹窗；
      interactive=False（非交互：由调用方保证不弹窗）时凭证不可用直接抛 AUTH_REQUIRED。

    弹窗策略：只有「凭证本身不可用」（missing/expired/invalid）才弹窗；
    网络 / 限流类错误（not_validated）一律直接抛网络错误，不弹登录窗。
    另：interactive=False 与 force_relogin=True 互斥——非交互不支持扫码重登。
    """
    if force_relogin and not interactive:
        raise LeyouLoginError(AUTH_REQUIRED,
                              "非交互模式不支持扫码重登：请用 force_relogin=False（只复用）")
    if not force_relogin:
        res = verify_credential(validate_remote=validate_remote, token_file=token_file)
        if res.get("authenticated"):
            return res
        reason = res.get("reason")
        if reason not in _POPUP_REASONS:
            # not_validated 等非凭证类错误：直接抛出（不弹窗）
            err = res.get("error") or {}
            raise LeyouLoginError(err.get("code", NOT_VALIDATED),
                                  err.get("message", "凭证校验未通过"),
                                  retryable=bool(err.get("retryable")))
        if not interactive:
            raise LeyouLoginError(AUTH_REQUIRED,
                                  f"凭证不可用（{reason}），非交互模式下不弹窗登录")
    return relogin(token_file=token_file, max_wait=max_wait, quiet=quiet)


# 兼容别名（旧名指向同一实现）
load_token_store = load_credential
save_token_store = save_credential


# ---------------- CLI ----------------
def check_env(token_file: str | None = None) -> dict:
    """环境自检：登录器可调用性（tkinter / 凭证文件可写）与下一步指引；绝不弹窗。"""
    path = token_file or DEFAULT_TOKEN_FILE
    out = {
        "ok": True,
        "python": sys.version.split()[0],
        "gui": None,
        "credentialPath": str(path),
        "fix": None,
        "next": "python login_leyou_cloud.py --reuse（弹窗登录）｜--status（只验证）",
    }
    try:
        import tkinter  # noqa: F401  —— 标准库：弹窗唯一依赖
        out["gui"] = "tkinter（标准库，已可用）"
    except ImportError:
        out.update(
            ok=False,
            gui=None,
            fix="当前 Python 缺少 tkinter：请重装 / 修复 Python（安装时勾选 tcl/tk 与 IDLE）",
            next="修复后重新运行 --check 或 --reuse",
        )
    try:
        _dir = os.path.dirname(os.path.abspath(os.path.expanduser(str(path))))
        os.makedirs(_dir, exist_ok=True)
    except OSError as exc:
        out.update(ok=False, fix="检查凭证目录写入权限",
                   next=f"凭证目录不可写：{exc!r}"[:200])
    return out


def _emit(out: dict, compact: bool = False) -> None:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    s = json.dumps(out, ensure_ascii=False,
                   separators=(",", ":") if compact else None,
                   indent=None if compact else 2)
    print(s)


def _build_parser():
    p = argparse.ArgumentParser(
        prog="login_leyou_cloud",
        description="乐药云智库独立登录器：企微扫码 → 完整凭证；两个接口（弹窗登录 / 取凭证）+ --check 环境自检",
        epilog=(
            "给 AI · Agent 的调用契约（唯一登录入口 → 直接调用本登录器（黑盒）；禁止读源码后自写登录）：\n"
            "  1) 自检：--check（依赖 tkinter；缺失给出修复指引）\n"
            "  2) 验证：--status（退出码 0 = 已有可用凭证，直接用）\n"
            "  3) 登录：--reuse（唯一点：直接调起原生扫码窗；有效复用、失效才弹窗）\n"
            "  4) 取凭证：--status（或门面 API：relogin / verify_credential / get_credential / is_authenticated）\n"
            "  用户已指定或提供凭证 / 登录方式 → 按其走（不受上列限制）。\n"
            "  弹窗失败 → --check 修复环境后重试；仍失败 → 询问用户（禁止出码绕路）。\n"
            "  禁止：自写登录流程 / 出码绕路 / 自取二维码 / 自拼鉴权 / 组装内部类（LoginFlow 等）/ 绕过本脚本解析凭证。\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--token-file", default=DEFAULT_TOKEN_FILE,
                   help="凭证文件路径（默认用户区 leyou_token.json）")
    p.add_argument("--status", action="store_true", help="只验证已有凭证（绝不弹窗）")
    p.add_argument("--reuse", action="store_true", help="有效则复用，失效才弹窗")
    p.add_argument("--check", action="store_true",
                   help="环境自检：检查 tkinter 与登录器可调用性；异常时给出修复指引")
    p.add_argument("--no-remote", action="store_true", help="跳过远端校验（只做本地检查）")
    p.add_argument("--wait", type=int, default=DEFAULT_MAX_WAIT, help="扫码等待秒数（默认300）")
    p.add_argument("--quiet", action="store_true", help="静默（不输出人类提示）")
    p.add_argument("--compact", action="store_true", help="单行 JSON 输出（机器解析友好）")
    return p


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.check:
            _emit(check_env(token_file=args.token_file), args.compact)
            return 0
        if args.status:
            res = verify_credential(token_file=args.token_file,
                                    validate_remote=not args.no_remote)
            _emit(res, args.compact)
            return 0 if res.get("authenticated") else 3
        cred = get_credential(force_relogin=not args.reuse,
                              validate_remote=not args.no_remote,
                              interactive=True, token_file=args.token_file,
                              max_wait=args.wait, quiet=args.quiet)
        _emit(cred, args.compact)
        return 0
    except LeyouLoginError as e:
        _emit({"ok": False, "error": e.to_dict()}, args.compact)
        return 3 if e.code in (AUTH_REQUIRED, LOGIN_CANCELLED) else 1
    except Exception as e:   # noqa: BLE001 —— CLI 统一兜底
        _emit({"ok": False, "error": {"code": INTERNAL_ERROR,
                                      "message": str(e)[:300], "retryable": False}},
              args.compact)
        return 2


if __name__ == "__main__":
    sys.exit(main())
