# 数据（板块索引）

> **板块归属（板块内单独说明 · 混合）**：对应自营「数据」/ 摇钱树「统计分析」，**按子板块分**：
> - `api_品种分析.md`、`api_销售报表.md` ＝ **① 通用**（两账号同源，用户 2026-11-13 确认）；
> - `api_店铺流量.md` ＝ **③ 仅自营**。
> 归属唯一事实源见 `references/sy.md §0.4`；Agent 按子板块路由，勿按板块名一刀切。
> 状态：**接口文档已交付，CLI 暂未开放**（`python scm.py query --module data` 返回 `MODULE_TODO`）。取数用 `python scm.py call`（`AGENT_GUIDE.md §4.1`）按本文档构造请求。
> 本文是数据板块入口：子板块地图、端点清单、账号与请求约定、阅读顺序、边界。
> 路径基准：`references/…` 相对技能包根（本资产根）。

## 1. 子板块地图

### 1.1 品种分析（`api_品种分析.md`）· **① 通用**

| 子板块 | 文档 | 覆盖内容 |
|---|---|---|
| 销售详情 · 按品种统计 | `api_品种分析.md §2.2` | 主列表（`tab=0`）、单品基础数据、销售/购买趋势、趋势报表 |
| 销售详情 · 委托配送商品 | `§2.3` | 主列表（`tab=2`）、委托配送加购统计 |
| 售后详情 | `§2.4` | 售后列表、商品售后明细、售后曲线 |
| 字典与级联 | `§2.5` | 仓库/省份基础数据、多城市、售后原因、省市区级联 |
| 导出 | `§3` | 3 个 xlsx（主表 / 售后 / 加购） |

### 1.2 销售报表（`api_销售报表.md`）· **① 通用**

| 子板块 | 文档 | 覆盖内容 |
|---|---|---|
| 统计方式（6 种） | `api_销售报表.md §1` | 天/周/月/区域/活动类型 → 主表；药店 → 药店表 |
| 数据2 · 主表（天/周/月/区域/活动） | `§2.2` | 筛选、响应容器、11 列 / 活动类型 8 列 |
| 数据2 · 按药店统计 | `§2.3` | 12 列 + 分页（`count` 为总行数） |
| 数据1 · 维度图（10 个） | `§2.4` | 销售 6 + 优惠 3 + 退款 1；4 槽位结构 |
| 访客数据 | `§2.5` | `visitorDataChart`（不吃筛选） |
| 字典 | `§2.6` | `getSubType` / `getWarehouseList` / `getChildAreas` |
| 导出 | `§3` | 3 个同步 xlsx |

### 1.3 店铺流量（`api_店铺流量.md`）· **③ 仅自营**

| 子板块 | 文档 | 覆盖内容 |
|---|---|---|
| 三指标趋势 | `api_店铺流量.md §2.2` | `getFlowInfo`：按天/周/月 + 近8天/30天/3月/自定义 |
| 三指标汇总卡 | `§2.3` | `topExposureStat`：曝光/点击/访客 + 同比 |
| 下载数据 | `§3` | **无接口**（前端 SheetJS 本地生成 xlsx） |

### 1.4 未建文档的子板块（归属未判定）

服务评价 / 商品热榜 / 商品上升热榜 / 稀缺品榜单 / 店铺参谋 —— **仅登记端点**（`modules/data/GUIDE.md` #37~#48，共 12 个）。

其中「好价榜」3 个端点采集已带完整参数与响应，**但未建独立文档**：

| 端点 | 请求体 | 响应 |
|---|---|---|
| `saleReport/goodPriceList` | `{pageNo, pageSize, keyWord, tabId, idList[]}` | `{totalRecord, list[]}`（36 字段：`id/wholesaleType/wholesaleTypeName/drugId/cnName/pack/factory/provDrugCode/unitPrice1~9/orderNum/orderCash/...`） |
| `saleReport/goodPriceListTabNum` | 同上 | `{tabRecord0~tabRecord4}`（5 个 tab 计数） |
| `saleReport/goodPriceListExport` | 同上 | xlsx 文件流 |

## 2. 端点清单（有完整文档 36 / 全板块登记 48，全部 `POST`）

> 本节只列**有完整参数文档**的 36 个；另有 12 个仅登记（好价榜 3 + 同前缀看板 2 + 其余 7），见 `modules/data/GUIDE.md` #37~#48。

### 2.1 品种分析（16）

| # | 端点 | 用途 | 分类 |
|---|---|---|---|
| 1 | `/scm-goods/drugsStat/saleReportDrugsStatList` | 主列表（按品种 `tab=0` / 委托配送 `tab=2`） | 读取 |
| 2 | `/scm-goods/drugsStat/saleReportBuyCarStat` | 委托配送加购统计（按当前页 `drugIds`） | 读取 |
| 3 | `/scm-goods/drugsStat/getSaleReportBase` | 基础数据：仓库 + 省份 | 读取·字典 |
| 4 | `/scm-goods/drugsStat/getMultiCity` | 多城市列表 | 读取·字典 |
| 5 | `/scm-goods/drugsStat/statReportVisit` | 销售趋势（点击/访客） | 读取·趋势 |
| 6 | `/scm-goods/drugsStat/statReportMoney` | 购买趋势（金额/店数） | 读取·趋势 |
| 7 | `/scm-goods/drugsStat/statReportTrendData` | 趋势数据报表 | 读取·趋势 |
| 8 | `/scm-goods/drugsStat/getStatReportDetailBase` | 单品基础数据 | 读取·详情 |
| 9 | `/scm-goods/drugsStat/getDrugsStatList` | 售后详情列表 | 读取·售后 |
| 10 | `/scm-goods/drugsStat/getDrugAfterList` | 商品售后明细 | 读取·售后 |
| 11 | `/scm-goods/drugsStat/getDrugsStatReport` | 售后曲线 | 读取·售后 |
| 12 | `/scm-order/afterSaleBase/getReasonList` | 售后原因字典 | 读取·字典 |
| 13 | `/scm-order/afterSaleBase/getChildAreas` | 省→市→区级联 | 读取·字典 |
| 14 | `/scm-goods/drugsStat/exportSaleReportDrugsStat` | 主表导出（xlsx） | 导出 |
| 15 | `/scm-goods/drugsStat/exportDrugsStatList` | 售后详情导出（xlsx） | 导出 |
| 16 | `/scm-goods/drugsStat/exportBuyCarStat` | 加购导出（xlsx） | 导出 |

### 2.2 销售报表（18）

| # | 端点 | 用途 | 分类 |
|---|---|---|---|
| 17 | `/scm-goods/saleReport/suppliersDateMonthWeekAreaActivity` | 数据2·主表（5 种统计方式） | 读取 |
| 18 | `/scm-goods/saleReport/suppliersDrugstoreTable` | 数据2·按药店表 | 读取 |
| 19 | `/scm-goods/saleReport/suppliersTotalAmount` | 维度图·销售总额 | 读取·图表 |
| 20 | `/scm-goods/saleReport/suppliersNetPurchase` | 维度图·净销售总额 | 读取·图表 |
| 21 | `/scm-goods/saleReport/suppliersSalesOrder` | 维度图·订单数 | 读取·图表 |
| 22 | `/scm-goods/saleReport/suppliersPStore` | 维度图·采购药店数 | 读取·图表 |
| 23 | `/scm-goods/saleReport/suppliersNewPStore` | 维度图·新增采购药店数 | 读取·图表 |
| 24 | `/scm-goods/saleReport/suppliersDrugNum` | 维度图·动销品种数 | 读取·图表 |
| 25 | `/scm-goods/saleReport/suppliersPlatformDiscountAmount` | 维度图·专享补贴金额 | 读取·图表 |
| 26 | `/scm-goods/saleReport/suppliersTotalCouponsAmount` | 维度图·商家优惠券金额 | 读取·图表 |
| 27 | `/scm-goods/saleReport/suppliersCouponsNum` | 维度图·商家优惠券数量 | 读取·图表 |
| 28 | `/scm-goods/saleReport/suppliersRefundAmount` | 维度图·客户退款金额 | 读取·图表 |
| 29 | `/scm-goods/saleReport/visitorDataChart` | 访客数据图表 | 读取 |
| 30 | `/scm-goods/saleReport/getSubType` | 活动类型/药店类型字典 | 读取·字典 |
| 31 | `/scm-goods/provider/getWarehouseList` | 分仓字典（**非 saleReport 前缀**） | 读取·字典 |
| 32 | `/scm-goods/saleReport/suppliersDateMonthWeekAreaActivityExport` | 主表导出（xlsx） | 导出 |
| 33 | `/scm-goods/saleReport/suppliersDrugstoreTableExport` | 按药店导出（xlsx） | 导出 |
| 34 | `/scm-goods/saleReport/exportVisitorData` | 访客数据导出（xlsx） | 导出 |

### 2.3 店铺流量（2）

| # | 端点 | 用途 | 分类 |
|---|---|---|---|
| 35 | `/scm-setting/flow/getFlowInfo` | 三指标趋势（按天/周/月） | 读取 |
| 36 | `/scm-base/saleReport/topExposureStat` | 三指标汇总卡 + 同比 | 读取 |

> **36** ＝有完整参数文档的端点数；`modules/data/__init__.py` 的 `ENDPOINTS` 共 **48**（含 12 个仅登记端点），由 `tests/selftest.py` 校验 48=48。
> 本板块**无写接口**（纯统计查询）。导出产物为服务端生成的文件流，属读取行为；**店铺流量例外**——「下载数据」是前端本地生成，无服务端导出接口（见 `api_店铺流量.md §3`）。

## 3. 使用约定

1. **请求形态**：`POST`，`Content-Type: application/json;charset=UTF-8`（**必须带 `;charset=UTF-8`**，漏写网关报 `40002`）。
2. **公共参数**（每个请求都带）：`token`/`platform`/`version`/`ua`/`ex`/`lastBuildTime`。`ex` 按子板块取：品种分析 `ProductAnalysis`、销售报表 `NewSaleReportNested`、店铺流量 `StoreTraffic`（`call --ex <值>`）。
3. **`ex` 按子板块取**：品种分析 `ProductAnalysis`（主表/趋势）、`AfterSaleDetail`（售后明细）；销售报表 `NewSaleReportNested`。
4. **⚠️ 时间格式两个子板块不同**：
   - 品种分析：`dateRange` 字符串数组（主表带 `HH:mm:ss`、趋势纯日期）
   - 销售报表：`startTime`/`endTime` **Unix 秒时间戳**
5. **鉴权**：会话 cookie + body `token`；复用 `core.credential` 凭证，见 `references/通用/api_认证与公共约定.md`。
6. **成功码**：`40001`；`40002` 业务/参数校验失败（含瞬态限流，可间隔重试）；`40004` 参数异常。
7. **分页**：品种分析主表 `data.results[]` + `totalRecord`；销售报表主表 `data.dateMonthWeekList[]` + `count`、按药店 `data.list[]` + `count`。**两者容器名不同，勿套用**。

## 4. 阅读顺序

1. 本文 §1 选子板块 → 进 `api_品种分析.md` 或 `api_销售报表.md` 对应小节；
2. 字段名不确定 → `zddz.md`（筛选/返回/枚举对照）；
3. 鉴权与公共参数 → `references/通用/api_认证与公共约定.md`；
4. 端点在附录的位置 → `references/附录/接口总表.md`。

## 5. 边界与待确认

| # | 项 | 现状 |
|---|---|---|
| 1 | 摇钱树「统计分析」同名子项 | **已确认通用**（用户 2026-11-13）：品种分析、销售报表两账号同源；**店铺流量不在摇钱树地图内（自营专属）** |
| 2 | `province`/`city`/`district` 形态 | 品种分析导出实测为**省码数字数组**；参考文档曾记为字符串。列表接口未实采 → 首次按数组，`40002` 再退字符串（见 `api_品种分析.md §5`） |
| 3 | 品种分析趋势 `dateRange` | 实测**纯日期** `["YYYY-MM-DD","YYYY-MM-DD"]`，与列表/导出带时刻不同 |
| 4 | `stockBalance` 品种库存 | 可能为 `"-"`，解析按数值兜底 |
| 5 | 品种分析列表封顶 | `saleReportDrugsStatList` 实测 `totalRecord=3000` 触顶；导出同样上限 |
| 6 | 销售报表 `ACTIVITY` 模式字段 | 抓包未触发（`activityList` 为空），`activityList[]` 字段取自参考文档源码列定义；首次使用先跑一次核对 |
| 7 | 销售报表维度图槽位 | 非统一结构：常规 5 指标给 `totalData`+`list`，`NewPStore` 只给 `newStoreData`，优惠/退款只给 `totalData`；`instrumentData` 本次全 `null` |
| 8 | 店铺流量「下载数据」 | **无服务端导出接口**（前端 SheetJS 生成 xlsx）；自动化请用 `getFlowInfo` 结果自行落盘 |
| 9 | 店铺流量自定义时间 | `rangeFlag=4` + `startTime`/`endTime` **纯日期 `YYYY-MM-DD`**（带时分报 `40002`）；`key` 按天是 8 位 `YYYYMMDD`（`20261014`），非带横线格式 |
