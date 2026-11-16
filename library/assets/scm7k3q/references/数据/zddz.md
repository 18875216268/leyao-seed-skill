# 数据 · 品种分析 字段对照（zddz）

> 配套 `sy.md`（板块索引）与 `api_品种分析.md`（接口合同）。本文专管**字段**：界面列 ↔ API key、筛选项 ↔ 参数、枚举、字段含义判定与复验口径。
> 数据来源：真实抓包 `采集/Scm 系统_采集结果_数据板块_采集结果.json`（含请求体与响应首行），以及首行真实值交叉验证。
> 账号标签与 `references/商品/sy.md §3.1` 一致：**① 通用** / **② 仅摇钱树** / **③ 仅自营** / **④ 转PMS** / **⑤ 禁用**。
> 本板块按子板块分：**品种分析、销售报表 = ① 通用**；**店铺流量 = ③ 仅自营**。

## 0. 通用列定义

| 列名 | 含义 |
|---|---|
| 界面项 | 页面上看到的筛选项 / 表格列 |
| API key | 请求或响应中的字段名 |
| 类型 | `int` / `str` / `int[]` / `[str,str]` / `obj` |
| 约束 | 格式、值域、易错点 |

---

## 1. 筛选项 ↔ 请求参数

### 1.1 销售详情 · 按品种统计（`tab=0`）

| 界面项 | API key | 类型 | 约束 |
|---|---|---|---|
| 商品id | `drugId` | int | 精确 |
| 商品名称 | `drugName` | str | 模糊；界面合并框另有 `drugIdName`（可填名称或ID） |
| 厂家 | `factoryName` | str | 模糊 |
| 商品编码 | `provDrugCode` | str | 精确（如 `SP0232148`） |
| 时间 | `dateRange` | `[str,str]` | **带时刻** `YYYY-MM-DD HH:mm:ss` |
| 选择地区 | `province` / `city` / `district` | int[] | 三级**数字数组**；省码取 `getSaleReportBase.provinceList[].areaCode`；未筛省略。**导出实测、列表接口未实采**，`40002` 时退字符串，见 `api_品种分析.md §5.3` |
| 分仓 | `wareHouse` | int | `11501` 重庆仓 / `11502` 央拓虚拟仓（动态） |

### 1.2 销售详情 · 委托配送商品（`tab=2`）

| 界面项 | API key | 类型 | 约束 |
|---|---|---|---|
| 商品编码 / 商品id / 商品名称 / 厂家 / 时间 / 选择地区 / 分仓 | 同上 | — | 参数完全复用 §1.1 |
| 委托配送商品 | `forAgentProvider` | int/str | 委托配送 / 非委托配送（`tab=2` 专用） |
| 委托方 | `providerIds` | int[] | 多选 |

### 1.3 售后详情

| 界面项 | API key | 类型 | 约束 |
|---|---|---|---|
| 商品id / 商品名称 | `drugId` / `drugName` | int / str | |
| 厂家 | `factoryName` | str | |
| 时间 | `dateRange` | `[str,str]` | 带时刻 |
| 售后原因 | `reasonId` | int[] | 值域取 `getReasonList`（返回**对象** `{code:name}`） |

> **售后筛选不含地区/分仓**（与销售详情不同）。

---

## 2. 返回字段 ↔ 界面列

### 2.1 销售详情 · 按品种统计（`saleReportDrugsStatList` `tab=0`，15 列）

| 界面列 | API key | 类型 | 说明 |
|---|---|---|---|
| 商品id | `drugId` | int | |
| 商品名称 | `cnName` | str | 注意是 `cnName`，非 `drugName` |
| 规格包装 | `pack` | str | 如 `100mg*28片` |
| 生产厂家 | `factoryName` | str | |
| 商品编码 | `provDrugCode` | str | 如 `SP0232148` |
| **销量** | **`amount`** | num | **数量**（见 §4 判定） |
| **销售额** | **`totalCost`** | num | **金额**（两位小数） |
| 点击量 | `visitTime` | int | 访问次数 |
| 访问量 | `visitUser` | int | 访客数 |
| 加购店数 | `buycarStoreAmount` | int | |
| 加购数量 | `buycarAmount` | int | 加购次数 |
| 采购店数 | `storeCount` | int | |
| 采购订单数 | `orderCount` | int | |
| 品种库存 | `stockBalance` | num/str | **可能为 `"-"`**，聚合前过滤 |
| 环比增长 | `addRateStr` / `addRate` | str / num | 展示串 `"247.17%"` / 数值 `247.17` |

**未上表但存在**：`buycarUserAmount`（加购用户数，委托配送 tab 用）、`favorCount`（收藏数）、`wholesaleId`（活动ID）、`drugProviderId`（供应商ID）、`providerName`（商家）、`warehouseName`（仓库）、`agentProviderType`（委托配送类型）。

### 2.2 销售详情 · 委托配送商品（`tab=2`，14 列）

与 §2.1 同名同义，差异仅三列：

| 界面列 | API key | 来源 |
|---|---|---|
| 访客量 | `visitUser` | 列表 |
| 加购用户数 | `buycarUserAmount` | **列表（`tab=2`）或 R2 `saleReportBuyCarStat`**（按 `drugIds` 聚合） |
| 委托配送商品 | `agentProviderType` | 列表（`tab=2` 才有值；`tab=0` 为 `null`） |

> 若列表返回的加购三列为 0 而页面有值，用 R2 按当前页 `drugIds` 重拉后按 `drugId` 回并。

### 2.3 售后详情（`getDrugsStatList`，8 列）

| 界面列 | API key | 说明 |
|---|---|---|
| 商品id | `drugId` | |
| 商品名称 | `cnName` | |
| 厂家 | **`factory`** | **不是** `factoryName` |
| 规格包装 | `pack` | |
| 商品编码 | **`drugCode`** | **不是** `provDrugCode` |
| 订单数 | `orderCount` | |
| 售后订单 | `afterCount` | |
| 售后率 | `afterRate` | 数值/百分比按原值展示 |
| （批次） | `batch` | 界面未列，明细里有 |

### 2.4 商品售后明细（`getDrugAfterList`）

| 界面项 | API key | 说明 |
|---|---|---|
| 售后原因 | `reason` | |
| 时间 | `ctime` | |
| 补充描述 | `note` | |
| 订单id | `orderId` | |
| 批次 | `batch` | |
| 图片 | `evidenceUrls` | **带签名时效**，需即时下载；模型见 `evidenceModel` |
| 售后ID | `afterId` | |
| 商品名称 / 商品id / 商品编码 / 规格包装 / 厂家 / 下单时间 | **不在本接口返回** | 由列表行（§2.3）补齐；下单时间取订单详情或 `ctime`（下单时间口径未实测） |

### 2.5 单品详情与趋势

| 接口 | 返回字段 |
|---|---|
| `getStatReportDetailBase` | `drugInfo`（商品资料）、`isLy`、`provinceList` |
| `statReportVisit` | `pvData`（点击）、`uvData`（访客）、`xaxis`（横轴） |
| `statReportMoney` / `statReportTrendData` | `amountData`（数量）、`moneyData`（金额）、`price`、`storeNum`（店数）、`xaxis` |

> `xaxis` 在按天时为 `"11/06"` 形式，按周/按月为区间或月份标签（实测服务端直出，直接展示即可）。

---

## 3. 字典返回

| 接口 | 返回形态 |
|---|---|
| `getSaleReportBase` | `{ warehouseFlag, warehouseList:[{value:int,label:str}], provinceList:[{areaCode:int, areaName:str}], isLy, isLeyo, isCashCow, deliveryProviders }` |
| `getMultiCity` | `[{ areaCode:int, areaName:str }]` |
| `getReasonList` | `{ "<code>": "<原因名>" }`（**对象**） |
| `getChildAreas` | `[{ area_code:"11"（字符串）, area_name }]` |

> **同一个省码有两种类型**：`provinceList.areaCode` 是**数字**，`getChildAreas.area_code` 是**字符串**。组装列表/导出请求时统一成数字（实测导出的 `province` 为 `[12,13,...]`）。

---

## 4. 关键判定：`amount` = 销量、`totalCost` = 销售额

真实首行（2026-11-06~11-12，示例商品 100mg*28片）：

| amount | totalCost | totalCost/amount | orderCount | 判定 |
|---|---|---|---|---|
| 9255 | 472725.35 | **51.08** | 404 | 单价 ≈ 51 元/盒（市场价区间）→ `amount`=数量、`totalCost`=金额 |
| 9701 | 365016.38 | 37.63 | 530 | 同上 |
| 69555 | 312326.75 | 4.49 | 28 | 迪根（低价药）单价 4.49 元，合理 |
| 5763 | 194636.38 | 33.77 | 99 | 可定（瑞舒伐他汀）单价 33.77 元，合理 |
| 1938 | 163262.44 | 84.24 | 334 | 礼达（迈之灵片）单价 84.24 元，合理 |

8 个品种的「金额/数量」全部落在 4.49~84.24 元/件的常见单价区间 → **`amount` 是销量（件）、`totalCost` 是销售额（元）**。
参考文档《数据-品种分析_API文档.md §4.1》把 `amount` 记为"销售额"、`totalCost` 记为"成本"，**与实测值矛盾，以本文为准**。

---

## 5. 枚举

| 项 | 取值 |
|---|---|
| `tab` | `0` 按品种统计 / `2` 委托配送商品 |
| `group` | `1` 按天 / `2` 按周 / `3` 按月 |
| `exportType` | `0` 直接导出 / `1` 按商品ID导出 |
| `ex` | `ProductAnalysis` / `AfterSaleDetail` |
| `wareHouse` | `11501` / `11502`（动态） |
| 省码 | 国标前两位（11 京 … 65 新），全表见 `api_品种分析.md §4` |

---

## 6. 取数口径与复验（品种分析）

1. **时间**：列表/导出用 `dateRange`（带 `HH:mm:ss`）；趋势用纯日期。跨月/跨年直接换区间，勿传 Unix 秒。
2. **全量取数**：列表 `totalRecord` 上限 3000 → 用导出（同样 3000 行封顶）。需要超过 3000 行时按时间切片多次导出。
3. **复验**：列表改动后用同参数再查一次 `totalRecord` 与首行 `drugId`；导出核对列头与行数（导出为文件流，无 `code` 包络）。
4. **聚合**：`stockBalance` 可能为 `"-"`；`addRateStr` 可能为 `"--"`（无上期数据时），做数值计算前统一过滤。
5. **地区**：`province/city/district` 只传选了的那一级（选到省只传 `province`），未选省就不要传 `city`/`district`。

---

## 7. 销售报表：筛选项 ↔ 请求参数

> 与品种分析**完全不同的一套参数**（时间用 Unix 秒、区域用 `areaCode[]`、无 `dateRange`）。

| 界面项 | API key | 类型 | 约束 |
|---|---|---|---|
| 统计方式 | `groupEnum` | str | `DAY`/`WEEK`/`MONTH`/`AREA`/`ACTIVITY`/`PHARMACY` |
| 选择时间 | `startTime` / `endTime` | int | **Unix 秒**（如 `1793894400` ≈ 2026-11-06 00:00:00） |
| 选择区域 | `areaCode` | int[] | 省/市/区码数组（级联 `getChildAreas`） |
| **活动类型** | **`subType`** | int[] | 值域 `getSubType`（0/1/2/3/4/5/6/8） |
| **药店类型** | **`wholesaleTypes`** | int[] | 值域同 `getSubType`；**名字易误解，它管药店类型** |
| 分仓 | `warehouse` | int | `getWarehouseList` 的 `warehouseCode`（11501/11502） |
| 药店名称 | `storeName` | str | 仅 `PHARMACY`，模糊 |
| 分页 | `pageNo` / `pageSize` | int | 主表与药店表都要 |

## 8. 销售报表：返回字段 ↔ 界面列

### 8.1 主表 · 天/周/月/区域（`data.dateMonthWeekList[]`，11 列）

| 界面列 | API key | 实测样例（DAY） |
|---|---|---|
| 日期/周/月/区域 | `key` | `"2026-11-06"` / `"2026年第45周"` / `"2026年11月"` / 省名 |
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

### 8.2 主表 · 按活动类型（`data.activityList[]`）

| 界面列 | API key |
|---|---|
| 活动类型 | `wholesaleType` |
| 销售总额 | `totalAmount` |
| 订单 | `orders` |
| 动销品种数 | `activeVarieties` |
| 退款金 | `refundAmount` |
| 专享补贴金 | `platformSubsidyAmount` |
| 净销售总额 | `wsCash` |
| （采购药店数） | `drugstoreBranchIdCount` |

> 抓包未触发 `ACTIVITY`（该容器为空），上表来自参考文档的前端源码列定义。

### 8.3 按药店统计（`data.list[]`，12 列 + 辅助）

| 界面列 | API key | 实测样例 |
|---|---|---|
| 药店编码 | `providerCode` | `K0353615` |
| 药店ID | `drugstoreBranchId` | 2771024 |
| 药店名称 | `storeTitle` | 沈阳军创大药房… |
| 药店类型 | `subTypeStr` / `subType` | 零售单体 / 0 |
| 省 | `province` / `provinceAreaCode` | 辽宁省 / 21 |
| 市 | `city` / `cityAreaCode` | 沈阳市 / 2101 |
| 销售总额 | `totalAmount` | 14660.8 |
| 订单数 | `orders` | 2 |
| **购药品种** | **`drugType`** | 1 |
| 商家优惠券金额 | `discountAmount` | 0.0 |
| 商家优惠券数量 | `couponNum` | 0 |
| 净销售总额 | `wsCash` | 14225.87 |

> **「购药品种」= `drugType`**，不是 `activeVarieties`（该行无此键）。这是最容易取错的一列。

### 8.4 维度图（10 个，4 槽位）

| 槽位 | 结构 | 谁填 |
|---|---|---|
| `totalData` | `{name, type:"line", data:[{col,value}]}` | 全部 10 个（`NewPStore` 除外） |
| `list` | `[{name,type,data:[...]}]`（**分仓 2 条折线**） | 仅 5 个销售指标（TotalAmount/NetPurchase/SalesOrder/PStore/DrugNum） |
| `newStoreData` | `{name,type,data:[...]}` | **仅 `suppliersNewPStore`** |
| `instrumentData` | — | 本次全 `null` |

> 常规指标 `totalData`+`list` 双填；优惠/退款只有 `totalData`。渲染前判空。

## 9. 两子板块参数差异（对照，最易混）

| 维度 | 品种分析 | 销售报表 |
|---|---|---|
| 时间参数 | `dateRange` 字符串数组 | **`startTime`/`endTime` Unix 秒** |
| 区域参数 | `province`/`city`/`district`（三个字段） | **`areaCode[]`（一个数组）** |
| 活动类型 | 无 | `subType[]` |
| 药店类型 | 无 | `wholesaleTypes[]` |
| 分仓 | `wareHouse`（大写 H） | **`warehouse`（全小写）** |
| 分页容器 | `data.results[]` + `totalRecord` | `data.dateMonthWeekList[]`/`list[]` + `count` |
| `ex` | `ProductAnalysis` / `AfterSaleDetail` | `NewSaleReportNested` |

> 分仓参数大小写不同（`wareHouse` vs `warehouse`），跨子板块复用代码时必检。

---

## 10. 店铺流量：筛选项与返回字段

### 10.1 筛选项 ↔ 请求参数（`getFlowInfo`）

| 界面项 | API key | 类型 | 取值 |
|---|---|---|---|
| 统计方式 | `granularity` | int | `1` 按天 / `2` 按周 / `3` 按月 |
| 时间周期 | `rangeFlag` | int | `1` 近8天 / `2` 近30天 / `3` 近3个月 / `4` 自定义 |
| 自定义起止 | `startTime` / `endTime` | str | **仅 `rangeFlag=4`**，纯日期 `"YYYY-MM-DD"`（带时分报 `40002`） |

### 10.2 返回字段 ↔ 界面指标

| 界面指标 | 趋势（`getFlowInfo`） | 汇总卡（`topExposureStat`） | 同比基准 / 变化率 |
|---|---|---|---|
| 活动曝光数 | `exposureList[].num` | `exposureNum` | `exposureNumSame` / `exposureUpRatio` |
| 详情点击数 | `wsDetailVisitList[].num` | `detailClickNum` | `detailClickNumSame` / `detailClickNumUpRatio` |
| 店铺访客数 | `storeVisitList[].num` | `visitNums` | `visitNumsSame` / `visitNumsUpRatio` |

趋势行结构：`{key, num, numAvrg}`；`num`=当期、`numAvrg`=对比基准（灰线）、`key`=时间标签。

### 10.3 `key` 格式

| `granularity` | 格式 | 实测样例 |
|---|---|---|
| `1` 按天 | `YYYYMMDD`（8 位无分隔） | `"20261014"` |
| `2` 按周 | `YYYYWW` | `"202642"` |
| `3` 按月 | `YYYYMM`（预期格式，未实采） | `"202611"` |

> ⚠️ 参考文档按天示例写成 `"2026-11-06"` 有误，实测为 `"20261014"`。

### 10.4 与其它子板块的参数差异

| 维度 | 店铺流量 | 品种分析 | 销售报表 |
|---|---|---|---|
| 时间 | `rangeFlag`（+自定义纯日期） | `dateRange` 字符串数组 | `startTime`/`endTime` Unix 秒 |
| 统计粒度 | `granularity` 1/2/3 | 无（`tab`/`group`） | `groupEnum` |
| 导出 | **无接口**（前端生成） | 3 个 xlsx 接口 | 3 个 xlsx 接口 |
| `ex` | `StoreTraffic` | `ProductAnalysis`/`AfterSaleDetail` | `NewSaleReportNested` |
| 前缀 | `scm-setting/flow` + `scm-base/saleReport` | `scm-goods/drugsStat` | `scm-goods/saleReport` |

> `*UpRatio` 是**小数比率**（`0.33`=33%），`*Same` 是对比期绝对值；渲染时 ×100 加 `%`。
> ⚠️ **同名 `startTime`/`endTime` 跨子板块类型相反**：销售报表＝**int（Unix 秒）**，店铺流量＝**str（纯日期 `YYYY-MM-DD`）**，品种分析趋势＝字符串数组 `dateRange`。禁止复用同一个时间构造函数。
