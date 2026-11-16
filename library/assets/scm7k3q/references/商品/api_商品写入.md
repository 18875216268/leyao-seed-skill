# 商品写入（API）

> 账号判定见 `sy.md §3.2`；写操作红线见 `sy.md §3.4`；字段/复验见 `zddz.md`。写操作须按 `AGENT_GUIDE.md §10` 授权。板块/文档归属见 `references/sy.md §0`。
>
> **本文裸 § 引用约定（消歧）**：凡**未注明文件名**的 `§2.x` / `§3.x`（如 `§2.1`/`§3.2`/`§3.5`/`§3.8`），**均指 `references/商品/api_pms活动管理.md`**（PMS 域）；本文自身章节只有 `§1.x`。看到 `转 ④ §3.x` 一律按 PMS 文档解析。

## 1. 写入

> **全部写操作须按 `AGENT_GUIDE.md §10` 授权、限范围、留回滚值与审计日志。**

### 1.1 接口总表（按账号分类，每行唯一归类）

> **账号分类列取值（四类 + 例外，权威定义见 `sy.md §3.1`）**：
> ① **`通用`**＝所有账号通用；② **`仅摇钱树`**＝仅摇钱树账号；③ **`仅自营`**＝仅自营账号；④ **`转PMS`**＝转 `Pms_活动管理`（自营侧被自动运营接管，实际出口在 `api_pms活动管理.md`）；⑤ **`禁用`**＝两账号均不可用/无 API 出口（例外类，须走网页端）。
> 分类只对**该行接口**成立；"自营列/摇钱树列"是该分类下的**具体行为与出口**，不是第二个分类。自营/摇钱树是**权限体系**称谓，非具体账号（账号由凭证动态取得，勿硬编码）。

| 操作 | 路径 | 账号分类 | 自营账号 | 摇钱树账号 |
|---|---|---|---|---|
| 复制新建 | `/scm-goods/wholesaleDrug/addWholesale`（`mode=copy`） | ① 通用 | ✅ | ✅ |
| 整表编辑 | 同上（`mode=edit`） | ① 通用 | ⚠️ PMS 托管字段不落库：限购类转 ④ `api_pms活动管理.md §3.5`、定向类转 ④ `§3.6`（`ifLimit`/`maxAmount` 无接口，见该文 §3.8） | ✅ 全字段可用 |
| 批购包邮整表编辑 | `/scm-goods/freeShipping/addWholesale`（`ex=batchFsShelfDetail`） | ① 通用 | ✅ | ✅（wt=8 必用此端点） |
| 改说明 | `/scm-goods/wholesaleDrug/editWsDesc` | ① 通用 | ✅ | ✅ |
| 改价格提示 | `/scm-goods/wholesaleDrug/editWsPriceTips` | ① 通用 | ✅ | ✅ |
| 改主图 | `/scm-goods/wholesaleDrugOnsale/updateLogo` | ① 通用 | ✅ | ✅ |
| 改排序 | `/scm-goods/wholesaleDrug/editOrder` | ① 通用 | ✅ | ✅ |
| 改库存 | `/scm-goods/wholesaleDrug/editStock2` | ① 通用 | ✅ | ✅ |
| 改阶梯价（单品阶梯价） | `/scm-promotion/admin/singleCoupon/addLadderPrice` | ③ 仅自营 | ✅ | ❌ 无此功能（界面无入口，见 §1.9） |
| 图片上传 | `/scm-base/common/upload2Local` | ① 通用 | ✅ multipart | ✅ multipart |
| 改单店上限 | `/scm-goods/wholesaleDrug/editMaxAmountPerStore` | ② 仅摇钱树 | 不可用：转 ④ `api_pms活动管理.md §3.5` | ✅ |
| 批量下架 | `/scm-goods/WholesaleDrugES2/batchPause` | ② 仅摇钱树 | 软成功（rc=0）：转 ④ `api_pms活动管理.md §3.2` | ✅ 真实生效 |
| 单条下架 | `/scm-goods/WholesaleDrugES2/pause` | ② 仅摇钱树 | ❌ `40003 自动运营活动，不可手动编辑`；转 ④ `§3.2` | ✅（拼团须单条） |
| 批量重上架 | `/scm-goods/WholesaleDrugES2/batchRestart` | ② 仅摇钱树 | ❌ `40003 没有处于下架状态的活动`；转 ④ `§3.2`（注意重上架副作用） | ✅ |
| 批量结束 | `/scm-goods/WholesaleDrugES2/batchEnd` | ② 仅摇钱树 | ❌ 软成功且状态不变；**自营无 API 出口**（PMS 亦无终态码，见 ④ `§3.2`，须网页端） | ✅（须先下架） |
| 改价（独立接口） | `/scm-goods/wholesaleDrug/editPrices` | ⑤ 禁用 | ❌ `请至网页端进行调价操作`；价格正式出口见 ④ `§3.7` 快速调价 | ❌ `摇钱树商家不能进行此操作` |

> **③ 仅自营**：含 PMS 代托管接口**与 SCM 侧自营专属能力**（如阶梯价，见本文 §1.9）；PMS 接口总表见 `api_pms活动管理.md` `§2.1`（读取）/`§3.1`（写入）/`§4`（导出）。
> **④ 转PMS 出口**（参数/成功判据见 `api_pms活动管理.md`）：
> - **读取**（写前必做定位）：R1~R17 见 `§2.1`，筛选见 `§2.3`，状态枚举见 `§2.6`；
> - **写入**：下架/重上架 W1→`§3.2`、运营策略 W2→`§3.3`、活动期间 W3→`§3.4`、限购 W4→`§3.5`、定向 W5→`§3.6`、快速调价/撤销审批 W6/W7→`§3.7`；
> - **导出**：一口价/特价 E1/E2→`§4`（同步 xlsx 流）；
> - **字段缺口**：`ifLimit`/`maxAmount`、活动结束终态 → `§3.8`。
> **⑤ 禁用**：`editPrices` 两账号均不可用。改价两条正式路径：① 摇钱树/通用 → 整表 `addWholesale(mode=edit)`（§1.5），价格传字符串 + 全档位等比缩放防 `40042`；② 自营 → PMS 快速调价 `§3.7`（走审批流，非立即生效）。
> 其它商品子板块端点（批量编辑 `batchEdit`、套餐主从 `getPackageMainIds`、三方首推 `markThirdFr`/`unmarkThirdFr`、首推审核 `priorityAudit*`、删除 `deleteWholesale`、解绑 `unBindAct`、查重 `checkProvDrugCode`、上架表单、图片/视频端点等）：**账号分类均为 `① 通用`（未实测出账号差异）**，参数见 `references/附录/接口总表.md`，本文不展开。
> **本条括注不含阶梯价**：`addLadderPrice` 的分类是 `③ 仅自营`（摇钱树无入口），以上表那一行为准。

### 1.2 复制新建 `addWholesale(mode=copy)`

| 要素 | 内容 |
|---|---|
| 请求 | `POST /scm-goods/wholesaleDrug/addWholesale`，body = `wholesaleInfo` **全量 217 键** + 必带顶层键（实测 **251 键**可接受）+ 覆盖字段 |
| 关键参数 | `wholesaleId`/`id`=源ID、`mode=copy`、`copyId=1`、`checkExist=0`、`wholesaleType=1`、`drugId`、`provDrugCode`、`minAmount`/`step`/`maxAmountPerStore`/`maxAmount`/`ifLimit`、`beginDate`/`endDate`（另附小写 `startdate`/`enddate`）、全档位价格、`areaGroupId`、`logo`/`logoAudit`/`picUrlList`/`picsAudit` |
| 返回 | `{code:40001, message:"添加采购活动成功", data:{data:{wholesaleId:<新ID>}}}` |
| 说明 | 复制为**新链接**，源活动零改动；类型由 `wholesaleType` 决定 |

> **⚠️ 两阶段口径（2026-11-13 真机确证，勿混）**：
> 1. **读模板**：`POST /scm-goods/wholesaleDrug/getWholesale` 请求参数带 `mode=copy` + `copyId=1` + `wholesaleId=<源ID>` + `wholesaleType` + `ctype=1`，返回 `data.wholesaleInfo` **217 键**。
> 2. **提交**：以上述模板为基础覆盖业务字段，`POST /scm-goods/wholesaleDrug/addWholesale` 的提交体里 **`mode:1`(int)、`copyid:1`(int)**（真机实测），且模板**没有 `checkExist`**。
> 3. **层级（真机确认：平铺，无 `wholesaleInfo` 嵌套）**：`getWholesale.data.wholesaleInfo` ＝ 217 键；`addWholesale` 提交体**实测 251 键可接受** = `wholesaleInfo` **全量 217 键** + 历史表单 `过程区/详情图实测/表单_一口价.json`（113 键）里**响应没有的必带键**（`appNameType`/`hasBarcode`/`ifLimit`/`isTcm`/`tcm*`/`checkExist`/`copyId`/`startdate`/`enddate` 等）+ 目标覆盖。
>    ⚠️ **不可把 113 键历史表单当键白名单**：它不含 `unitPrice3~9`，按白名单会让 `unitPrice9`（含税成本价）变成 `0.0`——真机已踩（活动 `1457243830`）。
> 4. **`ex` 必须 `fixedPriceShelf`**：复制提交的 `ex` **不是** `goodsOnShelves`；用错报 `40002 操作失败，请稍后再试`（真机实测）。
> 5. **价格类型按 stage/mode 分层（勿一概而论）**：
>    - `addWholesale` + `mode=copy` + **自营**：传**数字**（`86.0`，真机验证）；
>    - `addWholesale` + `mode=edit` 整表、以及所有 `edit*` 接口：传**字符串**（`"86.00"`，见 §1.5/§1.7 第 6 条）；
>    - 摇钱树 `mode=copy`：历史实测为**字符串**。
>    - **价格档位必须全量**（见第 7 条），`unitPrice7/8/9` 是**必须传**的，不传会被置 0（含税成本价丢失）。
>    - 类型不符统一报 `40004 参数异常`；首次调用可按本账号口径试，40004 再换类型。
> 6. **`oldData` 是 JSON 字符串**（不是对象）；传对象报 `40004`。
> 7. **价格档位必须按 `data.priceTypes` 全量提交（不可用历史表单当键白名单）**：该账号实测 `priceTypes` = **5 档**——`1` 偏远省份价 / `2` 省内价 / `7` 周边省份价 / `8` KA价 / **`9` 含税成本价**。提交体必须以 `wholesaleInfo` **全量**为底（含 `unitPrice3~9`），表单只用来补「响应里没有的必带键」。
>    - 反例（真机踩过）：以 `过程区/详情图实测/表单_一口价.json`（113 键）为白名单 → 它**不含 `unitPrice9`** → 含税成本价被丢成 `0.0`（新活动 `1457243830` 即此问题）。
>    - **`unitPrice9`（含税成本价）必须原值带回**，不可归零、不可跟随目标售价；`unitPrice1/2/7/8` 按用户目标价；`unitPrice3~6`（摇钱树档位）保持源值。
>    - 档位清单以 `getWholesale.data.priceTypes` 为准（不同账号/权限**动态变化**），不要硬编码。
> 8. **必带顶层键**：`appNameType`(实测 3)、`hasBarcode`(-1)、`ifLimit`(0)、`isTcm`(0)、`tcm*` 系列、`checkExist`(0)、`copyId`(1)、`startdate`/`enddate`、`platform`/`ua`/`version`/`lastBuildTime`/`token`（后 5 个由 `scm.py call` 自动注入）。
> 9. **⚠️ 复制活动下架：SCM 被拒时改用 PMS W1（真机 2026-11-13）**：
>    - **现象**：复制时若未带 `operationFlag`，落库为 `0` → 被判「自动运营」：`pause`（`{id,pauseNote}`）/`batchPause`（`{handleList}`）返回「自动运营活动，不可手动编辑」（`rightCount=0`）；PMS W2 切运营模式返回「只有长期链接可以切换运营模式，请检查」（当天短期链接）。
>    - **正确解法**：**直接调 PMS W1** `ykjWholesaleOperation/updateYkjWholeSaleStatus/v27280`，body `{wholeSaleId, wholeSaleType, status:1}`（`1`下架/`2`重上架）——**无需先切运营模式**。真机 `result=1`，SCM 复验 `status=4 已下架`。
>    - **根治**：复制提交时**显式带 `operationFlag=2`（跟随源）**，避免落成 0。
>    - **不要**在短期链接上卡 PMS W2、也不要用 `batchEnd`（进行中会报「状态不符合」）。
> 10. **字段来源分层：活动实例取 `wsList` 行，商品主数据取 `wholesaleInfo`/`drugInfo`**（真机逐字段 diff 得出）：
>    - **活动实例字段**（每个活动可不同，复制时**必须从源 `wsList` 行取值**）：`prodDate`、`validDate`、`batchId`、`beginDate`、`endDate`、`oldPrice`、`maxAmount`、`maxAmountPerStore`、`operationFlag`、`isTraceCode`、`allowManualStockFlag`、`isCashAuto`、`isRebateCommission`、`productCollectAudit`、`disPrice`、`minCnt`、`status`。
>    - **商品主数据字段**（取 `wholesaleInfo`/`drugInfo`）：`drugName`、`pack`/`specification`、`approval`、`factoryName`、`wholePack`、`barcode`、`unitPrice3~9` 等。
>    - 真机证据：源 `wsList.beginDate=1740879656` 而 `wholesaleInfo.beginDate=None`；源 `wsList.operationFlag=2` 而复制产物变 `0`（因此被判自动运营、无法下架）。**只读 `wholesaleInfo` 会丢活动实例值**。
>    - 原则：**用户未指定的字段一律严格跟随源活动实例值**（从源 `wsList` 行覆盖），不得用模板默认值替代。
> 本表「关键参数」行的 `mode=copy`/`copyId=1`/`checkExist=0` 是**读模板阶段的请求参数写法**；提交体里 `mode` 也是 `copy`（字符串）、`copyId=1`/`checkExist=0` 为顶层数字。证据：`过程区/账号权限实测/scene_full.txt`、`browser_verify2.txt`、`_payload2.json`。

**② 仅摇钱树 价格约束**（实测）：

- 动态档位用 `unitPrice1~6`；摇钱树 `mode=copy` 历史实测价格**传字符串**（浮点报 `40004`）；自营 `mode=copy` 实测为数字，见第 5 条。
- **供乐药价上限 = 同一品类近 30 天成交均价 × 5**；实测 drugId 436429 供价 9.49 时，`40.0` 成功、`40.1` 起 `40042 系统检测到您的价格费率可能发生变化`。同价重提仍 40042、原价重提 40001，属确定性校验。
- **价格联动**：`chainPrice = unitPrice × 1.0`；`cunitPrice`/`cchainPrice = unitPrice × 0.8946`（保持源费率比）；`unitPrice1~6` 提交值被服务端按档位适用性重算（未配置档位落 0）。破坏费率比例或超 5 倍上限均报 `40042`。→ **写入必须等比缩放全档位**，不能全档设同一值。
- ③ 仅自营 可全档位同值（实测 99999）。

### 1.3 生命周期：下架 / 重上架 / 结束

**通用 SCM 参数**：

| 操作 | 接口 | 请求 | 成功判据 |
|---|---|---|---|
| 批量下架 | `WholesaleDrugES2/batchPause` | `{ex:"goodsOffShelves", handleList:[<ID>]}` | `code=40001` **且** `rightCount=N`/`errorCount=0` |
| 单条下架 | `WholesaleDrugES2/pause` | `{id, pauseNote}` | `40001` + `msg=暂停成功` |
| 重上架 | `WholesaleDrugES2/batchRestart` | `{ex:"goodsOnShelves", handleList:[<ID>], start:1}` | `info="重新成功上架N个…"` + `successNum=N` |
| 结束 | `WholesaleDrugES2/batchEnd` | `{handleList:[<ID>]}` | `info="已成功结束活动N个"` + `errorReasonList=[]` |

> `start=1`=恢复并立即上架。**结束为终态 `status=7` 不可逆**；② 仅摇钱树 结束须先下架（对进行中直接结束报「已成功结束活动0个」）。

**【仅摇钱树账号】**：上述四接口全部真实生效，全生命周期闭环 `复制 → 下架(4) → 重上架(0) → 再下架(4) → 结束(7)` 已实测。

**③ 仅自营 + ④ 转PMS**：SCM 侧生命周期被自动运营接管（`batchPause` 软成功、`pause` 报 40003、`batchRestart`/`batchEnd` 无效）。**唯一可用路径是 PMS**：活动查询、下架/结束、重上架、运营策略的完整接口、参数、成功判据与前置规则见 **`api_pms活动管理.md §2/§3`**。摘要：

| 操作 | PMS 接口 | 关键参数 | 前置 | 详见 |
|---|---|---|---|---|
| 活动查询（定位） | `pageOneFixedWsList` / `getSpecialProductWholeSaleList` / `pageWholeSaleByType` | `providerId`（必填）+ `wholesaleId` 或 `provDrugCode` | 任何写操作前先定位，读 `wholesaleStatus`/`operationFlag` | `§2.1` |
| 下架 | `updateYkjWholeSaleStatus` | `wholeSaleId` `wholeSaleType` `status=1` | 若 `operationFlag=1`（自动运营）**先切手动运营**；`0/2` 可直接下架 | `§3.2` |
| 重上架 | `updateYkjWholeSaleStatus` | `status=2` | 复验 `wholesaleStatus=5`；**副作用：强制切为手动运营并提示检查价格** | `§3.2` |
| 运营策略切换 | `checkUpdateOneFixedWsOpFlag` → `updateOneFixedWsOpFlag` | `wholesaleId` `operationFlag`（1自动/2手动） | 两步均须 `result=1`；`operationFlag=0` 的活动不可切（报 40003） | `§3.3` |
| 活动期间 | `updateYkjWsActivityTime` | `wholeSaleId` `beginDate` `endDate` `wholeSaleType` | 须 `result=1`；`endDate` ≥ `beginDate` | `§3.4` |
| 限购参数 | `updateGoodsSaleLimitConf` | `wholesaleId` `providerId` `minQty` `step` `maxAmountPerStore` `calculatePeriod` | 勿漏传 `minQty`/`step`；留空取现值回填 | `§3.5` |
| 定向管理（控销/禁销） | `updateGoodsSaleAreaConf` | `wholesaleId` `providerId` `areaGroupId` `storetypeGroupId` `isRestrict` `restrictId` | 缺 `areaGroupId`/`storetypeGroupId` 时先报错，不盲发 | `§3.6` |
| 快速调价（走审批） | `channel/fastAdjustPriceBatch` | `provDrugCode` `providerId` `warehouseId` `fastAdjustPriceRequestList[]` | 先用 `listWsPriceInfoBeforeEdit` 取现值；可能进审批不等于生效 | `§3.7` |
| 导出（同步 xlsx） | `exportOneFixedWsList` / `downloadSpecialProductWholeSaleList` | 与列表同款筛选、无分页 | 不套异步三步链；`stream=True` 取文件 | `§4` |
| 结束终态 | — | — | **PMS 无终态码、SCM `batchEnd` 软成功 → 自营活动无法经 API 结束，须走网页端**（见 `sy.md §4.1`） | `§3.2` |

> PMS 状态枚举与 SCM **不同**：PMS `wholesaleStatus` `5`=进行中、`3`=已下架、`4`=缺货下架、`0`=待开始；SCM `status` 见 `api_商品读取.md §1.2`。勿混用。
> 上表"详见"列中的 `§x.x` 均指 **`api_pms活动管理.md`** 的章节。

### 1.4 列表行操作：单字段编辑接口

> 对应界面：商品列表行操作 / 「更多」下拉。下表的 `id` 均指**活动ID（`wholesaleId`）**——实测自营老活动 ID 可以很小（如 `48344242`），不要与 `drugId` 或明细ID混淆。

| 界面项 | 接口 | 参数 | 复验口径 | 适用 |
|---|---|---|---|---|
| 修改主图 | `wholesaleDrugOnsale/updateLogo` | `{wholesaleId, logo:<URL>}`；URL 须先经 `upload2Local`（§1.4.1） | `getWholesale.logo` | 通用 |
| 修改排序 | `wholesaleDrug/editOrder` | `getWholesale.data.wholesaleInfo` **全量回填** + 覆盖 `order`（**须与原值不同**，同值报「没有修改」） | `getWholesale.order` | 通用 |
| 同步库存＝**是**（同步 ERP） | `wholesaleDrug/editStock2` | `{drugId, id:<活动ID>, manualSyncStock:0, wholesaleType}`，**省略 `drugStock`** | `wsList.msyncStock`（`0`=同步） | 通用 |
| 同步库存＝**否**（手动） | `wholesaleDrug/editStock2` | `{drugId, id:<活动ID>, manualSyncStock:1, wholesaleType, drugStock:<数量>}`，**`drugStock` 必带**。实锤请求体：`{drugId:4363, id:48344242, manualSyncStock:1, wholesaleType:1, drugStock:19750}` | `wsList.msyncStock`（`1`=手动）+ `wsList.stockAvailable`（手动模式下即设定值） | 通用 |
| 活动备注 | `wholesaleDrug/editWsDesc` | `{id:<活动ID>, wsDesc:<文本>}`；传 `""` 清空 | **必须 `wsList` 行的 `wsDesc`**（`getWholesale` 不返回该字段） | 通用 |
| 改价格提示 | `wholesaleDrug/editWsPriceTips` | `{id, wsPriceTips}` | `wsList` | 通用 |
| 单店采购上限 | `wholesaleDrug/editMaxAmountPerStore` | `{id, maxAmountPerStore}`；`0` 不被接受（报「请设置单个药店采购上限」） | `wsList` | ② 仅摇钱树；自营转 **④ 转PMS** |

> ⚠️ **`drugStock` 只存在于写入请求体**：`wsList`（215 字段）与 `getWholesale` 均不返回它。手动库存的**回读**只能看 `wsList.stockAvailable`（手动模式下等于设定值），不要拿 `drugStock` 去读响应。

#### 1.4.1 图片上传（`updateLogo` 前置）

`POST /scm-base/common/upload2Local`，`multipart` 文件字段 `file`；须显式在请求头带 `Cookie`（由 `credential.cookies` 拼 `k=v;…`）+ `provideridm`，表单带公共参数。**坑**：`core/http.build_session` 的 cookie jar 已绑定 domain 且默认带 `application/json` 头，二者都会污染 multipart，若再叠加 `Cookie` 头会形成畸形头 → `40002`；须用干净 `requests.Session` 只发显式 `Cookie` 头。

> **实现**：已封装为 `core/http.py` 的 `upload_file(credential, token, file_bytes, filename, ex)`（成功返回直链，失败返回 `None`）。Agent 写脚本时直接 `from core.http import upload_file` 调用，**不要重写这段 multipart/Cookie 逻辑**。该函数无 CLI 子命令（图片上传属一次性脚本场景）。**另两坑**：① multipart 的 `file` 部分**不可**显式设 `Content-Type`（会让 PhpSpreadsheet 解析异常 → `40002`），交给 `requests` 默认 octet-stream；② **脚本一律优先用 `upload_file`**，`assets/tpcl/goods-image.md §6.2` 的命令行 `curl` 是等价手工实现，不得改动 Cookie 拼装逻辑。

> **详情图无独立接口**：主图有 `updateLogo`，详情图 `picUrlList` 只能随整表 `addWholesale(mode=edit)` 提交 `picsAudit`/`picUrlList`（≤10 张），复验用 `getWholesale.picUrlList`。

### 1.5 整表编辑 `addWholesale(mode=edit)`

| 维度 | 自营 | 摇钱树 |
|---|---|---|
| 提交接口 | 与「复制后编辑」完全相同（不存在两种入口） | 同左 |
| 可落库字段 | 主图/详情图/排序/库存/开单/时间/商圈/标签等 SCM 默认字段 | **全部字段**（无灰显、无拦截） |
| 不落库字段 | `ifLimit`/`maxAmount`/`maxAmountPerStore`/`isRestrict`/`restrictGroupId` 等 PMS 托管字段（返回 40001 但不持久化）；价格仅 `mode=copy` 时可设定 | 无 |
| 处置 | PMS 托管字段转 **④ 转PMS**；`wsDesc` 用 `editWsDesc` 可改 | — |

**wt=8（批购包邮）整表编辑端点**（分类 ① 通用，两账号均有 wt=8 活动；以下约束在摇钱树账号实测）：
- 必须走 `/scm-goods/freeShipping/addWholesale` + `ex:"batchFsShelfDetail"` + `getWholesale` 全字段完整体。
- 必须显式带限购字段：`minAmount`/`step`/`maxAmountPerStore=1`/`maxAmount=1`/`ifLimit=1`。
- 漏传报 `40003 请设置单个药店采购上限`；走 `wholesaleDrug/addWholesale` 对 wt=8 一律 `40002 操作失败`。

**② 仅摇钱树 配送商切换约束**：`getDeliveryProviders` 返回 22 家，但服务端校验 `provDrugCode` 与目标配送商的供货关系；切到无关系的配送商报 `40003 商品编码不匹配，请检查`。可用值 = 该商品已建立供货关系的配送商。

> 字段级可改性、界面字段 ↔ API key、灰显/派生/只读清单见 `zddz.md`。

### 1.6 两账号写入差异速查

| 维度 | 自营账号 | 摇钱树账号 |
|---|---|---|
| 自动运营 | 有 | 无 |
| 生命周期 | SCM 拦截 → 转 PMS | SCM 真实生效 |
| 事后整表 edit | PMS 托管字段不落库 | 随时全字段可用 |
| 灰显字段 | 有（app名称/排序/橱窗/同步库存开关等，界面层） | 无 |
| 字段编辑时机 | 价格仅 `mode=copy` 设定；其余 SCM 字段事后可改 | 复制时 + 事后均可 |
| 价格上限 | 可设高价 | 品类均价 × 5，超限 40042 |
| `getDeliveryProviders` | 空数组 | 22 家 |
| 同品种重复上架 | 有次数上限（过量 `40003`） | 同左 |

### 1.7 写操作判据坑（通用，两账号均适用）

1. **复验有索引延迟**：`wsList` 写后不能立即相信复验结果，需 `sleep` + 重试（实测最多约 `6×2s`）；`wsListCount` 才是真实总数。
2. **生命周期状态复验**：终态（已结束）活动 `getWholesale.status` 返回异常旧值、`statusName` 为空 → 必须用 `wsList` 按 `status` 页签过滤核验（见 `zddz.md §5`）。
3. **批量接口 `code=40001` ≠ 成功**：`pause` 类必须读 `rightCount`/`errorCount`；`batchEnd` 类必须读 `info`/`errorReasonList`。
4. **拼团活动下架须单条**：`batchPause` 对拼团报 `40003`，改用 `WholesaleDrugES2/pause` 单条。
5. **控销三态**：`isRestrict`（`0` 非控非禁 / `1` 控销 / `2` 禁销）无独立写接口；整表 `addWholesale(mode=edit)` 设它返回 `40002`，仅在 `mode=copy`/`mode=add` 建/复制时随 `addWholesale` 提交有效。
6. **`edit*` 通用约束**：body 必带 `public_params(token)`（否则 `40004`，见 `api_认证与公共约定.md`）；价格字段传**字符串**（如 `"120.00"`），浮点报 `40004`；`editStock2` 最小体即可；`editOrder` 须完整 `wholesaleInfo` + `order` 不同值。
7. **自动运营限制**：自动运营活动（PMS `operationFlag=1`）禁止手动 `pause`/`edit`/`end`，自营账号须转 `api_pms活动管理.md` 或走网页端。注意 SCM `autoOperationFlag`(6/7/8) 是另一套编码，勿与 PMS `operationFlag` 互推。
8. **测试活动必下架**：为验证而复制/新建的活动，验证后（含失败路径）必须复验已下架，不得留活口；用 `wsList` 按 `status` 页签核验（索引有延迟，见 #1）。
9. **脚本禁调登录**：严禁在写脚本内 `scm.py login`（弹 GUI 挂死，且需人工验证码/企微扫码），应复用已有凭证直连（见 `api_认证与公共约定.md`）。

### 1.8 采集期登记端点（未实测 / 参数未采集，不得猜测）

> 以下来自采集记录，**不提供可照抄的完整参数**。标「仅端点名」者连参数键名都未采集，Agent 命中时按 `references/sy.md §0.5` 第 6 步如实告知，**不得编参数**。写端点一律按 `AGENT_GUIDE.md §10` 授权。

| 组 | 端点 | 已采集信息 | 状态 |
|---|---|---|---|
| **① 商品视频（8 个，均 POST）** | `/scm-goods/wholesaleDrugVideo/add` | `wholesaleId` + 视频地址（**描述，非键名**） | 仅登记，键名未采集 |
| | `.../edit` | 视频 ID（描述，非键名） | 仅登记 |
| | `.../getList` | `wholesaleId` + 分页（描述） | 仅登记 |
| | `.../getDetail` | 视频 ID（描述） | 仅登记 |
| | `.../getCount` | `wholesaleId` | 仅登记，返回未采集 |
| | `.../upLoadVideo` | multipart 文件（**文件字段名未采集**） | 仅登记（写） |
| | `.../checkPageWhitelist` | 仅公共参数，无业务参数 | 仅登记 |
| | `.../wsQuickSearch` | `keyword`（唯一明确键名） | 仅登记，返回未采集 |
| **② 校验 / 开关** | `/scm-goods/wholesaleDrug/getCanUploadPic` | `{drugId, +公共参数}` → `data.canUploadPic`(1/0) | **已实测**（详情图上传开关） |
| | `/scm-goods/wholesaleDrug/zyFixPriceCheck` | 原文「**可能**先调」（`restrictId`+`restrictType`），无响应记载 | 参数未证实 / 采集 0 命中 |
| | `/scm-goods/wholesaleDrug/checkProvDrugCode` | `provDrugCode` → `40001 status=0`（编码合法） | 采集登记 + 实测调用过 |
| | `checkMerpProvDrugCode` | **无任何参数记载**（仅端点名） | 仅端点名登记 |
| **③ 单字段编辑** | `/scm-goods/wholesaleDrug/editSalePrice` | `wholesaleId`+`drugId`+`unitPrice`+`minAmount`；**仅 `wholesaleType=8`（批购包邮）适用**，非 type=8 报 `40003 非批购包邮不能进行此操作`；缺 `drugId`/`minAmount` 各报 `40004` | **type=8 上未完整验证**（无成功返回记录），勿标"可用" |

> 视频能力可见性由 `getProviderInfo4List2.beVideo` 控制（见 `api_动态字典.md`）。`addWholesale` 提交体**历史采集口径为 112 顶层键**（72 个与 `wholesaleInfo` 同名 + 40 个需映射，含 `tcm*` 17 项 + 25 个具名），**实测直接提交 `wholesaleInfo` 全量 217 键 + 必带顶层键（共 251 键）也被接受**（见 §1.2 第 3 条），见 `zddz.md §3`；勿从字段名凑数。

### 1.9 单品阶梯价（商品列表 → 更多 → 单品阶梯价）

> **独立页面**（前端路由 `edit-single-tiered-pricing`，组件 `edit-new-213c5472.js`），**不是**整表 `addWholesale` 的一部分：`getWholesale` 不返回阶梯价档位字段，必须走本节专用接口。
> **最多 2 档阶梯**（页面硬上限 `dt=2`）。导出 CSV 的「促销起始数量1/2/3、阶梯价1/2/3」是**导出模板的 3 个档位列**，不等于可配 3 档。
> **账号分类：`③ 仅自营 `** —— 摇钱树账号**无此功能**（商品列表「更多」中不提供入口）。注意 `getDiscountType` 字典两账号都返回「单品阶梯价」项，那是**通用字典项**，不代表摇钱树可配置；判断能力归属以功能入口/接口可用性为准，不以字典项为准。

#### 1.9.1 接口

| 用途 | 接口 | 关键参数 |
|---|---|---|
| 读取 | `POST /scm-promotion/admin/singleCoupon/getLadderPriceInfo` | `{id:<活动ID>}`（参数名是 `id`，值传**活动ID**） |
| 添加 / 修改 / 删除 | `POST /scm-promotion/admin/singleCoupon/addLadderPrice` | 见 §1.9.2（删除也走本接口，`add:0`） |
| 价格校验（提交前） | `POST /scm-goods/drug/checkPriceAct` | `{wholesaleId, disPrice, disPrice2, from:"addWsDisTag", ifDisWs:1}` → 返回**提示文案**（空=通过） |
| 补贴计划风险检查 | 见 `references/附录/接口总表.md`（`subsidyPlan`） | `{wholesaleId, provDrugCode, origin:{ifDisWs}, next:{ifDisWs}}` → `{proceed, hadAbortRisk}` |

#### 1.9.2 提交体 `addLadderPrice`

```json
{
  "wholesaleId": 1451805285,
  "disType": 1,
  "add": 1,
  "minCnt": 10,
  "disPrice": 9.90,
  "minCnt2": 50,
  "disPrice2": 8.80,
  "limitArea": 0,
  "areaCodes": [],
  "tagDesc": "满10盒9.9元",
  "beginDate": 1762500000,
  "endDate": 1765091999,
  "tagPic": "",
  "tagPicAudit": "https://img.ysbang.cn/.../xxx.png"
}
```

| 字段 | 含义 | 取值 / 约束 |
|---|---|---|
| `wholesaleId` | 活动ID | 必填 |
| `disType` | 折扣类型 | 固定 `1`＝单品阶梯价 |
| `add` | 是否添加 | `1`＝添加/保留；`0`＝**删除**该阶梯价（界面「是否添加阶梯价」选否，无独立删除接口） |
| `minCnt` / `disPrice` | 第 1 档：促销起始数量 / 优惠价 | 数值；`disPrice` 精度 2 位、最小 `0.01` |
| `minCnt2` / `disPrice2` | 第 2 档（可选） | 不填则**省略键**；页面最多 2 档 |
| `limitArea` | 区域 | `0`＝不限；`1`＝限制区域 |
| `areaCodes` | 限制区域编码 | `limitArea=1` 时必填；值来自级联区域树组件（页面 `AllLoadAreaTree`），按其原值二维数组提交 |
| `tagDesc` | 促销标题/说明 | 字符串，可空 |
| `beginDate` / `endDate` | 促销开始 / 结束时间 | **Unix 秒**（页面 `dayjs().unix()`）；`endDate` 可空 |
| `tagPic` | 促销期间列表图片（已存） | URL；清空传 `""` |
| `tagPicAudit` | 新上传待审核图片 | URL；取上传组件返回的首个 URL |
| `id` | 阶梯价记录ID | **仅编辑时传**（页面 `mode=edit` 的 `id`）；新增不传 |

#### 1.9.3 页面真实提交顺序

1. 两档数组回写 `minCnt/disPrice`、`minCnt2/disPrice2`；
2. 二次确认「确认 添加/删除 单品阶梯价活动吗？」；
3. `checkPriceAct` 价格校验 → **返回非空文案则中止并弹提示**；
4. 风险检查 → `{proceed, hadAbortRisk}`，`proceed=false` 中止（**该检查与第 7 步「中止补贴计划」的端点路径/参数未采集，附录只登记了 `getOrderSubsidyPlanDetailList`；调用前须真机抓包，不得臆造**）；
5. 上传图片 → 写入 `tagPicAudit`；
6. `addLadderPrice` 提交（带 `disType:1`）；
7. `hadAbortRisk=true` → 追加调用「中止补贴计划」接口（见附录 `subsidyPlan`）。

#### 1.9.4 复验

- **权威读回**：`getLadderPriceInfo({id:<活动ID>})` → 比对 `minCnt/disPrice/minCnt2/disPrice2/tagDesc/beginDate/endDate/areaCodes/tagPicAudit`。
- **列表侧**：`wsList` 行只含 `minCnt/disPrice/minCnt2/disPrice2`（无阶梯价时值为 `null`）；`disType/tagDesc/tagPic/limitArea/areaCodes` **不在 wsList**，勿用列表字段判断这几项。
- 写后有索引延迟（见 §1.7 #1）。

> 证据：前端 chunk `edit-new-213c5472.js`（页面状态与提交构造）+ `fullAmountPromotion-e7855caf.js`（接口导出映射 `f→getLadderPriceInfo`、`h→addLadderPrice`）+ `groupEdit-3528c3f6.js`（`checkPriceAct`）；抓取与解析脚本 `过程区/账号权限实测/probe_ladder*.py`。
