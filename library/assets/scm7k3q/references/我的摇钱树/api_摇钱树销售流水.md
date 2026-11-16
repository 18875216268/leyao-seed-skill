# 摇钱树销售流水（API）

> 子板块：我的摇钱树 → **摇钱树销售流水**（页面 `#/my-cashcow-management/sale-log`，菜单 menuId 966）。
> **账号归属：② 仅摇钱树**（自营账号无此子板块，越界不调用；归属唯一事实源 `references/sy.md §0.4`）。
> 请求约定见 `sy.md §3`：`POST` + JSON；**`ex` = `MyCashcowSaleLog`**（实测 2026-11-16 抓包确证，非空串）。
> 参数与字段来自真实抓包：采集 2026-11-16（登录摇钱树账号，只读导航 + 导出触发，零业务影响），列表/计数/级联/导出 4 接口业务码均 `40001` 可达。

## 1. 总览

| 界面 | 后端 | 说明 |
|---|---|---|
| 销售流水列表（分页 + 状态页签） | `saleLogsAct` | 主列表；`data.tabStatus` 为 9 态文案字典 |
| 计数 / 统计 | `saleLogsCountAct` | 与列表同参；实测返回 `int` 总数 |
| 区域筛选（省市区级联） | `areaGroup/getAreaCodeWithoutLimit` | 三级级联字典（`level`/`maxLevel`/`parentCode`） |
| 导出 xlsx | **`exportSaleLogsAct`** | 服务端文件流（✅ 本次实测捕获） |

> 流水/计数/导出在 `/scm-setting/cashcoworder/`，级联在 `/scm-goods/areaGroup/`（**跨前缀**，勿只搜一个前缀）。

---

## 2. 读取

### 2.1 读取接口总表

| # | 接口 | 用途 | 业务参数 |
|---|---|---|---|
| R1 | `POST /scm-setting/cashcoworder/saleLogsAct` | 销售流水列表 | 12 个（§2.2） |
| R2 | `POST /scm-setting/cashcoworder/saleLogsCountAct` | 计数/统计 | 与 R1 相同 |
| R3 | `POST /scm-goods/areaGroup/getAreaCodeWithoutLimit` | 省市区级联 | 3 个（§2.6） |

### 2.2 R1 销售流水列表 `saleLogsAct`

**实测请求体**（2026-11-16，筛选「近 7 天」）：

```json
{
  "pageNo": 1, "pageSize": 10,
  "cnName": "", "compCode": "", "provider": "", "deliveryProvider": [],
  "orderStatus": null, "provDrugCode": "", "storeName": "",
  "province": [], "city": [], "district": [],
  "startPayTime": 1794240000, "endPayTime": 1794844799,
  "ex": "MyCashcowSaleLog"
}
```

**业务参数**（12 个，均为空/默认时前端仍发送）：

| 界面筛选项 | 参数 | 类型 | 说明 |
|---|---|---|---|
| 商品名称 | `cnName` | string | 空串为不筛 |
| 药店 | `storeName` | string | 店铺名称 |
| 供应商 | `provider` | string | — |
| 配送商 | `deliveryProvider` | **array** | 配送商数组（空 `[]` 为不筛） |
| 商品编码 | `provDrugCode` | string | 药品/商品编码 |
| 本公司编码 | `compCode` | string | 企业编码 |
| 订单状态 | `orderStatus` | int\|null | 实测默认 `null`；取值见 §4 |
| 下单付款时间起 | `startPayTime` | int | **Unix 秒时间戳**（实测 `1794240000`） |
| 下单付款时间止 | `endPayTime` | int | **Unix 秒时间戳**（实测 `1794844799`） |
| 区域·省 | `province` | **array** | 省 `areaCode` 数组（R3 取值） |
| 区域·市 | `city` | **array** | 市 `areaCode` 数组 |
| 区域·区县 | `district` | **array** | 区县 `areaCode` 数组 |

> ⚠️ **列表接口 vs 导出接口的筛选集不同**：列表含「下单付款时间」（`startPayTime`/`endPayTime`），实测**不含** `orderId`/`wholesaleId`/`drugId`；导出接口（§3）恰相反——含这三个 id、**不含**时间。页面筛选项为**二者并集**（见 §2.4）。

分页：`pageNo`（从 1 起）/ `pageSize`。

### 2.3 R1 响应结构

`data` 顶层：

| 字段 | 含义 |
|---|---|
| `data` | 流水行数组（见下表） |
| `tabStatus` | **状态文案字典**（键 `1`~`9` → 中文，页签渲染用，见 §4） |
| `isCashcow` | 是否摇钱树数据标记 |
| `deliverProvider` | 顶层附带的配送商字段（用途待确证） |

流水行字段（实测 60 字段）：

| 界面结果项 | 字段 | 实测样例/说明 |
|---|---|---|
| 订单id | `orderId` | `806407058`；另有 `odId`（内部单 id） |
| 时间·支付 | `payTime` / `payTimeStr` | Unix 秒 / 展示串（`payTimeStr` 实测为 null） |
| 时间·出库 | `deliverTime` / `deliverTimeStr` | 可为 null（未出库） |
| 时间·退款 | `refundTime` / `refundTimeStr` | `0` = 无退款 |
| 订单状态 | `orderStatusDesc` / `processStatus` / `status` | 文案 `orderStatusDesc`（如「正在开单」）；`status`/`processStatus` 为码值，与文案映射待确证（§5） |
| 结算 | `clearStatus` / `clearStatusDesc` / `clearPrice` / `clearMoney` / `clearTime` / `clearTimeStr` | `clearStatus=0`→「未结算」；`clearPrice`=定价（结算价）、`clearMoney`=结算金额 |
| 成交单价 | `dealUnitPrice` | `16.0` |
| 采购数量 | `amount` | `20.0` |
| 商品信息 | `cnName` / `specification` / `factoryName` / `approval` / `pack` | 商品名称 / 规格 / 厂家 / 国药准字 / 包装 |
| id 组 | `provDrugCode` / `drugId` / `compCode` / `wholesaleId` / `wsParentid` | 商品编码 / 药品id / 本公司编码 / 活动id / 父活动（0=无） |
| 药店与区域 | `storetitle` / `storeId` / `drugstoreBranchId` / `province` / `city` / `district` / `areaCode` / `areaId` | 区域为**中文字符串**（如「湖南省/常德市/石门县」），与筛选用 code 不同 |
| 供应商 | `erpProviderName` / `drugProviderId` / `wsProviderId` / `providerId` | 药品供应商（如「摇钱树22796」）；`providerId` 实为配送商 id |
| 配送商 | `deliverProviderName` | 如「央拓医药」 |
| 来源 | `op` | **实测「交易」**（字典见 §4） |
| 活动类型 | `wholesaleType` / `wholesaleTypeDesc` | `7` → **「药惠拼（拼团）」**（字典见 §4） |
| 签收单 | `autographUrl` | URL 或空串 |
| 退款id | `refundId` | `0` = 无 |

> 「特价不可用券」：用户口径存在、实测 60 字段**仍未见直接对应字段**（可能为活动类型派生展示）；勿映射到 `wholesaleType`。

### 2.4 页面筛选项 ↔ 接口参数对照（完整性核对）

| 用户描述筛选项 | 参数 | 所在接口 |
|---|---|---|
| 订单状态 | `orderStatus` | 列表 + 导出 |
| **订单id** | `orderId` | **导出**（列表未发送） |
| 药店 | `storeName` | 列表 + 导出 |
| 供应商 | `provider` | 列表 + 导出 |
| 商品名称 | `cnName` | 列表 + 导出 |
| 下单付款时间 | `startPayTime`/`endPayTime` | **列表**（导出未发送） |
| **活动id** | `wholesaleId` | **导出**（列表未发送） |
| **药品id** | `drugId` | **导出**（列表未发送） |
| 商品编码 | `provDrugCode` | 列表 + 导出 |
| 本公司编码 | `compCode` | 列表 + 导出 |
| 区域（省市区级联） | `province`/`city`/`district` | 列表 + 导出 |
| 配送商 | `deliveryProvider` | 列表 + 导出 |

> 12 项筛选项全部落实；`orderId`/`wholesaleId`/`drugId` 在列表接口未实测出现，首次按列表筛选这三个时若 `40002` 或无效，改用导出接口形态或补实测。

### 2.5 R2 计数 `saleLogsCountAct`

- 请求参数与 R1 **完全相同**；
- 实测返回 `data` 为 **`int`**（样本 `768`）——即当前筛选条件下的总条数；
- 用途：页签计数 / 总数校验。

### 2.6 R3 省市区级联 `getAreaCodeWithoutLimit`

**实测请求体**：`{"level": 0, "maxLevel": 3, "parentCode": 0}`（`ex` = `MyCashcowSaleLog`）

| 参数 | 说明 |
|---|---|
| `level` | 起始层级（实测 `0` = 从省开始） |
| `maxLevel` | 最大层级（实测 `3`） |
| `parentCode` | 上级区域编码（实测 `0` = 顶级；展开下级时传上级 `areaCode`，如 `13` → 河北省各市 `1301`…） |

响应 `data` 为数组，元素：`{areaCode, areaName, leaf, areaCodeMap}`：

- `areaCode`：**数字**（如 `11`=北京市、`13`=河北省、`3101`=上海市、`1301`=石家庄市）；港澳台亦有码（`81` 香港、`71` 台湾）
- `areaName`：中文名
- `leaf`：是否末级（省/市实测 `false`）
- `areaCodeMap`：映射（实测空对象）

> ✅ 修正旧结论：旧逆向 xlsx 记本接口实测 `40002`「缺数据」，实际是**参数形态未对**；带 `level=0, maxLevel=3, parentCode=0` 后实测 `40001` 正常返回省列表。筛选用 `province`/`city`/`district` 即传对应层级的 `areaCode`（数字）。

---

## 3. 导出 `exportSaleLogsAct`（✅ 实测捕获，服务端文件流）

| 项 | 值 |
|---|---|
| 端点 | `POST /scm-setting/cashcoworder/exportSaleLogsAct` |
| `ex` | `MyCashcowSaleLog` |
| 响应 | **二进制文件流（xlsx）**，HTTP 200；`scm.py call --out <文件>` 落盘 |

**实测请求体**（注意与列表的差异）：

```json
{
  "pageNo": 1, "pageSize": 10,
  "cnName": "", "compCode": "", "provider": "", "deliveryProvider": [],
  "drugId": "", "orderId": "", "orderStatus": null, "provDrugCode": "",
  "storeName": "", "wholesaleId": "", "province": [], "city": [], "district": [],
  "ex": "MyCashcowSaleLog"
}
```

> 导出体比列表体多 `drugId`/`orderId`/`wholesaleId`，少 `startPayTime`/`endPayTime`（详见 §2.4 对照）。导出结果 = 当前搜索条件的 xlsx，与用户描述一致。

---

## 4. 字典（实测确证）

### 4.1 状态字典 `tabStatus`（9 态）

| 码 | 文案 | 码 | 文案 |
|---|---|---|---|
| 1 | 待处理 | 6 | 配送中 |
| 2 | 正在开单 | 7 | 配送异常 |
| 3 | 审核资质 | 8 | 配送完成 |
| 4 | 分拣中 | 9 | 整单退款 |
| 5 | 待配送 | | |

### 4.2 活动类型 `wholesaleType`（实测样本）

| 码 | 文案 | 来源 |
|---|---|---|
| 7 | 药惠拼（拼团） | `wholesaleTypeDesc` 实测 |

> 其余码值待实测积累；解析以 `wholesaleTypeDesc` 展示为准。

### 4.3 结算状态 `clearStatus`

| 码 | 文案 | 来源 |
|---|---|---|
| 0 | 未结算 | `clearStatusDesc` 实测 |

### 4.4 来源 `op`

实测样本 `op="交易"`；完整枚举待积累。

### 4.5 `orderStatus` 筛选入参

实测默认 `null`（不筛）；码值枚举待实测（页签用 `tabStatus` 文案，筛选入参码值未确证）。

---

## 5. 已知坑与待确认

1. **`ex` 必须传 `MyCashcowSaleLog`**：默认 `goodsOnShelves`、旧结论「空串」均不正确（实测确证）。
2. **两个接口筛选集不同**：列表带时间不带 id；导出带 id 不带时间——用对应接口的实测 body 构造，勿混。
3. **数组参数**：`deliveryProvider`/`province`/`city`/`district` 都是**数组**（`--param 'province=[43]'`）；区域传 `areaCode` 数字。
4. **时间戳**：`startPayTime`/`endPayTime` 是 **Unix 秒**（非字符串日期）。
5. **区域返回是中文、筛选传 code**：行里 `province`/`city`/`district` 是中文名，筛选入参是数字 `areaCode`，不通用。
6. **`orderStatusDesc` 与 `status`/`processStatus` 映射未确证**：实测样本 `status=1, processStatus=3, orderStatusDesc="正在开单"`，与 `tabStatus` 键值非一一对应；解析以 `orderStatusDesc` 文案为准。
7. **「特价不可用券」无直接字段**：勿臆造映射。
8. **仅摇钱树账号可达**：自营凭证会因体系隔离失败；先 `status` 确认账号归属。
9. **`pageSize` 上限未实测**：默认 10；导出用 `pageSize` 未实测是否影响导出范围（建议导出仅传筛选、不依赖分页，以实测为准）。
