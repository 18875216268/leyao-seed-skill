"""商品筛选用的动态字典（值随账号配置变化，禁止硬编码）。"""

from __future__ import annotations

from core.errors import SkillError
from core.http import post

DICTS: dict[str, dict] = {
    "priceTypes": {"name": "价格档位", "path": "/scm-goods/wholesaleDrug/getPriceTypes"},
    "storeTypes": {"name": "供货对象", "path": "/scm-goods/wholesaleDrug/getStoreTypeGroup"},
    "deliverAlones": {"name": "开单组合", "path": "/scm-goods/wholesaleDrug/getDeliverAlones"},
    "discountTypes": {"name": "阶梯价/赠品", "path": "/scm-goods/wholesaleDrug/getDiscountType"},
    "busiScopes": {"name": "经营范围", "path": "/scm-goods/wholesaleDrug/getBusiScopeForProvider"},
    "deliveryProviders": {"name": "配送商", "path": "/scm-goods/wholesaleDrug/getDeliveryProviders"},
    "groupThemes": {"name": "端口主题", "path": "/scm-goods/wholesaleDrug/getAllGroupTheme"},
    "areaGroups": {"name": "商圈", "path": "/scm-goods/wholesaleDrug/getAreaGroupDropList"},
    "rankOptions": {"name": "近7天排名区间", "path": "/scm-goods/wholesaleDrug/wsListRankFilterOptions"},
    "clinicStoreTypes": {"name": "诊所供货对象", "path": "/scm-goods/wholesaleDrug/getStoreTypeGroupForClinic"},
    "busiScopePage": {"name": "经营范围（分页）", "path": "/scm-goods/wholesaleDrug/getBusiScopeList"},
}


def get_dict(session, token: str, name: str) -> object:
    """按名称取字典原始数据。"""
    meta = DICTS.get(name)
    if not meta:
        raise SkillError("PARAM_INVALID", f"未知字典：{name}", hint="可用：" + "、".join(DICTS))
    return post(session, token, meta["path"], {})


def list_dicts() -> list[dict]:
    """列出可选字典。"""
    return [{"id": key, **value} for key, value in DICTS.items()]
