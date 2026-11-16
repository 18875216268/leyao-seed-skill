"""板块导出（标准接口）。

订单导出的**接口文档已交付**（`references/订单/api_订单导出.md`：直接 CSV +
自定义导出共 6 个端点），但本技能 CLI 尚未封装 `export` 命令；
直接调用能力模块时统一走 `modules/_skeleton.py` 的 `MODULE_TODO` 契约，
避免重复实现抛错逻辑。Agent 需要导出时按该文档直连，不要等 CLI。
"""

from __future__ import annotations

from .._skeleton import unavailable

from . import ENDPOINTS, GUIDE, NAME

MODULE = __package__.rsplit(".", 1)[-1]


_NOTE = "订单导出 CLI 未封装（6 个导出端点的接口文档已交付）"
_HINT = "按 references/订单/api_订单导出.md 直连取数；不要判为功能不存在"


def export(session, token, out, **filters):
    """导出并下载（标准接口）。"""
    unavailable(MODULE, NAME, 6, GUIDE, "导出", note=_NOTE, hint=_HINT)


def export_group_center(session, token, out):
    """组单中心导出（标准接口）。"""
    unavailable(MODULE, NAME, 6, GUIDE, "导出", note=_NOTE, hint=_HINT)
