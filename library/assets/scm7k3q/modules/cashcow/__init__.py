"""我的摇钱树板块（待开发）。

状态：todo —— 接口文档已交付（摇钱树专属，11 端点经实时导航 + 导出/写动作抓包验证
2026-11-16），CLI 未封装；取数按 references/我的摇钱树/api_*.md 用 `scm.py call` 直连。
实现方式见 modules/goods/__init__.py 的结构。
"""

NAME = "我的摇钱树"
STATUS = "todo"
GUIDE = "modules/cashcow/GUIDE.md"

ENDPOINTS = [
    "/scm-setting/cashcoworder/saleLogsAct",
    "/scm-setting/cashcoworder/saleLogsCountAct",
    "/scm-setting/cashcoworder/exportSaleLogsAct",
    "/scm-goods/areaGroup/getAreaCodeWithoutLimit",
    "/scm-setting/myVariety/myDrugsAct",
    "/scm-setting/myVariety/init",
    "/scm-setting/myVariety/export",
    "/scm-setting/myVariety/update",
    "/scm-setting/myVariety/batchEditBottomPrice",
    "/scm-base/provider/getProviderDelivers",
    "/scm-base/provider/getAreaPriceList",
]
# 注：`/scm-goods/cashcow/editMinLeyoPrice`（拼团最低供乐药价维护候选，静态分析）已登记在
# `modules/marketing/__init__.py` 的 ENDPOINTS（不跨板块重复）；本板块文档以其为交叉引用。

