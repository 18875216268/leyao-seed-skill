"""板块注册表。

每个板块一个文件夹：`modules/<id>/`
- `__init__.py`：元信息（状态、端点清单、能力、固定映射）
- `GUIDE.md`：该板块的使用说明（Agent 按需阅读）
- `query.py`：查询能力，标准接口 `query / count / statistics`
- `export.py`：导出能力，标准接口 `export / export_group_center`

`status = todo` 的板块，`query.py` / `export.py` 只保留接口签名，抛错逻辑统一在
`modules/_skeleton.py`（避免每个文件复制同一段）。常规链路先由 `require_ready`
拦截（退出码 2），骨架抛错是直接 import 能力模块时的契约兜底。

`MODULES` 里的 `endpoints` 是计数、各板块 `__init__.py` 的 `ENDPOINTS` 是明细清单，
两者由 `tests/selftest.py` 校验一致，勿单边修改。

**例外：`status = ready` 的商品板块（`goods`）不维护 `ENDPOINTS` 清单**——它的能力由
`modules/goods/query.py` / `export.py` 直接实现，端点明细在 `references/商品/*`；
其 `endpoints=83` 只是展示用计数（ready 板块不会走 `MODULE_TODO` 分支）。
因此 selftest 的计数断言只对**存在 `ENDPOINTS`** 的板块生效，这是设计如此，不是遗漏。

新增板块：建目录 + GUIDE + `__init__.py` + 能力模块，并在 `MODULES` 登记一行，不改核心层。
"""

from __future__ import annotations

from core.errors import SkillError

# status: ready=已实现 ｜ todo=待开发（仅端点清单）
MODULES: dict[str, dict] = {
    "goods": {
        "name": "商品", "status": "ready", "endpoints": 83,
        "guide": "modules/goods/GUIDE.md",
        "capabilities": ["query", "export", "dict"],
        "reference": ["references/商品", "references/通用"],
    },
    "order": {
        "name": "订单", "status": "ready", "endpoints": 85,
        "guide": "modules/order/GUIDE.md", "capabilities": ["query"],
        "reference": ["references/订单", "references/附录/接口总表.md"],
    },
    "aftersale": {
        "name": "售后", "status": "todo", "endpoints": 2,
        "guide": "modules/aftersale/GUIDE.md", "capabilities": [],
        "reference": ["references/附录/接口总表.md"],
    },
    "customer": {
        "name": "客户", "status": "todo", "endpoints": 33,
        "guide": "modules/customer/GUIDE.md", "capabilities": [],
        "reference": ["references/客户", "references/附录/接口总表.md"],
    },
    "data": {
        "name": "数据", "status": "todo", "endpoints": 48,
        "guide": "modules/data/GUIDE.md", "capabilities": [],
        "reference": ["references/数据", "references/附录/接口总表.md"],
    },
    "cashcow": {
        "name": "我的摇钱树", "status": "todo", "endpoints": 11,
        "guide": "modules/cashcow/GUIDE.md", "capabilities": [],
        "reference": ["references/我的摇钱树", "references/附录/接口总表.md"],
    },
    "marketing": {
        "name": "营销", "status": "todo", "endpoints": 79,
        "guide": "modules/marketing/GUIDE.md", "capabilities": [],
        "reference": ["references/附录/接口总表.md"],
    },
    "qualification": {
        "name": "资质", "status": "todo", "endpoints": 4,
        "guide": "modules/qualification/GUIDE.md", "capabilities": [],
        "reference": ["references/附录/接口总表.md"],
    },
    "shop": {
        "name": "店铺", "status": "todo", "endpoints": 52,
        "guide": "modules/shop/GUIDE.md", "capabilities": [],
        "reference": ["references/附录/接口总表.md"],
    },
    "finance": {
        "name": "资金", "status": "todo", "endpoints": 33,
        "guide": "modules/finance/GUIDE.md", "capabilities": [],
        "reference": ["references/附录/接口总表.md"],
    },
    "home": {
        "name": "首页", "status": "todo", "endpoints": 57,
        "guide": "modules/home/GUIDE.md", "capabilities": [],
        "reference": ["references/附录/接口总表.md"],
    },
}


def list_modules() -> list[dict]:
    """返回全部板块（含状态与说明路径）。"""
    return [{"id": mid, **meta} for mid, meta in MODULES.items()]


def get(mid: str) -> dict:
    """按 id 取板块元信息；未知抛错。"""
    meta = MODULES.get(mid)
    if not meta:
        raise SkillError("MODULE_UNKNOWN", f"未知板块：{mid}",
                         hint="可用板块见 `python scm.py modules`")
    return {"id": mid, **meta}


def require_ready(mid: str) -> dict:
    """要求板块已实现；待开发板块给出明确指引。"""
    meta = get(mid)
    if meta["status"] != "ready":
        raise SkillError(
            "MODULE_TODO",
            f"{meta['name']}板块暂未开放（已登记 {meta['endpoints']} 个端点）",
            hint=f"查看 {meta['guide']}",
            details={"module": mid, "endpoints": meta["endpoints"]},
        )
    return meta
