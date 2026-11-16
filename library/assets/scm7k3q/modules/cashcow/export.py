"""板块导出（标准接口）。未实现时抛 `MODULE_TODO`（见 `modules/_skeleton.py`）。

注：摇钱树销售流水 / 我的品种的「导出 xlsx」已有服务端接口
（`exportSaleLogsAct` / `myVariety/export`，见 `references/我的摇钱树/api_*.md`），
当前走 `scm.py call --out` 直连；本骨架为 CLI 封装前的契约兜底。
"""

from __future__ import annotations

from .._skeleton import make_export_api

from . import ENDPOINTS, GUIDE, NAME

MODULE = __package__.rsplit(".", 1)[-1]

export, export_group_center = make_export_api(MODULE, NAME, ENDPOINTS, GUIDE)
