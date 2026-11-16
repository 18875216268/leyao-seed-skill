# 订单查询（API）

> 只读。公共参数/鉴权见 `references/通用/api_认证与公共约定.md`；分页见 `references/通用/api_认证与公共约定.md §9`（列表用 `page`+`pagesize`）。
> 字段/值域见 `zddz.md`；导出见 `api_订单导出.md`；详情（证件/业务员/开票）见 `api_订单详情.md`。
> **账号归属：③ 仅自营**（权威判定见 `references/sy.md §0.4`；本子板块为自营账号体系专属，摇钱树账号不调用）


## 1. 接口总表

| # | 接口 | 用途 | 返回 |
|---|---|---|---|
| 1 | `POST /scm-order/wholesaleOrder/list` | 订单列表 | `data.{pageNo,pageSize,totalRecord,totalPage,results[]}` |
| 2 | `POST /scm-order/wholesaleOrder/tabCount` | 状态页签计数 | `data.{tab1..tab9}` |
| 3 | `POST /scm-order/wholesaleOrder/listCommon` | 共用列表变体 | 同 `list` |
| 4 | `POST /scm-base/index/realTimeOrderInfo` | 实时订单概览 | `{newOrder,newCli,waitAuditRefund,unprocessedOrder,unShippedOrder,urgeShipOrder}` |
| 5 | `POST /scm-order/wholesaleOrder/fusedStatusInfo` | 融合状态信息 | `{maxDayDeliveryQty,toCollectOrderNumber,fusedStatus,...}` |

## 2. 列表筛选参数（实测）

公共参数 `ex:"AllOrdersList"`、`lastBuildTime`。业务参数（采集请求体实测）：

| 参数 | 说明 | 对应界面字段 |
|---|---|---|
| `orderId` | 订单号 | 订单id |
| `drugStore` | 客户（药店）编码（模糊） | 药店 |
| `phone` | 收货电话 | 手机号 |
| `order_time` | **数组** `[起ISO, 止ISO]` | 下单时间 |
| `logisticsNo` | 快递单号 | 快递单号 |
| `drugname` | 商品名（模糊） | 商品名称 |
| `orderTypeList` | 多选数组 | 订单类型 |
| `deliver_alone` | 开单组合（标志位） | 开单组合 |
| `wholesale_type` | 订单活动类型 | 订单活动类型 |
| `delivery_lack` | 开单后需退款（标志位） | 开单后需退款 |
| `pay_on_cash` | 收款方式（标志位） | 收款方式 |
| `is_close` | 结算状态（标志位） | 结算状态 |
| `subTypeList` | 多选数组 | 药店类型 |
| `drugstore_id` | 药店 ID | 药店ID |
| `latestCollectTime` | 揽收情况（标志位） | 揽收情况 |
| `insBundleDeputyFlag` | 医械城拼团换购（标志位） | 医械城拼团换购 |
| `order_source` | 医械城订单（标志位） | 医械城订单 |
| `tbBundled` | 随心购订单（标志位） | 随心购订单 |
| `wholesale_id` | 活动 ID | 活动ID |
| `area` | 地区（多选数组） | 地区 |
| `acc_end_time` | **数组** `[起ISO, 止ISO]` | 处理时间 |
| `clear_time` | **数组** `[起ISO, 止ISO]` | 申请结算时间 |
| `deliverFeeFlag` | 运费（标志位） | 运费 |
| `containHempFlag` | 特殊药品（标志位） | 特殊药品 |
| `autograpFlag` | 签收回执（标志位） | 签收回执 |
| `autograpFlag2` | 购销合同（标志位） | 购销合同 |
| `storeInvoiceType` | 发票类型 | 发票类型 |
| `warehouseCode` | 分仓筛选（裸名） | 分仓筛选 |
| `orderShipping` | 随货同行单（标志位） | 随货同行单 |
| `operationFlag` | 运营标签（标志位） | 运营标签 |
| `bindType` | 区域标签 | 区域标签 |
| `isTraceCode` | 是否有追溯码（标志位） | 是否有追溯码 |
| `isHostedDrug` | 托管（标志位） | 托管 |
| `maintainPriceType` | 维价类型 | 维价类型 |
| `tcmStoreGroupOrderFlag` | 多品凑单订单（标志位） | 多品凑单订单 |
| `cert_status` | 资质状态（见 `zddz.md §2` 状态） | 公共 |
| `tabProcessStatus` | 状态页签 `1`~`9`（`8`=配送完成已验证） | 公共 |
| `order_str` | 综合关键词 | 公共 |
| `is_logist` | 是否物流 | 公共 |
| `invoiceCount` | 发票张数 | 公共 |
| `page` / `pagesize` | `page` 从 1；`pagesize` 默认 10（**小写 s**） | 公共 |

> **重要更正（浏览器实测，2026-11-11）**：此前「`<响应字段名>List` 约定」**不成立**。实测（Playwright 驱动系统 Edge，对 35 个筛选字段逐字段隔离设值+抓包，见 `zddz.md §1.3`）表明：除 `orderTypeList`/`subTypeList`/`area` 为真正数组外，绝大多数开关/枚举类筛选以**独立标志位参数**提交（如 `pay_on_cash`、`is_close`、`deliver_alone`、`latestCollectTime`、`deliverFeeFlag`、`containHempFlag`、`autograpFlag`、`autograpFlag2`、`storeInvoiceType`、`operationFlag`、`bindType`、`isTraceCode`、`isHostedDrug`、`maintainPriceType`、`tcmStoreGroupOrderFlag`、`insBundleDeputyFlag`、`order_source`、`tbBundled`、`orderShipping`、`wholesale_type`、`delivery_lack`），**请勿再套用 List 约定**。`receive_status` 非筛选参数（请求中恒为 `''`）。
> 上表 35 个筛选参数名**全部经浏览器实测锁定**，覆盖度见 `zddz.md §1.3`（均 ✅）。公共参数 `token/platform/version/ex/ua` 等鉴权参另见 `通用/api_认证与公共约定.md`。

## 3. 调用样本

> 订单模块 `build_body` 会用 `--param start=` / `--param end=`（日期，自动组装成 `order_time` 数组），**优先用这两个**；直接传 `--param order_time='[...]'` 在 PowerShell 下引号易丢失，不建议。
> CLI `--param` 支持 JSON 数组/对象（`value` 以 `[`/`{` 开头即按 JSON 解析），但订单时间区间用 start/end 更稳。

```bash
# 默认（最近 30 天、页签=配送完成 tab=8）
python scm.py query --module order --limit 20

# 时间范围 + 客户 + 页签 + 快递单号
python scm.py query --module order \
  --param start=2026-10-01 --param end=2026-10-31 \
  --param drugStore=D001 --param tabProcessStatus=8 --param logisticsNo=SF123

# 页签计数
python scm.py query --module order --count
```

> 若返回 `total:0`：先放宽 `--param start=`/`end=` 与 `tabProcessStatus`；实时账号无对应数据时列表为空属正常（字段映射以采集真实响应为准，见 §4）。

最小请求体：

```json
{
  "page": 1, "pagesize": 10,
  "order_time": ["2026-09-11T00:00:00+08:00", "2026-11-11T23:59:59+08:00"],
  "orderId": "", "drugStore": "", "phone": "", "logisticsNo": "",
  "drugname": "", "drugstore_id": "", "wholesale_id": "",
  "cert_status": "", "tabProcessStatus": 1, "order_str": "",
  "is_logist": "", "invoiceCount": "", "receive_status": "",
  "ex": "AllOrdersList", "lastBuildTime": "2026-11-09 20:28"
}
```

## 4. 返回字段（行级，节选）

> **2026-11-12 实测全量**：抓真实响应得 `data={pageNo,pageSize,totalRecord,totalPage,results[]}`，返回行 **177 个顶层字段 + `orderDetails[]` 内 53 字段**（本次 `totalRecord=12`）。全量键名清单见 `zddz.md §10`，分组映射见 `zddz.md §2`，原始响应 `过程区/账号权限实测/response_dump.json`。下表为核心分组：

- **订单标识**：`orderId` `orderSn` `orderTypeName` `className` `orderTime` `status` `processStatus`/`processStatusName`
- **物流**：`logisticsId` `logisticsNo` `logisticsName` `isCar` `thirdDelivery` `isLogistReject`
- **药店/收货**：`storeTitle` `storeFullName` `drugstoreBranchId` `providerId` `providerCode` `receiverName`/`receiverPhone`/`receiverAddress`
- **金额**：`orderPay` `totalCost` `actualCost` `deliverFee` `couponPay` `subsidyPay`
- **发票**：`invoiceSign` `invoiceTypeName` `storeInvoiceType`
- **售后**：`hasAfterSale` `latestRefundType` `latestRefundStatus` `refundAmount`
- **资质/异常**：`certStatus` `isAbnormal` `smApplyStatus` `specialFlag` `isTraceCode` `isHostedDrug`
- **商品明细**：`orderDetails[]`（见 `zddz.md §2` 末行）

## 5. 实时概览 / 融合状态

- `realTimeOrderInfo`：`newOrder`/`newCli`/`waitAuditRefund`/`unprocessedOrder`/`unShippedOrder`/`urgeShipOrder`（计数）。
- `fusedStatusInfo`：`maxDayDeliveryQty`/`toCollectOrderNumber`/`fusedTimes`/`providerStatus`/`fusedStatus`（供货融合状态，非列表筛选）。

## 6. 限制

- 只读；不提供写操作。
- `tabProcessStatus` 各页签名称以页面为准（`8`=配送完成已验证）。
- 展开搜索：35 个筛选参数名 **全部浏览器实测锁定**（`zddz.md §1.3`），对应**下拉选项与提交值**见 `zddz.md §9`（仅「订单类型」动态，其余静态）；旧的 `<响应字段名>List` 推断约定已作废，禁止套用。
- 异常标签计数端点见 `api_订单详情.md §6` 与 `zddz.md §7`。
