# 委托配送商品（API）

> 子板块：商品 → **委托配送商品**（页面 `#/commodity-management/goods-consignment`）。
> 公共参数/鉴权见 `references/通用/api_认证与公共约定.md`；字段/值域见 `references/商品/zddz.md §8`。
> 所有接口 `ex:"ConsignedGoods"`。板块索引见 `references/商品/sy.md`；账号/板块归属见 `references/sy.md §0`。
> **账号归属：③ 仅自营**（权威判定见 `references/sy.md §0.4`；本子板块为自营账号体系专属，摇钱树账号不调用）


## 1. 接口总表

| # | 接口 | 用途 | 参数 | 返回 |
|---|---|---|---|---|
| 1 | `POST /scm-goods/saleOthers/agentWholesaleList` | 委托配送商品列表 | 见 §2 | 分页 `data.{results[], totalRecord, ...}` |
| 2 | `POST /scm-goods/saleOthers/agentWholesaleExport` | 列表导出 | 同 §2 | 触发导出 |
| 3 | `POST /scm-goods/saleOthers/exportJqbWsInfo` | 导出极速达/批购信息 | 同 §2 | 触发导出 |
| 4 | `POST /scm-goods/saleOthers/setDeliveryOrder` | 设为配送单（推荐至配送平台） | 见 §4 | `code/msg` |
| 5 | `POST /scm-goods/saleOthers/changeDeliverAlone` | 改独立配送 | `deliverAlone`, `wholesaleId` | `code/msg` |
| 6 | `POST /scm-goods/saleOthers/changeDrugCode` | 改药品编码 | `provDrugCode`, `wholesaleId` | `code/msg` |
| 7 | `POST /scm-goods/saleOthers/checkDrugCode` | 校验药品编码 | `provDrugCode`, `wholesaleId` | `code/msg` |
| 8 | `POST /scm-goods/saleOthers/changeProvDrugFactor` | 改供应商药品系数 | `provDrugFactor`, `wholesaleId` | `code/msg` |
| 9 | `POST /scm-goods/saleOthers/getAgentWholesalePromotion` | 查推广信息 | `wholesaleId` 等 | 推广数据 |
| 10 | `POST /scm-goods/saleOthers/getStoreOpType` | 查门店运营类型 | 公共参数 | 类型数据 |
| 11 | `POST /scm-goods/saleOthers/listDrugProvider` | 供应商列表 | 公共参数 | 供应商列表 |

## 2. 列表筛选参数（浏览器实测 2026-11-12）

> **实测方法**：Playwright 驱动系统 Edge，直接进 `#/commodity-management/goods-consignment`，对 14 个 `search-item` **逐字段设值→点搜索→抓 `agentWholesaleList` 请求体**，用相邻差集去累积后锁定 label↔param；再逐个打开下拉枚举全部选项标签、监听字典接口判定动态/静态、抽样选值读提交值。脚本 `过程区/账号权限实测/weituo_live.py`/`weituo_iso.py`/`weituo_recover.py`/`weituo_dynvals.py`，结果 `weituo_mapping_clean.json`/`weituo_dynvals.json`。本次实测覆盖查询与导出。
> 端点：`POST /scm-goods/saleOthers/agentWholesaleList`；`ex:"ConsignedGoods"`；分页用 **`pageNo`+`pageSize`**（与订单列表 `page`+`pagesize` 不同）。响应 `data={pageNo,pageSize,totalRecord,totalPage,results[]}`（实测 `totalRecord=10000`）。

### 2.1 界面字段 ↔ 请求参数（全 14 项，实测）

| 界面字段 | 请求参数 | 控件 | 选项 → 提交值（实测） |
|---|---|---|---|
| 商品 | `drugId` | 文本框 | — |
| 活动ID | `wholesaleId` | 文本框 | — |
| 厂家 | `factory` | 文本框 | — |
| 商品编码 | `drugCode` | 文本框 | — |
| 摇钱树联络人ID | `cashcowProviderId` | 文本框 | —（配套 `cashcowProviderName`） |
| 已推荐到列表 | `wholesaleRecommend` | 下拉 | 已推荐=`1`、未推荐=`0`（静态） |
| 活动类型 | `wholesaleType` | 下拉 | 一口价/秒杀/折扣活动/不可用券/限时特价(可用商家券)/限时特价(不可用商家券)/拼团/批购包邮/乐药分销/赠品（静态，样本值 `3`） |
| 销售类型 | `saleType` | 下拉 | 单品销售/套餐销售（静态，样本 `1`） |
| 供货对象 | `provObject` | 下拉 | 全部供应/连锁/非连锁（静态，样本 `3`） |
| 促销类型 | `promotionType` | 下拉 | 全部/新品/特价/套餐（静态，样本 `2`） |
| 委托方 | `providerId` | 下拉 | 全部/【无效】神威直营/广康直营/复盛公直营/明瑞直营/益佰控销/摇钱树4608/4611/4612/山西鸿茅…（**动态字典** `listDrugProvider`，样本 `4350`） |
| 乐药特推 | （隐藏字段，未提交） | hidden | 界面存在但本次未产生独立参数 |
| 活动状态 | `status` | 下拉（数组） | 缺货下架/进行中/未启动/已结束/审核不通过（不可再次申请）/审核不通过（可再次申请）/资质待审核/未上架（静态，样本 `[100]`） |
| 主题 | `promotionTypeId` | 下拉（数组） | 摇钱树自动上架拼团（同步一口价）/摇钱树拼团/摇钱树周末拼团/补贴自动生成拼团/摇钱树夜间拼团/…（**动态字典** `getAgentWholesalePromotion`，样本 `[3783]`） |

**动态/静态判定**：页面**初始加载**即拉取 `listDrugProvider`（委托方）、`getAgentWholesalePromotion`（主题）、`getStoreOpType`、`getDeliverAlones` 等字典接口；因此这两个下拉是**动态**（选项来自接口，随数据变化），但**打开下拉时不再发请求**（选项已预取）。其余 6 个下拉 `dynOpen=False` = 前端静态硬编码。`status`/`promotionTypeId` 为数组，`wholesaleRecommend`/`wholesaleType`/`saleType`/`provObject`/`promotionType`/`providerId` 为标量。

### 2.2 完整请求体（实测业务参数）

```json
{"drugId":"","factory":"","drugCode":"","promotionType":"","providerId":"",
 "cashcowProviderName":"","cashcowProviderId":"","providerType":[],"status":[],
 "promotionTypeId":[],"pageNo":1,"pageSize":10,
 "token":"…","platform":"scm-admin","version":"1.0.3","ua":"…",
 "ex":"ConsignedGoods","lastBuildTime":"2026-11-09 20:28"}
```

> 另有 `wholesaleId`/`wholesaleRecommend`/`wholesaleType`/`saleType`/`provObject` 等仅在使用对应筛选时出现（上面是初始值样本）。`providerType` 亦为数组参数。

## 3. 返回字段（实测 150 个，全量见 `过程区/账号权限实测/weituo_returned_fields.json`）

> 抓真实 `agentWholesaleList` 响应，返回行 **150 字段**（`totalRecord=10000`）。表头实测 15 列：`''`(展开) / ID / 类型 / 商品信息 / 商品管理 / app显示名称 / 销售价格 / 业务商圈 / 采购 / 排序 / 活动状态 / 库存 / 近30天总销量 / 剩余库存天数 / 详情。全量键名（`过程区/账号权限实测/weituo_returned_fields.json`）：

| 分组 | 字段（全量） |
|---|---|
| 商品标识 | `id` `wholesaleName` `fullName` `drugId` `cnName` `commonName` `drugName` `drugNamePrefix` `factory` `brand` `pack` `specification` `drugCode` `dnPrefix` `dnSuffix` `unit` `munit` `unitAmt` `midPack` `wholePack` `approval` `prodPlace` `prodDate` `validDate` `imageUrl` `imageTitle` `imageJump` `logo` `blogo` `detail` `descExt` |
| 委托配送标识 | `recommendToDp` `dpOrder` `deliverAlone`/`deliverAloneStr` `provDrugFactor` `deliverType`/`deliverTypeStr` `deliveryProviderId` `whName` `warehouseCode` |
| 价格 | `recommendPrice` `unitPrice` `currentPrice` `oldPrice` `chainPrice` `disPrice` `bottomPriceDesc` `bottomPriceUrl` `unitPrice1`~`unitPrice9` |
| 状态 | `status` `statusName` `state` `approval` `stockAvailable` `stockFlag` `preOver` `preSaleType` `haveInvoice` `isRestrict`/`isRestrictStr` `hideDisPrice` `hideSaleAmt` `timeLimitsOn` |
| 统计 | `orderNum` `orderAmount` `totalamount` `totalCost` `monthWs` `daysStockTogo` `paidOrders` `paidAmount` `salePerday` `initAmount` `order` `topOrder` `globalOrder` `recommendOrder` |
| 推荐/置顶 | `isRecommend` `recommendOrder` `isTop`/`isTopName` `isCashCow` `isRecommend` |
| 活动/促销 | `wholesaleType`/`wholesaleTypeNum`/`wholesaleTypeStr` `wholesaleId`→`id` `promotionType` `promotionTitle` `eventId` `minAmount` `maxAmount` `minCnt` `maxAmountPerStore` `maxAmountPerUser` `step` `disType`/`disTypeName` `calculateBeginDate` `calculateOrgDate` `calculatePeriod`/`calculatePeriodStr` `beginDate` `endDate` `ctime`/`ctimeStr` `mtime`/`mtimeTimestamp` `rushBeginDate` `rushEndDate` |
| 分组/品类/商圈 | `areaGroupId` `groupName` `storetypeGpId` `storetype` `storeTypeExport` `busiScope`/`busiScopeStr` `virtualType` `specClsType` `clinicType` `restrictGroupId`/`restrictGroupIdStr` `wsdrugasktypeId`/`wsdrugasktypeIdStr` `sgpId` |
| 供应商/合作 | `providerId` `providerName` `providerType` `cashcowProviderId` `cashcowProviderName` `partnerType`/`partnerTypeName` `saleType` `provObject` `manualSyncPrice` `manualSyncStock` `returnAdmin` `returnTime` `tax` `wsDesc` |
| 广告 | `pushAdTitle` `pushAdUrl` `pushAdJump` |

## 4. 写操作

### 4.1 设为配送单 `setDeliveryOrder`

```json
{ "dpOrder": 2000, "recommendToDp": 1, "wholesaleIdList": [1454073284] }
```
- `dpOrder`：配送端展示排序值。
- `recommendToDp`：`1`=推荐至配送平台（委托配送），`0`=否。
- `wholesaleIdList`：商品 ID 列表。

### 4.2 改独立配送 `changeDeliverAlone`

```json
{ "deliverAlone": 0, "wholesaleId": 1454073284 }
```
- `deliverAlone`：`0`/1（是否独立配送）。

### 4.3 改/校验药品编码 `changeDrugCode` / `checkDrugCode`

```json
{ "provDrugCode": "SP0013061-50", "wholesaleId": 1454073284 }
```

### 4.4 改供应商药品系数 `changeProvDrugFactor`

```json
{ "provDrugFactor": 1, "wholesaleId": 1454073284 }
```

> 本节为采集样本端点记录；实际能否调用由账号的系统权限与 `AGENT_GUIDE.md §10` 授权决定，账号/板块归属见 `references/sy.md §0`。

## 5. 导出（浏览器实测 2026-11-12）

页面有 2 个导出按钮：**「导 出」**（主导出）与**「导出业务商品」**（`exportJqbWsInfo`）。主导出交互实测：

1. 点「导 出」→ 弹 **确认框**「确定要导出吗？」（按钮 `取 消` / `确 定`）——**只点「导 出」不发请求**，需再点「确 定」。
2. 点「确 定」→ 发 `POST /scm-goods/saleOthers/agentWholesaleExport`，请求体 = 当前全部筛选参数 + 额外 `handleList:[]`（选中行 ID 列表，空=按筛选全量导出）：

```json
{"drugId":"","wholesaleId":"","factory":"","drugCode":"","providerId":"",
 "cashcowProviderName":"","cashcowProviderId":"","providerType":[],"status":[],
 "promotionTypeId":[],"pageNo":1,"pageSize":10,"handleList":[],
 "token":"…","platform":"scm-admin","version":"1.0.3","ua":"…",
 "ex":"ConsignedGoods","lastBuildTime":"…"}
```

3. **异步导出**：点确定后**不直接触发浏览器下载**，走后台导出任务（通用导出中心/下载列表取文件），与《通用导出列表》异步口径一致。脚本 `过程区/账号权限实测/weituo_export2.py`，结果 `weituo_export_final.json`。

## 6. 限制

- 本子板块为**商品委托配送管理**（与订单板块的「配送完成」页签无直接参数耦合）。
- 写操作按 `AGENT_GUIDE.md §10` 授权；账号/板块归属见 `references/sy.md §0`。
- 返回行含 150 字段，按需取用；全量键名见 §3 与 `过程区/账号权限实测/weituo_returned_fields.json`。
- 筛选项「委托方」「主题」为动态字典（页面加载时预取），选项值随账号/数据变化，勿硬编码。

---

## 7. 本次实测覆盖度小结（2026-11-12）

| 项目 | 订单列表 | 商品-委托配送 |
|---|---|---|
| 页面路由 | `#/all-orders` | `#/commodity-management/goods-consignment` |
| 列表端点 | `/scm-order/wholesaleOrder/list` | `/scm-goods/saleOthers/agentWholesaleList` |
| 筛选字段 | 35（参数名全实测，`zddz.md §1.3`） | 14（参数名全实测，§2.1） |
| 下拉选项值 | 25 下拉逐选项实测（`zddz.md §9`） | 8 下拉实测（§2.1） |
| 动态/静态 | 仅「订单类型」动态，余 24 静态 | 「委托方」「主题」动态（预取），余 6 静态 |
| 返回字段 | 177 顶层 + 53 `orderDetails`（`zddz.md §10`） | 150（§3） |
| 表头 | 8 列 | 15 列 |
| 导出 | （订单导出见 `api_订单导出.md`） | `agentWholesaleExport` 确认框→异步（§5） |
| 写操作 | 未测 | 未测（§4 仅采集样本） |
