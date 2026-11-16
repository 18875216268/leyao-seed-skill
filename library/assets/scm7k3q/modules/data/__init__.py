"""数据板块。

状态：todo —— CLI 未开放；**品种分析**、**销售报表**、**店铺流量**已交付完整接口文档
（`references/数据/`），其余子板块（服务评价/热榜/参谋）仅登记端点。

取数请按 `references/数据/{api_品种分析.md, api_销售报表.md, api_店铺流量.md}` 直接构造请求
（`scm.py query --module data` 仍返回 MODULE_TODO）。实现方式见 modules/goods/__init__.py。
"""

NAME = "数据"
STATUS = "todo"
GUIDE = "modules/data/GUIDE.md"

ENDPOINTS = [
    # ---- 品种分析（已交付：api_品种分析.md）16 ----
    "/scm-goods/drugsStat/saleReportDrugsStatList",
    "/scm-goods/drugsStat/saleReportBuyCarStat",
    "/scm-goods/drugsStat/getSaleReportBase",
    "/scm-goods/drugsStat/getMultiCity",
    "/scm-goods/drugsStat/statReportVisit",
    "/scm-goods/drugsStat/statReportMoney",
    "/scm-goods/drugsStat/statReportTrendData",
    "/scm-goods/drugsStat/getStatReportDetailBase",
    "/scm-goods/drugsStat/getDrugsStatList",
    "/scm-goods/drugsStat/getDrugAfterList",
    "/scm-goods/drugsStat/getDrugsStatReport",
    "/scm-order/afterSaleBase/getReasonList",
    "/scm-order/afterSaleBase/getChildAreas",
    "/scm-goods/drugsStat/exportSaleReportDrugsStat",
    "/scm-goods/drugsStat/exportDrugsStatList",
    "/scm-goods/drugsStat/exportBuyCarStat",
    # ---- 销售报表（已交付：api_销售报表.md）18 ----
    "/scm-goods/saleReport/suppliersDateMonthWeekAreaActivity",
    "/scm-goods/saleReport/suppliersDrugstoreTable",
    "/scm-goods/saleReport/suppliersTotalAmount",
    "/scm-goods/saleReport/suppliersNetPurchase",
    "/scm-goods/saleReport/suppliersSalesOrder",
    "/scm-goods/saleReport/suppliersPStore",
    "/scm-goods/saleReport/suppliersNewPStore",
    "/scm-goods/saleReport/suppliersDrugNum",
    "/scm-goods/saleReport/suppliersPlatformDiscountAmount",
    "/scm-goods/saleReport/suppliersTotalCouponsAmount",
    "/scm-goods/saleReport/suppliersCouponsNum",
    "/scm-goods/saleReport/suppliersRefundAmount",
    "/scm-goods/saleReport/visitorDataChart",
    "/scm-goods/saleReport/getSubType",
    "/scm-goods/provider/getWarehouseList",
    "/scm-goods/saleReport/suppliersDateMonthWeekAreaActivityExport",
    "/scm-goods/saleReport/suppliersDrugstoreTableExport",
    "/scm-goods/saleReport/exportVisitorData",
    # ---- 店铺流量（已交付：api_店铺流量.md）2 ----
    "/scm-setting/flow/getFlowInfo",
    "/scm-base/saleReport/topExposureStat",
    # ---- 商品热榜 / 好价榜（采集有参数与响应，未建独立文档）3 ----
    "/scm-base/saleReport/goodPriceList",
    "/scm-base/saleReport/goodPriceListTabNum",
    "/scm-base/saleReport/goodPriceListExport",
    # ---- 同前缀看板（非店铺流量子板块，未建文档）2 ----
    "/scm-base/saleReport/topOnsaleStat",
    "/scm-base/saleReport/topOrderStat",
    # ---- 其余子板块（仅登记，参数未整理）7 ----
    "/provider.php/Admin/SaleReport/suppliersReport",
    "/provider.php/WsPlan/changePlanStatus",
    "/scm-base/providerTask/updateStatPromptFlag",
    "/scm-base/spotCheck/getProvStatusHis",
    "/scm-goods/WholesaleDrugES2/changeBindStatus",
    "/scm-goods/wholesaleDrug/getProviderAlertStatus",
    "/scm-order/provider/getColdStatus",
]
