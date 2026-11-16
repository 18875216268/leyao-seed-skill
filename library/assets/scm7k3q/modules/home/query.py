"""板块查询（标准接口）。未实现时抛 `MODULE_TODO`（见 `modules/_skeleton.py`）。"""

from __future__ import annotations

from .._skeleton import make_query_api

from . import ENDPOINTS, GUIDE, NAME

MODULE = __package__.rsplit(".", 1)[-1]

query, count, statistics = make_query_api(MODULE, NAME, ENDPOINTS, GUIDE)
