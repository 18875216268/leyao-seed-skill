# -*- coding: utf-8 -*-
"""技能自检：结构 / 注册表 / 文档 / CLI 冒烟。

用法：
  python tests/selftest.py            # 离线检查
  python tests/selftest.py --live     # 追加真实凭证与查询检查
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRY = "app.md"  # 资产入口（框架规范：app.md；SKILL.md 只属包根）
sys.path.insert(0, str(ROOT))

PASS = FAIL = 0


def ok(name: str, cond: bool, extra: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [PASS] %s" % name)
    else:
        FAIL += 1
        print("  [FAIL] %s %s" % (name, extra))


def check_structure() -> None:
    print("\n=== 1. 目录深度（≤2 层文件夹） ===")
    deepest = 0
    offenders = []
    for path in ROOT.rglob("*"):
        if not path.is_dir() or "__pycache__" in path.parts:
            continue
        depth = len(path.relative_to(ROOT).parts)
        deepest = max(deepest, depth)
        # 扁平结构：assets/<资产>/ 最多 2 层
        if depth > 2:
            offenders.append(str(path.relative_to(ROOT)))
    ok("最深层级 = %d" % deepest, deepest <= 2 and not offenders, str(offenders))
    ok("顶层目录 7 个（含 examples/scripts）", sorted(p.name for p in ROOT.iterdir() if p.is_dir() and p.name != "__pycache__")
       == ["assets", "core", "examples", "modules", "references", "scripts", "tests"])


def check_registry() -> None:
    print("\n=== 2. 板块注册表 ===")
    from modules import MODULES, list_modules, require_ready
    ok("板块数量 = 11", len(MODULES) == 11, list(MODULES))
    ok("goods 为 ready", MODULES["goods"]["status"] == "ready")
    todo = [k for k, v in MODULES.items() if v["status"] == "todo"]
    ok("待开发板块 = 9", len(todo) == 9, todo)
    try:
        require_ready("aftersale")
        ok("待开发板块应抛 MODULE_TODO", False)
    except Exception as exc:  # noqa: BLE001
        ok("待开发板块抛 MODULE_TODO", getattr(exc, "code", "") == "MODULE_TODO")

    # 防双源漂移：MODULES 的 endpoints 计数必须与各板块 __init__ 的清单长度一致
    import importlib as _il
    mismatch = []
    for mid, meta in MODULES.items():
        mod = _il.import_module("modules.%s" % mid)
        listed = getattr(mod, "ENDPOINTS", None)
        if isinstance(listed, (list, tuple, set)) and len(listed) != meta["endpoints"]:
            mismatch.append("%s: 登记 %d / 实际 %d" % (mid, meta["endpoints"], len(listed)))
    ok("板块端点计数与清单一致", not mismatch, mismatch)

    # 防跨板块重复登记：同一端点只能归属一个板块
    _seen = {}
    _dup = []
    for mid in MODULES:
        _mod = _il.import_module("modules.%s" % mid)
        for _e in getattr(_mod, "ENDPOINTS", []) or []:
            if _e in _seen:
                _dup.append("%s：%s & %s" % (_e, _seen[_e], mid))
            else:
                _seen[_e] = mid
    ok("端点不跨板块重复", not _dup, _dup[:5])

    from modules.order.query import build_body

    体 = build_body(page=2, size=50, drug_store="D1", order_id="O1", phone="138",
                   logistics_no="L1", drug_name="X", tab=8,
                   start="2026-10-01", end="2026-10-31")
    ok("订单查询体完整",
       体["page"] == 2 and 体["pagesize"] == 50 and 体["tabProcessStatus"] == 8
       and 体["drugStore"] == "D1" and 体["orderId"] == "O1"
       and 体["ex"] == "AllOrdersList"
       and 体["order_time"] == ["2026-10-01T00:00:00+08:00", "2026-10-31T23:59:59+08:00"])
    ok("list_modules 可用", len(list_modules()) == 11)


def check_module_dirs() -> None:
    print("\n=== 3. 板块目录与 GUIDE ===")
    from modules import MODULES
    for mid, meta in MODULES.items():
        folder = ROOT / "modules" / mid
        ok("%s/ 存在" % mid, folder.is_dir())
        ok("%s/GUIDE.md 存在" % mid, (folder / "GUIDE.md").is_file())
        if meta["status"] == "todo":
            guide = (folder / "GUIDE.md").read_text(encoding="utf-8")
            ok("%s 标注开放状态" % mid,
               ("暂未开放" in guide) or ("开放部分" in guide))
            ok("%s 有端点表" % mid, "| # | 路径 |" in guide)


def check_references() -> None:
    print("\n=== 4. 参考文档 ===")
    files = sorted(p for p in (ROOT / "references").rglob("*.md"))
    ok("参考文档 ≥9 篇", len(files) >= 9, str(len(files)))
    for name in ["sy.md", "通用/sy.md", "通用/api_认证与公共约定.md", "通用/api_动态字典.md", "通用/api_导出任务.md",
                 "商品/sy.md", "商品/zddz.md", "商品/api_商品读取.md", "商品/api_商品写入.md",
                 "商品/api_商品下载.md", "商品/api_pms活动管理.md",
                 "订单/sy.md", "订单/zddz.md", "订单/api_订单查询.md",
                 "订单/api_订单导出.md", "订单/api_订单详情.md",
                 "客户/sy.md", "客户/zddz.md", "客户/api_客户列表.md", "客户/api_控销组.md", "客户/api_黑名单.md",
                 "数据/sy.md", "数据/zddz.md", "数据/api_品种分析.md", "数据/api_销售报表.md",
                 "数据/api_店铺流量.md",
                 "我的摇钱树/sy.md", "我的摇钱树/zddz.md", "我的摇钱树/api_摇钱树销售流水.md",
                 "我的摇钱树/api_我的品种.md", "我的摇钱树/api_区域划分查看.md",
                 "附录/接口总表.md"]:
        ok("存在 references/%s" % name, (ROOT / "references" / name).is_file())

    # 防「端点数漂移」：附录合计声明必须等于编号行数，且 SKILL.md 板块表数字须与注册表一致
    import re as _re
    from modules import MODULES as _MODULES
    ap = (ROOT / "references/附录/接口总表.md").read_text(encoding="utf-8")
    rows = _re.findall(r"^\|\s*\d+\s*\|", ap, _re.M)
    declared = _re.search(r"> 合计 \*\*(\d+)\*\* 个端点。", ap)
    ok("附录合计=编号行数",
       bool(declared) and int(declared.group(1)) == len(rows),
       "声明=%s 行数=%d" % (declared.group(1) if declared else "?", len(rows)))

    skill_txt = (ROOT / ENTRY).read_text(encoding="utf-8")
    drift = []
    for line in skill_txt.splitlines():
        mm = _re.match(r"\|\s*\S+\s*\|\s*`(\w+)`\s*\|", line)
        if not mm or mm.group(1) not in _MODULES:
            continue
        # 说明列可能同时出现「分项数」和「板块总数」：只要包含注册表总数即通过
        nn = [int(x) for x in _re.findall(r"(\d+)\s*个端点", line)]
        real = _MODULES[mm.group(1)]["endpoints"]
        if nn and real not in nn:
            drift.append("%s: 文档%s / 注册%d" % (mm.group(1), nn, real))
    ok("SKILL 端点数与注册表一致", not drift, str(drift))

    # 状态口径守门：客户/数据/摇钱树＝开放部分（有 api 文档）；其余 6 个＝完全暂未开放（无 references 文档）
    for mid, cn in (("customer", "客户"), ("data", "数据"), ("cashcow", "我的摇钱树")):
        apis = list((ROOT / "references" / cn).glob("api_*.md"))
        ok("%s 开放部分须有 api 文档" % mid, len(apis) >= 1, str(len(apis)))
    for mid, cn in (("aftersale", "售后"), ("marketing", "营销"),
                    ("qualification", "资质"), ("shop", "店铺"),
                    ("finance", "资金"), ("home", "首页")):
        ok("%s 暂未开放不建 references 文档" % mid,
           not (ROOT / "references" / cn).exists())

    status_drift = []
    for line in skill_txt.splitlines():
        mm = _re.match(r"\|\s*(\S+)\s*\|\s*`(\w+)`\s*\|\s*([^|]+)\|", line)
        if not mm or mm.group(2) not in _MODULES:
            continue
        state = mm.group(3).strip()
        if mm.group(2) in ("customer", "data", "cashcow") and "开放部分" not in state:
            status_drift.append("%s 应为开放部分" % mm.group(2))
        if mm.group(2) in ("aftersale", "marketing", "qualification", "shop",
                          "finance", "home") and "暂未开放" not in state:
            status_drift.append("%s 应为暂未开放" % mm.group(2))
    ok("SKILL 四档状态口径一致", not status_drift, str(status_drift))

    # 归属副本一致性：§0 变更后这些副本必须同步（防止双源漂移）
    for _f, _tag in (("api_品种分析.md", "① 通用"), ("api_销售报表.md", "① 通用"),
                     ("api_店铺流量.md", "③ 仅自营")):
        _head = "\n".join((ROOT / "references/数据" / _f).read_text(
            encoding="utf-8").splitlines()[:8])
        ok("数据/%s 归属副本" % _f, _tag in _head, _tag)
    for _f in ("api_摇钱树销售流水.md", "api_我的品种.md", "api_区域划分查看.md"):
        _head = "\n".join((ROOT / "references/我的摇钱树" / _f).read_text(
            encoding="utf-8").splitlines()[:8])
        ok("我的摇钱树/%s 归属副本" % _f, "② 仅摇钱树" in _head, "② 仅摇钱树")

    # 安全：PII / 具体 providerId / 测试账号明文不得入包
    _pii = []
    for _p in ROOT.rglob("*"):
        if not _p.is_file() or _p.suffix not in (".md", ".py", ".json") or _p.name == "selftest.py":
            continue  # 守门器自身持有黑名单字面量，跳过
        _t = _p.read_text(encoding="utf-8", errors="ignore")
        for _pat in ("13800000000", "LY000000", '"provider_id": 9999',
                     '"name": "重庆央拓"', '"userName":"张三"'):
            if _pat in _t:
                _pii.append("%s:%s" % (_p.name, _pat))
    ok("无 PII / 具体标识明文", not _pii, str(_pii[:4]))

    # 防本次已知坏引用回潮
    _stale = []
    _allmd = "\n".join(p.read_text(encoding="utf-8") for p in ROOT.rglob("*.md"))
    for _s in ("opFlag=2", "见 1.9", "§4.1 #5", "订单导出（暂未开放）", "其余 83 个"):
        if _s in _allmd:
            _stale.append(_s)
    ok("无已知坏引用", not _stale, str(_stale))

    # 安全红线：测试活动下架护栏 + 三种授权
    ok("测试活动下架护栏已落地",
       "测试/复制产生的活动" in (ROOT / "AGENT_GUIDE.md").read_text(encoding="utf-8")
       and "测试活动必下架" in (ROOT / ENTRY).read_text(encoding="utf-8"))
    ok("写授权为三种",
       "### 10.1 三种授权" in (ROOT / "AGENT_GUIDE.md").read_text(encoding="utf-8"))

    # 订单导出 MODULE_TODO 必须给出「按文档直连」提示，避免 Agent 判为功能不存在
    _hint, _msg = "", ""
    try:
        from core.errors import SkillError as _SE2
        from modules.order import export as _oe2
        try:
            _oe2.export(None, None, None)
        except _SE2 as _e2:
            _hint = str(getattr(_e2, "hint", ""))
            _msg = str(_e2)
        ok("订单导出 MODULE_TODO 指向直连文档",
           "api_订单导出.md" in _hint and "CLI 未封装" in _msg,
           (_hint + "|" + _msg)[:80])
    except Exception as _e3:  # noqa: BLE001
        ok("订单导出 MODULE_TODO 指向直连文档", False, str(_e3))

    # 订单导出：文档层已交付、CLI 未封装；不得再出现「订单导出（暂未开放）」
    ok("SKILL 不再把订单导出列为不能做",
       "订单导出（暂未开放）" not in skill_txt)
    ok("订单导出能力复用公共骨架",
       "from .._skeleton import unavailable" in
       (ROOT / "modules/order/export.py").read_text(encoding="utf-8"))
    try:
        from core.errors import SkillError as _SE
        from modules.order import export as _oe
        try:
            _oe.export(None, None, None)
            _actual = "未抛错"
        except _SE as _exc:
            _actual = _exc.details.get("endpoints")
        ok("订单导出 MODULE_TODO 的 endpoints 是整数",
           isinstance(_actual, int), repr(_actual)[:80])
    except Exception as _e:  # noqa: BLE001
        ok("订单导出 MODULE_TODO 的 endpoints 是整数", False, str(_e))


def check_docs() -> None:
    print("\n=== 5. app.md / manifest ===")
    skill = (ROOT / ENTRY).read_text(encoding="utf-8")
    _nm = (re.search(r'^name:\s*"([^"]+)"', skill, re.M) or [None, ""])[1]
    ok("frontmatter 含 name", bool(_nm) and " " not in _nm, _nm)
    ok("app.md ≤260 行", len(skill.splitlines()) <= 260, str(len(skill.splitlines())))
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    ok("manifest.name 非空且无空格",
       bool(manifest.get("name")) and " " not in str(manifest.get("name")),
       manifest.get("name"))
    ok("manifest 板块数 = 11", len(manifest.get("modules", {})) == 11)
    ok("manifest 资产数 = 2", len(manifest.get("assets", {})) == 2)


def check_no_hardcode() -> None:
    print("\n=== 6. 无硬编码账号 ===")
    hits = []
    # 通用守门：代码里不得把具体账号名写成字面量（换任何测试账号都能防住）。
    # 匹配 login --account xxx / account = "xxx" / "account": "xxx"，排除 <...> / {...} 占位符。
    import re as _re
    _pat = _re.compile(
        r"""(?:--account\s+|account\s*=\s*|["']account["']\s*:\s*)["']"""
        r"""(?![<{])[A-Za-z][A-Za-z0-9_]{3,}["']"""
    )
    for path in ROOT.rglob("*.py"):
        if "__pycache__" in path.parts or path.name == "selftest.py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for _m in _pat.finditer(text):
            hits.append("%s:%s" % (path.name, _m.group(0).strip()))
    ok("代码中无账号硬编码", not hits, str(hits))


def run_cli(*args: str) -> tuple[int, dict]:
    proc = subprocess.run([sys.executable, str(ROOT / "scm.py"), *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=120)
    try:
        payload = json.loads((proc.stdout or "{}").strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        payload = {}
    return proc.returncode, payload


def check_cli() -> None:
    print("\n=== 7. CLI 冒烟 ===")
    code, data = run_cli("modules")
    ok("modules 退出码 0", code == 0)
    ok("modules 返回 11 个", len(data.get("modules") or []) == 11)
    code, data = run_cli("assets")
    ok("assets 退出码 0", code == 0 and len(data.get("assets") or []) == 2)
    code, data = run_cli("asset", "ljgl")
    ok("asset ljgl 可用", code == 0 and data.get("id") == "ljgl")
    code, data = run_cli("asset", "nope")
    ok("未知资产 → 退出码 2", code == 2 and data.get("error") == "PARAM_INVALID")
    from modules.goods.dicts import DICTS

    code, data = run_cli("dict", "--list")
    ok("dict --list 与 DICTS 一致", code == 0 and len(data.get("dicts") or []) == len(DICTS))
    code, data = run_cli("query", "--module", "aftersale")
    ok("骨架板块 → 退出码 2", code == 2 and data.get("error") == "MODULE_TODO")

    import scm as cli

    ok("--param 整数转 int", cli.parse_params(["storeType=122690"])["storeType"] == 122690)
    ok("--param 数组按 JSON 解析", cli.parse_params(["busiScope=[1,2]"])["busiScope"] == [1, 2])
    ok("--param 对象按 JSON 解析", cli.parse_params(['opt={"a":1}'])["opt"] == {"a": 1})
    try:
        cli.parse_params(["x=[1,"])
        ok("--param 非法 JSON 报错", False)
    except Exception as exc:  # noqa: BLE001
        ok("--param 非法 JSON 报错", getattr(exc, "code", "") == "PARAM_INVALID")


def check_skeletons() -> None:
    print("\n=== 8. 板块能力入口 ===")
    import importlib
    from modules import MODULES
    for mid in MODULES:
        folder = ROOT / "modules" / mid
        for kind in ("query", "export"):
            path = folder / ("%s.py" % kind)
            ok("%s/%s.py 存在" % (mid, kind), path.is_file())
            try:
                _ = importlib.import_module("modules.%s.%s" % (mid, kind))
                ok("%s/%s.py 可导入" % (mid, kind), True)
            except Exception as exc:  # noqa: BLE001
                ok("%s/%s.py 可导入" % (mid, kind), False, repr(exc))
    for mid, meta in MODULES.items():
        if meta["status"] != "todo":
            continue
        try:
            _ = importlib.import_module("modules.%s.query" % mid).query(None, "token")
            ok("%s.query 抛 MODULE_TODO" % mid, False)
        except Exception as exc:  # noqa: BLE001
            ok("%s.query 抛 MODULE_TODO" % mid, getattr(exc, "code", "") == "MODULE_TODO")


def check_assets() -> None:
    print("\n=== 9. 资产 ===")
    tpcl = ROOT / "assets" / "tpcl"
    ok("assets/tpcl/tpcl.py 存在", (tpcl / "tpcl.py").is_file())
    guide = (tpcl / "GUIDE.md").read_text(encoding="utf-8")
    ok("tpcl GUIDE 指向线上文档", "https://st.cfdaili.top/md" in guide)
    code, data = run_cli("asset", "tpcl")
    ok("asset tpcl 可用", code == 0 and data.get("id") == "tpcl")
    proc = subprocess.run([sys.executable, str(tpcl / "tpcl.py"), "status", "--no-remote"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=60)
    try:
        payload = json.loads((proc.stdout or "{}").strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        payload = {}
    ok("tpcl status --no-remote 可运行",
       proc.returncode == 0 or payload.get("error") == "IMAGE_KEY_MISSING",
       str(payload)[:160])


def check_goods() -> None:
    print("\n=== 10. 商品行为 ===")
    import scm as cli
    from modules.goods import TABCODE_MAP, normalize_status, normalize_types
    from modules.goods.query import build_body

    body = build_body(status="进行中", types=["一口价"], keyword="来曲唑",
                      condition="品种补贴", extra={"isRestrict": 1, "busiScope": [1, 2]})
    ok("goods 归一字段正确",
       body["status"] == 0 and body["wholesaleType"] == ["1"]
       and body["searchInfo"] == "来曲唑" and body["condition"] == 14)
    ok("goods 扩展筛选生效", body["isRestrict"] == 1 and body["busiScope"] == [1, 2])
    ok("goods extra 不覆盖归一字段",
       build_body(status="进行中", extra={"status": 9, "searchInfo": "x"})["status"] == 0)
    ok("goods 空值不进请求体", "drugName" not in build_body(extra={"drugName": ""}))
    ok("状态/类型/tabCode 映射",
       normalize_status("全部") == -1 and normalize_types(["1"]) == ["1"] and len(TABCODE_MAP) == 10)
    try:
        normalize_types(["time_limit"])
        ok("非法类型报错", False)
    except Exception as exc:  # noqa: BLE001
        ok("非法类型报错", getattr(exc, "code", "") == "PARAM_INVALID")
    ok("--param 前导零保留", cli.parse_params(["provDrugCode=0123"])["provDrugCode"] == "0123")
    ok("--param 布尔转 bool", cli.parse_params(["hasLogo=true"])["hasLogo"] is True)
    code, data = run_cli("export", "--group-center", "--all-status")
    ok("组单中心不接受筛选", code == 2 and data.get("error") == "PARAM_INVALID")


def check_export_polling() -> None:
    """回归：status=4 是短暂异常态，必须继续轮询直到 3，不得误判失败。"""
    print("\n=== 11. 导出轮询状态机 ===")
    from unittest import mock

    import core.export_task as et
    from core.errors import SkillError

    RID = 123456
    URL = "https://ysbexport.example/a.csv"

    def task(status, url=""):
        return {"exportTaskRecordPageResult": {"results": [
            {"recordId": RID, "status": status, "qiniuUrl": url}]}}

    def run(statuses, final_url=URL, **kw):
        """按给定状态序列驱动 wait_url；时钟每次调用推进 10s，不真实 sleep。"""
        clock = iter(range(0, 100000, 10))
        seq = iter(statuses)

        def fake_post(*a, **k):
            st = next(seq)
            return task(st, final_url if st == 3 else "")

        with mock.patch.object(et, "post", side_effect=fake_post), \
             mock.patch.object(et.time, "monotonic", side_effect=lambda: next(clock)), \
             mock.patch.object(et.time, "sleep"):
            try:
                return et.wait_url(None, "t", RID, interval=1, **kw), None
            except SkillError as exc:
                return None, exc
            except StopIteration:
                return None, "序列耗尽"

    # ① status=4 短暂态 → 转 3 成功（本次修复的核心）
    url, err = run([4, 4, 4, 3], timeout=900)
    ok("status=4 后转 3 成功返回 URL", url == URL and err is None, str(err))
    with mock.patch.object(et, "post", side_effect=lambda *a, **k: task(3, URL)), \
         mock.patch.object(et.time, "monotonic", side_effect=iter([0, 0, 1])), \
         mock.patch.object(et.time, "sleep"):
        ok("status=3 且带 qiniuUrl 直接返回", et.wait_url(None, "t", RID, interval=1) == URL)
    # status=3 但无下载地址应给明确提示，且提示勿重复提交
    with mock.patch.object(et, "post", side_effect=lambda *a, **k: task(3, "")), \
         mock.patch.object(et.time, "monotonic", side_effect=iter([0, 0, 1])), \
         mock.patch.object(et.time, "sleep"):
        try:
            et.wait_url(None, "t", RID, interval=1)
            ok("status=3 无 URL 报 EXPORT_NO_URL", False)
        except SkillError as exc:
            ok("status=3 无 URL 报 EXPORT_NO_URL", exc.code == "EXPORT_NO_URL"
               and "勿重复提交" in exc.hint, str(exc))

    # ② 4 → 1 → 3：中间回到进行中应重置异常宽限
    clock = iter(range(0, 100000, 30))
    seq = iter([4, 4, 1, 1, 3])
    with mock.patch.object(et, "post", side_effect=lambda *a, **k: task(next(seq), URL)), \
         mock.patch.object(et.time, "monotonic", side_effect=lambda: next(clock)), \
         mock.patch.object(et.time, "sleep"):
        ok("4→1→3 不误判且成功", et.wait_url(None, "t", RID, interval=1, timeout=900,
                                             abnormal_grace=90) == URL)

    # ③ 持续 4 超过宽限 → EXPORT_FAILED，且提示勿重复提交
    url, err = run([4] * 200, final_url="", timeout=900, abnormal_grace=120)
    ok("持续 status=4 超宽限报 EXPORT_FAILED",
       isinstance(err, SkillError) and err.code == "EXPORT_FAILED", str(err))
    ok("EXPORT_FAILED 提示勿重复提交",
       isinstance(err, SkillError) and "勿重复提交" in err.hint, str(err))

    # ④ status=5 已过期立即失败
    url, err = run([1, 5], timeout=900)
    ok("status=5 立即报 EXPORT_EXPIRED",
       isinstance(err, SkillError) and err.code == "EXPORT_EXPIRED", str(err))

    # ⑤ 字符串状态可归一化
    with mock.patch.object(et, "post", side_effect=lambda *a, **k: task("3", URL)), \
         mock.patch.object(et.time, "monotonic", side_effect=iter([0, 0, 1])), \
         mock.patch.object(et.time, "sleep"):
        ok("字符串 '3' 也能识别", et.wait_url(None, "t", RID, interval=1) == URL)

    # ⑥ 默认超时覆盖实测约 10 分钟延迟
    ok("默认超时 900s 覆盖 status=4 约 600s 延迟", et.DEFAULT_TIMEOUT >= 600)

    # ⑦ CLI 暴露 --poll-timeout
    import scm as cli
    p = cli.build_parser().parse_args(["export", "--poll-timeout", "120"])
    ok("CLI --poll-timeout 可解析", p.poll_timeout == 120)
    ok("其它板块骨架不受 poll_timeout 影响", cli._poll_kwargs(p, lambda a, b, c: None) == {})


def check_call() -> None:
    print("\n=== 11.1 通用调用器 scm.py call ===")
    import tempfile
    from pathlib import Path
    from unittest.mock import patch

    import scm as cli
    from core.errors import SkillError
    from core.http import call_endpoint

    parser = cli.build_parser()
    a = parser.parse_args(["call", "--path", "/scm-order/wholesaleOrder/list"])
    ok("call 子命令已注册", a.command == "call" and callable(cli.cmd_call))
    ok("call 默认值 scm/post/goodsOnShelves",
       a.host_key == "scm" and a.method == "post" and a.ex == "goodsOnShelves")

    b = parser.parse_args(["call", "--path", "/x", "--body", '{"a":1,"b":"s"}',
                            "--param", "b=2", "--param", "c=true", "--param", "d=[1,2]"])
    ok("--body/--param 合并且覆盖",
       cli._call_payload(b) == {"a": 1, "b": 2, "c": True, "d": [1, 2]},
       str(cli._call_payload(b)))
    with tempfile.TemporaryDirectory() as td:
        fp = Path(td) / "payload.json"
        fp.write_text('{"tab":0}', encoding="utf-8")
        c = parser.parse_args(["call", "--path", "/x", "--body", "@" + str(fp)])
        ok("--body @文件 可读", cli._call_payload(c).get("tab") == 0)
    d = parser.parse_args(["call", "--path", "/x", "--drop", "lastBuildTime"])
    ok("--drop 可解析", d.drop == ["lastBuildTime"])

    for bad in ("https://invalid.example/x", "/a/../b", "x"):
        try:
            cli.cmd_call(parser.parse_args(["call", "--path", bad]))
            ok("拒绝非法 path " + bad, False, "未抛错")
        except SkillError as exc:
            ok("拒绝非法 path " + bad, exc.code == "PARAM_INVALID", exc.code)

    class _Resp:
        def __init__(self, payload=None, content=b""):
            self.status_code = 200
            self._payload = payload
            self.content = content
            self.headers = {"Content-Type": "application/octet-stream"}

        def json(self):
            if self._payload is None:
                raise ValueError("binary")
            return self._payload

    class _Session:
        def __init__(self, resp):
            self.resp, self.calls = resp, []

        def request(self, method, url, **kw):
            self.calls.append((method, url, kw))
            return self.resp

    s = _Session(_Resp({"code": "40001", "data": {"rows": [1]}}))
    r = call_endpoint(s, "https://scm.ysbang.cn/x", {"token": "T"}, headers={"X": "1"})
    ok("call_endpoint JSON 成功", r.get("kind") == "json" and r["data"] == {"rows": [1]}, str(r))
    ok("call_endpoint POST json + 头",
       s.calls[0][0] == "POST" and "json" in s.calls[0][2]
       and s.calls[0][2]["headers"] == {"X": "1"})

    s2 = _Session(_Resp({"code": "40001", "data": []}))
    call_endpoint(s2, "https://scm.ysbang.cn/x", {}, method="get")
    ok("call_endpoint GET 走 params",
       "params" in s2.calls[0][2] and "json" not in s2.calls[0][2])
    try:
        call_endpoint(_Session(_Resp({"code": "40020", "message": "x"})), "u", {})
        ok("业务码统一映射", False, "未抛错")
    except SkillError as exc:
        ok("业务码统一映射", exc.code == "AUTH_EXPIRED", exc.code)
    with tempfile.TemporaryDirectory() as td:
        out = str(Path(td) / "sub" / "o.xlsx")
        r = call_endpoint(_Session(_Resp(content=b"PK\x03\x04")), "u", {}, out=out)
        ok("文件流落盘", r.get("kind") == "file"
           and Path(out).read_bytes() == b"PK\x03\x04", str(r))
    try:
        call_endpoint(_Session(_Resp(content=b"PK")), "u", {})
        ok("文件流无 --out 报错", False, "未抛错")
    except SkillError as exc:
        ok("文件流无 --out 报错", exc.code == "RESPONSE_INVALID", exc.code)

    # SCM 分支：cms_token 优先 + --drop 生效（全程 mock，不发网络）
    with patch("scm.credential.load", return_value={
            "cms_token": "CT", "token": "T", "provider_id_m": "m", "cookies": {}}), \
         patch("scm.build_session", return_value=_Session(_Resp({"code": "40001"}))), \
         patch("scm.call_endpoint", return_value={"kind": "json"}) as mocked, \
         patch("scm.emit"):
        cli.cmd_call(d)
        sent = mocked.call_args[0][2]
        ok("SCM 自动取 cms_token", sent.get("token") == "CT", str(sent.get("token")))
        ok("--drop 删除公共参数字段", "lastBuildTime" not in sent, str(sorted(sent)))

    with patch("core.pms_client.load_credential", return_value={"token": "PT"}):
        base, pp, hh = cli._pms_context({"page": 1}, {"module": "custom"})
    ok("PMS 主机/双 token/头",
       base.endswith("pms.ysbang.cn") and pp["token"] == "PT" and hh["token"] == "PT"
       and pp["page"] == 1 and hh["module"] == "custom", str(sorted(hh)))
    with patch("core.pms_client.load_credential", return_value={}):
        try:
            cli._pms_context({}, {})
            ok("PMS 无凭证给提示", False, "未抛错")
        except SkillError as exc:
            ok("PMS 无凭证给提示",
               exc.code == "AUTH_REQUIRED" and "pms-login" in exc.hint, exc.code)

    guide = (ROOT / "AGENT_GUIDE.md").read_text(encoding="utf-8")
    ok("AGENT_GUIDE §4.1 含 ex 速查", "### 4.1 通用调用器" in guide and all(
        x in guide for x in ("AllOrdersList", "OldCustomerManagement", "ProductAnalysis",
                             "NewSaleReportNested", "StoreTraffic", "--drop lastBuildTime")))
    ok("call 用法写入入口文档",
       "scm.py call" in (ROOT / ENTRY).read_text(encoding="utf-8")
       and "scm.py call" in (ROOT / "USER_GUIDE.md").read_text(encoding="utf-8"))


def check_order_link() -> None:
    print("\n=== 11.2 高频场景 ljgl ===")
    doc = ROOT / "assets/ljgl/GUIDE.md"
    ok("ljgl 场景文档存在", doc.is_file())
    if not doc.is_file():
        return
    t = doc.read_text(encoding="utf-8")
    for label, needle in (
        ("仅自营", "仅自营"), ("控销绑定字段", "restrictGroupId"),
        ("同空间验证", "同一 ID 空间"), ("全国商圈动态取", "nationwide=1"),
        ("默认当天整天", "00:00:01"), ("二维码 PNG", "qrcode[pil]"),
        ("一次性自动任务", "scheduleType=once"), ("成本价不改", "绝不改写"),
        ("217 键透传", "原样透传"), ("回滚", "## 7. 回滚"),
        ("真机确证章节", "## 9. 真机确证结论"),
    ):
        ok("ljgl 含 " + label, needle in t)
    idx = (ROOT / "assets/ljgl/GUIDE.md").read_text(encoding="utf-8")
    top = (ROOT / "assets/GUIDE.md").read_text(encoding="utf-8")
    skill = (ROOT / ENTRY).read_text(encoding="utf-8")
    ok("ljgl 已登记资产表", "| `ljgl/` |" in top and "scene ljgl" in top)
    ok("ljgl 已登记 assets/SKILL",
       "订单链接" in top and "ljgl/GUIDE.md" in skill)
    ok("C1~C5 全部定谳",
       "✅ **复制提交形态（真机确证）**" in t
       and "✅ **库存 / 限购（真机确证）**" in t
       and "✅ **下架体系（真机确证）**" in t
       and "✅ **商品编码 vs 药师帮id（已定谳）**" in t
       and "药师帮id ＝ 商品ID ＝ `drugId`" in t)
    ok("场景文档无悬空 §10 引用", "见 §10" not in t and "按 §10" not in t)
    ok("价格档位规则（priceTypes/unitPrice9）",
       "priceTypes" in t and "unitPrice9" in t)
    ok("提交必须 ex=fixedPriceShelf", "fixedPriceShelf" in t)
    ok("下架路径含 PMS W1", "updateYkjWholeSaleStatus" in t)
    ok("字段来源分层规则", "活动实例字段" in t)
    ok("活动备注默认模板", "WorkBuddy做单链接" in t and "editWsDesc" in t)
    ok("无被推翻的旧结论", "113 键平铺" not in t
       and "属 `priceType=0` 正常" not in t)
    ok("场景文档无具体账号硬编码",
       not any(x in t for x in ("ytlrc", "yqs22796", "22796", "3364")))


def check_scene_registry() -> None:
    print("\n=== 11.3 场景封装注册（assets/*/scene.json）===")
    import contextlib
    import importlib.util
    import io

    d = ROOT / "assets/ljgl"
    tri = ("GUIDE.md", "scene.json", "entry.py")
    ok("场景三件套齐备", all((d / f).is_file() for f in tri),
       str([f for f in tri if not (d / f).is_file()]))

    meta = json.loads((d / "scene.json").read_text(encoding="utf-8"))
    need = ("name", "version", "summary", "actions", "write", "entry")
    ok("scene.json 必填字段齐备", all(k in meta for k in need),
       str([k for k in need if k not in meta]))

    # 顶层无副作用：import 时不得产生 stdout 输出
    buf = io.StringIO()
    spec = importlib.util.spec_from_file_location("t_scene_entry", d / "entry.py")
    mod = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(buf):
        spec.loader.exec_module(mod)
    ok("entry.py 顶层无输出副作用", buf.getvalue().strip() == "",
       buf.getvalue()[:80])
    ok("SCENE 与 scene.json.name 一致", getattr(mod, "SCENE", None) == meta.get("name"),
       "%r vs %r" % (getattr(mod, "SCENE", None), meta.get("name")))
    ok("entry.py 提供 main(argv)", callable(getattr(mod, "main", None)))

    # actions 与 entry 的子命令一致
    parser = mod.build_parser()
    choices = [a.choices for a in parser._actions
               if hasattr(a, "choices") and isinstance(a.choices, dict)]
    cmds = set(choices[0]) if choices else set()
    ok("actions 与 entry 子命令一致", cmds == set(meta.get("actions") or []),
       "parser=%s meta=%s" % (sorted(cmds), meta.get("actions")))

    # 主 CLI 能动态发现
    import scm
    names = [m.get("name") for m in scm._scene_meta()]
    ok("scm.py scene 可发现 ljgl", "ljgl" in names, str(names))
    ok("场景写操作声明为 True", meta.get("write") is True)


def check_live() -> None:
    print("\n=== 12. 真实环境（--live） ===")
    code, data = run_cli("status", "--no-remote")
    ok("status 可用", code in (0, 3), str(data))
    if code == 0:
        code, data = run_cli("query", "--limit", "1")
        ok("query 返回数据", code == 0 and data.get("ok") is True, str(data)[:200])
        code, data = run_cli("dict", "--name", "priceTypes")
        ok("dict 可取价格档位", code == 0 and data.get("ok") is True, str(data)[:200])


def main() -> int:
    live = "--live" in sys.argv
    print("技能根目录:", ROOT)
    check_structure()
    check_registry()
    check_module_dirs()
    check_references()
    check_docs()
    check_no_hardcode()
    check_cli()
    check_skeletons()
    check_assets()
    check_goods()
    check_export_polling()
    check_call()
    check_order_link()
    check_scene_registry()
    if live:
        check_live()
    print("\n=== 汇总 ===")
    print("PASS=%d FAIL=%d" % (PASS, FAIL))
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
