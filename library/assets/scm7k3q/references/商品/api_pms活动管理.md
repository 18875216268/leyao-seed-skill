# PMS 活动管理（API）· 自营专属 · 转PMS 出口

> **定位**：自营活动在 PMS 侧的**读取（查询）/ 写入 / 导出**完整出口。SCM 侧下架/重上架/运营策略被自动运营拦截、限购/控销字段"返回成功但不落库"时，走本文接口。
> **归属**：`references/sy.md §0.4` 标**自营专属**；`商品/sy.md §3.1` 分类为 **③ 仅自营 / ④ 转PMS**。摇钱树账号不走本文（摇钱树 SCM 侧真实生效）。
> **配套**：`api_商品读取.md`（SCM 读）、`api_商品写入.md`（SCM 写，其 `转PMS` 标记指向本文）、`zddz.md`（字段台账）。
> **请求体系独立**：PMS 主机 `https://pms.ysbang.cn`（部分微服务在 `pms.leyopharm.com`），登录由 `python scm.py pms-login` 子进程委托主技能 PMS 登录器完成、本资产 `core/pms_client.py` 只读消费凭证（CLI：`python scm.py pms-login` / `pms-status`）；与 SCM 的主机、凭证、请求形态**完全独立**，勿混用。
> **请求直连**：业务请求直连 PMS 官方主机，按本文 §1.2 的请求形态构造；路径与版本以本文接口表为准。
> **范围说明**：本文只覆盖**商品活动管理**页。**出库统计**属数据板块（`references/` 暂无该板块文档），不在本文范围。
> **路径基准**：`references/…`、`AGENT_GUIDE.md` 相对技能包根（本资产根）；`sy.md`、`zddz.md` 与本文同目录，直接用文件名互引。
> **账号一律动态取得**：`providerId` 由 PMS 凭证（`core/pms_client.py` 只读消费）给出（字符串型），**文档与脚本都不得硬编码具体账号/公司 ID**。

---

## 1. 通用约定

### 1.1 登录链路（本资产委托主技能登录器、只读消费凭证；官方主机 + 端点白名单）

| 步 | 端点 | 说明 |
|---|---|---|
| ① 企微扫码 | `https://login.work.weixin.qq.com` | tkinter 弹窗出码 |
| ② 换乐药 token | `POST https://auth.leyopharm.com/auth-service/auth/loginByWorkWeChat/v100` | `{"code":<auth_code>}` |
| ③ 校验子系统 | `POST https://auth.leyopharm.com/auth-service/auth/index/v100` | 须 200 |
| ④ 换 PMS token | `POST https://pms.ysbang.cn/api/Index/loginViaLeyoKeyToken/v1170` | form（含 `isAuth8=0`） |
| ⑤ 激活/校验 | `POST https://pms.ysbang.cn/api/Index/index/v423` | 凭证有效性探测端点 |
| ⑥ 公司口径 | `POST https://pms.ysbang.cn/pms-main/merpUser/getSubProviderList/v2050` | → `providers` / `provider_id` / `provider_name` |
| ⑦ 发货仓 | `POST https://pms.leyopharm.com/datacenter_pms/web/search/providerWarehouseOption/pv9210` | JSON → `warehouses` |

- **调用入口（禁止自组装登录）**：
  - CLI（推荐，路径无关）：`python scm.py pms-status`（只校验，不弹窗）/ `python scm.py pms-login`（扫码登录）；
  - Python 门面：`from core import pms_client` → `pms_client.get_credential()` / `pms_client.verify_credential()`（本资产只读消费凭证，**无** `relogin`/`is_authenticated`——那属 SCM 登录器 `scripts/scm_login.py`）；脚本内用 `pms_client.get_credential(force_relogin=False)` 复用有效凭证；
  - PMS 登录器实体在主技能 `p3nes3/scripts/pms_login.py`，本资产不自带登录器；**Agent 执行一律走 `python scm.py pms-status`（干净 JSON、已脱敏）**，登录走 `python scm.py pms-login`（子进程委托主技能）。
- **凭证**：`%LOCALAPPDATA%\pms-operations-query\credential.json`（**与 SCM 的 `scm-operations-query` 分离**）；关键字段 `token`、`headers`、`user{userId,userName,accountNo,account}`、`providers`、`provider_id`（单公司自动确定，多公司留空）、`provider_name`、`warehouses`、`createdAt`/`validatedAt`。
- **有效期口径**：PMS 凭证**无固定过期时间**（只有 `createdAt`/`validatedAt`），是否有效由远端 `/api/Index/index/v423` 实时校验判定；返回 `reason` 为 `missing`/`invalid`/`expired`/`not_validated`（后者多为网络或限流，**不代表凭证失效**，可重试）。
- **SCM 与 PMS 凭证互不影响**：登录其一不会覆盖或失效另一个。
- **严禁在脚本内 `scm.py login` / 自组装 PMS 登录**（会弹 GUI 挂死，且需人工扫码）。

### 1.2 业务请求形态（对 PMS 主机直连）

| 要素 | 内容 |
|---|---|
| 主机 | `https://pms.ysbang.cn`（部分微服务 `pms.leyopharm.com`） |
| 方法 | 业务接口全部 `POST`（旧版 `/api/*` 为 form，新版 `/pms-main/*` 为 JSON） |
| Content-Type | **`application/json`**（登录 form 除外） |
| 路径形态 | `/pms-main/<module>/<apiName>/v<NNNN>` |
| 请求头 | `Accept: application/json, text/plain, */*`、`Content-Type: application/json`、`module: goods_act_manage`、`__module__: goods_act_manage`、`appVersion: 14.30.1`、`platform: web`、`timestamp`（秒）、`token` |
| Body | 通用 `{token, appVersion, platform, timestamp, buildTime}` + 各接口业务字段；**`token` 在 header 与 body 各一份** |
| `buildTime` | 前端构建时刻常量（`YYYY-MM-DD HH:mm:ss`），原样透传即可；格式函数对**时/分/秒补零、月/日不补零** |
| 成功判定 | `code == "40001"`（HTTP 恒 200）；**写**接口另需 `data.data.result === 1`，业务错误在 `data.data.errorMsg` |
| 版本 | `/v27280`、`/v24100`、`/v1540` 等是 URL 一部分，**必须原样保留**（版本不对 404） |
| 网络 | 不走系统代理、禁止跟随离开官方主机的重定向 |

> **版本/模块差异**：活动管理写+查共 11 个接口统一 `ykjWholesaleOperation/.../v27280`；唯独 `pageWholeSaleByType` 走 **`wholesaleOperation/pageWholeSaleByType/v24100`**（不同 module、不同版本），不要套 v27280。

### 1.3 分页字段三套（勿混）

| 场景 | 分页字段 |
|---|---|
| `pageOneFixedWsList` / `getSpecialProductWholeSaleList` / `exportOneFixedWsList` | `page` + `pageSize`（导出无分页） |
| `pageWholeSaleByType` | `pageNum` + `pageSize` |
| 出库统计（不在本文范围） | `current` + `size` |

---

## 2. 读取（查询）

### 2.1 读取接口总表

| # | apiName / 路径 | 用途 | 关键入参 | 返回位置 |
|---|---|---|---|---|
| R1 | `ykjWholesaleOperation/pageOneFixedWsList/v27280` | **一口价**活动列表 | `providerId`(必填) + §2.3 + `page`/`pageSize` | `data.total` + `data.results[]` |
| R2 | `ykjWholesaleOperation/getSpecialProductWholeSaleList/v27280` | **特价**活动列表 | 同 R1（无 `pricingStatusList`/`abnPricingTypeList`，多 `operationFlagList`/`linkFlagList`） | 同 R1 |
| R3 | **`wholesaleOperation/pageWholeSaleByType/v24100`** | **批购包邮 / 整件购 / 随心购**列表 | `providerId` + `tabType`(2/3/4) + `pageNum`/`pageSize` | `data.total` + `data.list[]` |
| R4 | `ykjWholesaleOperation/getProductWholeSaleCount/v27280` | **五个 tab 统计卡** | `providerId` | `data` |
| R5 | `ykjWholesaleOperation/getManualOpNumByProviderId/v27280` | 手动运营品种数**额度**（如 2003/2405） | `providerId` | `data` |
| R6 | `ykjWholesaleOperation/getMyAbnWaitCheckWsNum/v27280` | **我的异常待确认**角标 | `providerId` | `data` |
| R7 | `channel/getDayAdjustPriceCount/v1540` | **待审批调价活动**角标 | `{}` | `{submitProductCount, submitWholesaleCount, waitApproveWholesaleCount}` |
| R8 | `wholesaleOperation/wholeSaleCountStat/v24100` | 批购包邮 tab 顶部**四个计数** | `providerId` + `tabType` | `{autoAdjustPriceCount, autoFollowPriceCount, inProvinceLinkCount, outProvinceLinkCount}` |
| R9 | `wholesaleOperation/getFollowNumByPid/v22240` | **跟价数** | `providerId` | `data` |
| R10 | `ykjWholesaleOperation/getYKJEnumConf/v27280` | **枚举候选**（商圈/供货对象/控销禁销组） | **`providerId`（必填，漏传 `40004`）** `page` `pageSize` `searchInfo` `type`(1/2/3) | `data.list[{id,name}]` |
| R11 | `ykjWholesaleOperation/listReviewSceneOptions/v28110` | **定价异常类型**枚举 | `providerId` | `[{type:0~10, desc}]` |
| R12 | `ykjWholesaleOperation/listWsPriceInfoBeforeEdit/v27280` | **调价弹窗**：各档现价 + 预估费率 | `tabType` `wholesaleId` | `estOutboundCost`/`manualRate`/`freightRate`/`platformRate` + 各档价 |
| R13 | `channel/checkWholesaleAudit/v351` | **调价审批**单 | `page` `pageSize` `wholesaleId` | `wsdlId`/`status`/`ruleDesc`/`priceType`/`modifiedBefore`/`After`/`hasCancelBtn` |
| R14 | `priceAdjustConfig/listWsOpRecord/v100` | **操作记录** | `wholesaleType` `wholesaleId` `contentType` `startTime` `endTime` `page` `pageSize` | `contentTypeStr`/`modifiedBefore`/`After`/操作人/时间 |
| R15 | `wholesaleOperation/pageWholesalePurchaseDetail/v29320` | **采购明细** | `providerId` `wholesaleId` `orderId` `orderTimeStart` `orderTimeEnd` `page` `pageSize` | `orderId`/`storeName`/`orderTime`/`dealPrice`/`quantity`/`totalAmount` |
| R16 | `channel/getDrugInfoByWholesaleId/v7150` | 活动对应**商品详情** | `wholesaleId` | 商品对象 |
| R17 | `drugInfo/getMedicareNetPriceByDrugId/v483` | **医保支付价** | `providerId` `drugId` | `data` |

> **R1/R2/R3 是任何写操作前的必做定位**（§3 全部写接口都需先确认现值）。

### 2.2 tab ↔ 查询接口 ↔ 编码映射（实测）

| 界面 tab | 查询接口 | `tabType` | 列表 `wholesaleType` |
|---|---|---|---|
| 一口价 | R1 `pageOneFixedWsList` | — | `1` |
| 特价 | R2 `getSpecialProductWholeSaleList` | — | `4`（不可用券） |
| 批购包邮 | R3 `pageWholeSaleByType` | **`2`** | 列表无此字段 |
| 整件购 | R3 | **`3`** | 列表无此字段 |
| 随心购 | R3 | **`4`** | —（前端源码 `Se` 确证 `apiWholeSaleType=4`；本账号返回空集） |
| ⚠️ 无效 | — | `1`/`5`/`6` | 返回 `40004` |

> 界面共 5 类 tab。实测空查询量：`tabType=2` 全量 19552（状态全 5）、`tabType=3` 全量 7989（状态 3/5/6 混合）。

### 2.3 筛选参数全表（R1/R2 通用；R3 同构 + `tabType`/`pageNum`/`negMarginProfitRate`）

| 参数 | 对应 UI | 类型 | 说明 |
|---|---|---|---|
| `providerId` | 平台店铺 | string | **必填**，缺失则查不到任何活动；由凭证动态取得 |
| `wholesaleId` | 活动ID | string | 精确匹配；**带它时 `wholesaleStatus` 被忽略** |
| `wholesaleStatus` | 活动状态 | int | 见 §5.1；页面默认 `5` 进行中 |
| `provDrugCode` | 药师帮ID（精确字段） | string | 商品编码，如 `YP00085`；**直接 body 指定有效**（实测 16023→27） |
| `drugKeyword` | 商品/药师帮ID 输入框 | string | UI 上 placeholder 为"商品名称/药师帮ID"的输入框传此字段（实测填 `YP00085`→`drugKeyword`，**不是** `provDrugCode`）；两字段并存，精确筛选用 `provDrugCode` |
| `approval` | 批准文号 | string | 如 `国药准字H20093819` |
| `factory` | 厂家 | string | 模糊 |
| `enterprise` | 厂牌营销方 | string | |
| `contactor` | 品种负责人 | int | **userId 数字**（实测"张琼宁"→`44871`）；数据源 **R20** `getChildrenValidUser(userType=contactor)` |
| `operator` | 运营负责人 | int | **userId 数字**（实测"张丹"→`1001`）；数据源 **R20**（userType=operator） |
| `bpManager` | 厂牌项目经理 | int | **userId 数字**；数据源 **R21** `bpManagerChooseListWithSubUser` |
| `busiFlag` | 业务类型 | string | 见 §5.4 |
| `checkFlag` | 考核品种 | int | **页面默认 `1`**（只看考核品种，源码 `st()` 确认）；要全部品种须显式置 `""`。注意：默认 `1` 会窄化范围，实测两者均置 1 时曾导空，见 §4 踩坑 |
| `leyoTagIdList` | 标签筛选（集团自定义标签） | int[] | tagId 数组（**R22** `getDiyTagListForFilter` → `data.leyoTags`） |
| `provTagIdList` | 标签筛选（子公司自定义标签） | int[] | tagId 数组（**R22** → `data.provTags`） |
| `pricingStatusList` | 定价状态 | list | 数组 |
| `abnPricingTypeList` | 定价异常类型 | int[] | `0~10`（R11） |
| `specialFlag` | **维价类型**（非特价标记） | int | `0`无 / `2`集团维价 / `3`集采维价 / `6`采购维价（UI 四项全实测，见 §5.13） |
| `operationFlagList` | 运营策略多选 | int[] | `1`自动 / `2`手动 / `8`临时手动；空=全部 |
| `linkFlagList` | 链接类型多选 | int[] | `1`长期 / `2`短期；空=全部 |
| `saleStatDataType` | 销量统计口径 | int | `1`=近28天，固定 1 |
| `beClickAbnWaitCheck` | 点击"异常待确认"卡 | int/str | 仅点击该卡时置 `1`，**常规查询/导出留空 `""`** |
| `beClickMyAbnWaitCheck` | 点击"我的异常待确认"卡 | int/str | 仅点击该卡时置 `1`，**常规查询/导出留空 `""`**（见 §4 踩坑说明） |
| `page`/`pageSize` | 分页 | int | R3 用 `pageNum` |
| `negMarginProfitRate` | 负毛利（**R3 独有**） | string | |

**实测有效的核心过滤**：`wholesaleId`（精准 total=1）、`wholesaleStatus`（16023→2098 等）、`provDrugCode`（16023→27）。
**实测无效**：`status`/`statusList`/`wsStatus`/`queryStatus`/`drugId`/`searchInfo`/`keyword`/`drugName`/`searchValue`（均回落全量）。

### 2.4 响应行关键字段（R1/R2 `data.results[]`；R3 为 `data.list[]`）

| 分组 | 字段 |
|---|---|
| 活动 | `wholesaleId` `wholesaleType`/`wholesaleTypeDesc` `wholesaleStatus`/`wholesaleStatusStr` `operationFlag` `beginDateStr` `endDateStr` `createTime` `validDate` `offNote` `offTime` |
| 商品 | `drugCode` `provDrugCode` `drugId` `cnName` `drugName` `pack` `approval` `factory` `enterpriseName` `businessType` `busiFlag`/`busiFlagStr` |
| 人员 | `uname` `operator` `contactor` `bpManagerName` |
| 价格 | `salePriceList[]`（`priceType`+`value`/`suggestPrice`/`beAuditing`/`auditingPrice`）、`unitPrice`/`unitPrice1~9`/`chainPrice` |
| 限购 | `minQty` `maxAmountPerStore` `calculatePeriod` `step` |
| 定向 | `areaGroupId`/`Name` `storetypeGroupId`/`Name` `isRestrict` `restrictId` `restrictDesc` |
| 标签 | `leyoDiyTags`/`Str` `provDiyTags`/`Str` |
| 统计 | `proStoreRank28` `proCustomerNum7/28` `customerNum7/28` `proSalesNum7/28` `salesNum7/28` `avgUnitPrice7/28` `cnUnitPrice7/28` `customerMarketRate7/28` `salesMarketRate7/28` |
| 库存 | `stockExOcc` `stockAvailable` `canSaleDays` `rationalP4` `hasMedicarePrice` |

> R3 额外行字段：`operationFlagStr`（自动调价/自动跟价）、`linkFlagStr`（省内/省外链接）、`relationWholesaleId`（链接源活动）、`followFactor`/`inPriceFactor`/`outPriceFactor`、`marginProfitRate`、`saleSituation{storeCount,quantity,amount}`。

### 2.5 筛选区下拉数据源（7 个，缺一个下拉就填不了值）

| # | 筛选项 | 接口 | 请求体要点 |
|---|---|---|---|
| R18 | 平台店铺（公司口径） | `pms.ysbang.cn/pms-main/merpUser/getSubProviderList/v2050`（即 §1.1 ⑥） | 公共参数 → `providers[]` / `provider_id` / `provider_name`，取 ID 填 `providerId`；**不是**发货仓接口（发货仓 `providerWarehouseOption` 见 §1.1 ⑦，非筛选区下拉） |
| R19 | 商品 | `pms.leyopharm.com/datacenter_pms/web/search/goodsOption/pv7240` | `{size:100, providerId, goods:"<关键词>"}` → `goodsName/goodsId/goodsSpec/goodsCode/approvalNo/manufacturer/drugId/productCode` |
| R20 | 品种负责人 / 运营负责人 | `pms-main/drugInfo/getChildrenValidUser/v7160` | `{userType:"contactor", providerId, keyword:""}` → `[{userId,username}]`；`userType` 随下拉切换（`contactor`=品种负责人） |
| R21 | 厂牌项目经理 | `pms-main/common/bpManagerChooseListWithSubUser/v15120` | `{providerId}` → `[{userId,erpName}]` |
| R22 | 业务标签 | `pms-main/tagManage/getDiyTagListForFilter/v1630` | `{providerIds:[<id>]}` → `data.leyoTags[]` + `data.provTags[]`，id 填 `leyoTagIdList`/`provTagIdList` |
| R23 | 定价异常类型 | `pms-main/ykjWholesaleOperation/listReviewSceneOptions/v28110` | 同 R11（`0~10` + desc） |
| R24 | 均价开关 | `pms-main/common/avgPriceSwtich/v910` | `{providerId}` → `{avgSwitch:1}` |

> 引用关系：§2.3 的 `contactor`/`operator` 候选由 **R20** 提供，`bpManager` 由 **R21** 提供，`leyoTagIdList`/`provTagIdList` 由 **R22** 提供；`abnPricingTypeList` 与 R11/R23 同源。

### 2.6 状态枚举 `wholesaleStatus`（PMS 全集）

| 值 | 语义 | 一口价全量 total |
|---|---|---|
| `0` | 待开始 | 4 |
| `5` | 进行中（页面默认） | 6534 |
| `3` | 已下架 | 2098 |
| `4` | 缺货下架 | 7387 |
| `6` | 未销售（`UN_SALE`，2026-11-17 前端源码 `Pe.UN_SALE=6` 补录；页面状态下拉是否展示待确认） | — |
| 不带 | 返回全部 | 16023 |

> **前端源码常量（2026-11-17 Scrapling 逆向 chunk 99623）**：`Pe={DOING:5, TO_START:0, off_SALE:3, off_SALE_STOCK_OUT:4, UN_SALE:6}`；状态筛选选项 `Ee` 含"进行中/待开始/已下架/缺货下架/未销售"五项。
> **PMS 只有上架/下架两态**：`ACTIVITY_STATUS_TEXT={5:'上架',3:'下架'}`、`ACTIVITY_STATUS_UPDATE_CODES={5:[2,0],3:[1]}`，**不存在"结束/终态"码**（`7`=已结束属 SCM 枚举）。
> **与 SCM 勿混**：SCM `status` = `0`进行中/`4`已下架/`7`已结束（见 `api_商品读取.md §1.2`）。

### 2.7 标准定位流程（写操作前必做）

1. `{providerId, wholesaleId}` → 按 §2.2 选接口 → 取 `wholesaleStatus`/`operationFlag`/`wholesaleType`。
2. 按商品反查：`{providerId, provDrugCode}` → 该药品全部活动。
3. 按状态批量筛：`{providerId, wholesaleStatus, page, pageSize}`。

> **四套编码勿互推**：PMS 写 `wholeSaleType`(1/2) ≠ 查询 `tabType`(2/3/4) ≠ SCM `wholesaleType`(1/4/5/6/7/71/8/10/11) ≠ 状态枚举。
> 字段名：写 `wholeSaleId`（大写 S）vs 查 `wholesaleId`（小写 s），**值相同**；PMS `restrictId` vs SCM `restrictGroupId`，值相同。

---

## 3. 写入

> **本节全部为真实写接口**：写前必查现值（§2）、留回滚值与审计（`AGENT_GUIDE.md §10`）、写后按 §2 复查询核验。
> 成功判定统一：`code=40001` **且** `data.data.result === 1`。

### 3.1 写入接口总表

| # | apiName / 路径 | 用途 | 关键入参 |
|---|---|---|---|
| W1 | `ykjWholesaleOperation/updateYkjWholeSaleStatus/v27280` | **下架 / 重上架** | `wholeSaleId` `wholeSaleType` `status`(1下/2上) |
| W2 | `ykjWholesaleOperation/checkUpdateOneFixedWsOpFlag/v27280` → `updateOneFixedWsOpFlag/v27280` | **运营策略**（自动↔手动，两步） | `wholesaleId` `operationFlag`(1/2) |
| W3 | `ykjWholesaleOperation/updateYkjWsActivityTime/v27280` | **活动期间**（时间窗） | `wholeSaleId` `beginDate` `endDate` `wholeSaleType` |
| W4 | `ykjWholesaleOperation/updateGoodsSaleLimitConf/v27280` | **限购参数**（起订量/步长/单店上限/周期） | `wholesaleId` `providerId` `minQty` `step` `maxAmountPerStore` `calculatePeriod` |
| W5 | `ykjWholesaleOperation/updateGoodsSaleAreaConf/v27280` | **定向管理**（控销/禁销） | `wholesaleId` `providerId` `areaGroupId` `storetypeGroupId` `isRestrict` `restrictId` |
| W6 | `channel/fastAdjustPriceBatch/v1540` | **快速调价**（批量，走审批） | `provDrugCode` `providerId` `warehouseId` `fastAdjustPriceRequestList[]` |
| W7 | **`/api/sale/cancelAudit/v351`（form）** | **撤销调价审批** | `wsdlId` + 公共 form 字段 |

### 3.2 下架 / 重上架（W1）

| 要素 | 内容 |
|---|---|
| 参数 | `wholeSaleId` + `wholeSaleType` + **`status`**：`1`=下架 / `2`=重上架（`0` 无需尝试） |
| 下架成功 | `result=1`；复验 `wholesaleStatus=3` + `offTime` 落库 |
| 重上架成功 | `result=1`；复验 `wholesaleStatus=5` |
| **前置规则** | 查询 `operationFlag=1`（自动运营）→ **必须先按 §3.3 切手动运营再下架**；`0/2` 可直接下架 |
| **副作用** | 重上架会**强制切为手动运营**并提示"请检查价格" |
| 结束终态 | **PMS 无结束能力**（无终态码）；SCM `batchEnd` 对自营软成功但不改状态 → **自营活动无法经任一 API 结束，须走网页端** |

### 3.3 运营策略：自动 ↔ 手动（W2，两步）

| 要素 | 内容 |
|---|---|
| 接口 | **两步**：`checkUpdateOneFixedWsOpFlag`（校验）→ `updateOneFixedWsOpFlag`（提交）；两步均须 `result=1` |
| 参数 | `wholesaleId` + `operationFlag`（**`1`自动 / `2`手动**）；**无 `providerId`/`wholeSaleType`** |
| 适用范围 | 调用层不限活动类型（payload 只有两个字段），**实测仅覆盖一口价**；非一口价先验证 |
| 前置 | 能否切换取决于**当前** `opFlag`：只有 `1` 可切；`operationFlag=0` 切手动报 `40003` |

### 3.4 活动期间 / 时间窗（W3）

- `beginDate`/`endDate`：`yyyy-MM-dd HH:mm:ss`，省略时刻默认 `00:00:00` / `23:59:59`；`endDate` 不得早于 `beginDate`。
- 参数用 **`wholeSaleId`**（大写 S）+ `wholeSaleType`。
- **SCM 对应**：`beginDate`/`endDate` 在 SCM 复制/整表编辑时可改且持久化，本接口为备选出口。

### 3.5 限购参数（W4）

| 字段 | 界面 | 说明 |
|---|---|---|
| `minQty` | 起订量 | >0，且 ≥ `step`、为其整数倍；**勿漏传**（否则报错） |
| `step` | 购买倍数 | >0；**勿漏传** |
| `maxAmountPerStore` | 单店采购上限 | **`0`=不限** |
| `calculatePeriod` | 上限刷新周期 | `0`活动期内 / `1`每笔 / `2`每天 / `3`每周 / `4`每月 |

- 界面留空字段取**当前活动现值回填**，不是跳过。
- **SCM 对应**：`maxAmountPerStore` 在 SCM 改不落库 → **本接口是唯一真正出口**（`api_商品写入.md §1.1` 标 ④ 转PMS）。

### 3.6 定向管理：控销 / 禁销（W5）

| 字段 | 界面 | 取值 |
|---|---|---|
| `areaGroupId` | 商圈 | 候选 R10 `type=1` |
| `storetypeGroupId` | 供货对象 | 候选 R10 `type=2` |
| `isRestrict` | 是否控销 | **`0`否 / `1`控销 / `2`禁销** |
| `restrictId` | 控销/禁销组 | 候选 R10 `type=3`；`isRestrict=0` 时强制 `restrictId=0` |

- **前置**：当前活动缺 `areaGroupId` 或 `storetypeGroupId` 时报错，**不盲发**。
- **键名差异**：SCM `restrictGroupId` ≠ PMS `restrictId`（值相同）。

### 3.7 价格类写入（W6 / W7）—— 唯一价格改动出口

| 要素 | 内容 |
|---|---|
| 快速调价 | `POST /pms-main/channel/fastAdjustPriceBatch/v1540`，body：`provDrugCode` + `providerId` + `warehouseId` + `fastAdjustPriceRequestList:[{wholesaleId, updatePriceList:[{name,type,value,note}]}]` |
| `type`（价格档） | `1`偏远省份价 / `2`省内价 / `7`周边省份价 / `8`KA价 / `-1`单体价 / `-2`连锁价 |
| 返回 | message 汇总"X个成功 / X无变化 / X需审批 / X失败"（**可能进审批流，不等于立即生效**） |
| 撤销审批 | `POST /api/sale/cancelAudit/v351`（form）`wsdlId=<审批单ID>` + 公共 form 字段 |
| 审批查询 | R13 `checkWholesaleAudit/v351`；`status` 见 §5.6；`hasCancelBtn=1` 才可撤销 |
| **SCM 对应** | SCM `editPrices` **两账号均不可用**（`api_商品写入.md §1.1` ⑤ 禁用）；SCM 侧唯一替代是整表 `addWholesale(mode=edit)`。**PMS 快速调价是走审批的正式出口**，两者口径不同，勿混 |

> **不可盲试**：价格与费率强相关，动手前必须先用 R12 取现值与预估费率。

### 3.8 字段缺口（明确无接口，勿臆造）

| 字段 | 状态 | 说明 |
|---|---|---|
| `ifLimit` / `maxAmount`（是否限购 + 限购数量） | **缺口** | PMS 限购板块只有 `minQty`/`step`/单店上限/周期，无此二字段 |
| `wsDesc`（活动备注） | 不适用 | SCM `editWsDesc` 可直接改（复验走 `wsList`），见 `zddz.md §5` |
| 活动**结束**（终态） | **无接口** | PMS 无终态码；自营须网页端 |

---

## 4. 导出（**同步 xlsx 二进制流**，非异步任务）

> **与 SCM/促销的异步三步链完全不同**：PMS 活动导出是 **POST JSON → 响应体即 xlsx 二进制**，**无任务 ID、无轮询、无加密 zip**。

| # | 接口 | 用途 | 活动类型（一级 tab） |
|---|---|---|---|
| E1 | `POST /pms-main/ykjWholesaleOperation/exportOneFixedWsList/v27280` | **一口价**导出 | 一口价 |
| E2 | `POST /pms-main/ykjWholesaleOperation/downloadSpecialProductWholeSaleList/v27280` | **特价**导出 | 特价 |
| E3 | `POST /pms-main/wholesaleOperation/exportWholeSaleByType/v24100` | **批购包邮 / 整件购 / 随心购**导出 | 由 `tabType` 区分（2/3/4） |

> E3 补自 2026-11-17 实机采集（`参考区/采集文件/Pms_采集结果.json`）。三套导出与列表接口 R1/R2/R3 **一一对应**，请求体 = 对应列表查询同款筛选（去掉分页）+ 点击标记，**无分页字段**。

### 4.1 默认筛选模型（用户口径 → 参数）

| 场景 | 默认参数 |
|---|---|
| 平台店铺 | `providerId` = 当前账号店铺（单公司自动确定，如 3364；多公司需用户指定） |
| 活动状态 | `wholesaleStatus: 5`（进行中） |
| 考核品种 | `checkFlag: 1`（是） |
| 活动类型 | 默认**一口价** → 走 E1；`tabType`/二级选项均不设 = 该类型全部 |
| 用户改活动类型 | 一口价→E1、特价→E2、批购包邮/整件购/随心购→E3（`tabType`=2/3/4）；**不主动选二级选项即代表该类型全部** |

> ⚠️ **照抄警示**：下方示例已给"常规全量"中性默认值，可直接照抄。但两个窄化标记要理解：`checkFlag`（`1`=只看考核品种）、`beClickMyAbnWaitCheck`（`1`=只点"我的异常待确认"卡）。**默认模型里 `checkFlag=1` 是业务默认（考核品种=是），照抄会重现该默认**；若用户要全部品种须置 `""`。实测：`checkFlag`/`beClickMyAbnWaitCheck` 均置 1 → 曾导空；置空 → 6607 行。`token`/`buildTime` 由请求层自动注入，**body 不必手填**。

### 4.2 基础筛选项 → 参数映射（三套导出通用，来源 §2.3）

> ⚠️ **动态下拉选的是 ID/数字值，不是界面显示名**（2026-11-17 浏览器实测）：用户看到"张琼宁"，传给接口的是 `contactor:44871`（userId）；看到"集采维价"传 `specialFlag:3`。**必须从下拉数据源取 ID 填入，禁止把显示名当值传**。下拉数据源接口见 §2.5（R18-R24），多数在页面加载时已缓存，点击时不一定发新请求。

| 用户筛选项 | 参数 | 取值（实测） | 动态下拉数据源 |
|---|---|---|---|
| 平台店铺 | `providerId` | 店铺 ID（单公司自动确定，如 `3364`；选当前店不改变） | R18 `getSubProviderList` |
| 活动ID | `wholesaleId` | 精确 | 手输 |
| 活动状态 | `wholesaleStatus` | `5`进行中/`0`待开始/`3`已下架/`4`缺货下架（UI 实测四项） | 静态 |
| 商品 | `drugKeyword` | 关键词（placeholder"商品名称/药师帮ID"） | R19 `goodsOption`（模糊搜索） |
| 药师帮ID | `provDrugCode` | 编码 | 手输/商品下拉 |
| 批准文号 / 厂家 / 厂牌营销方 | `approval` / `factory` / `enterprise` | 文本 | 手输 |
| 品种负责人 | `contactor` | **userId 数字**，实测"张琼宁"→`44871` | R20 `getChildrenValidUser(userType=contactor)` |
| 运营负责人 | `operator` | **userId 数字**，实测"张丹"→`1001` | R20（userType=operator） |
| 厂牌项目经理 | `bpManager` | **userId 数字**，实测"杨燕念"等 | R21 `bpManagerChooseListWithSubUser` |
| 业务标签（界面显示集采/普品/控销） | `busiFlag` | `5`普品/`3`集采（实测"普品"→`5`）；**不是** `leyoTagIdList` | 静态枚举 §5.4 |
| 考核品种 | `checkFlag` | 页面默认 `1`（只看考核品种）；全部品种置 `""` | 静态 |
| 链接类型 / 定价模式 / 定价状态 / 定价异常类型 | `linkFlagList`/`pricingStatusList`/`abnPricingTypeList` 等 | 见 §5；定价异常类型候选 R11/R23 | 筛选型下拉（本地过滤） |
| 预估负利润率 | `negMarginProfitRate` | **仅 E3**（批购包邮等 tab 才显示） | 手输 |
| 维价类型 | `specialFlag` | `0`无/`2`集团维价/`3`集采维价/`6`采购维价（UI 四项全实测） | 静态 §5.13 |
| 标签筛选（集团/子公司自定义标签） | `leyoTagIdList`/`provTagIdList` | **tagId 数字数组**，实测 `leyoTagIdList:[7]`（首推精品厂牌）、`provTagIdList:[178]`（A1B3重点品种）；界面两大组"集团自定义标签/子公司自定义标签"是**两个并列多选下拉**（非 cascader），分别映射到两个参数 | R22 `getDiyTagListForFilter` → `data.leyoTags[]`/`data.provTags[]`（各含 `tagId`+`tagName`） |

**控件类型与取数/传参方式（2026-11-17 全项实测）**：

| 控件类型 | 筛选项 | 如何取值 | 如何传参 |
|---|---|---|---|
| **纯输入框** | 活动ID、药师帮ID（`商品名称/药师帮ID`）、批准文号、厂家、厂牌营销方 | 用户直接输入文本 | 活动ID→`wholesaleId`；药师帮ID框→`drugKeyword`（**不是** `provDrugCode`）；其余→对应文本字段 |
| **静态下拉**（页面加载缓存，点击不触发 XHR） | 平台店铺、活动状态、商品、品种负责人、运营负责人、厂牌项目经理、业务标签、考核品种、预估负利润、维价类型 | 点开选一项；候选值为 **ID 数字/枚举**（非显示名） | 见上表各参数；如"张琼宁"→`contactor:44871`、"普品"→`busiFlag:5`、`wholesaleStatus` 5/0/3/4、`specialFlag` 0/2/3/6 |
| **筛选型下拉**（filterable，本地过滤候选、非真远程） | 链接类型、定价模式、定价状态、定价异常类型 | 输入关键字→**本地过滤**已缓存候选（如输"成本"→成本异常/成本偏高），无 XHR | 见 §5；`abnPricingTypeList`/`pricingStatusList` 等数组 |
| **多级标签选择**（两大组并列多选，R22 供数） | 标签筛选 | 点"集团自定义标签"/"子公司自定义标签"→触发 R22→从 `leyoTags`/`provTags` 取 `tagId` | `leyoTagIdList:[tagId...]` / `provTagIdList:[tagId...]` |

> **端到端传参铁证（2026-11-17）**：① 标签筛选用真实 `tagId`（`leyoTagIdList:[7]`、`provTagIdList:[178]`）导出得 136 行（全量 6607 行），筛选确实生效；② 组合筛选（活动状态=已下架 `wholesaleStatus:3` + 品种负责人=张琼宁 `contactor:44871` + 维价=集采 `specialFlag:3`）三项均正确进入导出 body；③ 维价 UI 四项全实测：无→`0`、集团→`2`、集采→`3`、采购→`6`。**自定义筛选与自定义导出链路全通**。

### 4.3 活动类型二级选项 → 参数

| 一级 | 二级选项（UI） | 参数 |
|---|---|---|
| 一口价 | 自动运营 / 手动运营 / 临时手动 | `operationFlagList`（`1`/`2`/`8`） |
| 一口价 | 长期链接 / 短期链接 | `linkFlagList`（`1`/`2`） |
| 一口价 | 异常待确认 / 我的异常待确认 | `beClickAbnWaitCheck` / `beClickMyAbnWaitCheck`（置 `1`） |
| 特价 | UI 无二级 | E2 仍带 `operationFlagList`/`linkFlagList`（实测均 `[]`） |
| 批购包邮 / 整件购 / 随心购 | 自动调价 / 自动跟价 | `operationFlag`（**单值** `1`自动调价 / `2`自动跟价，采集实测 `1`） |
| 批购包邮 / 整件购 / 随心购 | 省内链接 / 省外链接 | `linkFlag`（**单值** `1`省内 / `2`省外）——**2026-11-17 浏览器实测确认**：列表 `pageWholeSaleByType` 与导出 `exportWholeSaleByType` 均用此字段；**不是** `linkFlagList`（那是 E2 特价的数组字段） |

> ⚠️ **E3 与 E2 的链接字段不同**：E3 批购包邮系用单值 `linkFlag`（1/2），E2 特价用数组 `linkFlagList:[]`——勿混用。点二级选项后**列表会先发一次带该参数的请求**，导出请求带同样的参数（实测点击"省内链接"→ `linkFlag:1` 出现在两个请求 body）。

### 4.4 请求体模板

**E1 一口价 / E2 特价**（差异：E2 无 `pricingStatusList`/`abnPricingTypeList`，多 `operationFlagList`/`linkFlagList`）：

```json
{ "providerId": "<当前providerId>", "wholesaleId": "", "wholesaleStatus": 5,
  "provDrugCode": "", "drugKeyword": "", "approval": "", "factory": "",
  "enterprise": "", "contactor": "", "operator": "", "bpManager": "",
  "busiFlag": "", "checkFlag": 1,
  "leyoTagIdList": [], "provTagIdList": [],
  "pricingStatusList": [], "abnPricingTypeList": [],
  "specialFlag": "", "saleStatDataType": 1,
  "beClickAbnWaitCheck": "", "beClickMyAbnWaitCheck": "",
  "operationFlagList": [], "linkFlagList": [],
  "token": "<TOKEN>", "buildTime": "<前端构建时刻>" }
```

**E3 批购包邮/整件购/随心购**（`tabType` 2/3/4；多 `negMarginProfitRate`/`operationFlag`）：

```json
{ "providerId": "<当前providerId>", "wholesaleId": "", "wholesaleStatus": 5,
  "provDrugCode": "", "drugKeyword": "", "approval": "", "factory": "",
  "enterprise": "", "contactor": "", "operator": "", "bpManager": "",
  "busiFlag": "", "checkFlag": 1,
  "leyoTagIdList": [], "provTagIdList": [],
  "specialFlag": "", "saleStatDataType": 1, "negMarginProfitRate": "",
  "tabType": 2, "operationFlag": 1,
  "linkFlag": "",
  "token": "<TOKEN>", "buildTime": "<前端构建时刻>" }
```
> E3 二级选项按需填：`operationFlag`（1自动调价/2自动跟价）、`linkFlag`（1省内/2省外）；**不填 = 该维度全部**（UI 不主动选二级选项的语义）。实测：点"省内链接"→ `linkFlag:1`；点"省外链接"→ `linkFlag:2`。

- **取文件**：`requests` 必须 `stream=True`；从响应头 `Content-Disposition` 取文件名落盘（body 即 xlsx，无需 url 下载）。
- **耗时**：实测 4000+ 行约 2~5 秒。
- **筛选必须带全**：缺字段服务端按默认处理，会导错范围 → **导出前先按 §2 确认筛选**。
- **频控**：PMS 高并发（≥16 线程）会触发连接重置，批量并发 **≤6**。
- **禁止**套用 `通用/api_导出任务.md` 的三段式轮询（那是 SCM `/export-file/` 的口径）。

---

## 5. 枚举字典

### 5.1 活动状态 `wholesaleStatus`

`0`待开始 / `5`进行中（页面默认）/ `3`已下架 / `4`缺货下架 / `6`未销售（源码 `Pe.UN_SALE`，页面是否展示待确认）；不带=全部。**无"结束/终态"码**。

### 5.2 运营方式 `operationFlag`

`1`自动运营（自动调价）/ `2`手动运营（自动跟价）/ `8`临时手动 / `0`非自动运营态（切手动报 `40003`）。

### 5.3 链接类型 `linkFlag` / `linkFlagList`（勿混）

- **E3 批购包邮系**：单值 `linkFlag`，`1`省内链接 / `2`省外链接（2026-11-17 浏览器实测，列表+导出同字段）。
- **E1/E2 一口价/特价的"长期/短期链接"二级选项**：数组 `linkFlagList`，`1`长期 / `2`短期（见 §4.3）。
- 两者字段形态（单值 vs 数组）与语义（省内省外 vs 长期短期）**都不同**，勿混用。

### 5.4 业务类型 `busiFlag`

`5`普品 / `3`集采 / `1`·`2`·`4` 其余（业务大类由 `businessType` 文本给出）。

### 5.5 价格档 `priceType` / `type`

`1`偏远省份价 / `2`省内价 / `7`周边省份价 / `8`KA价 / `-1`单体价 / `-2`连锁价。

### 5.6 调价审批 `status`（`checkWholesaleAudit`）

`0`待审批（`hasCancelBtn=1` 可撤销）/ `1`已通过 / `4`已撤销。

### 5.7 定价异常类型（`listReviewSceneOptions`）

`0`正常 `1`成本异常 `2`无分箱且无均价 `3`滞销品 `4`短期涨价 `5`短期跌价 `6`与当前价差>5% `7`托底价 `8`近效期 `9`七天不动销 `10`成本偏高。

### 5.8 活动 tab `tabType`

`2`批购包邮 / `3`整件购 / `4`随心购；`1`/`5`/`6` 无效（返回 `40004`）。

### 5.9 写接口活动类型码 `wholeSaleType`

**仅 `1` 一口价 / `2` 特价**；批购包邮/整件购/随心购按默认 `1`。

### 5.10 限购刷新周期 `calculatePeriod`

`0`活动期内 / `1`每笔 / `2`每天 / `3`每周 / `4`每月。

### 5.11 控销 / 禁销 `isRestrict`

`0`否 / `1`控销 / `2`禁销（`0` 时强制 `restrictId=0`）。

### 5.12 枚举候选 `getYKJEnumConf.type`

`1`商圈 / `2`供货对象 / `3`控销禁销组（**仅此三值**）。

### 5.13 维价类型 `specialFlag`

`0`无 / `2`集团维价 / `3`集采维价 / `6`采购维价（2026-11-17 UI 四项全部实测）。**字段名叫 `specialFlag` 但对应 UI「维价类型」，不是「特价」标记。**

> **四套编码系统切勿互推**：PMS 写 `wholeSaleType`(1/2) ≠ 查询 `tabType`(2/3/4) ≠ SCM `wholesaleType`(1/4/5/6/7/71/8/10/11) ≠ 各自状态枚举。字段名 `wholeSaleId`(写) ≠ `wholesaleId`(查)，`restrictId`(PMS) ≠ `restrictGroupId`(SCM)，值相同。

---

## 6. 批量执行模型（幂等，直连复刻时参考）

| 要素 | 内容 |
|---|---|
| 并发 | 默认 20，拉取式 worker 池；**建议 ≤6**（PMS 高并发会连接重置） |
| 单活动流程 | 按 ID 查询定位 → 逐板块比对现值 → **只发需要改的板块**（全是目标值则跳过）→ 改完复查询回填 `after` |
| 板块顺序 | 限购参数 → 定向管理 → 活动期间 → 运营策略 → 活动状态 |
| 结果口径 | `not_found` / `already_target` / 成功 / 失败（含失败详情汇总） |

---

## 7. 红线与待确认

**红线（写前必读）**

1. 这些是**真实活动写接口**：写前必查现值、留回滚值与审计记录，写后按 §2 复查询核验（`result==1` + `wholesaleStatus`/`offTime` 落库）。
2. **价格相关**走 W6 快速调价（审批流）或 SCM 整表编辑；**勿臆造价格接口**。
3. 登录走 `python scm.py pms-login`（子进程委托主技能 PMS 登录器）/ `core.pms_client` 凭证门面，**禁止自组装登录**；业务请求按 §1.2 直连 PMS 官方主机。
4. 自动运营活动（`operationFlag=1`）下架前**必须先切手动运营**；重上架会强制改运营策略，操作前须确认影响。
5. 导出是**同步二进制流**，禁止套异步三步链；筛选必须带全。
6. **测试活动必下架**：为验证产生的活动收尾须复验为已下架，不留活口。
7. **凭证明文不外传**：`credential.json` 与主技能 PMS 登录器 `--status` 的输出均含 `token`，**不得写入日志、记录区、对话或提交仓库**；对外只报 `account`/`providerId`/`providerName` 等非敏感摘要（`python scm.py pms-status` 已按此脱敏）。

**待确认**

> 商品板块唯一待确认台账见 `sy.md §4`（三份文档共用，避免漂移）。本文相关：
> - 已确认：PMS 无结束终态（§2.6/§3.2）、`wholeSaleType` 仅 1/2（§5.9）、`calculatePeriod` 含 `4` 每月（§5.10）、`getYKJEnumConf.type` 仅 1/2/3（§5.12）、运营策略调用层不限类型（§3.3）、`buildTime` 格式（§1.2）、导出为同步流（§4）、`tabType=4`↔随心购（前端源码 `Se` 确证，2026-11-17）、状态 `6`=未销售（源码 `Pe.UN_SALE`，页面展示待确认）。
> - 仍待实测：PMS 挂网价与 SCM 设定价口径差异（`unitPrice9` 显示源价）、非一口价活动的写接口/运营策略实际行为、`fastAdjustPriceBatch` 的审批流阈值、状态 `6` 在页面状态下拉是否可点选。
