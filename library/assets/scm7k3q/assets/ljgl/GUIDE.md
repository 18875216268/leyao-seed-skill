# 场景：订单链接（临时控销 → 复制活动 → 链接/二维码 → 定时下架）

> **状态**：参数默认值已由用户 2026-11-13 定稿（含 M6 复制类型规则）；**§9 C1~C5 全部定谳（含「药师帮id＝商品ID＝`drugId`」，用户确认 + 真机交叉验证）；写操作须先按 `AGENT_GUIDE.md §10` 授权**。
> 本文件是流程手册（不放可复用脚本），**不含任何写操作本身**；Agent 执行前须按 `AGENT_GUIDE.md §10` 取得场景授权。
> **账号归属：仅自营**。`scm.py status` 不输出账号体系标签 → 必须由用户明确告知或指定 `--account` 自营凭证，无信息先问、不猜。
>
> **粒度说明**：本场景整体仅自营，因为 `create`/`off`/`pms-*` 走商品复制与 PMS 活动接口（自营专属）；
> 其中的 `group-*` 虽调用标为「通用」的 `api_控销组.md`，但**在本场景内仍只面向自营凭证**。
> 摇钱树账号的控销组需求请直接按 `references/客户/api_控销组.md §0` 归属标记用 `call` 处理，不走本场景。

- **ID**：`ljgl`
- **触发语**：「给药店 X 做一条订单链接」「生成下单链接」「复制一条临时控销链接」
- **所需资产**：`scm.py call`（`AGENT_GUIDE.md §4.1`）、`references/客户/api_客户列表.md`、`api_控销组.md`、`references/商品/api_商品读取.md`、`api_商品写入.md`
- **前置**：①`python scm.py status`（仅自营）②确认目标商品可查 ③用户已就本场景授权写操作

---

## 0. 一分钟决策（Agent 先读这段）

| 我要… | 动作 | 写? |
|---|---|---|
| 查药店全部信息 | `store --keyword <id/名称/编码>` | 否 |
| 查商品有哪些活动链接 | `find --drug <编码/国药准字/名称/药师帮id>` | 否 |
| 查控销组内有哪些药店 | `group-list --group <组id>` | 否 |
| 按活动id查 PMS 一口价/特价 | `pms-find --id <活动id> [--type 1或4]` | 否 |
| **做一条新链接（一气呵成）** | `create --store ... --drug ... [--source ...] --confirm` | **是** |
| 改活动备注 | `ws-desc --id --desc` | 是 |
| 改库存 / 同步开关 | `ws-stock --id --sync off --qty N` | 是 |
| 设单品阶梯价（最多 2 档） | `ws-ladder --id --min-qty N --price P` | 是 |
| **改价** | `reprice --id --price P [--min-qty N]` → 先出两方案 | 是 |
| 管控销组 | `group-create` / `group-update` / `group-del` | 是 |
| 组内加/减药店 | `group-add` / `group-remove` | 是 |
| 加**未下单**药店 | `group-nostore`（搜）→ `group-add-nostore` | 是 |
| 改限购（起订/倍数/单店上限/周期） | `pms-limit --id ...` | 是 |
| 改商圈 / 供货对象 / 控销 | `pms-area --id ...` | 是 |
| 改活动时间 | `pms-time --id --begin --end` | 是 |
| 下架 / 重上架 / 结束 | `off` / `restart` / `end` | 是 |
| 定时下架 | `schedule --id --at "YYYY-MM-DD HH:MM"` | 否（引导） |
| 生成二维码 | `qr --id` | 否 |
| 看历史台账 | `list` | 否 |

## 动作总表（25 个 / 6 组）

### 1.1 查询（只读）

| 动作 | 作用 | 接口 | 关键参数 |
|---|---|---|---|
| `store` | 药店全部信息（id/编码/名称等全字段） | `crm/list` | `--keyword` |
| `find` | 一口价+特价活动候选（不含已结束） | `wsList` | `--drug` `[--store]` |
| `group-list` | 组内药店 | `getBranchInfo` | `--group` |
| `group-nostore` | 搜索**未下单**药店 | `getNoOrderStore` | `--group` `[--name]` |
| `pms-find` | PMS 按活动id/编码搜一口价或特价 | `pageOneFixedWsList` / `getSpecialProductWholeSaleList` | `[--id]` `[--code]` `--type 1\|4` |
| `list` | 台账最近记录 | 本地 `link-records.jsonl` | `[--limit]` |

> **模糊输入（含用户发图）的检索优先级**：**国药准字 / 商品编码 / 规格 > 商品名 / 通用名 > 厂家**。
> 实测：准字与规格各命中约 2 个商品编码；商品名 7、通用名 12、厂家 23（已按商品编码分组）。
> Agent 从图里提取到多个字段时，**优先用准字或规格**；只有名称时先搜再让用户从分组候选里选。
> 候选已自动**过滤本场景自建活动**（`wsDesc` 含 `WorkBuddy`/`agent`），需要时加 `--include-self`。

### 1.2 创建（一气呵成）

| 动作 | 作用 | 关键参数 |
|---|---|---|
| `create` | S1 定位药店 → S2 建组 → S3 加店 → S4 选源 → S5 复制 → S7 库存/备注 → 链接/二维码 | `--store --drug [--source] [--price] [--stock] [--limit] [--date] [--desc] [--desc-date] [--group-id] [--confirm]` |

### 1.3 SCM 单项修改（写）

| 动作 | 作用 | 接口 | 关键参数 |
|---|---|---|---|
| `ws-desc` | 活动备注 | `editWsDesc` | `--id --desc` |
| `ws-stock` | 同步开关 + 库存数量 | `editStock2` | `--id --sync on\|off [--qty]` |
| `ws-ladder` | 单品阶梯价（读/写/删，≤2 档） | `getLadderPriceInfo` / `checkPriceAct` / `addLadderPrice` | `--id [--get] [--min-qty --price] [--min-qty2 --price2] [--tag] [--remove]` |
| `reprice` | 改价：先出 `ladder` / `rebuild` 两方案 | 组合 | `--id --price [--min-qty] [--plan ladder\|rebuild]` |
| `group-create` | 新建控销组 | `editStoreGroup` | `[--name] [--desc] [--store]` |
| `group-update` | 改组名/描述 | `editStoreGroup`（非空ID） | `--group [--name] [--desc]` |
| `group-del` | 删组（格式+引用双护栏） | `wsCountByRG` → `delGroups` | `--group [--force]` |
| `group-add` | 药店加入组 | `addStoreBatch` | `--group --store` |
| `group-remove` | 药店移出组 | `delStoreBatch` | `--group --store` |
| `group-add-nostore` | 添加未下单药店 | `addNoOrderStore` | `--group --full-name [--store-id]` |

### 1.4 PMS 单项修改（写）

| 动作 | 作用 | 接口 | 关键参数 |
|---|---|---|---|
| `pms-limit` | 起订量 / 购买倍数 / 单店上限 / 刷新周期 | `updateGoodsSaleLimitConf/v27280`（W4） | `--id [--min-qty] [--step] [--max-per-store] [--period 0~4]` |
| `pms-area` | 商圈 / 供货对象 / 控销·禁销 | `updateGoodsSaleAreaConf/v27280`（W5） | `--id [--area-group] [--storetype-group] [--restrict 0\|1\|2] [--restrict-id]` |
| `pms-time` | 活动时间 | `updateYkjWsActivityTime/v27280`（W3） | `--id --begin --end [--type]` |

### 1.5 生命周期（写，`schedule` 除外）

| 动作 | 作用 | 关键参数 |
|---|---|---|
| `off` | 下架（SCM `pause` → 失败降级 PMS W1） | `--id` |
| `restart` | 重上架（`batchRestart` → PMS W1 `status=2`） | `--id` |
| `end` | 结束（**内部先下架**再 `batchEnd`；失败给网页引导） | `--id` |
| `schedule` | 定时下架**引导**：输出 IDE `automation_update` 参数 | `--id --at "YYYY-MM-DD HH:MM"` |

### 1.6 辅助

| 动作 | 作用 | 关键参数 |
|---|---|---|
| `qr` | 生成链接二维码 PNG | `--id [--out]` |

> **写动作统一 `--confirm`**；`create` 默认 dry-run、`reprice` 默认只出候选，都不会改动数据。
> **定时下架以引导为主**：`schedule` 只输出 IDE `automation_update`（`scheduleType=once`）参数，技能内**不起常驻进程**；到点由 Agent 执行 `off --confirm`。
> **改价限制**：复制后价格改不了 → `reprice` 给两个方案（阶梯价 / 重建），不擅自执行。

---

## 1. 流程总览

| 步 | 目标 | 接口 / 命令 | 读/写 |
|---|---|---|---|
| S1 | 拿药店ID | `crm/list`（`call --ex OldCustomerManagement --param version=1.0.0 --drop lastBuildTime`） | 读 |
| S2 | 建临时控销组 | `saleControl/editStoreGroup`（`storeGroupId:null`）→ 回查 `storeGroup` 拿组ID | **写** |
| S3 | 药店加入该组 | `saleControl/addStoreBatch`（`batchType=0` + `branchIdList`） | **写** |
| S4 | 查候选链接 | `wsList`（`--status 全部` + `--type 一口价 --type 特价`） | 读 |
| S5 | 复制并编辑 | `getWholesale`(mode=copy) → `wholesaleDrug/addWholesale` | **写** |
| S6 | 拼链接 + 二维码 + 汇报 | 本地生成 PNG | 读 |
| S7 | 可选定时下架 | IDE 一次性自动化 → 到点下架 | **写** |

**顺序不可颠倒**：S2/S3 必须在 S5 之前——`isRestrict`/`restrictGroupId` **仅在 `mode=copy` 提交时有效**，`mode=edit` 返回 40001 但不落库（`api_商品写入.md §1.7 #5`）。

---

## 2. 分步说明

### S1 获取药店ID

- **输入**：药店ID / 药店名称 / 药店编码，**三者必填其一**。
- 给的是药店ID → 直接用作 `drugstoreBranchId`，跳过本步。
- 否则 `call --path /scm-order/crm/list --ex OldCustomerManagement --param version=1.0.0 --drop lastBuildTime`，筛选参数：药店名称 `storeTitle`（模糊）、药店编码 `providerCode`（精确）。
- **成功判据**：`code=40001`，返回行 `drugstoreBranchId`。⚠️ **不要传 `providerId`**（那是商家ID，不是药店ID）。
- **失败处理**：0 行 → 如实告知并请用户补全/更正；多行 → 列出候选（药店ID+名称+编码）让用户选，不自动取第一条。
- **口径**：客户列表是**自营专属**，公共参数特例见 `api_客户列表.md` 头部。

### S2 建立控销组

- `call --path /scm-setting/saleControl/editStoreGroup --ex ControlDrugstoreGroup`
  `--body '{"storeGroupId":null,"groupName":"<药店id>临时控销","groupDesc":"agent临时控销！<yyyymmdd>后可删除。"}'`
- **描述日期**：用户指定则用其日期，否则当天；格式 `YYYYMMDD`。
- **成功判据**：`code=40001` 且 `message=添加成功`，但 **`data` 为 `null`，不回带组ID**。
- **必做回查**：`call --path /scm-setting/saleControl/storeGroup --ex ControlDrugstoreGroup --param groupIds=[] --param groupName=<组名>`，取 `results[0].storeGroupId`。
  ✅ 已验证：`restrictGroupId` 与 `storeGroupId` **同一 ID 空间**（实测 `152845` 精确反查命中）。
- **失败处理**：组名重复/超限时如实报错，不自动改名重试。

### S3 添加药店到组

- `call --path /scm-setting/saleControl/addStoreBatch --ex ControlDrugstoreGroup`
  `--body '{"batchType":0,"storeGroupId":<S2组ID>,"branchIdList":[<药店id>]}'`
- **成功判据**：`code=40001` **且 `rightCount>=1`、`errorCount=0`**；只看 code 会漏判。
- **失败处理**：`40003 请输入正确的药店ID` → 回 S1 复核；失败明细在 `data.data` 二维数组。

### S4 查候选链接

- `python scm.py query --status 全部 --type 一口价 --type 特价 --keyword <商品信息> --limit 50`
  （或 `call --path /scm-goods/wholesaleDrug/wsList --ex goodsOnShelves --param status=-1 --param wholesaleType=[1,4] --param ...`）
- **检索口径**：商品名称 `drugName`（模糊）、商品编码 `provDrugCode`、国药准字 `approval` 可作独立参数；**药师帮id ＝ 商品ID ＝ `drugId`，但 `wsList` 的 48 项筛选里没有 `drugId` 参数 → 必须用 `--keyword <drugId>`**（`searchInfo` 综合匹配含 活动ID/商品编码/商品名称/批准文号/**商品ID**/厂家/活动备注）。
- **不含已结束**：`status=-1`（全部）**本就不含 `7` 已结束**（实证：用一条 status=7 的活动ID 反查 `status=-1` 得 `totalRecord=0`），符合用户「已结束不要」，无需补查 7。
- **候选判定**：按 `provDrugCode` 分组；同组出现多条**且不一致**时，返回候选让用户选，展示 `商品编码 + 商品名称 + 商品规格 + 厂家`（`provDrugCode`/`drugName`/`pack`/`factoryName`）并附 `wholesaleId`、`wholesaleTypeStr`、`statusName`、`unitPrice`、`stockAvailable`。**只有 1 条时直接采用，不打断用户。**
  - **同产品不同编码后缀也算差异**（真机：示例商品同一国药准字下查出 `SP0000001` 与 `SP0000002` 两条，价格 81.80 / 83.99 / 84.90 三条）→ 必须让用户选，不能按名称自动合并。
  - **源链接可能是「缺货下架」**（真机 3 条候选全部 `statusName=缺货下架`、`status=3`、`stockAvailable=-1`）→ 复制后状态不可假定「进行中」，必须写后复验。
- **坑**：`totalRecord` 有 10000 硬上限（`api_商品读取.md §5`），计数须用 `wsListCount` 复核。

### S5 复制并编辑

1. `call --path /scm-goods/wholesaleDrug/getWholesale --ex goodsOnShelves --param wholesaleId=<源ID> --param wholesaleType=1 --param ctype=1 --param copyId=1 --param mode=copy` → 取 **217 键 `wholesaleInfo` 模板**。
2. 按 §3 覆盖字段，其余 **217 键原样透传**（用户定稿：「其他未说明地方，严格按源链接要求，完全一致」）。
3. `call --path /scm-goods/wholesaleDrug/addWholesale --ex fixedPriceShelf --body @payload.json`
   - **`ex` 必须 `fixedPriceShelf`**（用 `goodsOnShelves` 报 `40002`）。
   - **提交体 = 251 键平铺**（实测可接受）= `wholesaleInfo` **全量 217 键** + 历史表单 `过程区/详情图实测/表单_一口价.json`（113 键）里**响应没有的必带键**（`appNameType`/`hasBarcode`/`ifLimit`/`isTcm`/`tcm*`/`checkExist`/`copyId`/`startdate`/`enddate` 等）：同名键直接取、`drugInfo`/`providerInfo` 补 `approval` 等、缺失键用表单默认值；**不要嵌 `wholesaleInfo` 对象**，**更不要把 113 键表单当白名单**（会丢 `unitPrice3~9`）。
   - **价格传数字**（`86.0`）；**价格档位按 `data.priceTypes` 全量提交**（该账号 5 档：1/2/7/8 设目标价，**`unitPrice9` 含税成本价原值带回**，3~6 保持源值）——**不能以历史表单为键白名单**，否则 `unitPrice9` 会被丢成 0（真机已踩）。
   - **`oldData` 传 JSON 字符串**；`maxAmountPerStore` 必带但不落库（PMS 托管）。
   - **未指定字段一律严格跟随源**：`prodDate`/`validDate`/`batchId`/`beginDate`/`endDate`/`oldPrice`/`maxAmount`/`operationFlag`/`isTraceCode` 等活动实例字段**必须从源 `wsList` 行取**（`wholesaleInfo` 可能是 `None` 或商品主数据值）。真机教训：源 `operationFlag=2` 复制后变 `0` → 被判自动运营、无法下架。
4. **成功判据**：`code=40001`、`message=添加采购活动成功`，新活动ID 在 **`data.data.wholesaleId`**。
   **兜底**：若响应未回带 ID，用「创建前基线 ID 集合 + 差集轮询」找新ID（索引有延迟，最多 6×2s），**绝不能静默结束**。
5. **写后复验**：`wsList` 查新ID 确认在售/字段生效（索引有延迟）；控销绑定读 `getWholesale` 的 `restrictGroupId` 复核。

### S6 链接 + 二维码 + 汇报

- 链接：`https://dian.ysbang.cn/#/drugInfo?wholesaleid=<新活动id>&isAssemble=false&scene=1&trafficType=1`
- 二维码：本地生成 **PNG**（`qrcode[pil]`，用户已允许引入依赖），不外发 URL 到第三方；落盘路径随汇报返回。
- 汇报内容严格按 §4。

### S7 定时下架（仅用户要求时）

- 用户未要求 → **不创建任务**，只记录台账。
- 用户要求 → Agent 调 IDE `automation_update`：`mode=suggested create`、`scheduleType=once`、`scheduledAt=<ISO 8601 本地时刻>`、`status=ACTIVE`、`cwds=<技能包根>`、
  `prompt`＝「执行下架：读 `wsList` 行的 `operationFlag`；`1`（自动运营）→ 先按 PMS §3.3 切手动运营、再 PMS W1；`0/2/8` → 直接 SCM `WholesaleDrugES2/pause`（拼团须单条）→ 复验已下架 → 回写台账 → 如实汇报」。
- **技能包内不造调度器/常驻进程**；前提是 IDE 在该时刻在线（须如实告知用户）。
- ⚠️ **下架路径优先级（真机验证）**：① 先试 SCM `pause`（`{id, pauseNote}`）；② 若返回「自动运营活动」→ **直接 PMS W1 `ykjWholesaleOperation/updateYkjWholeSaleStatus/v27280`**（`wholeSaleId`+`wholeSaleType`+`status=1`），**不要卡在 PMS W2 切运营模式**（短期链接必被拒）；③ `batchEnd` 对进行中活动报「状态不符合」，不可用。
- **根治**：复制提交时带 `operationFlag=2`（跟随源），避免落成 `0` 被判自动运营。
- 台账：`%LOCALAPPDATA%/scm-operations-query/link-records.jsonl`，字段：药店id / 组ID / 源活动ID / 新活动ID / 链接 / 二维码路径 / 创建时间 / 下架时刻 / 状态 / 账号。

---

## 3. 复制参数默认值（用户 2026-11-13 定稿）

### 3.1 必改字段

| # | 字段 | 默认值 | 依据 |
|---|---|---|---|
| M1 | `restrictGroupId` | **S2 新建组的 `storeGroupId`** | 同空间已验证 |
| M2 | `isRestrict` | **`1`（控销）** | 与 M1 成对；`0`非控 / `2`禁销 |
| M3 | `beginDate` / `endDate` | **当天 `00:00:01` ~ `23:59:59`**；用户指定日期时间则以用户为准 | 覆盖 `商品/sy.md §3.4 #4`（原写当日 01:00:00），以用户口径为准 |
| M4 | `wholesaleName` | **默认（跟随源）** | 实测空串，`defaultAppName` 自动取「商品名+规格」 |
| M5 | `status` | **默认 / 进行中**（跟随源，实测 `0`） | 复制后须复验，不能静默留活口 |
| M6 | `wholesaleType` | **特价在售 ≥215 → 一口价；<215 → 特价**（用户 2026-11-13 定谳；「主要点 1」条件写反，已作废） | 实测特价在售 **309 > 215** → 当前应复制为**一口价** |
| M7 | `areaGroupId` | **全国**：运行时调 `getAreaGroupDropList` 取 `nationwide=1` 的 `id`（自营实测 `571`，`groupName=全国通用`），**勿硬编码** | 用户「全国通用」 |
| M8 | 复制控制 | **读模板**：`getWholesale` 带 `mode=copy` + `copyId=1`；**提交模板**为 `mode:1`(int) + `copyid:1`(int)，模板**无 `checkExist`**（§9 C2 真机确证） | 两阶段口径，不冲突 |

> **控销不走 PMS**：复制时直接设 `restrictGroupId`；**非复制（事后编辑）才需要转 PMS W5**（用户定谳）。

### 3.2 用户可选参数

| 用户说的话 | 覆盖字段 | 未指定时 |
|---|---|---|
| 「价格 X」 | 售价体系（**成本价 `purchasePrice`/`purchasePrice2` 绝不改写**） | **保持原链接价格** |
| 「限购 N」 | 仅 `maxAmountPerStore`（单店上限）；`maxAmount`/`maxAmountPerUser` 跟随源 | **保持原链接限购** |
| 「库存 N」 | 复制时 `manualSyncStock=1`；**复制成功后**用 `editStock2` 提交 `{drugId, id:<新活动ID>, manualSyncStock:1, wholesaleType, drugStock:N}`（217 键模板无 `drugStock`，§9 C3）。⚠️ 源 `stockAvailable=-1` 表示**缺货下架**，设手动库存后必须复验 | **保持原链接库存设置** |
| 「需求数量 N」 | 用户**另行报出**的采购量，仅用于库存充足性比较：若设定库存 < N，设置完毕后如实说明「已设置为不同步库存，并设置库存为 xxx，不足需求数量 N」 | 未报则不比较 |
| 「备注 X」 | 活动备注 `wsDesc`（**不在 217 键模板内**，复制后必须 `editWsDesc` 单接口设置） | **默认 `WorkBuddy做单链接，yyyy/mm/dd后可下架。`**（如 `WorkBuddy做单链接，2026/11/13后可下架。`）；用户指定则用用户的，`--desc ""` 清空 |
| 「日期时间」 | `beginDate` / `endDate` | 当天整天 |
| 「定时下架」 | S7 自动化任务 | 不创建 |

> **除 §3.1/§3.2 外的 217 键一律原样透传**，不做任何「顺带」修改（`AGENT_GUIDE.md §10` 授权范围红线）。

### 3.3 价格档位

价格字段：`unitPrice`、`unitPrice1~9`、`chainPrice`、`cchainPrice`、`cunitPrice`、`cunitPrice1~9`、`oldPrice`。
- 自营动态档位含义：`1`偏远省份价 / `2`省内价 / `7`周边省份价 / `8`KA价 / `9`**含税成本价**（`api_商品读取.md`）。
- 红线：**全档位必须设值**（缺档位→服务端默认 0→0 元购事故）；**价格类型按阶段/账号**：`mode=copy` 的 `addWholesale` **自营传数字**（`86.0`，真机验证）；`mode=edit` 整表与 `edit*` 接口**传字符串**（`"86.00"`）；摇钱树 `mode=copy` 历史实测为字符串。**类型不符统一报 `40004`，首次可先按本账号口径试、40004 再换**。改价后复验全档 > 0。
- ⚠️ 用户给单个价格时：`unitPrice`（及联动的 `chainPrice`）设为用户价，**其余档位按源链接比例等比缩放**；`purchasePrice`/`purchasePrice2` 与含税成本价档位 `unitPrice9` **不动**。未给价则全部保持源值。

---

## 4. 输出格式（用户定稿）

**下单链接**：链接文本 + PNG 二维码（文件路径）

**基本信息**（字段来源双证：`wsList` 215 字段 / `getWholesale` 217 键模板）：

| 展示项 | 来源字段 | 实测样例 |
|---|---|---|
| 活动id | `data.data.wholesaleId`（addWholesale 返回） | — |
| 商品编码 | `provDrugCode` | `SP0249613-9` |
| 商品名称 | `drugName` | `枢复来 盐酸罗匹尼罗片` |
| 商品规格 | `pack`（wsList）/ `specification`（模板） | `0.5mg*6片*5板` |
| 药师帮id | **`drugId`（商品ID，与药师帮id 同一字段）** | `4428525` |
| 国药准字 | `approval`（wsList 行） | `国药准字H20130044` |
| 整件数量 | `wholePack`（模板） | `160`（示例商品 200mg*28片） |
| 生产日期 | `prodDate` | `2026-03-16` |
| 有效期 | `validDate` | `2028-02-29` |
| 含税成本价格 | **`unitPrice9`（含税成本价档，`priceTypes` 里 `priceType=9`）**；`purchasePrice` 常为 0（未维护）不作主口径 | 源 `unitPrice9=80.0`；对照活动 `2.64` |
| 库存设置 | `manualSyncStock` + 设定数量（或「跟随源」） | — |
| 其他动态价格 | `unitPrice1` `unitPrice2` `unitPrice7` `unitPrice8` `unitPrice9` | — |
| 活动时间 | `beginDate` / `endDate` | 当天 `00:00:01`~`23:59:59` |
| 活动备注 | `wsDesc`（**必须用 `wsList` 行复验**，`getWholesale` 恒不返回该字段） | `WorkBuddy做单链接，2026/11/13后可下架。` |

> ⚠️ `purchasePrice`、`wholePack`、`specification` 不在 `wsList` 行里，须从 `getWholesale` 模板取；`approval`、`pack` 不在 217 键模板里，须从 `wsList` 行取。**两边都要读**。

---

## 5. 错误处理

| 错误 | 动作 |
|---|---|
| `40003 同一分仓…不可用券活动最多能上架215个` | 特价复制超限 → 按 §3.1 M6 规则改类型，**最多重试一次**，仍失败则如实汇报，不反复提交 |
| `RATE_LIMITED`（`40003` 频控） | 候选查询/写接口连续快速调用会触发（真机实测：连续 4 次 `wsList` 即被限）→ **间隔 ≥75 秒**或等 10 分钟，禁止重试风暴 |
| `40042`（价格校验） | 改价后复验**全档位 > 0**；自营可全档同值，摇钱树受「近30天均价×5」上限 |
| `40004 参数异常` | 检查**价格类型**（`mode=copy` 自营传数字 / `mode=edit` 与 `edit*` 传字符串）、`storeType` 是否数字、时间是否成对 |
| `40002` | 常见于试图用 `mode=edit` 改控销字段；改为在 copy 时带上 |
| `40020` / `40000` | 会话失效 → `scm.py login`（用户弹窗），复验后继续 |
| `AUTH_REQUIRED` | 先 `status`；PMS 相关先 `pms-status` |
| S5 未回带新ID | 基线差轮询，**不得静默结束** |
| 任一步失败 | 进 §8 回滚，如实汇报已完成/未完成的步骤 |

---

## 6. 验收清单

1. 账号已确认为自营；用户已授权本场景写操作。
2. S2 组名/描述格式正确，`storeGroupId` 已回查到。
3. S3 `rightCount>=1` 且 `errorCount=0`。
4. S4 候选不含已结束(7)，多条时已让用户选择。
5. S5 217 键透传、仅 §3 字段被覆盖；`restrictGroupId` 复核 = S2 组ID；`areaGroupId` = 全国。
6. 新活动ID 已取得且链接可拼；PNG 二维码已生成。
7. §4 全部字段已汇报；成本价未改动。
8. 用户要求定时下架时，自动化任务已创建且台账已落盘。
9. 无遗留测试活动/孤儿控销组（见 §8）。

---

## 7. 回滚

逆序清理，**源活动零改动**：

1. 已建新链接 → 下架并复验为已下架（普通活动 `WholesaleDrugES2/pause`；拼团须单条；自动运营/PMS 托管走 PMS W1，且下架前先切手动运营）。
2. 已建组 → 先 `wsCountByRG({groupIds:[组ID]})` 确认无活动引用，再 `saleControl/delGroups` 删除（不可逆）。
3. 已创建定时任务 → 取消/标记失效，回写台账状态。
4. 每步写操作留审计日志（时间/接口/对象/参数脱敏/结果/回滚值）；失败即回滚并如实报告。

---

## 8. 红线与已知边界

- **仅自营**；客户列表自营专属，摇钱树不可做。
- 全程 **4 类写操作**（建组/加店/复制/下架）须 `AGENT_GUIDE.md §10` 授权，只做授权范围内的接口。
- **测试/复制产生的活动必须下架**，不留活口（`商品/sy.md §3.4 #7`）。
- `drugStock` **只存在于 `editStock2` 写入请求体**，`wsList`/`getWholesale`/复制 217 键模板都不含它 → **复制后必须用 `editStock2` 单独设手动库存**（§9 C3 确证）。
- `wsList` 写后有索引延迟（最多 6×2s），复验须重试；`wsListCount` 才是真实总数。
- 二维码本地生成，链接不外发第三方；PNG 路径属技能 `filesystem_write`。
- 定时下架依赖 IDE 在线；不承诺离线执行。

---

## 9. 真机确证结论（C1~C5 全部定谳）

| # | 事项 | 实证依据 | 结论 |
|---|---|---|---|
| **C1** | ✅ **复制类型规则（已定谳）** | 用户 2026-11-13 最新指令：M6 第二句改为「否则特价即可」 | **≥215 → 一口价；<215 → 特价**。「主要点 1」的「≤215→一口价，否则→特价」条件写反，已作废。当前实测特价在售 309，故本场景复制为**一口价** |
| **C2** | ✅ **复制提交形态（真机确证）** | `getWholesale` **请求参数**用 `mode=copy` + `copyId=1`（真机返回 `code=40001`、217 键）；其**返回的提交模板**里是 `mode:1`(int)、`copyid:1`(int)，且模板**无 `checkExist`** | 「读模板请求参数」与「提交体字段」是两个层次，**不冲突**；已在 `api_商品写入.md §1.2` 补澄清 |
| **C3** | ✅ **库存 / 限购（真机确证）** | 217 键模板无 `drugStock`；库存相关为 `inStock=0`/`stockAvailable=1563`/`stockBalance=1563`/`manualSyncStock=0`，`maxAmountPerStore=None` | 库存：复制后走 `editStock2`（实锤体见 §3.2）；限购：复制时设 `maxAmountPerStore=N`，`maxAmount`/`maxAmountPerUser` 跟随源；「需求数量」＝用户另行报的采购量，未报不比较 |
| **C4** | ✅ **商品编码 vs 药师帮id（已定谳）** | 用户 2026-11-13 明确「药师帮id 就是商品ID」；真机用截图活动ID `1135522464` 反查：商品ID `4428525`=`drugId`、商品编码 `SP0268491`=`provDrugCode`、国药准字 `H20074168`=`approval`，**四项全部一致** | 输出映射：商品编码=`provDrugCode`、**药师帮id=`drugId`**、国药准字=`approval`。查询时 `drugId` **不是筛选参数**，用 `--keyword`（`searchInfo`） |
| **C5** | ✅ **下架体系（真机确证）** | `wsList` 行有 `operationFlag`（实测 `2`＝手动）；值域 `1`自动 / `2`手动 / `8`临时手动（`api_pms活动管理.md §2.3`），且 `=1` 下架前须先切手动运营（该文 §3.2） | **`1`** → PMS W2 切手动 + PMS W1 下架；**`0/2/8`** → 直接 SCM `WholesaleDrugES2/pause`（拼团须单条）。已写进 S7 / §5 / §7 |
| **R2** | ✅ **示例商品真实创建成功（2026-11-13）** | 药店 `<药店ID>`（示例药店（药店名称））｜源 `223640346` 一口价｜价格 86｜库存 1500｜新活动 `1457243830` | 结果：`status=0 进行中`、`beginDate=1794499201`/`endDate=1794585599`（当天 00:00:01~23:59:59）、`unitPrice/1/2/chainPrice=86.00`、`stockAvailable=1500`、`manualSyncStock=1`、`isRestrict=1`、`restrictGroupId=169282`、`areaGroupId=571(全国通用)`、`maxAmount/maxAmountPerUser=1500`。踩坑与修正：`40004 请输入上架时间`→补 `startdate/enddate`；`40002`→`ex` 改 `fixedPriceShelf` + 251 键结构；`40004`→价格数字 + `oldData` 字符串 + 去 `unitPrice7/8`。`unitPrice7/8/9=0` 曾被我误判为「`priceType=0` 正常」——**该结论已被 R3 推翻**（实为丢失档位，正确做法见 R3）。 |
| **R1** | ✅ **示例商品真机演练（2026-11-13）** | 按国药准字 `H00000000` 查出 3 条（`1150985692`/`252710684`/`223640346`），全部「缺货下架」；源模板 `drugId=3896100`、`wholePack=160`、`purchasePrice=0.0`、`unitPrice9=130.06`、`stockAvailable=-1`、`beginDate/endDate=None` | 验证了：候选差异判定、缺货下架状态、成本价回退 `unitPrice9`、库存 -1 语义；**写操作未执行**（缺药店信息） |

> 取证脚本：`过程区/账号权限实测/verify_link_scene{,2,3,4,5,6}.py`、`verify_browser.py`、`verify_scene_full.py`、`dump_form_values.py`（输出 `form_values.txt` / `scene_full.txt`）。
