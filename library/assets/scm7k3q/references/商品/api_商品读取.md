# 商品读取（API）

> 账号判定见 `sy.md §3.2`；写操作红线见 `sy.md §3.4`；字段/复验见 `zddz.md`。板块/文档归属见 `references/sy.md §0`。

## 1. 读取

### 1.1 接口总表

| # | 功能 | 方法 | 路径 | 适用 | 必需参数 | 返回要点 |
|---|---|---|---|---|---|---|
| 1.1 | 活动列表 | POST | `/scm-goods/wholesaleDrug/wsList` | 通用 | `pageNo` `pageSize` | `data.results[]`（215 字段）+ `totalRecord/pageNo/totalPage` |
| 1.2 | 状态页签计数 | POST | `/scm-goods/wholesaleDrug/wsListCount` | 通用 | 同 wsList | `[{wsStatus,count}]`（9 状态） |
| 1.3 | 第二排统计 | POST | `/scm-goods/wholesaleDrug/wsStatistic` | 通用 | 公共参数 + `status` | 15 计数字段 |
| 1.4 | 统计（备用） | POST | `/scm-goods/wholesaleDrug/tiWsStatistic` | 通用 | 公共参数 + `status` | `{"onShelfByAdminCount":0}`（仅 1 字段） |
| 1.5 | 淘宝/特殊计数 | POST | `/scm-goods/wholesaleDrug/wsListTsbCount` | 通用 | 公共参数 | `{"34":0,"36":0,"37":0}` 字典 |
| 1.6 | 价格过低计数 | POST | `/scm-goods/wholesaleDrug/priceTooLowCount` | 通用 | 公共参数 + `status` | `data`=数字 |
| 1.7 | 价格过高计数 | POST | `/scm-goods/wholesaleDrug/priceTooHighCount` | 通用 | 公共参数 + `status` | `data`=数字 |
| 1.8 | 价格过高修正计数 | POST | `/scm-goods/wholesaleDrug/fixPriceTooHighCount` | 通用 | 公共参数 + `status` | `data`=数字 |
| 1.9 | 滞销计数 | POST | `/scm-goods/wholesaleDrug/unsalableCount` | 通用 | 公共参数 + `status` | `data`=数字 |
| 1.10 | 单条详情 | POST | `/scm-goods/wholesaleDrug/getWholesale` | 通用 | `wholesaleId` | `data.wholesaleInfo`（217 字段）、`data.drugInfo` |
| 1.11 | 采购明细 | POST | `/scm-order/wholesaleOrder/wholesaleDetail` | 通用 | `wholesaleId` `page` `pagesize` | `results[]` |
| 1.12 | 采购明细导出 | POST | `/scm-order/wholesaleOrder/exportWholesaleDetail` | 通用 | `wholesaleId` | **直接 XLSX 文件流**，固定 8 列 |

> `wsList` 别名 `/scm-goods/WholesaleDrugES2/wsList`。**返回取 `data.results`**，不是 `list`/`records`。

### 1.2 `wsList` 请求参数

**基础骨架**（通用，实测）：

```json
{ "pageNo":1, "pageSize":20, "searchInfo":"", "status":-1,
  "wholesaleType":[], "notThroughStatus":0, "saleStatType":1 }
```

- `pageNo` 从 1；`pageSize` 上限 100。
- `searchInfo`：综合匹配 **活动ID / 商品编码 / 商品名称 / 批准文号 / 商品ID / app名称 / 厂家 / 活动备注**；空串=全部；`drugName` 为模糊子串。
  > **商品ID = 药师帮id = `drugId`**（用户 2026-11-13 确认 + 真机交叉验证），但 48 项筛选里**没有 `drugId` 参数** → 按商品ID 查询必须走 `searchInfo`（`--keyword <drugId>`），传 `drugId=` 会被忽略。
- `notThroughStatus`：`0` 全部 / `1` 仅可再次申请；`saleStatType` 固定 `1`。
- 界面"全选" = `wholesaleType:[]`，不传 `["all"]`。

**展开更多搜索：48 项筛选**（两账号 51/51 参数均 `40001` 接受；除标注外真实生效）：

| 界面筛选项 | 参数 | 取值 |
|---|---|---|
| 活动id | `wholesaleId` | 字符串，精确命中 |
| 商品名称 | `drugName` | 字符串，模糊子串 |
| 商品编码 | `provDrugCode` | 字符串 |
| 本公司编码 | `compCode` | ⚠️ 接受但**不生效** |
| 批准文号 | `approval` | 字符串 |
| 生产厂家 | `factoryName` | 字符串 |
| 活动备注 | `wsDesc` | 字符串 |
| 配送商 | `deliveryProviderId` | int（值域见通用字典） |
| 商圈 | `areaGroupId` | int |
| 商圈包含/不包含地区 | `areaIds` / `areaExcludeIds` | ⚠️ 接受但**不生效** |
| 供货对象 | `storeType` | int，**必须数字**（数组报 `40004`） |
| 开单组合 | `deliverAlone` | int |
| 阶梯价/赠品 | `disType` | int |
| 活动时间 | `wsBeginDate` + `wsEndDate` | **必须成对** `YYYY-MM-DD HH:mm:ss` |
| 上架时间 | `wsAddBeginDate` + `wsAddEndDate` | **必须成对**，同上格式 |
| 同步库存 | `manualSyncStock` | `0`是 / `1`否 |
| 是否有库存 | `hasStock` | `1`是 / `0`否 |
| 同步价格 | `manualSyncPrice` | `0`是 / `1`否 |
| 经营范围 | `busiScope` | int 数组 |
| 是否控销 | `isRestrict` | `0`非控非禁 / `1`控销 / `2`禁销 |
| 活动可见范围 | `customerType` | `0`全部 / `1`新店专享 / `2`仅直播 / `3`仅组单中心；**传数字** |
| 是否套餐 | `saleType` | `2`是 / `1`否 |
| 橱窗推荐 | `isTop` | `1`是 / `0`否 |
| 虚拟供应商 | `virtualType` | `1`是 / `0`否 |
| 端口主题 | `promotionTypeId` | int 数组 |
| 价格审核 | `checkStatus` | `0`待审核 / `1`已通过 / `2`未通过 |
| 是否成团 | `teambuyStatus` | `1`是 / `0`否 |
| 上架途径 | `sourceType` | `1`商家上架诊所 / `2`自动上架诊所 / `3`商家上架连锁 / `4`自动连锁一口价 / `5`自动连锁批购包邮 / `6`自动连锁拼团 |
| 是否有图 | `hasLogo` | `1`有 / `0`无 |
| 是否首推 | `recType` | `1`首推 / `2`中药超市 / `0`否 |
| 是否帮帮特推 | `thirdRecType` | `3`是 / `4`否 |
| 针剂活动 | `isInjection` | `1`是 / `0`否（**列表生效、导出不支持**） |
| 发货仓 | `warehouseCode` | 字符串 |
| 是否有视频 | `videoExist` | `1`有 / `0`无 |
| 特殊药品 | `isHempDrug` | `1`含麻 / `2`冷链仅预约 / `3`冷链不含预约 / `4`非冷链仅预约 / `0`其他 |
| 自动化运营标签 | `autoOperationFlag` | `6`跟价 / `7`调价 / `8`随心购 |
| 是否有追溯码 | `isTraceCode` | `1`有 / `0`无 |
| 追溯码对接 | `manualSyncTraceCode` | `1`同步 / `0`不同步 |
| 维价类型 | `maintainPriceType` | `0~3` |
| 是否托管 | `isHostedDrug` | `0/1` |
| 是否返佣返利 | `isRebateCommission` | `0/1` |
| 可开专票 | `canOpenSpecialTicket` | `0/1` |
| 近 7 天店铺/平台排名区间 | `near7dStoreDrugRankRangeKeys` / `near7dPlatformDrugRankRangeKeys` | int `key`（8/9 档）。⚠️ 字典返回键名是 `...Ranges`，**查询参数必须是 `...RangeKeys`**，用错静默不生效 |
| 潜在掉价 / 大库存 / 库存充足 / 稀缺品种 | `potentialPriceDropDrug` / `largeInventoryDrug` / `sufficientStockDrug` / `scarceDrug` | `0/1` |

**叠加 A · 状态页签 `status`**（通用，9 值全实测）：

| 值 | 页签 | 值 | 页签 |
|---|---|---|---|
| `0` | 进行中 | `5` | 资质待审核 |
| `1` | 待开始 | `6` | 资质不通过 |
| `2` | 缺货下架 | `7` | 已结束 |
| `3` | 未上架（价格审核未通过） | `8` | 未动销下架 |
| `4` | 已下架 | `-1` | 全部（**不含已结束**，查已结束必须显式 `7`） |

**叠加 B · 活动类型 `wholesaleType`**（数组，`[]`=全选，**只认数字**）：

| 值 | 类型 | 值 | 类型 |
|---|---|---|---|
| `1` | 一口价 | `7` | 普通拼团 |
| `4` | 特价（不可用券） | `71` | 诊所拼团 |
| `5` | 限时特价（不可用商家券） | `8` | 批购包邮 |
| `6` | 限时特价（可用商家券） | `10` | 赠品 |
| — | — | `11` | 连锁包邮 |

> 传英文枚举名（`time_limit`/`normal_group`/`clinic_group`）报「参数异常」。

**叠加 C · 统计标签 `condition`**（0~19）：`0`价格过低 `1`可售不足7天 `2`近效期 `3`商圈为空 `4`来货自动上架 `5`未同步库存 `6`未同步价格 `7`拼团起拼数建议 `8`即将下架拼团 `9`滞销预警 `10`价格过高 `11`拼团调价建议 `12`最近平台上架 `13`未动销且即将下架 `14`品种补贴 `15`未动销且未调价即将下架 `16`高风险资质待补全 `17`供货对象为空 `18`≤通用入门价（**不生效**） `19`一口价过高。

**实测坑**：

1. **`totalRecord` 有 10000 硬上限**（ES 截断）：自营空关键词恒返回 `10000`/`totalPage=2000`（`pageSize=5`），`pageNo=2001` → `40004`；按状态切片仍触顶。**真实总数与总数统计一律用 `wsListCount`**；大结果集唯一可靠取数途径是导出（见 `api_商品下载.md`）。摇钱树数据量小未触顶（2343 为真实值）。
2. 判定"筛选是否生效"不能只看 total 与基线相同（自营因 10000 上限会误判），须用 0/1 双值对照 + `wsListCount` 复核。**真正不生效的仅** `compCode`、`areaIds`、`areaExcludeIds`、`condition=18`。
3. 日期筛选单边传无效；`storeType`/`customerType` 传数组报 `40004`。

### 1.3 `wsStatistic` 的 15 个字段

```
lackStockOffCount / nearValidateCount / lowSaleDayCount / autoOnCount / nearOffGroupCount
notSyncStockCount / notSyncPriceCount / emptyAreaGroupCount / teamBuyNotSaleCount
autoOff40TipsNum / yqsAutoOff40TipsNum / duringSubsidyNum / highRiskDocsWaitSupplyNum
blankStoretypeWsNum / lteCommonAccessPriceNum
```

> `priceTooLowCount`/`priceTooHighCount` 不在该返回内，是独立接口。部分字段可能为 `null`（自营 `nearOffGroupCount`、摇钱树 `notSyncStockCount`）。② 仅摇钱树 `yqsAutoOff40TipsNum` 有值（63），自营为 `null`。

### 1.4 单条详情 `getWholesale`

| 要素 | 内容 |
|---|---|
| 请求 | `{ "wholesaleId": <ID> }` + 公共参数 |
| 返回 | `data.wholesaleInfo`（217 字段完整表单）、`data.drugInfo` |
| 账号隔离 | 只能查本供应商活动；跨账号报 `40003 该活动非本供应商的活动` |
| 复验口径 | 适用于**表单类字段**（价格/主图/详情图/排序）。**`wsDesc` 详情接口不返回该字段；终态活动的 `status` 返回旧值**——这两类必须用 `wsList` 复验，详见 `zddz.md §5` |

### 1.5 字典接口（值域勿硬编码）

全部 `POST`，多数仅需公共参数。**完整返回样例与真实值域见 `references/通用/api_动态字典.md`**；下表为商品列表筛选直接依赖的 10 个接口。

| 筛选项 | 接口 | 必需参数 | 返回主键 | 条数 自营/摇钱树 |
|---|---|---|---|---|
| 动态价格档位 | `wholesaleDrug/getPriceTypes` | 公共参数 | `priceType`/`priceTypeName`/`haveInvoice` | **5 / 6** |
| 配送商 | `wholesaleDrug/getDeliveryProviders` | 公共参数 | `deliveryProviderId`/`name` | **0（空数组）/ 22** |
| 商圈 | `wholesaleDrug/getAreaGroupDropList` | 公共参数 | `id`/`groupName`/`nationwide`/`allowModify` | 4526 / 182 |
| 供货对象 | `wholesaleDrug/getStoreTypeGroup` | 公共参数 | `id`/`groupName`/`storeSubtypes` | 67 / 15 |
| 开单组合 | `wholesaleDrug/getDeliverAlones` | 公共参数 | `deliverAlone`/`desc` | 20 / 20 |
| 阶梯价/赠品 | `wholesaleDrug/getDiscountType` | 公共参数 | `disType`/`desc` | 6 / 6 |
| 经营范围 | `wholesaleDrug/getBusiScopeForProvider` | 公共参数 | `id`/`busiScope` | 21 / 21 |
| 端口主题 | `wholesaleDrug/getAllGroupTheme` | 公共参数 | `id`/`title`/`topicId`… | 142 / 18 |
| 近7天排名区间 | `wholesaleDrug/wsListRankFilterOptions` | 公共参数 | `near7dStoreDrugRankRanges`/`near7dPlatformDrugRankRanges`，各 `[{key,label}]` | 8/9 档 |
| 发货仓 | `provider/getWarehouseListByProviderId` | **`id`=providerId** | `id`/`whName`/`warehouseCode` | 1 / 1 |

> 价格字段按档位动态拼 `unitPrice{priceType}`：自营 `1,2,7,8,9`（偏远省份价/省内价/周边省份价/KA价/含税成本价），摇钱树 `1~6`（单体/连锁周边价、偏远价、超偏远价）。发货仓两账号均 `warehouseCode=11501`。`nationwide=1` 判全国商圈（自营 id=571、摇钱树 id=8161）。

### 1.6 资料类 / 上架前置 / 辅助查询（28 个只读接口）

全部 `POST`，两账号均 `40001`。路径省略前缀 `/scm-goods/`（标注 `/scm-setting`、`/scm-order` 者除外）。

**资料类（14）**

| 用途 | 接口 | 必需参数 | 返回要点 |
|---|---|---|---|
| 商品价格 | `wholesaleDrug/getDrugPrice` | `drugId` `wholesaleId` | `data=0` |
| 商品价格（主路径） | `drug/getDrugPriceDataAct` | `drugId` `provDrugCode` `deliverProviderId` | 完整价格/库存对象 |
| 入门价（批量） | `wholesaleDrug/getAccessPrice` | `ids:[活动ID]` | `{活动ID:值}` |
| 入门价（按商品） | `wholesaleDrug/getAccessPriceByDrug` | `drugId` | `{drugId:值}` |
| 库存占用 | `wholesaleDrug/getStockOccupation` | `ids:[活动ID]` | `{活动ID:0}` |
| 下单库存 | `wholesaleDrug/wsOrderStock` | `wholesaleId` | `waitDealNum`/`openAccountNum`/`waitOrderNum`/`refundNum`/`waitPay` |
| 详情价格 | `wholesaleDrug/wsShowDetailPri` | `wholesaleId` | bool |
| 是否可连锁包邮 | `wholesaleDrug/ifCanChainFreeShip` | `wholesaleId` | `0` |
| 是否已有连锁包邮 | `wholesaleDrug/judgeHasChainFS` | `wholesaleId` | `{hasRelChainFS:0}` |
| 连锁包邮高价配置 | `wholesaleDrug/getChainFSPriceHighConfig` | 通用 | `{chainFSPriceHighConfig:1.2,fixedPriceHighConfig:1.1}` |
| 全部价格档位 | `wholesaleDrug/allPpl` | `wholesaleId` | 数组（自营 8 / 摇钱树 5） |
| 端口主题分组 | `wholesaleDrug/priorityThemeGroup` | 通用 | 数组 |
| 溯源初始化计数 | `drug/getSfSxgInitStatusCount` | 通用 | `0` |
| 追溯码变更计数/列表 | `drug/traceCodeAutoChangeCount` / `traceCodeAutoChangeList` | 通用 / `pageNo`+`pageSize` | `0` / `{dataList:[]}` |

**上架前置校验（7）**

| 用途 | 接口 | 必需参数 | 返回要点 |
|---|---|---|---|
| 套餐商品列表 | `drug/getDrugPackList` | `id`=drugId | `{hasDrugPack:1,drugPackList:[150],defaultDrugPack:150}` |
| 商圈黑名单提示 | `wholesaleDrug/blacklistAreaGroupTips` | `areaGroupId` `wholesaleId` | `{blackNum:0,openNum:null,pencent:0}` |
| 校验活动价格 | `wholesaleDrug/checkWsPrice` | `wholesaleId` `unitPrice` | `{showCheckWsPrice:false,checkWsPriceDesc:…}` |
| 可用单位 | `wholesaleDrug/getConfigUnitsByDrugId` | `id`=drugId | `["盒"]` |
| NMPM 标识需求 | `wholesaleDrug/getNMPMRequireFlag` | `drugId` `wholesaleId` `deliveryProviderId` | `0/1` |
| 非药品限制状态 | `wholesaleDrug/getNonDrugRestrictStatus` | `drugId` | `{inRestrict:0,endDate:""}` |
| 商品资料 | `wholesaleDrug/wholesaleDocs` | `drugId` `wholesaleId` `copyId` `tcm` `deliveryProviderId` | `{filePath,haveDocs,docIds,…}` |

**辅助 / 弹窗查询（7）**

| 用途 | 接口 | 必需参数 | 返回要点 |
|---|---|---|---|
| 地区码层级 | `areaGroup/getAreaCodeWithoutLimit` | `level=0` `maxLevel=3` `parentCode=0` | 34 个省级 |
| 商圈冲突校验 | `drug/checkAreaGroupAct` | **`ids` 至少 2 个活动ID** | `true`（传 1 个或 `wholesaleIds` → `40004`） |
| 供货对象已选/未选 | `/scm-setting/storetypeGroup/getNoSelectAndSelectStoreType` | 通用 | 8 项 `{storeType,storeTypeDesc,selected}` |
| 供货对象组列表 | `/scm-setting/storetypeGroup/getStoretypeGroupListAct` | `pageNo` `pageSize` | 10 组 |
| 采购明细 | `/scm-order/wholesaleOrder/wholesaleDetail` | `page` `pagesize` `wholesaleId` | 分页结果 |
| 销售统计明细 | `drugsStat/getStatReportDetailBase` | `drugId` | `{drugInfo,provinceList}` |
| 销售报表列表 | `drugsStat/saleReportDrugsStatList` | `dateRange:[起,止]` `tab` `pageNo` `pageSize` | `results[]` |

**采购明细参数**（界面"采购明细"按钮，实测）：基础 `{wholesaleId,page,pagesize}`；按下单时间 `orderTime:["起T00:00:00+08:00","止T23:59:59+08:00"]`；按订单 ID `orderId:"<字符串>"`；导出 `exportWholesaleDetail` 为直接 XLSX，固定 8 列（活动ID/订单ID/药店名称/下单时间/商品名称/购买价格/数量/总金额）。

### 1.7 读取差异汇总

| 维度 | 自营 | 摇钱树 |
|---|---|---|
| `wsList` 接口/参数/215 字段名 | 完全一致 | 完全一致（差异仅在取值） |
| `getPriceTypes` | 5 档 `1,2,7,8,9`，`haveInvoice` 有值 | 6 档 `1~6`，`haveInvoice=null` |
| 字典条数（商圈/主题/配送商/供货对象） | 4526 / 142 / **0** / 67 | 182 / 18 / **22** / 15 |
| `wsListCount` 真实总数 | 合计 173,521 | 2,343 量级 |
| 大结果集 | **必须导出**（分页/切片取不全） | 分页可覆盖 |
