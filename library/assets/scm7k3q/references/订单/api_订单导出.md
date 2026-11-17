# 订单导出（API）

> 两种导出：① 直接 CSV（`batchExportOrder` / `exportProviderOrder`）；② 自定义导出（`exportOrderData` 走通用导出中心）。
> 公共参数/鉴权见 `references/通用/api_认证与公共约定.md`；通用导出任务轮询/下载见 `references/通用/api_导出任务.md`。
> 字段组/模板见 `zddz.md §6`；筛选参数见 `zddz.md §1`。
> **账号归属：③ 仅自营**（权威判定见 `references/sy.md §0.4`；本子板块为自营账号体系专属，摇钱树账号不调用）


## 1. 接口总表

| # | 接口 | 方式 | 用途 |
|---|---|---|---|
| 1 | `GET /provider.php/Admin/ApiRouter/batchExportOrder` | GET | 直接导出 CSV（浏览器下载） |
| 2 | `POST /scm-order/wholesaleOrder/exportProviderOrder` | POST/GET | SCM 直接导出（含 `area[]`） |
| 3 | `POST /export-file/file/exportOrderData/v100` | POST | 自定义导出（异步，通用导出中心） |
| 4 | `POST /export-file/file/getSelectFields/v100` | POST | 取可选导出字段组 |
| 5 | `POST /export-file/file/getAllCustomizeTemplate/v100` | POST | 取已有自定义模板 |
| 6 | `POST /export-file/file/getExportTaskRecord/v100` | POST | 轮询/下载导出任务 |

---

## 2. 直接导出 CSV

### 2.1 `batchExportOrder`（GET，采集实测 query 全量）

```
GET /provider.php/Admin/ApiRouter/batchExportOrder
  ?page=1&pagesize=100
  &cert_status=&orderId=&drugStore=&phone=
  &order_time[0]=<起时刻>&order_time[1]=<止时刻>
  &logisticsNo=&drugname=&drugstore_id=&wholesale_id=
  &tabProcessStatus=<页签码>&order_str=&is_logist=&invoiceCount=&receive_status=
  &warehouseCode=<分仓码或留空>    # 分仓筛选；全量留空
  &endday=<起YMD>-<止YMD>         # 日期(YYYYMMDD-YYYYMMDD)，与 order_time 一致
  &starttime=00:00:00&endtime=23:59:59
  &usedForWeb=1
```

> ⚠️ 上方为**参数形态示例**（时间/页签/分仓均为占位符）：`order_time`/`endday` 按当前查询区间换算，`tabProcessStatus` 与列表页签一致，**全量导出去掉 `warehouseCode` 筛选**；照抄抓包里的历史日期+特定仓会导出空或错范围。

- 与列表共用全部筛选参数，额外：`warehouseCode`、`endday`、`starttime`/`endtime`、`usedForWeb=1`。
- 响应即 CSV（浏览器直接下载），非异步任务。

### 2.2 `exportProviderOrder`（SCM 端点）

请求体同样含 `page`/`pagesize`/`order_time[]`/`orderId`/`drugStore`/`phone`/`logisticsNo`/`drugname`/`drugstore_id`/`wholesale_id`/`tabProcessStatus`/`area[]`/`order_str`/`is_logist`/`invoiceCount`/`receive_status` 等。属 SCM 侧直接导出实现。

---

## 3. 自定义导出

### 3.1 流程

1. `getSelectFields/v100` → 取可选字段组（`orderList`/`drugList`/`receiptList`/`storeList`/`logisticsList`，见 `zddz.md §6`）。
2. `getAllCustomizeTemplate/v100` → 取已有模板（如 `455168` KA连锁总部订单明细、`455169` KA商业公司订单明细、`86088` 订单ID+客户信息、`204496` 药店金额、`204534` 分拣）。
3. `exportOrderData/v100` → 提交导出（异步）。
4. `getExportTaskRecord/v100` → 轮询 → `qiniuUrl` 下载（见 `references/通用/api_导出任务.md`）。

### 3.2 `exportOrderData/v100` 请求体（采集实测）

```json
{
  "timeType": 0,                 // 0=下单时间 / 1=支付时间
  "templateType": 2,             // 模板类型（订单明细/处理流水/快递信息/自定义）
  "templateId": <从 getAllCustomizeTemplate 运行时取得>,          // 模板ID（来自 getAllCustomizeTemplate）
  "startTime": "2026-04-30T16:00:00.000Z",
  "endTime": "2026-05-14T16:00:00.000Z",
  "isDH": 0,
  "orderId": "", "drugStore": "", "phone": "",
  "logisticsNo": "", "drugname": "", "drugstore_id": "",
  "processStatus": ["1","2","3","4","5","6","8","9"],  // 订单处理状态（数组）
  "sqlParams": "{...ES查询串...}"   // 后端自动生成，无需手填
}
```

| 参数 | 界面 | 取值 |
|---|---|---|
| `timeType` | 时间类型 | `0`=下单时间 / `1`=支付时间 |
| `templateType` | 导出模板 | `2`（订单明细类；其余类型待实测） |
| `templateId` | 模板 | `getAllCustomizeTemplate` 返回的 ID；自定义模板选其一 |
| `processStatus` | 订单处理状态 | 数组：`1`待处理 `2`资质审核 `3`正在开单 `4`分拣中 `5`待配送 `6`配送中 `8`配送完成 `9`整单退款（"所有状态"传全数组） |
| `startTime`/`endTime` | 时间区间 | ISO |
| `isDH` | 电汇支付？ | `0`；支付方式筛选参数名采集未明确，待实测 |

> **支付方式（全部/电汇支付）**：采集请求体未显式出现该参数名（`isDH` 疑似相关但语义不明），**待真机实测**确认参数名后再写入调用代码。

### 3.3 字段组（自定义模板选字段时）

`getSelectFields/v100` 返回 `orderList`(17)/`drugList`(13)/`receiptList`(6)/`storeList`(2)/`logisticsList`(0) 五组可选字段，用户勾选后并入模板。详见 `zddz.md §6`。

## 4. 限制

- 直接 CSV 与自定义导出**筛选参数同源**（见 `zddz.md §1`），但自定义导出用 `processStatus[]` 表达"订单处理状态"，列表用 `tabProcessStatus` 表达"页签状态"，二者不同。
- 导出任务机制同控销组：异步 → 轮询 `getExportTaskRecord` → 下载，避免重复提交触发 `40003` 限流。
