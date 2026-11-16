# 我的摇钱树 · 字段对照（zddz）

> 用途：页面口径（筛选项/结果项）↔ 代码字段 ↔ **枚举字典**的**唯一对照台账**。
> 范围：摇钱树销售流水（`cashcoworder` + `areaGroup`）、我的品种（`myVariety`）、区域划分查看（`provider`）。
> 标注规则：`实测` ＝ 2026-11-16 抓包确证；`推测` ＝ 中文口径未经交叉确证；`待确证` ＝ 枚举/格式待实测；**接口参数以 `api_*.md` 为准，本文不重复请求示例**。
> 归属：三个子板块均为 **② 仅摇钱树**（唯一事实源 `references/sy.md §0.4`）。

## 0. `ex` 取值（按子板块，实测确证）

| 子板块 | `ex` |
|---|---|
| 摇钱树销售流水 | `MyCashcowSaleLog` |
| 我的品种 | `MyVariety` |
| 区域划分查看 | `RegionDivision` |

> 旧逆向 xlsx 记「前端写死空串」——**已被实测推翻**。

## 1. 摇钱树销售流水

### 1.1 请求参数

**列表 / 计数（`saleLogsAct` / `saleLogsCountAct`，12 个）**：

| 参数 | 页面口径 | 类型 | 取值 |
|---|---|---|---|
| `cnName` | 商品名称 | string | — |
| `storeName` | 药店 | string | — |
| `provider` | 供应商 | string | — |
| `deliveryProvider` | 配送商 | **array** | 配送商 id 数组 |
| `provDrugCode` | 商品编码 | string | — |
| `compCode` | 本公司编码 | string | — |
| `orderStatus` | 订单状态 | int\|null | 默认 `null`；码值`待确证` |
| `startPayTime` / `endPayTime` | 下单付款时间 | int | **Unix 秒** |
| `province` / `city` / `district` | 区域（省/市/区县） | **array** | 数字 `areaCode` 数组 |

**导出（`exportSaleLogsAct`）**：同上，但**多** `drugId`（药品id）/ `orderId`（订单id）/ `wholesaleId`（活动id），**少** `startPayTime`/`endPayTime`。

### 1.2 返回字段（`saleLogsAct`，60 字段）

| 分组 | 字段 | 页面口径 | 状态 |
|---|---|---|---|
| 列表容器 | `data` / `tabStatus` / `isCashcow` / `deliverProvider` | 行数组 / 状态字典 / 摇钱树标记 / 配送商字段 | `实测` |
| 订单 | `orderId`（订单id）/ `odId`（内部单 id） | 订单id | `实测` |
| 订单状态 | `orderStatusDesc` / `processStatus` / `status` | 订单状态 | 文案以 `orderStatusDesc` 为准；码值映射`待确证` |
| 时间 | `payTime`/`payTimeStr`、`deliverTime`/`deliverTimeStr`、`refundTime`/`refundTimeStr` | 支付 / 出库 / 退款 | Unix 秒 + 展示串；`0`=无 |
| 结算 | `clearStatus`/`clearStatusDesc`、`clearPrice`、`clearMoney`、`clearTime`/`clearTimeStr` | 结算状态 / 定价（结算价）/ 结算金额 / 结算时间 | `实测`（`0`=未结算） |
| 价格 | `dealUnitPrice` | 成交单价 | `实测` |
| 数量 | `amount` | 采购数量 | `实测` |
| 商品 | `cnName`、`specification`、`factoryName`、`approval`、`pack`、`name` | 商品名称 / 规格 / 厂家 / 国药准字 / 包装 | `name` 口径`待确证` |
| ID | `provDrugCode`、`drugId`、`compCode`、`wholesaleId`、`wsParentid` | 商品编码 / 药品id / 本公司编码 / 活动id / 父活动 | `实测`（父活动 `0`=无） |
| 主体 | `storetitle`、`storeId`、`drugstoreBranchId`、`province`/`city`/`district`、`areaCode`、`areaId` | 药店 / 药店所在省市区 | 区域返回**中文**（与筛选 code 不同） |
| 供应商 | `erpProviderName`、`drugProviderId`、`wsProviderId`、`providerId` | 药品供应商 | 名称`实测`；`providerId` 实为配送商 id |
| 配送 | `deliverProviderName` | 配送商 | `实测` |
| 其他 | `op`、`wholesaleType`/`wholesaleTypeDesc`、`refundId`、`autographUrl` | 来源 / 活动类型 / 退款id / 签收单 | `op`=`交易`（实测）；「特价不可用券」**无直接字段** |

### 1.3 字典（实测）

| 字典 | 值 |
|---|---|
| `tabStatus`（9 态） | 1 待处理 / 2 正在开单 / 3 审核资质 / 4 分拣中 / 5 待配送 / 6 配送中 / 7 配送异常 / 8 配送完成 / 9 整单退款 |
| `wholesaleType` | 7 = 药惠拼（拼团）（实测；其余待积累） |
| `clearStatus` | 0 = 未结算（实测；其余待积累） |
| `op` | 交易（实测；其余待积累） |

### 1.4 级联字典（`areaGroup/getAreaCodeWithoutLimit`）

| 字段 | 说明 |
|---|---|
| `level` / `maxLevel` / `parentCode` | 请求：起始层级（0）/ 最大层级（3）/ 上级编码（0=顶级） |
| `areaCode` / `areaName` / `leaf` / `areaCodeMap` | 响应：数字编码（11=北京）/ 中文名 / 是否末级 / 映射 |

## 2. 我的品种

### 2.1 请求参数

**列表（`myDrugsAct`，10 个）**：

| 参数 | 页面口径 | 默认 | 取值 |
|---|---|---|---|
| `lyErpDrugCode` | 乐药ERP商品编码 | `""` | — |
| `erpDrugName` | ERP商品名称 | `""` | — |
| `erpStock` | ERP库存 | `-1` | -1 全部 / 1 大于0 / 2 小于等于0 |
| `fixedPrice` | 一口价 | `-1` | -1 全部 / 1 无进行中 |
| `storeCode` | 本公司编码 | `""` | — |
| `maintainPrice` | 维护底价 | `-1` | -1 全部 / 1 未维护 / 2 已维护 |
| `maintainLyPrice` | 维护最低供乐药价 | `-1` | -1 全部 / 1 未维护 / 2 已维护 |
| `adjustPriceStatus` | 调价状态 | `-1` | -1 全部 / 1 未调价 / 2 已调价 |
| `erpStockSort` | ERP库存排序 | `-1` | -1 无排序 / 1 正序 / 2 倒序 |
| `onlyNeedApply` | 仅查看需要申请新增商品的品种 | `0` | 0 否 / 1 是 |

**导出（`myVariety/export`）**：含 `drugId`（商品ID），不含 `maintainPrice`/`maintainLyPrice`/`adjustPriceStatus`/`erpStockSort`。

**写（`myVariety/update`）**：`id`（行 id）+ `updateType`（维护类型选择器；实测 `2`→写 `bottomPrice` 底价，`1` 推断为拼团最低供乐药价，未确证）+ `bottomPrice`（底价）。

**写候选（`cashcow/editMinLeyoPrice`，静态·未实测）**：拼团最低供乐药价维护候选端点；逆向工作簿字段疑误配，**参数未确证前不得调用**；已登记于 `modules/marketing/__init__.py` 静态清单（见 `api_我的品种.md §3.3`）。

**批量导入（`batchEditBottomPrice`）**：`multipart/form-data` 文件上传；模板列 3 种组合 = `乐药erp商品编码`+`底价` / `本公司编码`+`底价` / `本公司编码`+`配送商`+`底价`；文件字段名`待确证`。

### 2.2 返回字段（`myDrugsAct`）

| 分组 | 字段 | 页面口径 | 状态 |
|---|---|---|---|
| 分页 | `pageNo` / `pageSize` / `totalRecord` / `totalPage` / `results[]` | — | `实测` |
| ERP侧 | `provDrugCode`、`drugName`、`pack`、`factory`、`approval` | 乐药ERP商品编码 / ERP商品信息四件套 | `实测` |
| 平台侧 | `drugId`、`pdrugName`、`ppack`、`pfactory`、`papproval` | 匹配平台商品ID / 平台商品信息四件套 | `实测` |
| 供应 | `providerName`、`deliverProviderId` | 配送商 | `实测` |
| 价格 | `latestPurchasePrice`（可 null）、`commisionPercent1~11` | 最新供货价 / 一口价·特价费率 | 动态列按实际键遍历 |
| 库存 | `stockBalance` | ERP库存 | 可 null/`"-"` |
| 活动状态 | `wholeSaleType1/15/13/16/1789/75/73/76/7789/7/8/85/83/86` | 一口价/拼团/批购包邮 × 进行中/已暂停 | 值 0/1；映射`未定谳` |
| 编码 | `compCode` | 本公司编码 | `实测` |
| 价格维护 | `minLeyoPrice`、`minLeyoPriceModifiedCount`、`isMinLeyoPriceModified`、`bottomPrice` | 拼团最低供乐药价 / 维护计数 / 底价 | `bottomPrice=-1`=未维护 |
| 其他 | `id`、`showApply` | 行 id / 需申请标记 | `实测` |

### 2.3 筛选配置（`init`）

`erpStock` / `fixedPrice` / `maintainPrice` / `maintainLyPrice` / `adjustPriceStatus` / `erpStockSort` —— 各为 `[{code, value}]`，即 §2.1 表右列权威来源。

## 3. 区域划分查看

| 接口 | 字段 | 页面口径 | 状态 |
|---|---|---|---|
| `getProviderDelivers` | `providerNames[]`（`{id: 名称}` 单键对象，实测 21 条） | 配送商下拉 | `实测` |
| `getAreaPriceList` | 请求 `deliveryProviderId`（取自 R1） | 所选配送商 | `实测` |
| `getAreaPriceList` | `priceType`（6 种） | 价格类型 | 单体/连锁 × 周边/偏远/超偏远 |
| `getAreaPriceList` | `areaName` + `areaList[]` | 区域（查看） | 分组名 + 区域 `areaCode` 数组 |
| `getAreaPriceList` | `subType`（逗号分隔） | 适用药店类型 | 零售单体/第三终端/连锁总部（批零一体）/连锁总部（纯连锁）/连锁加盟/商业公司 |
