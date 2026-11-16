# 数据（data）

> 状态：🟡 **开放部分**（接口文档已交付、可按文档直接取数；CLI 暂未开放，`scm.py query --module data` 返回 `MODULE_TODO`）｜ 已登记端点 **48**
> **品种分析（16）、销售报表（18）、店铺流量（2）已交付完整接口文档**，用 `python scm.py call`（`AGENT_GUIDE.md §4.1`）按文档构造请求即可取数，无需等 CLI。

## 1. 说明

本板块覆盖 SCM「数据」菜单。已交付文档的子板块：**品种分析**、**销售报表**、**店铺流量**；其余（服务评价 / 热榜 / 参谋）只有端点登记。

- 板块归属（**按子板块分，勿按板块名一刀切**）：
  - **品种分析、销售报表 = ① 通用**（自营「数据」与摇钱树「统计分析」同源，用户 2026-11-13 确认）
  - **店铺流量 = ③ 仅自营**
- 请求约定：`POST`，`Content-Type: application/json;charset=UTF-8`（**必须带 charset**），公共参数见 `references/通用/api_认证与公共约定.md`。
- **三个子板块的时间参数各不相同**（最易混）：
  - 品种分析：`dateRange` 字符串数组
  - 销售报表：`startTime`/`endTime` **Unix 秒**
  - 店铺流量：`rangeFlag` + 自定义纯日期 `YYYY-MM-DD`

## 2. 已交付文档的子板块

| 子板块 | 文档 | 归属 | 核心内容 |
|---|---|---|---|
| 品种分析 | `references/数据/api_品种分析.md` | **① 通用** | 按品种统计 / 委托配送商品 / 售后详情 / 字典级联 / 3 个导出 |
| 销售报表 | `references/数据/api_销售报表.md` | **① 通用** | 6 种统计方式（2 端点）/ 10 个维度图 / 访客数据 / 3 个导出 |
| 店铺流量 | `references/数据/api_店铺流量.md` | **③ 仅自营** | 三指标趋势 + 汇总同比；**下载数据无服务端接口** |

> 字段对照（UI 列 ↔ API key、`amount`=销量、`drugType`=购药品种、各子板块参数差异）见 `references/数据/zddz.md`；板块索引见 `references/数据/sy.md`。

## 3. 已知端点（48）

| # | 路径 |
|---|---|
| 1 | `/scm-goods/drugsStat/saleReportDrugsStatList` |
| 2 | `/scm-goods/drugsStat/saleReportBuyCarStat` |
| 3 | `/scm-goods/drugsStat/getSaleReportBase` |
| 4 | `/scm-goods/drugsStat/getMultiCity` |
| 5 | `/scm-goods/drugsStat/statReportVisit` |
| 6 | `/scm-goods/drugsStat/statReportMoney` |
| 7 | `/scm-goods/drugsStat/statReportTrendData` |
| 8 | `/scm-goods/drugsStat/getStatReportDetailBase` |
| 9 | `/scm-goods/drugsStat/getDrugsStatList` |
| 10 | `/scm-goods/drugsStat/getDrugAfterList` |
| 11 | `/scm-goods/drugsStat/getDrugsStatReport` |
| 12 | `/scm-order/afterSaleBase/getReasonList` |
| 13 | `/scm-order/afterSaleBase/getChildAreas` |
| 14 | `/scm-goods/drugsStat/exportSaleReportDrugsStat` |
| 15 | `/scm-goods/drugsStat/exportDrugsStatList` |
| 16 | `/scm-goods/drugsStat/exportBuyCarStat` |
| 17 | `/scm-goods/saleReport/suppliersDateMonthWeekAreaActivity` |
| 18 | `/scm-goods/saleReport/suppliersDrugstoreTable` |
| 19 | `/scm-goods/saleReport/suppliersTotalAmount` |
| 20 | `/scm-goods/saleReport/suppliersNetPurchase` |
| 21 | `/scm-goods/saleReport/suppliersSalesOrder` |
| 22 | `/scm-goods/saleReport/suppliersPStore` |
| 23 | `/scm-goods/saleReport/suppliersNewPStore` |
| 24 | `/scm-goods/saleReport/suppliersDrugNum` |
| 25 | `/scm-goods/saleReport/suppliersPlatformDiscountAmount` |
| 26 | `/scm-goods/saleReport/suppliersTotalCouponsAmount` |
| 27 | `/scm-goods/saleReport/suppliersCouponsNum` |
| 28 | `/scm-goods/saleReport/suppliersRefundAmount` |
| 29 | `/scm-goods/saleReport/visitorDataChart` |
| 30 | `/scm-goods/saleReport/getSubType` |
| 31 | `/scm-goods/provider/getWarehouseList` |
| 32 | `/scm-goods/saleReport/suppliersDateMonthWeekAreaActivityExport` |
| 33 | `/scm-goods/saleReport/suppliersDrugstoreTableExport` |
| 34 | `/scm-goods/saleReport/exportVisitorData` |
| 35 | `/scm-setting/flow/getFlowInfo` |
| 36 | `/scm-base/saleReport/topExposureStat` |
| 37 | `/scm-base/saleReport/goodPriceList` |
| 38 | `/scm-base/saleReport/goodPriceListTabNum` |
| 39 | `/scm-base/saleReport/goodPriceListExport` |
| 40 | `/scm-base/saleReport/topOnsaleStat` |
| 41 | `/scm-base/saleReport/topOrderStat` |
| 42 | `/provider.php/Admin/SaleReport/suppliersReport` |
| 43 | `/provider.php/WsPlan/changePlanStatus` |
| 44 | `/scm-base/providerTask/updateStatPromptFlag` |
| 45 | `/scm-base/spotCheck/getProvStatusHis` |
| 46 | `/scm-goods/WholesaleDrugES2/changeBindStatus` |
| 47 | `/scm-goods/wholesaleDrug/getProviderAlertStatus` |
| 48 | `/scm-order/provider/getColdStatus` |

> 1~36 有完整参数文档（品种分析 1~16、销售报表 17~34、店铺流量 35~36）；37~48 仅登记，**不提供可直接照抄的参数**，命中时按 `references/sy.md §0.5` 第 6 步如实告知。
> 其中 37~39 属「商品热榜 / 好价榜」（采集已带参数与响应，未建文档：请求 `{pageNo,pageSize,keyWord,tabId,idList[]}`，`goodPriceListTabNum` 返回 `tabRecord0~4` 五个 tab 计数）；40~41 是店铺流量同前缀的在售/订单看板，不属于店铺流量子板块。

## 4. 参考

- `references/数据/sy.md`（板块索引 · 36 个有文档端点 / 48 个登记端点 · 边界）
- `references/数据/api_品种分析.md` / `api_销售报表.md` / `api_店铺流量.md`（接口合同）
- `references/数据/zddz.md`（字段对照）
- `references/附录/接口总表.md`（全量端点索引）
