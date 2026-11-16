"""板块导出（标准接口）。未实现时抛 `MODULE_TODO`（见 `modules/_skeleton.py`）。"""

from __future__ import annotations

from .._skeleton import make_export_api

from . import ENDPOINTS, GUIDE, NAME

MODULE = __package__.rsplit(".", 1)[-1]

export, export_group_center = make_export_api(MODULE, NAME, ENDPOINTS, GUIDE)
