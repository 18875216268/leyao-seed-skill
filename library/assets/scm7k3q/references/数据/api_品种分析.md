# 品种分析（API）

> 子板块：数据 → **品种分析**（页面 `#/statistic-analysis/product-analysis`；三个 tab 共用同一路由，靠 `tab` 参数切换）。
> **账号归属：① 通用**（自营「数据·品种分析」与摇钱树「统计分析·品种分析」同源，用户 2026-11-13 确认）。
> 请求约定见 `sy.md §3`（域名 `https://scm.ysbang.cn`、`Content-Type: application/json;charset=UTF-8`、公共参数、`code` 判定）。
> 字段 ↔ UI 列对照、枚举全量见 `zddz.md`。以下参数与返回字段均来自**真实抓包**（`采集/Scm 系统_采集结果_数据板块_采集结果.json`）。

## 1. 总览

| 业务 | 列表接口 | 详情/趋势 | 导出 |
|---|---|---|---|
| 销售详情 · 按品种统计 | `saleReportDrugsStatList`（`tab=0`） | `getStatReportDetailBase` + `statReportVisit`/`statReportMoney`/`statReportTrendData` | `exportSaleReportDrugsStat`（`exportType` 0/1） |
| 销售详情 · 委托配送商品 | `saleReportDrugsStatList`（`tab=2`）+ `saleReportBuyCarStat` | 同上 | `exportSaleReportDrugsStat` + `exportBuyCarStat` |
| 售后详情 | `getDrugsStatList` | `getDrugAfterList` + `getDrugsStatReport` | `exportDrugsStatList` |
| 字典/级联 | `getSaleReportBase`、`getMultiCity`、`getReasonList`、`getChildAreas` | — | — |

---

## 2. 读取

### 2.1 读取接口总表

| # | 接口 | 用途 | 必填业务参数 |
|---|---|---|---|
| R1 | `drugsStat/saleReportDrugsStatList` | 主列表（按品种/委托配送） | `dateRange`、`tab`、`pageNo`、`pageSize` |
| R2 | `drugsStat/saleReportBuyCarStat` | 委托配送加购（按当前页 drugIds） | `dateRange`、`tab`、`drugIds[]` |
| R3 | `drugsStat/getSaleReportBase` | 仓库 + 省份基础数据 | 无 |
| R4 | `drugsStat/getMultiCity` | 多城市列表 | 无 |
| R5 | `drugsStat/statReportVisit` | 销售趋势（点击/访客） | `drugId`、`group`、`dateRange` |
| R6 | `drugsStat/statReportMoney` | 购买趋势（金额/店数） | `drugId`、`group`、`dateRange` |
| R7 | `drugsStat/statReportTrendData` | 趋势数据报表 | `drugId`、`group`、`dateRange` |
| R8 | `drugsStat/getStatReportDetailBase` | 单品基础数据 | `drugId` |
| R9 | `drugsStat/getDrugsStatList` | 售后详情列表 | `dateRange`、`pageNo`、`pageSize` |
| R10 | `drugsStat/getDrugAfterList` | 商品售后明细 | `drugId`、`dateRange`、`pageNo`、`pageSize` |
| R11 | `drugsStat/getDrugsStatReport` | 售后曲线 | `drugId`、`group`、`dateRange` |
| R12 | `afterSaleBase/getReasonList` | 售后原因字典 | 无 |
| R13 | `afterSaleBase/getChildAreas` | 省→市→区级联 | `parentId`（省传 `0`） |

> 所有接口均为 `POST`，body 需带公共参数（`token`/`platform`/`version`/`ua`/`ex`/`lastBuildTime`）。下文示例省略公共参数。

### 2.2 销售详情 · 按品种统计（`tab=0`）

#### 2.2.1 列表 R1

```json
{
  "dateRange": ["2026-11-06 00:00:00", "2026-11-12 23:59:59"],
  "tab": 0, "pageNo": 1, "pageSize": 10,
  "wareHouse": 11501,
  "drugId": "", "drugName": "", "drugIdName": "",
  "factoryName": "", "provDrugCode": "",
  "province": [], "city": [], "district": []
}
```

> ⚠️ 上方为**常规全量示例**（drugId/地区留空）。`drugId`/`province`/`city`/`district` 仅在用户明确按品种或地区筛选时填具体值；实测抓包样本（drugId=3678871、province=[12,13] 等）只返回单一药品/地区，勿当模板照抄。

| 界面筛选项 | 参数 | 类型 | 说明 |
|---|---|---|---|
| 商品id / 名称 | `drugId` / `drugName` / `drugIdName` | int / str | `drugId` 精确；`drugName` 模糊；`drugIdName` 为界面合并框（按名称或ID） |
| 厂家 | `factoryName` | str | 模糊 |
| 商品编码 | `provDrugCode` | str | 精确 |
| 时间 | `dateRange` | `[str,str]` | **带时刻** `YYYY-MM-DD HH:mm:ss` |
| 选择地区 | `province` / `city` / `district` | int[] | **省码/市码/区码数字数组**（省码见 `getSaleReportBase.provinceList`）；未筛则省略 |
| 分仓 | `wareHouse` | int | `11501` 重庆仓 / `11502` 央拓虚拟仓（来自 R3，动态） |

**返回**：`data.results[]`（23 字段）+ `totalRecord`/`totalPage`/`pageNo`/`pageSize`。

| 字段 | 含义（UI 列） | 备注 |
|---|---|---|
| `drugId` | 商品ID | |
| `cnName` | 商品名称 | |
| `pack` | 规格包装 | |
| `factoryName` | 生产厂家 | |
| `provDrugCode` | 商品编码 | |
| `amount` | **销量** | **数量**（实测 `totalCost/amount` = 单价，见 `zddz.md §4`） |
| `totalCost` | **销售额** | **金额** |
| `visitTime` | 点击量 | |
| `visitUser` | 访问量（访客） | |
| `buycarStoreAmount` | 加购店数 | |
| `buycarAmount` | 加购数量（次数） | |
| `buycarUserAmount` | 加购用户数 | 委托配送 tab 展示「加购用户数」 |
| `storeCount` | 采购店数 | |
| `orderCount` | 采购订单数 | |
| `stockBalance` | 品种库存 | 可能为字符串 `"-"`，解析需兜底 |
| `addRate` / `addRateStr` | 环比增长 | 数值 `247.17` / 展示串 `"247.17%"` |
| `favorCount` | 收藏数 | 界面未列 |
| `wholesaleId` | 活动ID | |
| `drugProviderId` | 供应商ID | |
| `providerName` | 商家 | |
| `warehouseName` | 仓库 | |
| `agentProviderType` | 委托配送类型 | `tab=2` 时有值（委托配送/非委托配送） |

> **分页硬上限**：实测 `totalRecord=3000`（300 页 × 10）即触顶，不是真实总量。需要全量请改用导出（§3）。

#### 2.2.2 单品基础数据 R8

```json
{ "drugId": 3495098 }
```
→ `data: { drugInfo, isLy, provinceList }`（点表格行【查看】时加载「基础数据」）。

| 字段 | 内容 |
|---|---|
| `drugInfo` | `{ id, cnName, approval, pack, factoryName, provDrugCode }`（**6 字段**：商品ID/名称/批准文号/包装/厂家/商品编码） |
| `isLy` | `0/1`（是否乐药自营标识） |
| `provinceList` | `[{ areaCode(数字), areaName }]`，**34 项**（与 R3 的 `provinceList` 同源，供详情页区域筛选） |

#### 2.2.3 趋势数据 R5/R6/R7

```json
{ "drugId": 3495098, "group": 1, "dateRange": ["2026-11-01", "2026-11-12"] }
```

| 参数 | 取值 |
|---|---|
| `group` | `1` 按天 / `2` 按周 / `3` 按月 |
| `dateRange` | **纯日期** `["YYYY-MM-DD","YYYY-MM-DD"]`（与列表的带时刻格式**不同**） |

| 接口 | 返回 |
|---|---|
| R5 `statReportVisit` | `data: [{ pvData, uvData, xaxis }]`（点击/访客） |
| R6 `statReportMoney` | `data: [{ amountData, moneyData, price, storeNum, xaxis }]` |
| R7 `statReportTrendData` | `data: [{ amountData, moneyData, price, storeNum, xaxis }]`（同结构，报表用） |

> 采集里出现过带时刻样本，但**未验证兼容性**；唯一推荐纯日期 `YYYY-MM-DD`，勿照抄带时刻样本。

### 2.3 销售详情 · 委托配送商品（`tab=2`）

与 §2.2 同一列表接口，仅改 `tab`：

```json
{ "dateRange": ["2026-11-06 00:00:00","2026-11-12 23:59:59"], "tab": 2, "pageNo": 1, "pageSize": 10 }
```

- 额外筛选：`forAgentProvider`（委托配送 / 非委托配送）、`providerIds[]`（委托方）。
- 返回比 `tab=0` 多 `agentProviderType`（列表新增「委托配送商品」列）。
- **加购数据需另拉** R2：把当前页的 `drugId` 组成 `drugIds`：

```json
{ "dateRange": ["2026-11-06 00:00:00","2026-11-12 23:59:59"], "tab": 0, "drugIds": [3678871, 3495098] }
```
→ `data: [{ drugId, buycarStoreAmount, buycarUserAmount, buycarAmount }]`（按 `drugId` 回并到列表）。

> ⚠️ 本接口实测 `tab` 传 **`0`**（不是列表的 `2`）——它是独立的加购统计接口，`tab` 与列表 tab 语义**不对应**，照抄列表的 `tab:2` 可能取不到数；实测调用用 `tab:0` + 当前页 `drugIds`。

> 界面「访客量」列取列表的 `visitUser`；「加购用户数」取 R2 的 `buycarUserAmount`。

### 2.4 售后详情

#### 2.4.1 列表 R9

```json
{ "dateRange": ["2026-11-06 00:00:00","2026-11-12 23:59:59"], "pageNo": 1, "pageSize": 10,
  "reasonId": [], "drugId": "", "drugName": "", "factoryName": "" }
```

| 界面筛选项 | 参数 | 说明 |
|---|---|---|
| 商品id / 名称 | `drugId` / `drugName` | |
| 厂家 | `factoryName` | |
| 时间 | `dateRange` | 带时刻 |
| 售后原因 | `reasonId` | **数组**，值域见 R12 |

**返回** `data.results[]`（9 字段）：

| 字段 | 含义（UI 列） |
|---|---|
| `drugId` | 商品ID |
| `cnName` | 商品名称 |
| `factory` | 厂家（注意：此处是 `factory`，不是 `factoryName`） |
| `pack` | 规格包装 |
| `drugCode` | 商品编码（注意：此处是 `drugCode`，不是 `provDrugCode`） |
| `orderCount` | 订单数 |
| `afterCount` | 售后订单 |
| `afterRate` | 售后率 | **字符串**，值为百分数：`"0.50"` = **0.50%**（实测 `afterCount=2 / orderCount=404 ≈ 0.495%` → `"0.50"`）；`"0"` 表示 0%。直接用原串 + `%` 展示，勿当小数再 ×100 |
| `batch` | 批次 | 实测多为 `null` |

> ⚠️ 与品种分析主列表一样，本接口 **`totalRecord` 也有 3000 硬上限**（实测 `3000` / `totalPage=300`），全量须用 `exportDrugsStatList`。

#### 2.4.2 商品售后明细 R10

```json
{ "drugId": "64707", "reasonId": [], "dateRange": ["2026-11-01 00:00:00","2026-11-12 23:59:59"],
  "pageNo": 1, "pageSize": 10 }
```

> `drugId` 在此接口采集为**字符串**（`"64707"`），传数字通常也可，二者都试过再定。

**返回** `data.results[]`（8 字段）：`afterId`（售后ID）、`ctime`（时间）、`orderId`（订单ID）、`batch`（批次）、`reason`（售后原因）、`note`（补充描述）、`evidenceUrls`（图片，**带签名时效**）、`evidenceModel`（图片模型）。

> 界面还展示「商品名称/商品ID/商品编码/规格包装/厂家/下单时间」，这些来自 R9 行或 `evidenceModel`，**不在 R10 行内**——渲染时用列表行补齐，勿在 R10 里找。

#### 2.4.3 售后曲线 R11

```json
{ "drugId": "3678871", "reasonId": [], "group": 2, "dateRange": ["2026-11-06 00:00:00","2026-11-12 23:59:59"] }
```

→ `data: { drugsStatRateList: [{ date, afterCount, afterRate }] }`

| 字段 | 含义 | 实测样例（`group=2` 按周） |
|---|---|---|
| `date` | 时间标签 | `"202645"`（按周 `YYYYWW`）/ 按天 `YYYYMMDD` / 按月 `YYYYMM`——**随 `group` 变化** |
| `afterCount` | 当期售后订单数 | 1 |
| `afterRate` | 当期售后率 | `"0.31"`（**字符串**，= 0.31%） |

> `group`：`1` 按天 / `2` 按周 / `3` 按月；`date` 格式与之对应，解析前先看 `group`。

### 2.5 字典与级联

| 接口 | 请求体 | 返回 |
|---|---|---|
| R3 `getSaleReportBase` | `{}` | `data: { warehouseFlag, warehouseList:[{value,label}], provinceList:[{areaCode(数字), areaName}], isLy, isLeyo, isCashCow, deliveryProviders }` |
| R4 `getMultiCity` | `{}` | `data: [{ areaCode(数字), areaName }]` |
| R12 `getReasonList` | `{}` | `data: { "<code>": "<原因名>" }`（**对象**，非数组；如 `{"0":"药品近效期","66":"出库单问题"}`） |
| R13 `getChildAreas` | `{"parentId": 0}` | `data: [{ area_code(字符串), area_name }]`；逐级传父级 `area_code` 取市/区 |

> **省码是国标前两位**：11 北京市、12 天津市、13 河北省、14 山西省、15 内蒙古、21 辽宁省…（`provinceList` 与 `getChildAreas` 一致，只是**数字 vs 字符串**两种类型）。
> `getChildAreas` 属 `/scm-order/afterSaleBase/` 模块，**不是** `drugsStat` 自有路径（`/scm-goods/drugsStat/getChildAreas` 为 404）。

---

## 3. 导出

均为 `POST`，**同步返回文件**（服务端生成较慢，>30s 属正常）；列表同样 **3000 行封顶**。

| # | 接口 | 用途 | 业务参数 |
|---|---|---|---|
| E1 | `drugsStat/exportSaleReportDrugsStat` | 主表（按品种/委托配送） | `tab` + `exportType`（`0` 直接导出 / `1` 按商品ID导出）+ 与列表相同的筛选 |
| E2 | `drugsStat/exportDrugsStatList` | 售后详情 | `dateRange` + `reasonId[]` + `exportType` |
| E3 | `drugsStat/exportBuyCarStat` | 委托配送加购 | `tab:2` + `dateRange` |

E1 常规导出请求体（厂家/地区留空=全量；注意地区是**数字数组**）：

> ⚠️ 实测抓包样本带 `factoryName:"北京诺华制药有限公司"`、`province:[12,13,...]` 等，仅导出该厂家该区域数据，勿当模板照抄；下方示例为中性默认值。

```json
{
  "dateRange": ["2026-11-01 00:00:00", "2026-11-12 23:59:59"],
  "factoryName": "",
  "province": [], "city": [], "district": [],
  "tab": 0, "exportType": 0
}
```

> `province`/`city`/`district` 在导出实测为 **int[]**（可含重复值）；`exportType=1` 时按页面勾选的商品ID导出。

---

## 4. 枚举

| 项 | 取值 |
|---|---|
| `tab` | `0` 按品种统计 / `2` 委托配送商品 |
| `group`（趋势） | `1` 按天 / `2` 按周 / `3` 按月 |
| `exportType` | `0` 直接导出数据 / `1` 按商品ID导出 |
| `ex` | `ProductAnalysis`（主表/趋势）/ `AfterSaleDetail`（商品售后明细） |
| `wareHouse` | `11501` 重庆仓 / `11502` 央拓虚拟仓（动态，取 R3） |
| 省码 | 国标前两位：11 京 / 12 津 / 13 冀 / 14 晋 / 15 蒙 / 21 辽 / 22 吉 / 23 黑 / 31 沪 / 32 苏 / 33 浙 / 34 皖 / 35 闽 / 36 赣 / 37 鲁 / 41 豫 / 42 鄂 / 43 湘 / 44 粤 / 45 桂 / 46 琼 / 50 渝 / 51 川 / 52 黔 / 53 滇 / 54 藏 / 61 陕 / 62 甘 / 63 青 / 64 宁 / 65 新 |

---

## 5. 已知坑与待确认

1. **`Content-Type` 必须带 `;charset=UTF-8`**：漏写 → 网关 `40002 操作失败`（头号坑）。
2. **`amount` 是销量、`totalCost` 是销售额**：实测 8 个品种的 `totalCost/amount` 落在 4.49~84.24 元/件（合理单价区间），据此判定；**参考文档记的"amount=销售额、totalCost=成本"是反的**。
3. **地区参数形态有两种记载**：导出实测 **int[]**；参考文档记"字符串、非 areaCode"。列表接口未实采 → 首次按 **int[]**，若 `40002` 再退字符串；`getChildAreas` 返回的 `area_code` 是**字符串**，传给列表前需转数字或按原值试。
4. **两类时间格式不同**：列表/导出 `dateRange` 带 `HH:mm:ss`；趋势接口为纯日期。
5. **列表 3000 行封顶**（`totalRecord=3000`），全量取数用导出。
6. **售后接口字段名与销售不同**：`factory`（非 `factoryName`）、`drugCode`（非 `provDrugCode`）。
7. **`getReasonList` 返回对象不是数组**，遍历时取 `Object.entries`。
8. **`stockBalance` 可为 `"-"`**：做数值聚合前先过滤。
9. **`evidenceUrls` 带签名时效**：售后图片不能长期缓存，需即时下载。
10. **瞬态限流**：`40002` 可能同时表示「操作失败请稍后再试」，遇到时先间隔重试再接错误处理。
