"""商品板块：查询、导出、字典。

固定枚举（全账号一致）在此定义；动态字典见 `dicts.py`。
"""

from __future__ import annotations

from core.errors import SkillError

NAME = "商品"
STATUS = "ready"
GUIDE = "modules/goods/GUIDE.md"

# 状态页签：名称 ↔ status 值（导出还需 tabCode，见 TABCODE_MAP）
STATUS_MAP = {
    "进行中": 0, "待开始": 1, "缺货下架": 2, "未上架": 3, "已下架": 4,
    "资质待审核": 5, "资质不通过": 6, "已结束": 7, "未动销下架": 8, "全部": -1,
}
TABCODE_MAP = {
    0: "on_sale", 1: "not_start", 2: "auto_off", 3: "price_audit_fail", 4: "off_sale",
    5: "wait_audit", 6: "not_through", 7: "already_over", 8: "8", -1: "all",
}

# 活动类型
TYPE_MAP = {
    "一口价": "1", "特价": "4", "限时特价": "5", "限时特价可用券": "6",
    "拼团": "7", "诊所拼团": "71", "批购包邮": "8", "赠品": "10", "连锁包邮": "11",
}

# 标签筛选（condition）
CONDITION_MAP = {
    "价格过低": 0, "可售不足7天": 1, "近效期": 2, "商圈为空": 3, "来货自动上架": 4,
    "未同步库存": 5, "未同步价格": 6, "拼团起拼数建议": 7, "即将下架拼团": 8,
    "滞销预警": 9, "价格过高": 10, "拼团调价建议": 11, "最近平台上架": 12,
    "未动销且即将下架": 13, "品种补贴": 14, "未动销且未调价即将下架": 15,
    "高风险资质待补全": 16, "供货对象为空": 17, "≤通用入门价": 18, "一口价过高": 19,
}


def normalize_status(value: int | str | None, *, default: int = 0) -> int:
    """状态：接受中文名或数字。"""
    if value is None or value == "":
        return default
    if isinstance(value, int):
        if value in TABCODE_MAP:
            return value
        raise SkillError("PARAM_INVALID", f"未知状态值：{value}", hint="0~8 或 -1（使用 `modules/goods/GUIDE.md` 的页签名）")
    text = str(value).strip()
    if text in STATUS_MAP:
        return STATUS_MAP[text]
    if text.lstrip("-").isdigit():
        return normalize_status(int(text), default=default)
    raise SkillError("PARAM_INVALID", f"未知状态名：{value}", hint="可用：" + "、".join(STATUS_MAP))


def normalize_types(values: list[str] | None) -> list[str]:
    """活动类型：接受中文名或数字字符串；空表示全部类型（不传）。"""
    if not values:
        return []
    result = []
    for raw in values:
        text = str(raw).strip()
        if text in TYPE_MAP:
            result.append(TYPE_MAP[text])
        elif text.isdigit() and text in TYPE_MAP.values():
            result.append(text)
        else:
            raise SkillError("PARAM_INVALID", f"未知活动类型：{raw}", hint="可用：" + "、".join(TYPE_MAP))
    return result


def normalize_condition(value: int | str | None) -> int | None:
    """标签筛选：接受中文名或数字。"""
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if text in CONDITION_MAP:
        return CONDITION_MAP[text]
    if text.isdigit():
        return int(text)
    raise SkillError("PARAM_INVALID", f"未知标签：{value}", hint="可用：" + "、".join(CONDITION_MAP))
