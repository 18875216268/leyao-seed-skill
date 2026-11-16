# 销售报表（API）

> 子板块：数据 → **销售报表**（页面 `#/statistic-analysis/sale-report-pro/new-sale-report`）。
> **账号归属：① 通用**（自营「数据·销售报表」与摇钱树「统计分析·销售报表」同源，用户 2026-11-13 确认；与品种分析一致）。
> 请求约定同 `sy.md §3`；**本模块与品种分析的最大差异：时间参数是 Unix 秒时间戳**，不是日期字符串。
> 参数与字段来自真实抓包（`采集/Scm 系统_采集结果_数据板块_采集结果.json`）+ 前端源码列定义 + 用户提供的参考文档三方核对。

## 1. 总览

**6 种统计方式只用 2 个端点**（靠 `groupEnum` 区分）：

| 统计方式 | `groupEnum` | 端点 | 表格数据容器 |
|---|---|---|---|
| 按天统计 | `DAY` | `suppliersDateMonthWeekAreaActivity` | `data.dateMonthWeekList[]` |
| 按周统计 | `WEEK` | 同上 | `data.dateMonthWeekList[]` |
| 按月统计 | `MONTH` | 同上 | `data.dateMonthWeekList[]` |
| 按区域统计 | `AREA` | 同上 | `data.dateMonthWeekList[]` |
| 按活动类型统计 | `ACTIVITY` | 同上 | `data.activityList[]` |
| 按药店统计 | `PHARMACY` | **`suppliersDrugstoreTable`** | `data.list[]` |

**查询结果 = 两套数据**：
- **数据1（维度图）**：销售/优惠/退款三类共 **10 个 `suppliers*` 端点**，各返回一条/多条折线。按药店统计**无维度图**。
- **数据2（表格）**：上表两个端点的列表数据容器。
- 另有**访客数据**独立子页（`visitorDataChart`）。

---

## 2. 读取

### 2.1 读取接口总表

| # | 接口 | 用途 | 关键业务参数 |
|---|---|---|---|
| R1 | `saleReport/suppliersDateMonthWeekAreaActivity` | 数据2·主表（天/周/月/区域/活动） | `groupEnum`、`startTime`、`endTime`、`pageNo`、`pageSize` |
| R2 | `saleReport/suppliersDrugstoreTable` | 数据2·按药店表 | `groupEnum:"PHARMACY"` + 同筛选 + 分页 |
| R3 | `saleReport/suppliersTotalAmount` | 数据1·销售总额 | `groupEnum`、`startTime`、`endTime` |
| R4 | `saleReport/suppliersNetPurchase` | 数据1·净销售总额 | 同上 |
| R5 | `saleReport/suppliersSalesOrder` | 数据1·订单数 | 同上 |
| R6 | `saleReport/suppliersPStore` | 数据1·采购药店数 | 同上 |
| R7 | `saleReport/suppliersNewPStore` | 数据1·新增采购药店数 | 同上 |
| R8 | `saleReport/suppliersDrugNum` | 数据1·动销品种数 | 同上 |
| R9 | `saleReport/suppliersPlatformDiscountAmount` | 数据1·专享补贴金额 | 同上 |
| R10 | `saleReport/suppliersTotalCouponsAmount` | 数据1·商家优惠券金额 | 同上 |
| R11 | `saleReport/suppliersCouponsNum` | 数据1·商家优惠券数量 | 同上 |
| R12 | `saleReport/suppliersRefundAmount` | 数据1·客户退款金额 | 同上 |
| R13 | `saleReport/visitorDataChart` | 访客数据图表 | 无 |
| R14 | `saleReport/getSubType` | 活动类型/药店类型字典 | 无 |
| R15 | `provider/getWarehouseList` | 分仓字典（**注意前缀是 `/scm-goods/provider/`**） | 无 |
| R16 | `afterSaleBase/getChildAreas` | 区域级联（**与品种分析共用，不重复计入本子板块**） | `parentId` |

> 全部 `POST`；body 需带公共参数（`token`/`platform`/`version`/`ua`/`ex`/`lastBuildTime`），**`ex` = `NewSaleReportNested`**。
> **端点计数口径**：本子板块 **18 个**＝读取 15（R1~R15）＋ 导出 3（E1~E3）；R16 与品种分析共用（登记在品种分析侧），不重复计。

### 2.2 主表（R1，5 种统计方式）

#### 2.2.1 请求与筛选

```json
{
  "groupEnum": "DAY",
  "startTime": 1793894400, "endTime": 1794499199,
  "subType": [], "wholesaleTypes": [], "areaCode": [], "warehouse": 11501,
  "pageNo": 1, "pageSize": 10
}
```

| 界面筛选项 | 参数 | 类型 | 说明 |
|---|---|---|---|
| 统计方式 | `groupEnum` | str | `DAY`/`WEEK`/`MONTH`/`AREA`/`ACTIVITY`/`PHARMACY` |
| 选择时间 | `startTime` / `endTime` | **int（Unix 秒）** | 如 `1793894400` ≈ 2026-11-06 00:00:00 |
| 选择区域 | `areaCode` | int[] | 省/市/区码数组，级联源 R16 |
| **活动类型** | **`subType`** | int[] | 值域 R14（`getSubType`） |
| **药店类型** | **`wholesaleTypes`** | int[] | 值域同 R14；**名字易误解，它管的是药店类型** |
| 分仓 | `warehouse` | int | R15 的 `warehouseCode`（`11501` 重庆仓 / `11502` 央拓虚拟仓） |
| 药店名称 | `storeName` | str | **仅按药店统计**，模糊 |

> 三个筛选参数**相互独立**：活动类型=`subType`、药店类型=`wholesaleTypes`、分仓=`warehouse`。源码 state 为 `{groupEnum, areaCode:[], subType:[], storeName:"", warehouse:void 0, wholesaleTypes:[]}`。

**响应 `data` 结构**：

| 键 | 含义 |
|---|---|
| `dateMonthWeekList[]` | 表格数据（`DAY`/`WEEK`/`MONTH`/`AREA`） |
| `activityList[]` | 表格数据（`ACTIVITY`） |
| `list` | 另一份列表（按药店端点用；主表通常为空） |
| `count` | 行数（如 7 天 → `7`） |
| `warehouseFlag` / `warehouseList` / `warehouseName` | 分仓开关与字典 |

#### 2.2.2 天 / 周 / 月 / 区域 表格字段（`dateMonthWeekList[]`）

| UI 列 | 字段 | 实测样例（DAY） |
|---|---|---|
| 日期 / 周 / 月 / 区域 | `key` | `"2026-11-06"` / `"2026年第45周"` / `"2026年11月"` / `"云南省"` |
| 销售总额 | `totalAmount` | 1828404.09 |
| 净销售总额 | `wsCash` | 1770377.76 |
| 订单数 | `orders` | 4931 |
| 采购药店数 | `purchasingStores` | 2998 |
| 新增采购药店数 | `newPurchasingStores` | 74 |
| 动销品种数 | `activeVarieties` | 4408 |
| 商家优惠券金额 | `discountAmount` | 4345.94 |
| 商家优惠券数量 | `couponNum` | 140 |
| 退款金额 | `refundAmount` | 44148.39 |
| 专享补贴金额 | `platformSubsidyAmount` | 9500.9 |

> 用户规格写「按区域统计、按活动类型统计**无**新增采购药店数」——实测区域行仍返回 `newPurchasingStores`，字段存在就取，是否展示以界面为准。

#### 2.2.3 按活动类型表格字段（`activityList[]`）

| UI 列 | 字段 |
|---|---|
| 活动类型 | `wholesaleType` |
| 销售总额 | `totalAmount` |
| 订单 | `orders` |
| 动销品种数 | `activeVarieties` |
| 退款金 | `refundAmount` |
| 专享补贴金 | `platformSubsidyAmount` |
| 净销售总额 | `wsCash` |
| （采购药店数） | `drugstoreBranchIdCount` |

> 本次抓包未触发 `ACTIVITY`（`activityList` 为空），上表字段取自参考文档的前端源码列定义（同一接口 `data.activityList`）。

### 2.3 按药店统计（R2）

```json
{
  "groupEnum": "PHARMACY",
  "startTime": 1793462400, "endTime": 1794499199,
  "areaCode": [13, 14, 15], "subType": [8, 0], "wholesaleTypes": [5, 1, 4],
  "storeName": "", "pageNo": 1, "pageSize": 10
}
```

**响应**：`data.list[]`（`count` 为总行数，需翻页）+ `data.dateMonthWeekList`/`activityList`（该模式为空）。

| UI 列 | 字段 | 实测样例 |
|---|---|---|
| 药店编码 | `providerCode` | `K0353615` |
| 药店ID | `drugstoreBranchId` | 2771024 |
| 药店名称 | `storeTitle` | 沈阳军创大药房有限公司兴华南街店 |
| 药店类型 | `subTypeStr`（码值 `subType`） | 零售单体 / 0 |
| 省 | `province`（码 `provinceAreaCode`） | 辽宁省 / 21 |
| 市 | `city`（码 `cityAreaCode`） | 沈阳市 / 2101 |
| 销售总额 | `totalAmount` | 14660.8 |
| 订单数 | `orders` | 2 |
| **购药品种** | **`drugType`** | 1 |
| 商家优惠券金额 | `discountAmount` | 0.0 |
| 商家优惠券数量 | `couponNum` | 0 |
| 净销售总额 | `wsCash` | 14225.87 |

> **「购药品种」= `drugType`**（源码列定义 `dataIndex:"drugType"` 已确认），**不是** `activeVarieties`。这是本表最容易取错的一列。

### 2.4 维度图（数据1，10 个端点）

**统一响应骨架**：`data` 有 4 个槽位，**按指标填充其中一个/多个**（不是每个都填）：

```json
{
  "totalData":     {"name": "...", "type": "line", "data": [{"col": "2026-11-06", "value": 1828404.09}]},
  "list":          [{"name": "重庆仓", "type": "line", "data": [...]}, {"name": "央拓虚拟仓", ...}],
  "newStoreData":  {"name": "...", "type": "line", "data": [...]},
  "instrumentData": null
}
```

| 维度 | 端点 | 填充槽位 | `totalData.name` 实测 |
|---|---|---|---|
| 销售数据 | `suppliersTotalAmount` | `totalData` + `list`(2 条分仓) | 央拓医药采购总金额 |
| 销售数据 | `suppliersNetPurchase` | `totalData` + `list` | 央拓医药净采购总额 |
| 销售数据 | `suppliersSalesOrder` | `totalData` + `list` | 央拓医药销售订单 |
| 销售数据 | `suppliersPStore` | `totalData` + `list` | 央拓医药采购药店 |
| 销售数据 | `suppliersNewPStore` | **`newStoreData`**（totalData/list 为 null） | 新增采购药店 |
| 销售数据 | `suppliersDrugNum` | `totalData` + `list` | 央拓医药动销品种数 |
| 优惠数据 | `suppliersPlatformDiscountAmount` | 仅 `totalData` | 央拓医药专享补贴金额 |
| 优惠数据 | `suppliersTotalCouponsAmount` | 仅 `totalData` | 央拓医药商家优惠券金额 |
| 优惠数据 | `suppliersCouponsNum` | 仅 `totalData` | 央拓医药商家优惠券数量 |
| 退款数据 | `suppliersRefundAmount` | 仅 `totalData` | 央拓医药商家客户退款金额 |

- 折线点结构统一为 `{col, value}`：`col` 是标签（天=日期、周=`2026年第45周`、月=`2026年11月`、区域=省名），`value` 是数值。
- `list[]` 是**分仓拆分**（重庆仓 / 央拓虚拟仓两条线），只有 5 个销售指标给；优惠/退款类与 `NewPStore` 为 `null`。
- `instrumentData` 本次全部 `null`，未见填充场景。
- **按药店统计（PHARMACY）没有维度图**，不要调这 10 个端点。

### 2.5 访客数据（R13）

```json
{}   // 仅公共参数
```
→ `data.list = [{ addDate: "2026-11-02", addDateStr: "2026/11/02", userNum: 8914 }]`（`userNum` = 当日访客数）。

> 页面点「访客数据」进入独立子页；导出见 §3 的 `exportVisitorData`。**该接口不吃筛选参数**（无时间/区域入参），返回全量。

### 2.6 字典

| 接口 | 请求体 | 返回 |
|---|---|---|
| R14 `getSubType` | `{}` | `{"0":"零售单体","1":"第三终端","2":"连锁总部（批零一体）","3":"连锁加盟","4":"连锁总部（纯连锁）","5":"商业公司","6":"民营医院","8":"医疗器械经营店"}` |
| R15 `getWarehouseList` | `{}` | `[{id, whName:"重庆仓", warehouseCode:11501, isMasterWarehouse:1}, {whName:"央拓虚拟仓", warehouseCode:11502, ...}]` |
| R16 `getChildAreas` | `{"parentId": 0}` | `[{area_code:"11", area_name:"北京市"}, ...]`（逐级传父级 `area_code`） |

> `getSubType` 同时供「活动类型」(`subType`) 与「药店类型」(`wholesaleTypes`) 两个下拉；两个参数值域相同但**分开传**。

---

## 3. 导出

均为 `POST`，**同步返回 xlsx 二进制流**（`application/octet-stream`，实测文件名如「按天统计明细数据导出.xlsx」），非异步任务、无 `code` 包络。

| # | 接口 | 导出对象 | 请求要点 |
|---|---|---|---|
| E1 | `saleReport/suppliersDateMonthWeekAreaActivityExport` | 当前统计方式的主表 | `groupEnum` + 全部筛选 + 时间，**无分页**（导全部） |
| E2 | `saleReport/suppliersDrugstoreTableExport` | 按药店统计表 | `groupEnum:"PHARMACY"` + 筛选 + 时间，无分页 |
| E3 | `saleReport/exportVisitorData` | 访客数据 | 仅公共参数 |

E1 实测请求体：

```json
{ "groupEnum": "DAY", "startTime": 1793462400, "endTime": 1794499199,
  "areaCode": [13, 14, 15, 21], "subType": [8, 0], "wholesaleTypes": [1] }
```

> 导出与列表必须传**同一组筛选**，否则导出的不是当前查询结果（用户要求"直接导出对应查询出来的数据"）。

---

## 4. 枚举

| 项 | 取值 |
|---|---|
| `groupEnum` | `DAY` 按天 / `WEEK` 按周 / `MONTH` 按月 / `AREA` 按区域 / `ACTIVITY` 按活动类型 / `PHARMACY` 按药店 |
| `subType`（活动类型）/ `wholesaleTypes`（药店类型） | `0` 零售单体 / `1` 第三终端 / `2` 连锁总部（批零一体）/ `3` 连锁加盟 / `4` 连锁总部（纯连锁）/ `5` 商业公司 / `6` 民营医院 / `8` 医疗器械经营店 |
| 主表 `key` | 天 `"2026-11-06"` / 周 `"2026年第45周"` / 月 `"2026年11月"` / 区域 省名 |
| `warehouse` | `11501` 重庆仓 / `11502` 央拓虚拟仓（动态取 R15） |
| `ex` | `NewSaleReportNested` |
| 时间 | **Unix 秒时间戳**（`startTime`/`endTime`） |

---

## 5. 已知坑与待确认

1. **时间参数是 Unix 秒**：`startTime`/`endTime` 传时间戳（与品种分析的 `dateRange` 字符串完全不同）。跨天边界用 `00:00:00` → `23:59:59` 换算。
2. **「活动类型」= `subType`、「药店类型」= `wholesaleTypes`**：名字与直觉相反，`wholesaleTypes` 不是"活动类型"。另有独立分仓参数 `warehouse`。
3. **两个端点承载 6 种统计方式**：`PHARMACY` 必须走 `suppliersDrugstoreTable`，传 `groupEnum:PHARMACY` 调主表拿不到药店数据。
4. **主表按统计方式换数据容器**：`DAY/WEEK/MONTH/AREA` 取 `dateMonthWeekList[]`，`ACTIVITY` 取 `activityList[]`；**不要固定读一个键**。
5. **维度图槽位不固定**：常规 5 个销售指标给 `totalData`+`list`（分仓 2 条），`NewPStore` 只给 `newStoreData`，优惠/退款只给 `totalData`。渲染前先判空，否则 `null.data` 报错。
6. **「购药品种」= `drugType`**（按药店表），不是 `activeVarieties`——实测该行 `drugType:1`、无 `activeVarieties` 键。
7. **按药店统计无维度图**，且必须分页（`count` 是总行数，`list` 只是当前页）。
8. **访客接口不吃筛选**：`visitorDataChart` 仅公共参数，返回全量按天访客。
9. **导出是同步文件流**：直接落盘二进制，不要按 JSON 解析；导出与列表需同参数。
10. **`getWarehouseList` 在 `/scm-goods/provider/` 前缀**，不在 `saleReport/` 下（`saleReport/getWarehouseList` 不存在）。
11. **`ACTIVITY` 模式的字段**（`activityList[]`）本次抓包未触发，字段名取自参考文档源码列定义，首次使用建议先跑一次 `groupEnum:"ACTIVITY"` 核对。
