# -*- coding: utf-8 -*-
"""SCM 技能唯一入口。

用法：
  python scm.py status  [--account X] [--no-remote]
  python scm.py login   [--account X] [--password Y]
  python scm.py pms-status [--no-remote]        # PMS 凭证校验（自营活动管理需要）
  python scm.py pms-login                       # PMS 企微扫码登录（弹窗）
  python scm.py modules
  python scm.py query   [--status 进行中] [--type 一口价] [--keyword 词] [--limit 20]
  python scm.py export  [--status 进行中|--all-status|--group-center] [--out 路径]
  python scm.py dict    [--name priceTypes|--list]
  python scm.py assets / asset <名>
  python scm.py call    --path <端点> [--host-key scm|pms] [--body <JSON|@文件>]
                        [--param k=v] [--ex <ex>] [--out <文件>] [--method post|get]
  python scm.py scene   [<场景> ...]       # 高频场景（assets 动态发现）

输出恒为 JSON（stdout）；退出码 0 成功 / 1 业务 / 2 参数 / 3 凭证。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

# 统一 UTF-8 输出，避免 Windows 控制台 GBK 污染 JSON（Agent 直接按 UTF-8 解析）
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass

from core import credential  # noqa: E402
from core.errors import SkillError  # noqa: E402
from core.http import BASE, build_session, call_endpoint, public_params  # noqa: E402
from modules import list_modules, require_ready  # noqa: E402


def emit(value: dict) -> None:
    print(json.dumps(value, ensure_ascii=False, default=str))


def parse_params(pairs: list[str] | None) -> dict:
    """解析 --param：JSON 数组/对象、布尔、纯整数（无前导零）、其余按字符串。"""
    result = {}
    for item in pairs or []:
        if "=" not in item:
            raise SkillError("PARAM_INVALID", f"--param 需 k=v 形式：{item}")
        key, value = item.split("=", 1)
        key, value = key.strip(), value.strip()
        if value.startswith(("[", "{")):
            try:
                result[key] = json.loads(value)
            except json.JSONDecodeError as exc:
                raise SkillError("PARAM_INVALID", f"--param 的 JSON 不合法：{key}={value}") from exc
            continue
        if value.lower() in ("true", "false"):
            result[key] = value.lower() == "true"
            continue
        digits = value.lstrip("-")
        if digits.isdigit() and not (len(digits) > 1 and digits.startswith("0")):
            result[key] = int(value)
        else:
            result[key] = value
    return result


def default_out(prefix: str) -> str:
    return "%s_%s.csv" % (prefix, datetime.now().strftime("%Y%m%d_%H%M%S"))


def cmd_status(args) -> int:
    cred = credential.load(args.account)
    if not cred:
        raise SkillError("AUTH_REQUIRED", "没有可用凭证",
                         hint="python scm.py login --account <账号>")
    reason, error = credential.check(cred, remote=not args.no_remote)
    result = {
        "ok": not reason,
        "account": cred.get("account"),
        "providerId": cred.get("provider_id"),
        "expire": cred.get("expire_time"),
        "credentialPath": str(credential.cred_dir() / "credential.json"),
    }
    if reason:
        result.update({"reason": reason, "message": getattr(error, "message", "凭证不可用")})
        emit(result)
        return 3
    emit(result)
    return 0


def cmd_login(args) -> int:
    import scm_login as scm

    cred = scm.get_credential(force_relogin=True, interactive=True,
                                account=args.account, password=args.password)
    emit({"ok": True, "account": cred.get("account"), "providerId": cred.get("provider_id"),
          "expire": cred.get("expire_time"), "credentialPath": cred.get("credentialPath")})
    return 0


def _pms_identity(cred: dict) -> dict:
    """PMS 凭证摘要（status/login 共用，避免两处重复拼装）。"""
    user = cred.get("user") or {}
    return {
        "system": "pms",
        "account": user.get("account") or user.get("accountNo"),
        "userName": user.get("userName"),
        "providerId": cred.get("provider_id"),
        "providerName": cred.get("provider_name"),
        "providers": len(cred.get("providers") or []),
        "warehouses": len(cred.get("warehouses") or []),
    }


def cmd_pms_status(args) -> int:
    """PMS 凭证校验（绝不弹窗）。自营活动管理（转PMS）前必做。"""
    from core import pms_client as pms

    info = pms.verify_credential(validate_remote=not getattr(args, "no_remote", False))
    cred = pms.load_credential() or {}
    result = {
        "ok": bool(info.get("authenticated")),
        **_pms_identity(cred),
        # PMS 凭证无固定过期时间（靠远端 /api/Index/index 校验判定），故给创建/校验时刻
        "createdAt": cred.get("createdAt"),
        "validatedAt": cred.get("validatedAt"),
        "credentialPath": info.get("credentialPath") or cred.get("credentialPath"),
    }
    if not result["ok"]:
        err = info.get("error") or {}
        result.update({
            "reason": info.get("reason"),
            "message": err.get("message") or "PMS 凭证不可用",
            "hint": "python scm.py pms-login",
        })
        emit(result)
        return 3
    emit(result)
    return 0


def cmd_pms_login(_args) -> int:
    """PMS 企微扫码登录（弹窗）；成功后凭证落 pms-operations-query。"""
    from core import pms_client as pms

    cred = pms.get_credential(force_relogin=True, interactive=True)
    emit({
        "ok": True,
        **_pms_identity(cred),
        "createdAt": cred.get("createdAt"),
        "credentialPath": cred.get("credentialPath"),
    })
    return 0


def cmd_modules(_args) -> int:
    emit({"ok": True, "modules": list_modules()})
    return 0


def load_api(module: str, kind: str):
    """按板块加载 query / export 能力模块。"""
    import importlib

    return importlib.import_module(f"modules.{module}.{kind}")


def cmd_query(args) -> int:
    require_ready(args.module)
    api = load_api(args.module, "query")
    cred = credential.ensure(args.account)
    session = build_session(cred)
    token = str(cred.get("token"))
    common = dict(status=args.status, types=args.type, keyword=args.keyword,
                  condition=args.condition, extra=parse_params(args.param))
    if args.stats:
        data = api.statistics(session, token, status=args.status)
        emit({"ok": True, "statistics": data})
    elif args.count:
        data = api.count(session, token, **common)
        emit({"ok": True, "counts": data})
    else:
        data = api.query(session, token, page=args.page, size=args.limit, **common)
        emit({"ok": True, "total": data.get("totalRecord"), "page": data.get("pageNo"),
              "rows": data.get("results") or []})
    return 0


def _poll_kwargs(args, fn) -> dict:
    """仅当调用方支持 poll_timeout 且用户显式指定时才透传（兼容其它板块骨架）。"""
    import inspect
    if getattr(args, "poll_timeout", None) is None:
        return {}
    if "poll_timeout" in inspect.signature(fn).parameters:
        return {"poll_timeout": args.poll_timeout}
    return {}


def cmd_export(args) -> int:
    if args.group_center and (args.all_status or args.param):
        raise SkillError("PARAM_INVALID", "组单中心导出不接受筛选参数（--all-status / --param）")
    meta = require_ready(args.module)
    api = load_api(args.module, "export")
    cred = credential.ensure(args.account)
    session = build_session(cred)
    token = str(cred.get("token"))

    if args.group_center:
        if not hasattr(api, "export_group_center"):
            raise SkillError("NOT_SUPPORTED", f"{meta['name']}板块不支持组单中心导出")
        result = api.export_group_center(
            session, token, args.out or default_out("SCM_组单中心"),
            **_poll_kwargs(args, api.export_group_center),
        )
        emit({"ok": True, **result})
        return 0

    status = -1 if args.all_status else args.status
    result = api.export(
        session, token, args.out or default_out(f"SCM_{meta['name']}"),
        status=status, types=args.type, keyword=args.keyword,
        condition=args.condition, extra=parse_params(args.param),
        **_poll_kwargs(args, api.export),
    )
    emit({"ok": True, **result})
    return 0


def cmd_dict(args) -> int:
    from modules.goods import dicts

    if args.list:
        emit({"ok": True, "dicts": dicts.list_dicts()})
        return 0
    if not args.name:
        raise SkillError("PARAM_INVALID", "缺少 --name（或使用 --list）")
    cred = credential.ensure(args.account)
    session = build_session(cred)
    data = dicts.get_dict(session, str(cred.get("token")), args.name)
    emit({"ok": True, "name": args.name, "data": data})
    return 0


def _call_payload(args) -> dict:
    """--body（内联 JSON 或 @文件）为基础，--param k=v 覆盖同名字段。"""
    payload: dict = {}
    if args.body:
        raw = args.body
        if raw.startswith("@"):
            file_path = Path(raw[1:]).expanduser()
            if not file_path.is_file():
                raise SkillError("PARAM_INVALID", f"--body 文件不存在：{file_path}")
            try:
                raw = file_path.read_text(encoding="utf-8")
            except OSError as exc:
                raise SkillError("PARAM_INVALID", f"--body 文件读取失败：{exc}") from exc
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SkillError("PARAM_INVALID", f"--body 不是合法 JSON：{exc}") from exc
        if not isinstance(parsed, dict):
            raise SkillError("PARAM_INVALID", "--body 必须是 JSON 对象")
        payload.update(parsed)
    payload.update(parse_params(args.param))
    return payload


def _call_headers(pairs: list[str] | None) -> dict:
    """--header k=v（值原样为字符串，不做类型转换）。"""
    result = {}
    for item in pairs or []:
        if "=" not in item:
            raise SkillError("PARAM_INVALID", f"--header 需 k=v 形式：{item}")
        key, value = item.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def _pms_context(body: dict, extra_headers: dict) -> tuple[str, dict, dict]:
    """PMS 域请求上下文：复用登录器的固定头/常量，不自行组装登录。"""
    import time

    from core import pms_client as pms

    cred = pms.load_credential() or {}
    token = str(cred.get("token") or "")
    if not token:
        raise SkillError("AUTH_REQUIRED", "没有 PMS 凭证", hint="python scm.py pms-login")
    ts = str(int(time.time()))
    headers = dict(pms.PMS_HEADERS)
    headers.update({
        "token": token, "timestamp": ts, "content-type": "application/json",
        # 技能包 PMS 域只覆盖「商品活动管理」页，其 module 头与登录器默认模块不同
        "module": "goods_act_manage", "__module__": "goods_act_manage",
    })
    headers.update(extra_headers)
    payload = {"token": token, "appVersion": pms.APP_VERSION, "platform": "web",
               "timestamp": ts, "buildTime": pms._build_time()}
    payload.update(body)
    return pms.PMS_BASE, payload, headers


def cmd_call(args) -> int:
    """按 `references/**/api_*.md` 直连任意已交付端点（统一 token/公共参数/错误码/文件流）。"""
    import requests

    path = (args.path or "").strip()
    if not path.startswith("/") or "://" in path or ".." in path:
        raise SkillError("PARAM_INVALID", "--path 必须是以 / 开头的站内路径（不含 :// 或 ..）",
                         hint="例如 /scm-goods/drugsStat/saleReportDrugsStatList")
    body = _call_payload(args)
    extra_headers = _call_headers(args.header)

    # --drop 在公共参数注入之后统一执行：客户列表等接口明确「不带 lastBuildTime」
    drop_keys = set(args.drop or ())

    if args.host_key == "pms":
        base, payload, headers = _pms_context(body, extra_headers)
        session = requests.Session()
        session.trust_env = False
        url, host = base + path, "pms"
    else:
        # 不做本地 24h 过期拦截 / 远端探针：token 可能失效但 cms_token 仍有效
        # （见 通用/api_认证与公共约定.md §2.1），让接口业务码 40000/40020 来判定。
        # 发送 key：--token / SCM_TOKEN / --credential-file 提供"完整凭证 JSON"时，
        # 经 scm_common 构造等价凭证字典（含 cookies/provider_id_m），供 build_session 使用。
        cred = credential.load(args.account)
        injected = getattr(args, "token", None) or os.getenv("SCM_TOKEN", "").strip()
        cred_file = getattr(args, "credential_file", None) or os.getenv("SCM_CREDENTIAL_FILE", "").strip()
        if injected or cred_file:
            import scm_common
            cred = scm_common.resolve_credential(token=injected, credential_file=cred_file)
        if not cred:
            raise SkillError("AUTH_REQUIRED", "没有可用的 SCM 凭证",
                             hint="python scm.py login --account <账号>")
        session = build_session(cred)
        token = str(cred.get("cms_token") or cred.get("token") or "")
        payload = public_params(token, args.ex)
        payload.update(body)
        url, host = BASE + path, "scm"
        headers = extra_headers or None

    for key in drop_keys:
        payload.pop(key, None)

    result = call_endpoint(session, url, payload, method=args.method,
                           headers=headers, out=args.out)
    emit({"ok": True, "host": host, "path": path,
          "method": args.method.upper(), **result})
    return 0


def _scene_root() -> Path:
    return Path(__file__).resolve().parent / "assets"


def _scene_meta() -> list[dict]:
    """扫描 assets/*/scene.json（只读 JSON，不 import 代码，毫秒级）。"""
    out: list[dict] = []
    for p in sorted(_scene_root().glob("*/scene.json")):
        try:
            meta = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(meta, dict) or not meta.get("name") or meta.get("disabled"):
            continue
        meta["_dir"] = str(p.parent)
        out.append(meta)
    return out


def _run_scene(name: str, argv: list[str]) -> int:
    """懒加载 assets/<场景>/entry.py 并透传参数（单场景异常不影响其他）。"""
    import importlib.util

    for meta in _scene_meta():
        if meta.get("name") != name:
            continue
        entry = Path(meta["_dir"]) / str(meta.get("entry") or "entry.py")
        if not entry.is_file():
            raise SkillError("SCENE_BROKEN", f"场景 {name} 缺少 {entry.name}",
                             hint=f"检查 {meta['_dir']}")
        mod_name = "scm_scene_" + name.replace("-", "_")
        spec = importlib.util.spec_from_file_location(mod_name, entry)
        if spec is None or spec.loader is None:
            raise SkillError("SCENE_BROKEN", f"场景 {name} 无法加载")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return int(mod.main(argv) or 0)
    raise SkillError("PARAM_INVALID", f"未找到场景 {name}",
                     hint="python scm.py scene 查看已封装场景")


def cmd_scene(args) -> int:
    if not args.name:
        emit({"ok": True, "scenes": [
            {k: m.get(k) for k in ("name", "version", "summary", "actions",
                                   "write", "scope", "requires")}
            for m in _scene_meta()]})
        return 0
    return _run_scene(args.name, list(args.rest or []))


def _assets() -> list[dict]:
    base = ROOT / "assets"
    result = []
    for folder in sorted(p for p in base.iterdir() if p.is_dir()):
        guide = folder / "GUIDE.md"
        result.append({"id": folder.name, "guide": str(guide.relative_to(ROOT)).replace("\\", "/"),
                       "exists": guide.is_file()})
    return result


def cmd_assets(_args) -> int:
    emit({"ok": True, "assets": _assets()})
    return 0


def cmd_asset(args) -> int:
    for item in _assets():
        if item["id"] == args.name:
            emit({"ok": True, **item})
            return 0
    raise SkillError("PARAM_INVALID", f"未知资产：{args.name}", hint="python scm.py assets")


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--account", help="SCM 账号（默认使用当前生效凭证）")
    common.add_argument("--cred-dir", help="凭证目录（默认 %%LOCALAPPDATA%%\\scm-operations-query）")
    common.add_argument("--no-remote", action="store_true", help="跳过远端校验（仅 status）")
    common.add_argument("--token", help="外部注入 SCM token（发送 key；优先于本地凭证，绝不弹窗）")
    common.add_argument("--credential-file", help="外部凭证 JSON 文件（发送 key；字段 token/cms_token）")

    parser = argparse.ArgumentParser(prog="scm.py", description="SCM 商家后台助手")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", parents=[common], help="校验凭证")
    p_login = sub.add_parser("login", parents=[common], help="登录（弹窗）")
    p_login.add_argument("--password", help="密码（可省略，弹窗内输入）")

    # PMS 登录（自营活动管理「转PMS」前置）：凭证独立，落 pms-operations-query
    sub.add_parser("pms-status", parents=[common], help="PMS 凭证校验（不弹窗）")
    sub.add_parser("pms-login", parents=[common], help="PMS 企微扫码登录（弹窗）")

    sub.add_parser("modules", help="列出板块与状态")
    sub.add_parser("assets", help="列出资产")

    p_asset = sub.add_parser("asset", help="查看资产说明")
    p_asset.add_argument("name")

    p_query = sub.add_parser("query", parents=[common], help="查询（商品）")
    p_query.add_argument("--module", default="goods")
    p_query.add_argument("--status")
    p_query.add_argument("--type", action="append", help="活动类型，可重复")
    p_query.add_argument("--condition", help="标签筛选（名称或数字）")
    p_query.add_argument("--keyword", default="")
    p_query.add_argument("--limit", type=int, default=20)
    p_query.add_argument("--page", type=int, default=1)
    p_query.add_argument("--param", action="append", help="扩展筛选 k=v，可重复")
    p_query.add_argument("--count", action="store_true", help="返回状态计数")
    p_query.add_argument("--stats", action="store_true", help="返回第二排统计")

    p_export = sub.add_parser("export", parents=[common], help="导出（商品）")
    p_export.add_argument("--module", default="goods")
    p_export.add_argument("--status")
    p_export.add_argument("--all-status", action="store_true", help="全部状态（不含已结束）")
    p_export.add_argument("--group-center", action="store_true", help="组单中心活动")
    p_export.add_argument("--type", action="append")
    p_export.add_argument("--condition")
    p_export.add_argument("--keyword", default="")
    p_export.add_argument("--param", action="append")
    p_export.add_argument("--out")
    p_export.add_argument("--poll-timeout", type=int, default=None,
                          help="导出任务轮询超时秒数（默认 900；status=4 属短暂态会持续轮询）")

    p_dict = sub.add_parser("dict", parents=[common], help="动态字典")
    p_dict.add_argument("--name")
    p_dict.add_argument("--list", action="store_true")

    # 通用调用器：文档已交付但 CLI 未封装的端点，按 api_*.md 的 path/body 直接发
    p_call = sub.add_parser("call", help="通用端点调用（按 api_*.md 直连）")
    p_call.add_argument("--account", help="SCM 账号（默认当前生效凭证）")
    p_call.add_argument("--cred-dir", help="凭证目录（默认 %%LOCALAPPDATA%%\\scm-operations-query）")
    p_call.add_argument("--token", help="外部注入 SCM token（发送 key）")
    p_call.add_argument("--credential-file", help="外部凭证 JSON 文件（发送 key）")
    p_call.add_argument("--host-key", choices=["scm", "pms"], default="scm",
                        help="目标体系：SCM 后台 / PMS 活动管理（凭证独立）")
    p_call.add_argument("--path", required=True, help="站内路径，以 / 开头")
    p_call.add_argument("--method", choices=["post", "get"], default="post")
    p_call.add_argument("--body", help="JSON 对象字符串，或 @文件路径（UTF-8）")
    p_call.add_argument("--param", action="append", help="业务参数 k=v，可重复；覆盖 --body 同名字段")
    p_call.add_argument("--ex", default="goodsOnShelves",
                        help="SCM 公共参数 ex（数据板块见各自 api_*.md）")
    p_call.add_argument("--header", action="append", help="请求头 k=v，可重复（PMS module 差异用）")
    p_call.add_argument("--drop", action="append",
                        help="从请求体删除某公共参数字段，可重复（客户列表不带 lastBuildTime）")
    p_call.add_argument("--out", help="文件流落盘路径（同步 xlsx/CSV 导出必填）")

    # 高频场景：assets/<场景>/scene.json 动态发现，entry.py 懒加载
    p_scene = sub.add_parser("scene", help="高频场景（assets 动态发现）")
    p_scene.add_argument("name", nargs="?", help="场景名；省略则列出全部")
    p_scene.add_argument("rest", nargs=argparse.REMAINDER,
                         help="透传给场景 entry.py 的参数")
    return parser


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    if not raw:
        # 沙箱/评测器常以「无参运行」作为入口探测：打印帮助并正常退出
        build_parser().print_help()
        return 0
    args = build_parser().parse_args(raw)
    if getattr(args, "cred_dir", None):
        os.environ["SCM_OPERATIONS_HOME"] = str(Path(args.cred_dir).expanduser().resolve())
    handlers = {
        "status": cmd_status, "login": cmd_login, "modules": cmd_modules,
        "query": cmd_query, "export": cmd_export, "dict": cmd_dict,
        "assets": cmd_assets, "asset": cmd_asset, "call": cmd_call,
        "scene": cmd_scene,
        "pms-status": cmd_pms_status, "pms-login": cmd_pms_login,
    }
    try:
        return handlers[args.command](args)
    except SkillError as exc:
        emit(exc.to_dict())
        return exc.exit_code
    except KeyboardInterrupt:
        emit({"ok": False, "error": "CANCELLED", "message": "用户取消"})
        return 130
    except Exception as exc:  # noqa: BLE001
        emit({"ok": False, "error": "INTERNAL", "message": repr(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
