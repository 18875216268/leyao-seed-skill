# 订单（order）

> 板块归属：**自营专属**（见 `references/sy.md §0.4`）。
> 状态：✅ **只读查询（CLI）** · 🟡 **导出/详情开放部分**（接口文档已交付、用 `scm.py call` 直连，见 `AGENT_GUIDE.md §4.1`；CLI export 未封装）｜ 已知端点 **85** 个

## 1. 能力

- `query`：订单列表（`POST /scm-order/wholesaleOrder/list`），支持时间范围、客户编码、订单号、电话、物流单号、商品名、页签状态、分页；
- `count`：各页签计数（`POST /scm-order/wholesaleOrder/tabCount`，tab1~tab9）；
- `export`：**CLI 未封装**（调用返回 `MODULE_TODO`）；但导出接口文档已交付（`exportOrderData` 采集未登记、部分参数待实测，见 `api_订单导出.md §3.2`），按 `references/订单/api_订单导出.md` 直连（直接 CSV `batchExportOrder`/`exportProviderOrder` + 自定义导出 `exportOrderData` 等 6 端点），详情按 `references/订单/api_订单详情.md`。

## 2. 命令

```bash
# 最近 30 天、页签 8（配送完成）
python scm.py query --module order --limit 20

# 指定时间/客户/页签
python scm.py query --module order \
  --param start=2026-10-01 --param end=2026-10-31 \
  --param drugStore=D001 --param tabProcessStatus=8

# 按订单号 / 电话 / 物流单号 / 商品名
python scm.py query --module order --param orderId=xxx
python scm.py query --module order --param phone=138xxxx
python scm.py query --module order --param logisticsNo=SFxxx
python scm.py query --module order --param drugname=感冒灵

# 页签计数
python scm.py query --module order --count \
  --param start=2026-10-01 --param end=2026-10-31
```

| 参数 | 说明 |
|---|---|
| `start` / `end` | 日期 `YYYY-MM-DD`，默认最近 30 天 |
| `drugStore` | 客户编码 |
| `orderId` | 订单号 |
| `phone` | 收货电话 |
| `logisticsNo` | 物流单号 |
| `drugname` | 商品名 |
| `tabProcessStatus` | 页签状态 1~9；默认 `8`（配送完成）。**其余 28 个筛选用 `--param k=v` 透传**，完整清单见 `references/订单/api_订单查询.md §2` |

限制：只读；页签业务名称以页面为准（仅 8 已验证）；每页最多 100 条。

## 3. 已知端点（85）

| # | 路径 |
|---|---|
| 1 | `/provider.php/Admin/WholesaleAftersale/asRefundList/menuid/945` |
| 2 | `/scm-goods/leyoControlRule/getSubsidyWholesale` |
| 3 | `/scm-order/DrugCheckReport/batchUpdateBatchId` |
| 4 | `/scm-order/DrugCheckReport/exportDrugCheckReportList` |
| 5 | `/scm-order/DrugCheckReport/exportMissingBatch` |
| 6 | `/scm-order/DrugCheckReport/getApplyDrugCheckData` |
| 7 | `/scm-order/DrugCheckReport/queryDrugCheckReportList` |
| 8 | `/scm-order/DrugCheckReport/queryDrugCheckReportListCount` |
| 9 | `/scm-order/DrugCheckReport/updateDrugBatchId` |
| 10 | `/scm-order/drugstore/changeDrugCode` |
| 11 | `/scm-order/drugstore/changeProvCode` |
| 12 | `/scm-order/drugstore/chgProvCodeValid` |
| 13 | `/scm-order/drugstore/getBranchList` |
| 14 | `/scm-order/drugstore/openAccount` |
| 15 | `/scm-order/drugstore/openAccountInfo` |
| 16 | `/scm-order/drugstore/storeInfoIsChangeBatch` |
| 17 | `/scm-order/helpAdmin/getHandlingUrgeOrderCount` |
| 18 | `/scm-order/invoice/apply/batchInvoiceAssociatedOneOrder` |
| 19 | `/scm-order/invoice/apply/batchInvoiceAssociatedOrder` |
| 20 | `/scm-order/invoice/apply/exportOrderApplyList` |
| 21 | `/scm-order/invoice/apply/getInvoiceApplyData` |
| 22 | `/scm-order/invoice/apply/getListTabCount` |
| 23 | `/scm-order/invoice/apply/invOnlineAuth` |
| 24 | `/scm-order/invoice/apply/invOnlineConfirm` |
| 25 | `/scm-order/invoice/apply/invOnlineManual` |
| 26 | `/scm-order/invoice/apply/isOpenAutoInv` |
| 27 | `/scm-order/invoice/apply/openAutoInv` |
| 28 | `/scm-order/invoice/apply/queryOrderInvApplyList` |
| 29 | `/scm-order/invoice/apply/uploadApplyInvoice` |
| 30 | `/scm-order/logistic/importLogistics` |
| 31 | `/scm-order/logistic/uniqueStoreCheck` |
| 32 | `/scm-order/wholesaleOrder/afterSaleLog` |
| 33 | `/scm-order/wholesaleOrder/applyCompensation` |
| 34 | `/scm-order/wholesaleOrder/batchAddRemark` |
| 35 | `/scm-order/wholesaleOrder/batchQueryTrace` |
| 36 | `/scm-order/wholesaleOrder/batchRefund` |
| 37 | `/scm-order/wholesaleOrder/batchRefundConfirmInfo` |
| 38 | `/scm-order/wholesaleOrder/callbackWholesaleDrug` |
| 39 | `/scm-order/wholesaleOrder/callbackWholesaleDrugExport` |
| 40 | `/scm-order/wholesaleOrder/cancelCallback` |
| 41 | `/scm-order/wholesaleOrder/coldChainTempReportAssociatedOneOrder` |
| 42 | `/scm-order/wholesaleOrder/deliveryFloorMsg` |
| 43 | `/scm-order/wholesaleOrder/editCallBack` |
| 44 | `/scm-order/wholesaleOrder/editOrderQuickNote` |
| 45 | `/scm-order/wholesaleOrder/exportCallbackList` |
| 46 | `/scm-order/wholesaleOrder/exportOrder` |
| 47 | `/scm-order/wholesaleOrder/exportProviderOrder` |
| 48 | `/scm-order/wholesaleOrder/exportProviderOrderProcess` |
| 49 | `/scm-order/wholesaleOrder/exportWholesaleDrugCallbackList` |
| 50 | `/scm-order/wholesaleOrder/fusedStatusInfo` |
| 51 | `/scm-order/wholesaleOrder/generateTransportDeliveryReceipt` |
| 52 | `/scm-order/wholesaleOrder/getAgreementType3Url` |
| 53 | `/scm-order/wholesaleOrder/getBatchRefundData` |
| 54 | `/scm-order/wholesaleOrder/getCallbackList` |
| 55 | `/scm-order/wholesaleOrder/getCompensationInfo` |
| 56 | `/scm-order/wholesaleOrder/getDrugstoreInvoiceInfo` |
| 57 | `/scm-order/wholesaleOrder/getInfoBeforeRefundApply` |
| 58 | `/scm-order/wholesaleOrder/getLastNote` |
| 59 | `/scm-order/wholesaleOrder/getOrderInvApplyNotDoneCount` |
| 60 | `/scm-order/wholesaleOrder/getOrderInvApplyPer` |
| 61 | `/scm-order/wholesaleOrder/getOrderStoreInfoList` |
| 62 | `/scm-order/wholesaleOrder/getOrderSubsidyPlanDetailList` |
| 63 | `/scm-order/wholesaleOrder/getWholesaleDrugCallbackList` |
| 64 | `/scm-order/wholesaleOrder/imgUploadForTele` |
| 65 | `/scm-order/wholesaleOrder/lessThanDeliveryOrder` |
| 66 | `/scm-order/wholesaleOrder/list` |
| 67 | `/scm-order/wholesaleOrder/listCommon` |
| 68 | `/scm-order/wholesaleOrder/noteLog` |
| 69 | `/scm-order/wholesaleOrder/orderNote` |
| 70 | `/scm-order/wholesaleOrder/orderProcessCommon` |
| 71 | `/scm-order/wholesaleOrder/orderTopNums` |
| 72 | `/scm-order/wholesaleOrder/overtimeAfterSwitch` |
| 73 | `/scm-order/wholesaleOrder/overtimeInvoiceSwitch` |
| 74 | `/scm-order/wholesaleOrder/providerAbnormalOrderCount` |
| 75 | `/scm-order/wholesaleOrder/refundApply` |
| 76 | `/scm-order/wholesaleOrder/refundApplyGift` |
| 77 | `/scm-order/wholesaleOrder/refundConfirm` |
| 78 | `/scm-order/wholesaleOrder/refundUserExtraPaid` |
| 79 | `/scm-order/wholesaleOrder/resetExportTimes` |
| 80 | `/scm-order/wholesaleOrder/resetOrderBatch` |
| 81 | `/scm-order/wholesaleOrder/showDetailedSnapshot` |
| 82 | `/scm-order/wholesaleOrder/showSnapshot` |
| 83 | `/scm-order/wholesaleOrder/tabCount` |
| 84 | `/scm-order/wholesaleOrder/uploadColdChainTempRecord` |
| 85 | `/scm-setting/reply/searchLatestOrder` |

## 3. 参考

- `references/订单/sy.md`（板块索引）、`references/订单/api_订单查询.md`（35 个筛选参数）、`references/订单/zddz.md §1.3`（字段覆盖度）
- `references/附录/接口总表.md`（全量端点索引）
