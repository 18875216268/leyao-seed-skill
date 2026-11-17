# 商品字段对照（zddz）

> 配套 `sy.md`（子板块地图）：本文专管**字段**——界面字段 ↔ API key、字段可改性、提交模板、类型专属字段、复验口径。接口/参数见 `api_商品读取.md` / `api_商品写入.md` / `api_商品下载.md`。
> 账号标签与 `sy.md §3.1` 一致：**① 通用** / **② 仅摇钱树** / **③ 仅自营** / **④ 转PMS** / **⑤ 禁用**（`【待确认】` 仅作\"参数未实测\"的质量标记，不是账号分类）。
> 数据来源：`wsList.data.results[]`（215 字段）、`getWholesale.data.wholesaleInfo`（217 字段）、`addWholesale` 提交模板（112 顶层键）。三者同名但不同层，下表按用途分板块列出。
> **路径基准**：本文所有 `references/…` 相对**技能包根目录**（本资产根）；`sy.md`（子板块地图）、`api_pms活动管理.md` 与本文同目录，直接用文件名互引。

## 0. 通用列定义

| 列名 | 含义 |
|---|---|
| 界面字段 | 商品列表页 / 编辑页上看到的名称 |
| API key | 请求或响应中的字段名；**列表字段名与详情表单字段名不同时并列标出** |
| 适用 | 见 §0 标签 |
| 可改性 | `可改` / `只读` / `复制时设` / `派生` / `单接口` / `④ 转PMS ` |
| 约束·复验 | 值域、格式限制、以及"改完用哪个接口复验" |

> 复验总规则见 §5。字段名两账号完全一致，差异只在取值与可改性。

---

## 1. 列表返回字段（`wsList.data.results[]`）

### 1.1 活动

| 界面字段 | API key | 适用 | 可改性 | 约束·复验 |
|---|---|---|---|---|
| 活动ID | `wholesaleId` | 通用 | 只读 | 精确筛选参数；PMS 侧叫 `wholeSaleId`（大小写不同） |
| 活动类型 | `wholesaleType` / `wholesaleTypeName` | 通用 | 复制时设 | `1`一口价 `4`特价 `5``6`限时特价 `7`普通拼团 `71`诊所拼团 `8`批购包邮 `10`赠品 `11`连锁包邮 |
| 活动状态 | `status` / `statusName` | 通用 | ④ 转PMS/SCM 生命周期 | **SCM** `0`进行中 `1`待开始 `2`缺货下架 `3`未上架 `4`已下架 `5`资质待审核 `6`资质不通过 `7`已结束 `8`未动销下架；**PMS** 另用 `wholesaleStatus` `5`进行中 `3`已下架 `4`缺货下架 `0`待开始。勿混用 |
| 是否控销 | `isRestrict` | 通用 | ④ 转PMS | `0`否 `1`控销 `2`禁销 |
| 标签/主题 | `disTagName` / `themeTitle` / `promotionTitle` / `tagId` | 通用 | 复制时设/整表编辑 | — |

### 1.2 商品信息

| 界面字段 | API key | 适用 | 可改性 | 约束·复验 |
|---|---|---|---|---|
| 批准文号 | `approval` | 通用 | 只读 | 可作筛选 |
| 商品ID | `drugId` | 通用 | 只读 | 复制/库存接口必需参数 |
| 商品名称 | `drugName` | 通用 | 只读 | 筛选为模糊子串 |
| 规格包装 | `pack`（详情表单 `specification`） | 通用 | 只读 | — |
| 生产厂家 | `factoryName` | 通用 | 只读 | — |
| 经营范围 | `busiScopeName`（码值 `busiScope`） | 通用 | 只读 | 值域见 `references/通用/api_动态字典.md` |
| 商品编码 | `provDrugCode` | 通用 | 只读 | 复制必用**源活动原值**（含 `-50` 类后缀不可去）；PMS 侧可按此反查活动 |

### 1.3 app 显示

| 界面字段 | API key | 适用 | 可改性 | 约束·复验 |
|---|---|---|---|---|
| app 显示名称 | `appName`（`appNameDesc` 为说明文本） | ③ 仅自营 派生 / ② 仅摇钱树 可改 | 派生/可改 | 自营由"商品名+规格/包装"派生，界面灰显；摇钱树整表 `mode=edit` 可改（含申请固定前缀） |
| 效期 | `validDate` | 通用 | 复制时设/整表编辑 | — |
| 列表/店铺页排序 | `order` / `dpOrder` / `topOrder` | 通用 | 单接口/整表编辑 | `editOrder` 须传**与原值不同**的值；复验 `getWholesale.order` |
| 主图 | `logo` | 通用 | 单接口 | `updateLogo`；复验 `getWholesale.logo` |
| 是否有图 | `hasLogo`（筛选参数） | 通用 | — | `wsList` 返回中无此字段，判断有无图以 `logo` 是否为空为准 |
| 橱窗推荐 | `isRecommend` / `recommendToDp` / `recommendOrder` | ③ 仅自营 灰显 / ② 仅摇钱树 可改 | 派生/可改 | — |

### 1.4 销售价格

| 界面字段 | API key | 适用 | 可改性 | 约束·复验 |
|---|---|---|---|---|
| 是否同步价格 | **列表 `msyncPrice`**；详情表单/提交 `manualSyncPrice` | 通用 | 整表编辑 | `0`是 / `1`否 |
| 主售价 | `unitPrice` | ③ 仅自营 复制时设 / ② 仅摇钱树 整表编辑 | 复制时设/可改 | 摇钱树须传**字符串**，且 ≤ 品类近30天成交均价×5 |
| 动态价格 | `unitPrice1~9` / `chainPrice` / `cunitPrice` / `cunitPrice1~9` / `cchainPrice` / `oldPrice` | 同上 | 同上 | 按 `getPriceTypes` 拼 `unitPrice{priceType}`；自营 5 档 `1,2,7,8,9`，摇钱树 6 档 `1~6`；**全档位必须 >0 且 >原价** |
| 起购数量 | `minAmount` | 通用 | 复制时设/整表编辑 | 须为 `step` 整数倍 |
| 购买倍数 | `step` | 通用 | 复制时设/整表编辑 | >0 |
| 建议零售价 | `recommendedPrice` | 通用 | 整表编辑 | — |
| 限购开关/数量 | `ifLimit` / `maxAmount` | 通用 | **④ 转PMS 无对应板块** | SCM 返回 40001 但不落库；PMS 限购板块亦无此二字段，属真实缺口 |
| 单店采购上限 | 列表 `maxAmPerStore`；详情/提交 `maxAmountPerStore` | ③ 仅自营 + ④ 转PMS / ② 仅摇钱树 单接口 | 单接口 | `0`=不限，但 `editMaxAmountPerStore` 传 0 报「请设置单个药店采购上限」；自营走 PMS `updateGoodsSaleLimitConf`（须同传 `minQty`/`step`） |
| 上限刷新周期 | `calculatePeriod` | 通用 | 整表编辑 | `0`活动期内 `1`每笔 `2`每天 `3`每周；PMS 侧同名字段 |
| 上限启用时间 | **`calculateBeginDate`**（时间戳，即"上架应用时间"） | 通用 | 复制时设/整表编辑 | 配套 `calculatePeriod`；`timeLimitsOn` 是限时开关（不同语义）、`limitStartTime?` 无实采依据，均非本字段 |

**单品阶梯价**（独立促销实体，不属于价格档 `unitPriceN`；接口与提交体见 `api_商品写入.md §1.9`）：

| 界面字段 | API key | 适用 | 可改性 | 约束·复验 |
|---|---|---|---|---|
| 是否添加阶梯价 | `add` | ③ 仅自营 | 专用接口 | `1`添加 / `0`删除；删除也走 `addLadderPrice`，无独立删除接口 |
| 促销起始数量1 / 优惠价1 | `minCnt` / `disPrice` | 同左 | 专用接口 | `wsList` 有同名键（未配时为 `null`） |
| 促销起始数量2 / 优惠价2 | `minCnt2` / `disPrice2` | 同左 | 专用接口 | **最多 2 档**；不配则省略键 |
| 区域 | `limitArea` + `areaCodes` | 同左 | 专用接口 | `0`不限 / `1`限制区域（级联区域树）；二者不在 `wsList` |
| 促销标题 | `tagDesc` | 同左 | 专用接口 | 不在 `wsList`，用 `getLadderPriceInfo` 读回 |
| 促销起止时间 | `beginDate` / `endDate`（Unix 秒） | 同左 | 专用接口 | **与活动起止时间同名但不同表**（活动时间见 §1.8），勿混用 |
| 促销期间列表图片 | `tagPic` / `tagPicAudit` | 同左 | 专用接口 | 先 `upload2Local` 得 URL，提交 `tagPicAudit` |

### 1.5 库存

| 界面字段 | API key | 适用 | 可改性 | 约束·复验 |
|---|---|---|---|---|
| 是否同步库存 | **列表 `msyncStock`**；提交 `manualSyncStock`；复制时 `autoSyncStock` | 通用 | 单接口/整表编辑 | `0`同步 / `1`手动；复验用 `wsList.msyncStock` |
| 手动库存数量 | **`drugStock`**（不是 `stockAvailable`） | 通用 | 单接口 | **仅写入字段**：`editStock2` 手动时必带、切回同步时省略；`wsList`/`getWholesale` **都不返回** `drugStock`，回读手动值用 `wsList.stockAvailable` |
| 可用库存 | `stockAvailable` | 通用 | 只读（由同步方式决定） | — |
| ERP 库存 / 占用 / 可售天数 | `stockBalance` / `stockOccupation` / `canSaleDays` | 通用 | 只读 | — |

### 1.6 业务商圈

| 界面字段 | API key | 适用 | 可改性 | 约束·复验 |
|---|---|---|---|---|
| 发货仓 | `warehouseCode` / `whName` | 通用 | 复制时设 | 值域 `getWarehouseListByProviderId` |
| 商圈 | `areaGroupId` / `groupName` | 通用 | 复制时设/整表编辑 | `nationwide=1` 判全国（自营 571 / 摇钱树 8161） |
| 供货对象 | **列表 `storetype`**；详情/提交 `provObject` | ③ 仅自营 派生 / ② 仅摇钱树 可改 | 派生/可改 | 自营复制时派生不可改 |
| 配送商 | `deliveryProviderId` | ② 仅摇钱树 常用 | 复制时设/整表编辑 | 自营字典返回空数组；切换须商品已建立供货关系，否则 `40003 商品编码不匹配` |
| 控销/禁销组 | `restrictGroupId`（**PMS 侧叫 `restrictId`**） | 通用 | ④ 转PMS/仅复制时设 | 候选来自 `saleControl/allNoWsGroups`；`isRestrict=0` 时强制 0；事后 `mode=edit` 改必 `40002` |

### 1.7 销售情况

| 界面字段 | API key | 适用 | 可改性 | 约束·复验 |
|---|---|---|---|---|
| 采购店数 | `storeNum` / `userNum` | 通用 | 只读 | 界面显示本期/累计两个数 |
| 采购数量 / 金额 | `buyNum` / `totalCost` | 通用 | 只读 | — |
| 采购明细 | 接口 `/scm-order/wholesaleOrder/wholesaleDetail` | 通用 | 只读 | 支持 `orderTime`/`orderId` 过滤；导出 `exportWholesaleDetail` 直出 XLSX 8 列 |

### 1.8 备注与时间

| 界面字段 | API key | 适用 | 可改性 | 约束·复验 |
|---|---|---|---|---|
| 活动备注 | `wsDesc` | 通用 | **单接口 `editWsDesc`** | 传 `""` 可清空；**复验必须 `wsList` 行的 `wsDesc`**，`getWholesale` 不返回该字段（见 §5） |
| 活动起止时间 | `beginDate` / `endDate`（Unix 秒）；显示 `beginDateStr`/`endDateStr`；**提交用小写 `startdate`/`enddate`** | 通用 | 复制时设/整表编辑 | `beginDate`=当日 `01:00:00`、跨度 ≤1 月；PMS 侧另有 `updateYkjWsActivityTime`（格式 `yyyy-MM-dd HH:mm:ss`） |
| 上架/创建时间 | `wsAddBeginDate`/`wsAddEndDate`（筛选）；`createTime` | 通用 | 只读 | 日期筛选必须成对 |

---

## 2. 编辑页字段（按界面五大板块）

> 提交接口统一为 `addWholesale(mode=edit)`（整表）或 §1 各单字段接口；wt=8 批购包邮须走 `freeShipping/addWholesale`（见 `api_商品写入.md §1.5`）。

### 2.1 价格 / 库存

| 界面字段 | API key | 自营 | 摇钱树 | 约束 |
|---|---|---|---|---|
| 原价/供乐药价 | `unitPrice` | 复制时设 | 整表编辑（字符串） | 摇钱树 ≤ 品类均价×5 |
| 动态价格 | `unitPrice{priceType}` | 复制时设 | 整表编辑 | 全档位 >0 且 >原价；摇钱树须等比缩放防 `40042` |
| 采购起订量 / 购买倍数 | `minAmount` / `step` | 复制时设 | 整表编辑 | 倍数关系 |
| 活动库存 / 同步开关 | `stockAvailable` / `manualSyncStock` / `drugStock` | 单接口 `editStock2` | 同左 + 整表 | 两账号字段名一致 |
| 有效期至 / 生产日期 / 批号 | `validDate` / `prodDate` / `batchId` | 复制时设 | 整表编辑 | — |
| 单店上限 / 刷新周期 | `maxAmountPerStore` / `calculatePeriod` / `calculateBeginDate` | ④ 转PMS | 整表编辑 | 自营 SCM 改不落库 |
| 限购开关 / 数量 | `ifLimit` / `maxAmount` | ④ 转PMS 缺口 | 整表编辑（须显式传） | 漏传报 `40003 请设置单个药店采购上限` |

### 2.2 开单信息

| 界面字段 | API key | 自营 | 摇钱树 | 约束 |
|---|---|---|---|---|
| 最小发货单位 / 整包装单位 | `munit` / `standardUnit` | `standardUnit` 灰显不可改 | 整表编辑 | 其余字段两账号均可写 |
| 中包装数 / 整件数量 | `midPack` / `wholePack` | 复制时设 | 整表编辑 | — |
| app 显示名称 | `appName` | 派生只读 | 整表编辑 | 可申请固定前缀 |
| 商品编码 | `provDrugCode` | 只读 | 只读 | 商品固有属性 |
| 导单系数 | `provDrugFactor` | 复制须传 | 同左 | 字段名已确证 |
| 开单组合 | `deliverAlone` / `deliverType` | 复制时设 | 整表编辑 | 值域 `getDeliverAlones` |

### 2.3 活动时间

| 界面字段 | API key | 自营 | 摇钱树 | 约束 |
|---|---|---|---|---|
| 活动开始 / 结束 | `beginDate`/`startdate`、`endDate`/`enddate` | 复制时设；事后整表可改 | 整表编辑 | 开始=当日 01:00、跨度 ≤1 月 |
| 抢购开始 / 结束（wt=8、拼团） | `rushBeginDate` / `rushEndDate`（返回展示）；另有数组形态 `rushBeginDay`/`rushBeginTime`/`rushEndDay`/`rushEndTime` | 只读展示 | 只读展示 | **提交不带 `rush*`，用小写 `startdate`/`enddate`** |
| 限购三件套 | `ifLimit` / `maxAmount` / `maxAmountPerStore` + `minAmount` / `step` | ④ 转PMS/复制时设 | 整表编辑须**显式全传** | 漏传 `maxAmountPerStore` → `40003` |

### 2.4 商圈 / 控销

| 界面字段 | API key | 自营 | 摇钱树 | 约束 |
|---|---|---|---|---|
| 业务商圈 | `areaGroupId` | 复制时设/整表 | 整表编辑 | 值域动态 |
| 供货对象 | `provObject` | 派生只读 | 整表编辑 | — |
| 活动可见范围 | `customerType` | 复制时设/整表 | 整表编辑 | `0`全部 `1`新店专享 `2`仅直播 `3`仅组单中心 |
| 配送商 / 发货仓 | `deliveryProviderId` / `warehouseCode` | 自营字典为空 | 整表编辑 | 受供货关系约束 |
| 是否控销 / 控销组 | `isRestrict` / `restrictGroupId` | ④ 转PMS | **仅复制/新建时设**，事后 `mode=edit` 报 40002 | `0/1/2` |

### 2.5 图片 / 其他

| 界面字段 | API key | 自营 | 摇钱树 | 约束 |
|---|---|---|---|---|
| 主图 | `logo` | `updateLogo` 独立接口 | 同左 | URL 先经 `upload2Local` |
| 详情图 | `picUrlList`（≤10）/ `picsAudit`（待审核） | **无独立接口**，只能整表 `addWholesale` 提交 | 同左 | 复验 `getWholesale.picUrlList` |
| 商品活动说明 | `wsDesc` | `editWsDesc` | 同左 + 整表 | 复验走 `wsList` |
| 优惠标签 / 促销分类 | `tagId` / `tagList` / `promotionType` | 复制时设/整表 | 整表编辑 | — |
| 店铺页排序 | `dpOrder` / `order` | 单接口 `editOrder` | 同左 + 整表 | 须异值 |
| 推荐橱窗 | `isRecommend` / `recommendToDp` | 灰显 | 整表编辑 | — |
| 条形码 | **`barcode`**（小写 c） | 只读 | 只读 | `barCode` 仅为界面写法/探查候选键，非有效提交字段 |

---

## 3. 提交表单字段（`addWholesale` 112 顶层键）

| 要素 | 内容 |
|---|---|
| 读取来源 | `getWholesale` → `wholesaleInfo`（217 字段）、`drugInfo`（134）、`providerInfo`（28，含 `priceReadOnly`） |
| 同名直取 | **72 个**与 `wholesaleInfo` 同名；**含 `unitPrice`/`unitPrice1~9`/`chainPrice`/`cunitPrice`/`cchainPrice` 全部价格档位**（价格档位键一律直取，不得因历史表单没有就丢弃） |
| 需映射/默认值 | **40 个**读取响应中不存在（清单见本节末） |
| 名称映射 | `wholesaleInfo.beginDate/endDate` → 提交 **`startdate`/`enddate`**（小写） |
| 两种 mode | `mode=copy`+`copyId=1`+`wholesaleId/id`=源ID → 新建并返回新 ID；`mode=edit`+`copyId=0`+`checkExist=0` → 编辑现有并返回原 ID |
| 全量回写规则 | 必须把 `getWholesale` 读到的值**原样带回、只改目标字段**并逐字段 diff；表单内 `token` 必须换成当前凭证 |
| 价格保护 | 全量回写须逐字段校验 `unitPrice`/`chainPrice` 不低于用户红线；**不得提交 0 或低价** |
| 查重 | `checkExist=1` 遇「活动类型+业务商圈+供货对象」完全一致的已上架活动返回 `isExist:true`；确认继续用 `checkExist=0` |
| 必带 | `maxAmountPerStore`（新建漏传报 `40003 请设置单个药店采购上限`） |

**读取响应中不存在的 40 个字段**：
`appNameType` `approval` `auditPicUrl` `autoSyncPrice` `autoSyncStock` `changeTraceCode` `checkExist` `copyId` `docs` `enddate` `ex` `hasBarcode` `ifLimit` `imgUrlBarcode` `isTcm` `lastBuildTime` `oldData` `platform`；
`recomendPrice` `startdate` `syncSameWs` `tcm*` 系列 `token` `traceCodePicInfos` `ua` `version`。

### 3.1 批购包邮（wt=8）提交模板（75 字段，独立模块）

| 要素 | 内容 |
|---|---|
| 模块 | **`/scm-goods/freeShipping/*`**（不是 `wholesaleDrug/*`） |
| 读模板 | `POST /scm-goods/freeShipping/getWholesale`：`{wholesaleId, wholesaleType:8, ctype:1, copyId:1, mode:"copy", drugId:null, deliverFlag:null, isCopyDeliverType:null, deliverType:null, isCopyTraceCode:null}`，`ex=batchFsShelfDetail` |
| 提交 | `POST /scm-goods/freeShipping/addWholesale`，`ex=batchFsShelfDetail`，完整体 + **显式限购字段** |
| 配送字段 | `deliverAlone` `deliveryProviderId` **`deliverProviderId`**（无 y） `deliverType` `deliverFlag` `isCopyDeliverType`；漏传报 `40003 请选择配送商或者配送方式` |
| 前置校验 | `POST /scm-goods/freeShipping/beforeAddToFsWsAct`（仅公共参数）→ `deliver` 配送商字典（自营 0 / 摇钱树 22） |
| 合法值域 | `deliverTypes`=`1/2/6`；`deliverAlones`=`0/1/2/3/4/5/10/11/12/13/14/51` |
| 编码 | `drugId`/`provDrugCode` 必须用源活动原值（带 `-50` 后缀不可去），否则 `40003 商品编码不匹配` |
| 价格 | 真实 wt=8 活动 `unitPrice1~8` 本身可能为 0 → **复制必须强制全档位=目标价**，否则 0 元档 |

---

## 4. 活动类型专属字段

从真实活动 217 字段反推，两账号一致：

| 类型 | 专属字段（非空实测） | 样例活动 |
|---|---|---|
| 普通拼团 `7` | `bottomPriceUrl`（默认拼团图）/ `bottomPriceDesc`（规则长文案）/ `clinicType`（3普通/1诊所）/ `successAmount`（成团数=20）/ `maxAmountPerStore` / `maxAmountPerUser` / `maxAmount` / `themeId` / `isRestrict`+`restrictGroupId` | 自营 `1449235540`、摇钱树 `1448759272` |
| 诊所拼团 `71` | 同上 + `paidAmount` / `orderAmount` / `calculateOrgDate`，`clinicType=1` | 自营 `924245516` |
| 赠品 `10` | `initAmount`（初始量）/ `unitPrice1`/`unitPrice2`/`unitPrice9` 三档有值 / `topOrder` / `order=99999` / 短跨度时间 | 自营 `1448582244`（摇钱树无赠品活动） |
| 特价不可用券 `4` | `unitPrice1~9` **全档位填满** / `promotionType` / `maxAmountPerStore` / `maxAmountPerUser` / `isTop` / `tagList` | 自营 `1448733245`、摇钱树 `1449046066` |
| 批购包邮 `8` | `rushBeginDate`/`rushEndDate` / `minAmount` / `bindType` / `cunitPrice` / `cchainPrice`；走 `freeShipping` 模块（§3.1） | 自营 `1449109975`、摇钱树 `1445743847` |

> 摇钱树特价实证 `1449046066` 的 `unitPrice1~6` 全有值且各不同（32.19/31.85/32.43/32.09/32.79/32.43）、`unitPrice9=22.0` → 印证多档位须保持比例。

---

## 5. 复验口径总表（写操作必读）

| 要复验的内容 | 用哪个接口 | 原因 |
|---|---|---|
| `wsDesc` 活动备注 | **`wsList` 行的 `wsDesc`** | `getWholesale.wholesaleInfo` 不返回该字段（恒 None），用它复验会误判"未落库" |
| 活动生命周期状态（`status`） | **`wsList` 按 `status` 页签过滤** | `getWholesale.status` 对终态（已结束）活动返回旧值（如 3），`statusName` 同空 |
| 价格全档位、主图 `logo`、详情图 `picUrlList`、排序 `order` | `getWholesale.wholesaleInfo` | 表单类字段，详情接口完整返回 |
| 同步库存 `msyncStock` | `wsList` 行 | 列表字段名与提交名不同 |
| PMS 侧状态/运营策略 | PMS 查询接口 `pageOneFixedWsList` 等 | 见《api_pms活动管理.md》§2 |

> **写操作标准动作**：改前记录原值 → 提交 → 按上表复验 → 失败用原值回滚 → 写审计日志。

---

## 6. 字段名确证（原疑点已关闭）

| 界面/疑点 | 确证结论 | 依据 |
|---|---|---|
| 导单系数 `commissionRatio?` | **真实提交字段 = `provDrugFactor`**（`getWholesale` 实测值 `1.0`，写入实测携带）；`commissionRatio` 是 wsList 215 字段中的**另一个字段**，不是导单系数 | 过程区实测响应与写入脚本 |
| 上限启用时间 `limitStartTime?` | **真实字段 = `calculateBeginDate`**（时间戳，界面「上架应用时间」）；`timeLimitsOn` 是限时开关（不同语义），`limitStartTime` 无实采依据 | 归档《商品列表业务文档》《摇钱树操作文档》、过程区 `freeShipping只读验证.py` |
| `standardUnit` | ③ 仅自营 界面灰显不可改；② 仅摇钱树 无灰显、整表可改 | 归档《编辑字段对照》§1/§2 |
| `barcode` vs `barCode` | **真实字段 = `barcode`（小写 c），只读商品属性**；`barCode` 仅为界面写法/探查候选键，非有效提交字段 | 过程区 `字段全清单.txt`、写入脚本提交体 |
| `appNameDesc` / `defaultAppName` | 自动派生文本（值为「商品名+规格/包装」），**非独立可写字段** | 归档《编辑字段对照》§1 |
| PMS 写接口 `wholeSaleType` | 取值只有 `1`（一口价）/`2`（特价），批购包邮/整件购按默认 `1`；实测仅覆盖一口价 | `参考区/活动管理.html` `resolveYkjWholeSaleType()` |

> 商品板块剩余待实测项统一见 `sy.md §4`，本文不再维护独立清单。

---

## 7. 端点索引（本文不展开参数）

批量编辑 `batchEdit`、套餐主从 `getPackageMainIds`、三方首推 `markThirdFr`/`unmarkThirdFr`、首推审核 `priorityAudit`/`priorityAuditInfo`、删除 `deleteWholesale`、解绑 `unBindAct`、查重 `checkProvDrugCode`、上架表单与图片/视频端点 —— 全部见 `references/附录/接口总表.md`。

---

## 8. 委托配送商品（列表字段分组）

> 接口与参数见 `api_委托配送商品.md`；账号/板块归属见 `references/sy.md §0`；返回行 150 字段，按用途分组如下（全量键名以实际响应为准）：

| 分组 | 字段 |
|---|---|
| 商品标识 | `id` `wholesaleName` `fullName` `drugId` `cnName` `drugName` `factory` `pack` `specification` `drugCode` `dnPrefix`/`dnSuffix` |
| 委托配送标识 | `recommendToDp`（推荐至配送平台）`dpOrder`（配送端排序）`deliverAlone`/`deliverAloneStr`（独立配送）`provDrugFactor`（供应商药品系数）`provDrugCode`（药品编码） |
| 价格 | `recommendPrice` `unitPrice` `chainPrice` |
| 状态 | `approval` `status` `statusName` `stockAvailable` |
| 统计 | `orderNum` `totalamount` `totalCost` `monthWs` `daysStockTogo` |
| 推荐/分组 | `isRecommend` `recommendOrder` `areaGroupId` `groupName` `storetypeGpId` `storetype` `busiScope` `virtualType` `wholesaleType`/`wholesaleTypeStr` `isCashCow` |
| 供应商 | `providerId` `cashcowProviderId` `cashcowProviderName` `deliveryProviderId` `saleType` `beginDate` `blogo` |

> 写操作键：`setDeliveryOrder`(`dpOrder`,`recommendToDp`,`wholesaleIdList`)、`changeDeliverAlone`(`deliverAlone`)、`changeDrugCode`/`checkDrugCode`(`provDrugCode`)、`changeProvDrugFactor`(`provDrugFactor`)。
