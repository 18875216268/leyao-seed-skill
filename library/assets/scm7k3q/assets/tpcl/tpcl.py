#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图片处理资产（生图 v1.03）。

线上文档：https://st.cfdaili.top/md
API 基址：https://st.cfdaili.top/api

设计原则：不在本地内置 API 规格。模型/画幅/档位/新增参数一律由 Agent
读取线上文档后，通过 --param / --body 透传；本文件只负责稳定的
「提交 → 轮询 → 下载」与本地凭证管理。
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import time
import uuid
import warnings
from datetime import datetime
from html import unescape
from pathlib import Path

warnings.filterwarnings("ignore")

try:
    import requests  # noqa: E402
except ImportError:  # 最小环境未装依赖时不崩，仅该通道不可用
    requests = None  # type: ignore[assignment]

DOC_URL = "https://st.cfdaili.top/md"
DEFAULT_BASE = "https://st.cfdaili.top/api"
PURCHASE_URL = "https://www.kufaka.com/shop/qimeng"

TIMEOUT = (10, 60)
POLL_INTERVAL = 3
POLL_TIMEOUT = 600
IMAGE_TYPES = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}

EXIT_OK = 0
EXIT_BUSINESS = 1
EXIT_PARAM = 2
EXIT_AUTH = 3


for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass


class AssetError(Exception):
    def __init__(self, code: str, message: str, *, exit_code: int = EXIT_BUSINESS,
                 hint: str = "", details: dict | None = None, purchase: bool = False):
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_code = exit_code
        self.hint = hint
        self.details = details or {}
        self.purchase = purchase


def emit(value: dict) -> None:
    print(json.dumps(value, ensure_ascii=False, default=str))


def fail(exc: AssetError) -> int:
    out = {"ok": False, "error": exc.code, "message": exc.message}
    if exc.hint:
        out["hint"] = exc.hint
    if exc.details:
        out["details"] = exc.details
    if exc.purchase:
        out["purchaseUrl"] = PURCHASE_URL
    emit(out)
    return exc.exit_code


# --------------------------------------------------------------------------- #
# 凭证
# --------------------------------------------------------------------------- #
def data_home() -> Path:
    env = os.environ.get("SCM_OPERATIONS_HOME")
    if env:
        return Path(env).expanduser()
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "scm-operations-query"


def cred_path() -> Path:
    return data_home() / "image.json"


def load_cred() -> dict:
    path = cred_path()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_cred(api_key: str, base_url: str) -> Path:
    path = cred_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "api_key": api_key,
        "base_url": base_url,
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def mask_key(key: str) -> str:
    if len(key) <= 10:
        return key[:3] + "****"
    return key[:6] + "****" + key[-2:]


# --------------------------------------------------------------------------- #
# HTTP 与错误映射
# --------------------------------------------------------------------------- #
def session() -> requests.Session:
    s = requests.Session()
    s.trust_env = False
    s.headers.update({"User-Agent": "scm-tpcl/1.0", "Accept": "application/json"})
    return s


def request(s: requests.Session, method: str, url: str, *, key: str | None = None,
            body: dict | None = None) -> tuple[int, dict]:
    headers = {"Authorization": "Bearer %s" % key} if key else {}
    try:
        response = s.request(method, url, headers=headers, json=body, timeout=TIMEOUT)
    except requests.exceptions.Timeout as exc:
        raise AssetError("IMAGE_TIMEOUT", "请求超时", hint="稍后重试") from exc
    except requests.exceptions.RequestException as exc:
        raise AssetError("IMAGE_NETWORK", "网络请求失败：%s" % exc,
                         hint="检查网络或稍后重试") from exc
    try:
        data = response.json()
    except ValueError:
        data = {"raw": response.text[:500]}
    return response.status_code, data


def api_error(status: int, data: dict) -> AssetError:
    code = str(data.get("code") or "")
    message = str(data.get("message") or data.get("error") or "")
    if status == 401 or code in {"UNAUTHORIZED", "KEY_INVALID"}:
        missing = code == "UNAUTHORIZED" or not code
        return AssetError(
            "IMAGE_KEY_MISSING" if missing else "IMAGE_KEY_INVALID",
            message or ("缺少秘钥" if missing else "秘钥无效"),
            exit_code=EXIT_AUTH, purchase=True,
            hint="购买或更换秘钥后运行 set-key",
        )
    if status == 402 or code in {"NO_CREDITS", "INSUFFICIENT_CREDITS"}:
        return AssetError("IMAGE_NO_CREDITS", message or "额度不足",
                          exit_code=EXIT_AUTH, purchase=True,
                          hint="购买额度后重试")
    if status == 404:
        return AssetError("IMAGE_JOB_NOT_FOUND", message or "任务不存在", details={"status": status})
    if status == 400:
        return AssetError("IMAGE_PARAM_INVALID", message or "参数不合法",
                          exit_code=EXIT_PARAM, details={"code": code})
    if status == 429:
        return AssetError("IMAGE_RATE_LIMITED", message or "请求过于频繁",
                          hint="等待后重试（每秘钥 20 次/分钟、最多 3 个在途）")
    return AssetError("IMAGE_UPSTREAM_ERROR", message or ("HTTP %s" % status),
                      details={"status": status, "code": code})


def fetch_me(s: requests.Session, base: str, key: str) -> dict:
    status, data = request(s, "GET", "%s/v1/me" % base, key=key)
    if status != 200 or not data.get("ok", True):
        raise api_error(status, data)
    return data


# --------------------------------------------------------------------------- #
# 图片与参数
# --------------------------------------------------------------------------- #
def to_data_url(value: str) -> str:
    if value.startswith(("http://", "https://", "data:")):
        return value
    path = Path(value).expanduser()
    if not path.is_file():
        raise AssetError("IMAGE_PARAM_INVALID", "图片不存在：%s" % value, exit_code=EXIT_PARAM)
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return "data:%s;base64,%s" % (mime, encoded)


def parse_value(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def build_body(args) -> dict:
    body: dict = {}
    if args.body:
        try:
            extra = json.loads(args.body)
        except json.JSONDecodeError as exc:
            raise AssetError("IMAGE_PARAM_INVALID", "--body 不是合法 JSON：%s" % exc,
                             exit_code=EXIT_PARAM) from exc
        if not isinstance(extra, dict):
            raise AssetError("IMAGE_PARAM_INVALID", "--body 必须是 JSON 对象", exit_code=EXIT_PARAM)
        body.update(extra)

    for name, value in {
        "prompt": args.prompt, "model": args.model, "size": args.size,
        "image_size": args.image_size, "n": args.n, "quality": args.quality,
        "output_format": args.format, "wait": args.wait, "request_id": args.request_id,
    }.items():
        if value is not None:
            body[name] = value

    for item in args.param or []:
        if "=" not in item:
            raise AssetError("IMAGE_PARAM_INVALID", "--param 需 k=v：%s" % item, exit_code=EXIT_PARAM)
        key, value = item.split("=", 1)
        body[key.strip()] = parse_value(value.strip())

    images = [to_data_url(item) for item in (args.image or [])]
    if images:
        if len(images) == 1:
            body["image"] = images[0]
        else:
            body["images"] = images
    if args.mask:
        body["mask"] = to_data_url(args.mask)

    if not body.get("prompt"):
        raise AssetError("IMAGE_PARAM_INVALID", "缺少 --prompt（或 --body 中的 prompt）",
                         exit_code=EXIT_PARAM)
    body.setdefault("request_id", uuid.uuid4().hex)
    return body


# --------------------------------------------------------------------------- #
# 任务与下载
# --------------------------------------------------------------------------- #
def wait_job(s: requests.Session, base: str, key: str, job_id: str, *,
             interval: int = POLL_INTERVAL, timeout: int = POLL_TIMEOUT) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status, data = request(s, "GET", "%s/v1/jobs/%s" % (base, job_id), key=key)
        if status == 404:
            raise AssetError("IMAGE_JOB_NOT_FOUND", "任务不存在：%s" % job_id, details={"status": status})
        if status not in (200, 202):
            raise api_error(status, data)
        state = str(data.get("status") or "")
        if state == "done" or data.get("images"):
            return data
        if state == "failed":
            raise AssetError("IMAGE_TASK_FAILED", str(data.get("error") or "生成失败"), details=data)
        time.sleep(interval)
    raise AssetError("IMAGE_TIMEOUT", "任务 %s 超时未完成" % job_id,
                     hint="稍后用 job <id> 查询", details={"id": job_id})


def download_images(s: requests.Session, urls: list[str], out_dir: str) -> list[str]:
    folder = Path(out_dir).expanduser()
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved: list[str] = []
    for index, url in enumerate(urls, 1):
        try:
            response = s.get(url, timeout=TIMEOUT)
            if response.status_code != 200:
                continue
            ctype = (response.headers.get("content-type") or "").split(";")[0].strip()
            ext = IMAGE_TYPES.get(ctype)
            if not ext:
                suffix = Path(url.split("?")[0]).suffix.lstrip(".").lower()
                ext = suffix if suffix in {"png", "jpg", "jpeg", "webp"} else "png"
            path = folder / ("tpcl_%s_%s.%s" % (stamp, index, ext))
            path.write_bytes(response.content)
            saved.append(str(path))
        except requests.exceptions.RequestException:
            continue
    return saved


def result_payload(data: dict, job_id: str, saved: list[str]) -> dict:
    return {
        "ok": True,
        "id": data.get("id", job_id),
        "status": data.get("status"),
        "model": data.get("model"),
        "size": data.get("size"),
        "image_size": data.get("image_size"),
        "n": data.get("n"),
        "images": data.get("images") or [],
        "credits": data.get("credits"),
        "remaining": data.get("remaining"),
        "error": data.get("error") or "",
        "saved": saved,
    }


# --------------------------------------------------------------------------- #
# 命令
# --------------------------------------------------------------------------- #
def require_key(args) -> tuple[str, str]:
    cred = load_cred()
    key = cred.get("api_key")
    base = args.base_url or cred.get("base_url") or DEFAULT_BASE
    if not key:
        raise AssetError("IMAGE_KEY_MISSING", "未找到图片服务秘钥",
                         exit_code=EXIT_AUTH, purchase=True,
                         hint="购买后运行 set-key")
    return key, base


def cmd_status(args) -> int:
    cred = load_cred()
    key = cred.get("api_key")
    base = args.base_url or cred.get("base_url") or DEFAULT_BASE
    if not key:
        raise AssetError("IMAGE_KEY_MISSING", "未找到图片服务秘钥",
                         exit_code=EXIT_AUTH, purchase=True,
                         hint="购买后运行 set-key")
    if args.no_remote:
        emit({"ok": True, "key": mask_key(key), "base_url": base, "remote": False})
        return EXIT_OK
    data = fetch_me(session(), base, key)
    emit({"ok": True, "key": mask_key(key), "base_url": base,
          "quota": data.get("quota"), "used": data.get("used"),
          "remaining": data.get("remaining")})
    return EXIT_OK


def cmd_set_key(args) -> int:
    key = (args.key or "").strip()
    if not key.startswith("sk-"):
        raise AssetError("IMAGE_PARAM_INVALID", "秘钥格式应为 sk-...", exit_code=EXIT_PARAM)
    base = args.base_url or DEFAULT_BASE
    data = fetch_me(session(), base, key)
    path = save_cred(key, base)
    emit({"ok": True, "key": mask_key(key), "base_url": base,
          "quota": data.get("quota"), "used": data.get("used"),
          "remaining": data.get("remaining"), "credentialPath": str(path)})
    return EXIT_OK


def cmd_key(args) -> int:
    print("购买地址：%s" % PURCHASE_URL)
    if not args.no_open:
        try:
            print("额度购买页（请手动复制到浏览器打开）：%s" % PURCHASE_URL)
        except Exception:  # noqa: BLE001
            pass
    try:
        key = input("请粘贴秘钥（sk-...）：").strip()
    except EOFError as exc:
        raise AssetError("IMAGE_PARAM_INVALID", "未输入秘钥", exit_code=EXIT_PARAM) from exc
    if not key:
        raise AssetError("IMAGE_PARAM_INVALID", "未输入秘钥", exit_code=EXIT_PARAM)
    args.key = key
    return cmd_set_key(args)


def cmd_me(args) -> int:
    key, base = require_key(args)
    data = fetch_me(session(), base, key)
    emit({"ok": True, "base_url": base, **data})
    return EXIT_OK


def cmd_prices(args) -> int:
    key, base = require_key(args)
    status, data = request(session(), "GET", base + "/v1/prices", key=key)
    if status != 200 or not data.get("ok", True):
        raise api_error(status, data)
    emit(data)
    return EXIT_OK


def html_to_text(text: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?</\1>", "", text)
    text = re.sub(r"(?s)<[^>]+>", "\n", text)
    text = unescape(text)
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def cmd_doc(_args) -> int:
    try:
        response = session().get(DOC_URL, timeout=TIMEOUT)
    except requests.exceptions.RequestException as exc:
        raise AssetError("IMAGE_DOC_UNREACHABLE", "无法读取线上文档：%s" % exc,
                         hint="用 web_fetch 打开 %s" % DOC_URL) from exc
    if response.status_code != 200:
        raise AssetError("IMAGE_DOC_UNREACHABLE", "文档页 HTTP %s" % response.status_code,
                         hint="用 web_fetch 打开 %s" % DOC_URL)
    print("# 来源：%s\n" % DOC_URL)
    print(html_to_text(response.text))
    return EXIT_OK


def cmd_generate(args) -> int:
    key, base = require_key(args)
    body = build_body(args)
    s = session()
    status, data = request(s, "POST", "%s/v1/images/generations" % base, key=key, body=body)
    if status not in (200, 202) or not data.get("ok", True):
        raise api_error(status, data)
    job_id = str(data.get("id") or "")
    if not job_id:
        raise AssetError("IMAGE_NO_TASK", "提交成功但未返回任务 id", details=data)
    if args.no_wait:
        emit({"ok": True, "id": job_id, "status": data.get("status"), "raw": data})
        return EXIT_OK
    final = wait_job(s, base, key, job_id, interval=args.interval, timeout=args.timeout)
    images = final.get("images") or []
    saved = download_images(s, images, args.out) if args.out and images else []
    emit(result_payload(final, job_id, saved))
    return EXIT_OK


def cmd_job(args) -> int:
    key, base = require_key(args)
    s = session()
    status, data = request(s, "GET", "%s/v1/jobs/%s" % (base, args.id), key=key)
    if status not in (200, 202):
        raise api_error(status, data)
    images = data.get("images") or []
    saved = download_images(s, images, args.out) if args.out and images else []
    emit(result_payload(data, args.id, saved))
    return EXIT_OK


# --------------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--base-url", default=None, help="API 基址（默认 %s）" % DEFAULT_BASE)
    common.add_argument("--cred-dir", default=None, help="凭证目录（默认 %%LOCALAPPDATA%%\\scm-operations-query）")

    parser = argparse.ArgumentParser(prog="tpcl.py", description="图片处理（生图 v1.03）")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("status", parents=[common], help="检查凭证与额度")
    p.add_argument("--no-remote", action="store_true", help="仅检查本地凭证")

    p = sub.add_parser("set-key", parents=[common], help="录入并校验秘钥")
    p.add_argument("key")

    p = sub.add_parser("key", parents=[common], help="打开购买页并交互录入秘钥")
    p.add_argument("--no-open", action="store_true", help="不自动打开浏览器")

    sub.add_parser("me", parents=[common], help="查询额度")
    sub.add_parser("prices", parents=[common], help="查询模型与各档位价格")
    sub.add_parser("doc", parents=[common], help="读取线上 API 文档")

    p = sub.add_parser("generate", parents=[common], help="生成/编辑图片")
    p.add_argument("--prompt")
    p.add_argument("--model")
    p.add_argument("--size")
    p.add_argument("--image-size", dest="image_size")
    p.add_argument("--n", type=int)
    p.add_argument("--quality")
    p.add_argument("--format")
    p.add_argument("--image", action="append", help="参考图（本地路径/URL/data URL），可重复")
    p.add_argument("--mask", help="遮罩（本地路径/URL/data URL）")
    p.add_argument("--out", help="下载目录")
    p.add_argument("--wait", type=int, help="同步等待秒数 0-25")
    p.add_argument("--request-id", dest="request_id")
    p.add_argument("--param", action="append", help="透传参数 k=v，可重复")
    p.add_argument("--body", help="完整 JSON 请求体")
    p.add_argument("--no-wait", action="store_true", help="提交后立即返回，不轮询")
    p.add_argument("--interval", type=int, default=POLL_INTERVAL)
    p.add_argument("--timeout", type=int, default=POLL_TIMEOUT)

    p = sub.add_parser("job", parents=[common], help="查询任务")
    p.add_argument("id")
    p.add_argument("--out", help="下载目录")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "cred_dir", None):
        os.environ["SCM_OPERATIONS_HOME"] = str(Path(args.cred_dir).expanduser().resolve())
    handlers = {
        "status": cmd_status, "set-key": cmd_set_key, "key": cmd_key,
        "me": cmd_me, "prices": cmd_prices, "doc": cmd_doc,
        "generate": cmd_generate, "job": cmd_job,
    }
    try:
        return handlers[args.command](args)
    except AssetError as exc:
        return fail(exc)
    except KeyboardInterrupt:
        emit({"ok": False, "error": "CANCELLED", "message": "用户取消"})
        return 130
    except Exception as exc:  # noqa: BLE001
        emit({"ok": False, "error": "INTERNAL", "message": repr(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
