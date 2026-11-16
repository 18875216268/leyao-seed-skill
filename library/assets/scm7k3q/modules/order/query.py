"""订单板块 · 只读查询（订单列表与页签计数）。

接口：POST /scm-order/wholesaleOrder/list 与 /tabCount
参数：时间范围、客户编码、订单号、电话、物流单号、商品名、页签状态、分页。
"""

from __future__ import annotations

from datetime import datetime, timedelta

from core.errors import SkillError
from core.http import post

LIST_PATH = "/scm-order/wholesaleOrder/list"
TAB_PATH = "/scm-order/wholesaleOrder/tabCount"
EX = "AllOrdersList"
默认天数 = 30
每页上限 = 100


def _时刻(文本: str, 末尾: bool) -> str:
    """日期补全为带时区的 ISO 时间。"""
    文本 = (文本 or "").strip()
    if not 文本:
        return ""
    if "T" in 文本:
        return 文本
    return 文本 + ("T23:59:59+08:00" if 末尾 else "T00:00:00+08:00")


def _范围(开始: str, 结束: str) -> tuple[str, str]:
    if 开始 and 结束:
        return 开始, 结束
    今 = datetime.now()
    开始 = 开始 or (今 - timedelta(days=默认天数)).strftime("%Y-%m-%d")
    结束 = 结束 or 今.strftime("%Y-%m-%d")
    return 开始, 结束


def build_body(*, page: int = 1, size: int = 20, drug_store: str = "", order_id: str = "",
               phone: str = "", logistics_no: str = "", drug_name: str = "",
               tab=None, start: str = "", end: str = "", extra: dict | None = None) -> dict:
    """组装订单列表请求体（纯函数，便于离线校验）。"""
    参 = dict(extra or {})
    开始, 结束 = _范围(参.pop("start", start), 参.pop("end", end))
    体 = {
        "page": max(1, int(page)),
        "pagesize": min(每页上限, max(1, int(size))),
        "order_time": [_时刻(开始, False), _时刻(结束, True)],
        "drugStore": 参.pop("drugStore", drug_store),
        "orderId": 参.pop("orderId", order_id),
        "phone": 参.pop("phone", phone),
        "logisticsNo": 参.pop("logisticsNo", logistics_no),
        "drugname": 参.pop("drugname", drug_name),
        "cert_status": 参.pop("cert_status", ""),
        "drugstore_id": 参.pop("drugstore_id", ""),
        "wholesale_id": 参.pop("wholesale_id", ""),
        "order_str": 参.pop("order_str", ""),
        "is_logist": 参.pop("is_logist", ""),
        "invoiceCount": 参.pop("invoiceCount", ""),
        "receive_status": 参.pop("receive_status", ""),
        "ex": EX,
    }
    if tab not in (None, ""):
        try:
            体["tabProcessStatus"] = int(tab)
        except (TypeError, ValueError) as exc:
            raise SkillError("PARAM_INVALID", f"tabProcessStatus 需为整数：{tab}") from exc
    体.update(参)
    return 体


def query(session, token: str, *, page: int = 1, size: int = 20, status=None, types=None,
          keyword=None, condition=None, extra: dict | None = None, **kwargs) -> dict:
    """订单列表：默认最近 30 天、页签 8（配送完成）。"""
    参 = dict(extra or {})
    tab = 参.pop("tabProcessStatus", None)
    if tab is None and str(status or "").strip().isdigit():
        tab = int(str(status).strip())
    体 = build_body(page=page, size=size, tab=8 if tab is None else tab, extra=参)
    return post(session, token, LIST_PATH, 体) or {}


def count(session, token: str, *, status=None, types=None, keyword=None, condition=None,
          extra: dict | None = None, **kwargs) -> object:
    """各页签计数（tab1~tab9）。"""
    参 = dict(extra or {})
    开始, 结束 = _范围(参.pop("start", ""), 参.pop("end", ""))
    体 = {"order_time": [_时刻(开始, False), _时刻(结束, True)], "ex": EX}
    体.update(参)
    return post(session, token, TAB_PATH, 体) or {}


statistics = count
