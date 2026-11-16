"""商品列表查询：列表 / 计数 / 第二排统计。"""

from __future__ import annotations

from core.http import post

from . import normalize_condition, normalize_status, normalize_types

LIST_PATH = "/scm-goods/wholesaleDrug/wsList"
COUNT_PATH = "/scm-goods/wholesaleDrug/wsListCount"
STAT_PATH = "/scm-goods/wholesaleDrug/wsStatistic"


def build_body(*, status=None, types=None, keyword: str = "", condition=None,
               extra: dict | None = None) -> dict:
    body = {
        "searchInfo": keyword or "",
        "status": normalize_status(status),
        "notThroughStatus": 0,
        "saleStatType": 1,
    }
    normalized_types = normalize_types(types)
    if normalized_types:
        body["wholesaleType"] = normalized_types
    cond = normalize_condition(condition)
    if cond is not None:
        body["condition"] = cond
    for key, value in (extra or {}).items():
        if value in (None, "") or key in body:
            continue
        body[key] = value
    return body


def list_goods(session, token: str, *, status=None, types=None, keyword: str = "",
               condition=None, page: int = 1, size: int = 20,
               extra: dict | None = None) -> dict:
    """查询活动列表（分页）。"""
    body = build_body(status=status, types=types, keyword=keyword, condition=condition, extra=extra)
    body.update({"pageNo": max(1, int(page)), "pageSize": min(100, max(1, int(size)))})
    return post(session, token, LIST_PATH, body) or {}


def count_goods(session, token: str, *, status=None, types=None, keyword: str = "",
                condition=None, extra: dict | None = None) -> list:
    """按状态返回计数（wsListCount，9 个状态）。"""
    body = build_body(status=status, types=types, keyword=keyword, condition=condition, extra=extra)
    return post(session, token, COUNT_PATH, body) or []


def statistics(session, token: str, *, status=None) -> dict:
    """第二排统计（15 个计数字段）。"""
    body = {"status": normalize_status(status)}
    return post(session, token, STAT_PATH, body) or {}


# 标准接口别名（统一 CLI 调度）
query = list_goods
count = count_goods
