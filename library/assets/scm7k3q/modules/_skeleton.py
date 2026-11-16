"""骨架板块的统一占位实现。

`status = todo` 的板块（见 `modules/__init__.py` 的 `MODULES`）只在
`query.py` / `export.py` 里声明标准接口签名；未实现时统一从这里抛
`MODULE_TODO`（退出码 2），避免每个文件各自复制同一段错误构造。

常规调用链上 `require_ready()` 会先于能力入口拦截；此处的抛错是
「接口契约」的兜底（直接 import 能力模块时的行为）。
"""

from __future__ import annotations

from core.errors import SkillError


def unavailable(module: str, name: str, endpoints, guide: str, action: str,
                *, note: str | None = None, hint: str | None = None) -> None:
    """抛「板块暂未开放」标准错误。

    `endpoints` 允许是清单或数字：清单按长度计数，避免把整个列表插进文案。
    `note` / `hint` 供「接口文档已交付但 CLI 未封装」的场景覆盖默认文案，
    避免 Agent 把 MODULE_TODO 误判成「功能不存在」。
    """
    count = len(endpoints) if isinstance(endpoints, (list, tuple, set)) else int(endpoints or 0)
    raise SkillError(
        "MODULE_TODO",
        note or f"{name}板块暂未开放{action}（已登记 {count} 个端点）",
        hint=hint or f"查看 {guide}",
        details={"module": module, "endpoints": count},
    )


def make_query_api(module: str, name: str, endpoints, guide: str):
    """生成标准查询接口组（todo 板块专用，避免每个板块复制同一段）。"""
    def query(session, token, *, page: int = 1, size: int = 20, **filters):
        """列表查询（标准接口）。"""
        unavailable(module, name, endpoints, guide, "查询")

    def count(session, token, **filters):
        """状态计数（标准接口）。"""
        unavailable(module, name, endpoints, guide, "查询")

    def statistics(session, token, **filters):
        """统计信息（标准接口）。"""
        unavailable(module, name, endpoints, guide, "查询")

    return query, count, statistics


def make_export_api(module: str, name: str, endpoints, guide: str):
    """生成标准导出接口组（todo 板块专用）。"""
    def export(session, token, out, **filters):
        """导出并下载（标准接口）。"""
        unavailable(module, name, endpoints, guide, "导出")

    def export_group_center(session, token, out):
        """组单中心导出（标准接口）。"""
        unavailable(module, name, endpoints, guide, "导出")

    return export, export_group_center
