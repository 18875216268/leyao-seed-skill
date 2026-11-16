# 商品（板块索引）

> **板块归属（板块内单独说明）**：本板块为**混合归属**——`api_商品读取.md` / `api_商品下载.md` / `api_商品写入.md`（商品列表主系列）＝**通用**（两账号体系）；`api_pms活动管理.md`（PMS 代托管）、`api_委托配送商品.md`（商品-委托配送商品）＝**自营专属**。归属唯一事实源与完整板块地图见 `references/sy.md §0`。
> 适用账号体系：**自营账号体系**（自动运营）／**摇钱树账号体系**（无自动运营）。两套体系各有多个账号，具体账号名与 `providerId` 一律由凭证/`status` 动态取得，**不得硬编码**。账号判定见 §3.2；接口/字段在两体系间的行为差异见 `api_商品写入.md §1.6`、`api_商品读取.md §1.7`。
> 本文是商品板块的入口：子板块地图、已实现功能、账号判定、写操作红线、待确认台账。
> 路径基准：`references/…`、`AGENT_GUIDE.md`、`modules/…` 相对技能包根（`交付区/scm/`）。

## 1. 子板块地图

| 子板块 | 文档 | 内容 |
|---|---|---|
| 商品读取 | `api_商品读取.md` | `wsList` / `wsStatistic` / `getWholesale` / 字典 / 28 个只读 |
| 商品写入 | `api_商品写入.md` | 复制新建 / 生命周期（下架·重上架·结束）/ 单字段编辑 / 整表编辑 |
| 商品下载 | `api_商品下载.md` | 商品专属导出 / 三个入口 `tabCode` / 导出列 / 轮询限流 |
| PMS 活动管理（自营专属） | `api_pms活动管理.md` | 三段式：读取 R1~R24（列表/统计卡/筛选字典/行详情）、写入 W1~W7（下架·上架/运营策略/期间/限购/定向/调价）、导出 E1~E2（同步 xlsx） |
| 委托配送商品 | `api_委托配送商品.md` | 委托配送商品列表/导出/字典 |
| 字段对照 | `zddz.md` | 界面字段 ↔ API key / 提交键（历史 112 / 实测 251，见 `api_商品写入.md §1.2`）/ 活动专属 / 复验口径 / 委托配送商品 |

## 2. 已实现功能

| 能力 | 状态 | 说明 |
|---|---|---|
| 读取（列表/统计/详情/字典/辅助） | ✅ | `api_商品读取.md` |
| 写入（复制新建/生命周期/单字段/整表） | ✅ | `api_商品写入.md`；自营生命周期走 PMS（见 `api_pms活动管理.md`） |
| 单品阶梯价（商品列表→更多） | ✅ **仅自营** | `api_商品写入.md §1.9`：读 `getLadderPriceInfo`、写/删 `addLadderPrice`（均 `singleCoupon`）；**摇钱树账号无此功能入口** |
| 下载（商品专属导出） | ✅ | `api_商品下载.md`；轮询下载见 `references/通用/api_导出任务.md` |
| PMS 活动管理 | ✅ 仅自营 | `api_pms活动管理.md`：读取/写入/导出三段齐备；价格走 `api_pms活动管理.md §3.7` 审批流，导出为同步 xlsx |
| 委托配送商品 | ✅ | `api_委托配送商品.md` |
| 上架新商品 / 商品信息管理 / 批量 / 审核端点 | ⚠️ 未建独立文档 | 端点集中在 `references/附录/接口总表.md`；资料类接口已在 `api_商品读取.md §1.6`、`addWholesale` 提交键模板在 `zddz.md §3`（历史 112 键 / 实测 251 键可接受），**内容未丢但层级未独立** |
| 商品视频（`wholesaleDrugVideo/*` 8 端点） | ⚠️ 仅登记 | 端点与状态已在 `api_商品写入.md §1.8 ①` 登记（真实键名/multipart 字段名未采集，不得猜测） |
| `editSalePrice` / `getCanUploadPic` / `zyFixPriceCheck` / `checkMerpProvDrugCode` / `checkProvDrugCode` | ⚠️ 状态各异 | `api_商品写入.md §1.8 ②③`：`getCanUploadPic` 已实测、`editSalePrice` 仅 type=8 适用且未完整验证、其余仅登记 |
| `deleteWholesale` / `unBindAct` / `checkProvDrugCode` / `batchEdit` 等 | ⚠️ 仅登记 | 见 `api_商品写入.md §1.1` 尾注 + `zddz.md §7` + 附录 |

## 3. 使用约定

### 3.1 账号分类标签（五类：四类 + 例外，唯一事实源）

> 自营 / 摇钱树是**两套权限体系**的称谓，不是具体账号；账号由凭证/`status` 动态取得，**不得硬编码具体账号名**。每个写接口在 `api_商品写入.md §1.1` 都有且只有一个分类。

| 分类 | 标签 | 含义 | 出口 |
|---|---|---|---|
| ① 所有账号通用 | **`通用`** | 自营与摇钱树两体系接口、参数、行为一致 | 本文各 `api_*.md` |
| ② 仅摇钱树 账号 | **`仅摇钱树`** | 仅摇钱树账号体系可用 | 本文各 `api_*.md` |
| ③ 仅自营 账号 | **`仅自营`** | 仅自营账号体系可用 | `api_pms活动管理.md`（PMS 代托管）· `api_商品写入.md §1.9`（SCM 侧阶梯价） |
| ④ 转 Pms_活动管理 | **`转PMS`** | 自营 SCM 侧被自动运营接管，须转 PMS 体系 | `api_pms活动管理.md §2/§3` |
| ⑤ 例外：禁用 | **`禁用`** | 两账号均不可用 / 无 API 出口，须走网页端 | 无（如 `editPrices`、自营结束终态） |

> `【待确认】` 仍用作"接口存在但参数/取值未实测"的**质量标记**（非账号分类），与上述五类正交。旧的 `【仅自营】`/`【仅摇钱树】`/`【PMS→】` 写法已统一为上表标签。

### 3.2 账号体系判定（第一步）

> 判定的是**权限体系**，不是具体账号。具体账号名/`providerId` 由 `python scm.py status` 或凭证动态取得。

| 判定项 | 自营账号体系 | 摇钱树账号体系 |
|---|---|---|
| 体系识别 | `status` 返回的账号归属 / 用户告知 | 同左 |
| `providerId` | 由凭证动态取得 | 由凭证动态取得 |
| 生命周期（下架/重上架/结束） | SCM 接口被自动运营拦截 → **转 PMS**（`api_pms活动管理.md`） | SCM 接口真实生效 |
| 事后整表 `mode=edit` | PMS 托管字段返回成功但不落库 | 全字段随时可改 |
| 价格档位 `getPriceTypes` | 5 档：`1,2,7,8,9` | 6 档：`1~6` |
| 价格上限 | 可设高价 | 供乐药价 ≤ 品类近 30 天成交均价 × 5，超限 `40042` |
| `getDeliveryProviders` | 返回空数组 | 22 家 |
| `wsList.totalRecord` | 触 10000 硬上限 | 未触顶（实测值为真实总数） |

> 判定后按 `§3.1` 的四类标签过滤阅读；未标注即 `① 通用`。

### 3.3 前置与引导（不在本文重复定义）

| 需要 | 读 |
|---|---|
| 基础地址、认证链、公共参数六件套、`provideridm=md5(providerId)`、请求头、错误码、编码 | `references/通用/api_认证与公共约定.md` |
| 筛选参数的动态值域、能力开关、`dict` 命令字典清单 | `references/通用/api_动态字典.md` |
| **导出任务的轮询 / 下载 / 中断 / 任务状态 5 值** | `references/通用/api_导出任务.md` |
| 写操作授权、回滚值、`write-audit.jsonl` 审计 | `AGENT_GUIDE.md §10` |
| CLI 命令与 `--param` 传参规则 | `modules/goods/GUIDE.md` |
| 全量端点索引、其它板块与商品子板块（上架新商品、商品信息管理、批量/审核端点） | `references/附录/接口总表.md` |
| 界面字段 ↔ API key、字段可改性、复验口径 | `zddz.md` |

> 公共参数（每次请求必带）：`token`、`platform="scm-admin"`、`version="1.0.3"`、`ua`、`ex`、`lastBuildTime`。成功码 `code=="40001"`，HTTP 恒 200。
>
> **两种调用方式的鉴权口径（勿混）**：
> - **CLI（`scm.py query/export/dict`）**：`credential.ensure()` 已做 token + cmsToken 双远端校验，`build_session()` 把凭证 cookies（含 `cmsToken`）设到会话 Cookie 并带 `provideridm` 头；业务 body 的 `token` 用 `cred["token"]`。**无需手工取字段**。
> - **手工直连脚本**（`requests` + 自行拼 body）：凭证里 `token`（`ysbang_adminToken`）与 `cms_token`（`/scm-goods` 等 Java 服务会话令牌）身份不同；实测只带 `token` 不带 Cookie 会 `40020 该操作需要登录`，**取 `cred.get("cms_token") or cred.get("token")`**，并显式带 `Cookie` 与 `provideridm` 头。

### 3.4 写操作红线（写前必读）

1. 所有写操作须按 `AGENT_GUIDE.md §10` 授权、限范围、留回滚值与审计；下载 = 读取数据，**不属于写入**，无需写授权。
2. 价格字段必须全档位设值：`unitPrice`/`unitPrice1~9`/`chainPrice`/`cchainPrice`/`cunitPrice`/`cunitPrice1~9`/`oldPrice`。模板缺档位 → 服务端默认 `0` → 0 元购事故。
3. **成本价 `purchasePrice`/`purchasePrice2` 保持源原值，绝不改写**；其余售价按用户红线。
4. `beginDate` = 当日 `01:00:00`、`endDate` 跨度 ≤ 1 月；`minAmount` 须为 `step` 整数倍。
5. 复制/改价后立即复验全档位 > 0 且 > 原价；**复验字段口径见 `zddz.md §5`**（`wsDesc` 与生命周期状态不能用 `getWholesale` 复验）。
6. 批量接口的 `code=40001` ≠ 成功，必须读 `rightCount`/`errorCount`/`info`/`errorReasonList`。
7. **测试/复制产生的活动必须下架**：验证结束后无论成败，收尾用 `WholesaleDrugES2/pause`（或 PMS W1）复验为已下架；未达成须告警，不得留活口。

---


## 4. 待确认台账

### 4.1 仍需实测 / 外部确认（4 项）

| # | 项 | 现状与处置 |
|---|---|---|
| 1 | ② 仅摇钱树 三段式 CSV 产出 | 任务 `（示例任务号）` 提交成功但复查 3 次持续 `status=4` 未产出文件；该账号历史任务 `7999255` 曾 `status=3` 并产出 CSV，说明导出服务本身可用 → 需运营侧确认该任务，或改用 `api_商品下载.md §1.1` 直接下载型接口。**注意**：`status=4` 在自营是短暂态（约 10 分钟后转 3），但**不能假定摇钱树也会转**，勿重复提交（触发 40003 限流） |
| 2 | ③ 仅自营 `tabType=4` ↔ 随心购 | 本账号返回空集；开发素材兜底查询只试 `tabType=2/3/4`，无 tab 名称映射常量。需有随心购活动的账号验证 |
| 3 | ③ 仅自营 PMS 挂网价口径 | PMS 列表 `unitPrice9` 显示源价 34.5，与 SCM `mode=copy` 设定的价不一致；两者是否同源未定论。不影响查询/上下架操作，改价场景须复核 |
| 4 | ③ 仅自营 非一口价活动的 PMS 写操作 | `wholeSaleType` 源码规则为 1/2、运营策略调用层不限类型，但实测仅覆盖一口价；操作特价/批购包邮/整件购前先按 `api_pms活动管理.md §2` 定位并验证 |

### 4.2 已确证结论（本轮从待确认关闭，不再重复追查）

| 项 | 结论 | 出处 |
|---|---|---|
| `calculatePeriod` 值域 | `0`活动期内/`1`每笔/`2`每天/`3`每周/**`4`每月** | `api_pms活动管理.md §5.10` |
| `getYKJEnumConf type` | 全集仅 `1`商圈/`2`供货对象/`3`控销禁销组 | `api_pms活动管理.md §5.12` |
| PMS `wholeSaleType` | 仅 `1`一口价 / `2`特价，其余默认 1 | `api_pms活动管理.md §5.9` |
| 运营策略接口适用范围 | payload 只有 `wholesaleId`+`operationFlag`，调用层不判类型 | `api_pms活动管理.md §3.3` |
| PMS 状态候选码 | `{5:[2,0], 3:[1]}`，**无结束/终态码** | `api_pms活动管理.md §2.6` |
| `buildTime` 格式 | 时分秒补零、月日不补零 | `api_pms活动管理.md §1.2` |
| 字段名疑点 5 项 | `provDrugFactor`/`calculateBeginDate`/`standardUnit`/`barcode`/`appNameDesc` 全部确证 | `zddz.md §6` |

### 4.3 已知缺口与已澄清（非待确认）

| 项 | 定性 |
|---|---|
| `ifLimit` / `maxAmount`（是否限购 + 限购数量） | **确定的功能缺口**：SCM 返回 40001 但被自动运营回退、PMS 限购板块无对应字段，两系统均无出口 |
| `getOnSaleData` | 界面无此按钮，对应功能实为「采购明细」（`api_商品读取.md §1.6` 已闭环）；该端点为早期误记，不再追查 |
| ③ 仅自营 活动「结束」 | **已确认的 API 能力边界**：PMS `ACTIVITY_STATUS_UPDATE_CODES` 仅 `{5:[2,0],3:[1]}` 无终态码，SCM `batchEnd` 软成功 → 任何 API 均无法结束自营活动，须走网页端；无需再测 |

## 5. 阅读顺序

1. 先按 **§3.2 账号判定** 确定自营/摇钱树；
2. 读、写、下载分别进 `api_商品读取.md` / `api_商品写入.md` / `api_商品下载.md`；
3. 字段与复验查 `zddz.md`；自营生命周期/运营策略见 `api_pms活动管理.md`。
