# SCM 技能 · Agent 会话文档

> 面向 Agent。用户文档见 `USER_GUIDE.md`；资产索引见 `assets/GUIDE.md`；模块能力见 `modules/<板块>/GUIDE.md`。
> 一句话：**统一入口 `python scm.py`，stdout 恒为 JSON，默认只读、写需授权，不猜参数，不代输验证码。**

---

## 1. 调用总则

1. **统一入口**：优先 `python scm.py <command>`；场景文档明确给出 HTTP 写接口且无对应命令时，按 §10.5 复用凭证直接调用；**不要自写登录流程**。
2. **输出解析**：stdout 是单行 JSON；先解析 `ok`，失败看 `error` / `message` / `hint`，再看退出码。
3. **默认只读**：无人值守时只读；写操作（新增/编辑/删除/上下架/上传/替换）须先获授权，授权后仅限指定范围（详见 §10）。
4. **不猜参数**：暂未开放板块只报端点与 GUIDE；开放部分板块（客户/数据）按 `references/<板块>/api_*.md` 已交付参数直连，不编造参数。
5. **人工环节**：登录中只有"弹窗内输验证码/扫码"由用户完成；**调起登录是 Agent 的职责**（`python scm.py login`），不得推给用户运行。
6. **限流**：`40003` 必须退避（红线 10 分钟），不得连续重试。
7. **登录优先**：任务所需资源若需要登录，必须先完成登录再继续，不得跳过或改用其它来源。
8. **登录遇阻不得放弃**：先自行排查（`status` 错误码、凭证路径、网络/代理），再由 Agent 重试调起 `python scm.py login`；连续 2 次失败再询问用户。**不得只提示用户自行运行 login 而中止任务。**
9. **场景优先**：任务开始前 `python scm.py assets`；`ljgl` 有对应高频场景则按其 GUIDE 执行，无匹配再自行规划。
10. **资产优先**：中途卡点需要外部方法/工具时，先查 `assets/` 现成资产可用性，或从中获取思路；没有再自行规划。
11. **允许调研**：自行规划时可联网检索文章/论文/类似案例；接口参数仍以 `references/` 与线上文档为准，不得臆造。
12. **求助时机**：自行思考后仍有歧义或无法解决，再询问用户；需要用户选择时，选项顺序必须与用户输入顺序一致（如「第 1 张/第 2 张」），不得重排；图片角色不确定时先给选项，不要猜。

---

## 2. 标准会话动线

```text
① status                → 凭证是否可用
   ├─ 退出码 0 → 继续
   └─ 退出码 3 → 自查后 Agent 调起 login（用户弹窗内验证码/扫码）→ 复验后继续
①' pms-status           → 仅当任务涉及「自营活动管理/转PMS」时必做（PMS 凭证独立）
   ├─ 退出码 0 → 继续
   └─ 退出码 3 → Agent 调起 pms-login（用户扫码）→ 复验后继续
② modules               → 确认目标板块状态（ready / todo）
③ query / export / dict → 执行能力
④ 汇报                  → 路径、行数、筛选条件；失败给原始错误码
```

### 决策树

```text
用户提出业务请求
  ├─ 先查 assets：ljgl 有匹配场景 → 按场景 GUIDE 执行
  ├─ 涉及登录/凭证？
  │    └─ status；失败 → 先自查 → Agent 调起 login（用户弹窗内完成验证码/扫码）→ 复验继续
  ├─ 涉及「自营活动管理 / 转PMS」？
  │    └─ pms-status；失败 → Agent 调起 pms-login（用户扫码）→ 复验继续 → 读 references/商品/api_pms活动管理.md
  ├─ 涉及某板块？
  │    ├─ modules 查状态
  │    ├─ ready → 读 modules/<板块>/GUIDE.md → 执行
  │    │    └─ 若返回 MODULE_TODO（如订单 export）：属「开放部分」，用 scm.py call 按 references/<板块>/api_*.md 直连（§4.1），勿判为不可用
  │    ├─ todo 且 `references/<板块>/api_*.md` 已交付 → 开放部分：用 scm.py call 按文档直连取数（§4.1；CLI 仍 MODULE_TODO）
  │    └─ todo 且无文档 → 如实告知「暂未开放」+ GUIDE 路径 + 端点数量（MODULE_TODO）
  └─ 涉及写操作？ → 已授权且在范围内？→ 执行并审计；否则 → 说明影响、请求批准
```

> **两套凭证完全独立**：SCM `%LOCALAPPDATA%\scm-operations-query`（有 24h 过期）／PMS `%LOCALAPPDATA%\pms-operations-query`（无固定过期，靠远端实时校验）。登录其一不影响另一个；**任务需要哪个系统就登录哪个，不要用 SCM 凭证调 PMS 接口**。

---

## 3. JSON 契约

### 成功

```json
{"ok": true, "total": 10000, "page": 1, "rows": [ ... ]}
{"ok": true, "path": "SCM_商品_20261105_120000.csv", "rows": 29, "recordId": 123456}
{"ok": true, "dicts": [ {"id": "priceTypes", "name": "价格档位", "path": "..."} ]}
```

### 失败

```json
{"ok": false, "error": "MODULE_TODO", "message": "售后板块暂未开放（已登记 2 个端点）",
 "hint": "查看 modules/aftersale/GUIDE.md", "details": {"module": "aftersale", "endpoints": 2}}
```

### 退出码

| 码 | 含义 | Agent 动作 |
|---|---|---|
| `0` | 成功 | 汇报结果 |
| `1` | 业务错误 | 透出 `error/message`，不臆测成功 |
| `2` | 参数错误（含 `MODULE_TODO`） | 修正参数；若为 `MODULE_TODO`，**开放部分**板块（客户/数据/订单导出·详情）改按 `references/<板块>/api_*.md` 直连取数，**完全暂未开放**板块才如实告知；直连统一走 `scm.py call`（§4.1） |
| `3` | 凭证失效 | 自查后由 Agent 调起 login（用户弹窗内完成验证码/扫码），复验后继续原任务 |

---

## 4. 板块路由

> **第 0 步（先于本表）**：自营与摇钱树为两套独立权限体系，板块由系统天然隔离。先 `python scm.py status` 判定账号，再按 **`references/sy.md §0`** 确认目标板块/文档是否在该账号体系内；越界不调用、不试探。下表是**本技能 CLI 的开放状态**，与账号归属是两个维度。

| 板块 | id | 状态 | Agent 处理 |
|---|---|---|---|
| 商品 | `goods` | ✅ ready | 正常执行 query/export/dict |
| 订单 | `order` | ✅ ready（只读查询）· 🟡 导出/详情开放部分 | 〔自营专属〕query 走 CLI；导出/详情按 `references/订单/api_订单导出.md` / `api_订单详情.md` 直连；CLI export 返回 `MODULE_TODO` |
| 客户 | `customer` | 🟡 开放部分 | 按 `references/客户/api_*.md` 直接取数（客户列表/控销组/黑名单已实测）；CLI 返回 `MODULE_TODO` |
| 数据 | `data` | 🟡 开放部分 | 按 `references/数据/api_*.md` 直接取数（品种分析/销售报表/店铺流量）；CLI 返回 `MODULE_TODO` |
| 我的摇钱树 | `cashcow` | 🟡 开放部分 | **摇钱树专属**（自营账号无此板块）；按 `references/我的摇钱树/api_*.md` 直接取数（销售流水/我的品种/区域划分查看，含 2 导出 + 2 写，已实时抓包验证）；CLI 返回 `MODULE_TODO`；**`ex` 取专属值**（流水 `MyCashcowSaleLog` / 品种 `MyVariety` / 区域 `RegionDivision`） |
| 营销 | `marketing` | 🟡 开放部分（仅优惠券） | 按 `references/营销/api_优惠券管理.md` 取数（优惠券效期/作废/赠送/活动/创建）；CLI 返回 `MODULE_TODO`；其余 79 端点中非优惠券部分仅登记 |
| 售后/资质/店铺/资金/首页 | — | ⚪ 暂未开放 | 仅有端点清单；返回 `MODULE_TODO` + GUIDE + 端点数量 |


### 4.1 通用调用器 `scm.py call`（「按文档直连」的统一出口）

所有「接口文档已交付但 CLI 未封装」的端点（订单导出/详情、客户、数据、我的摇钱树、PMS 活动管理），**一律走 `call`**：复用 `core/http.py` 的凭证、公共参数、业务码与文件流，Agent 只需从 `references/**/api_*.md` 抄 `path` 与 `body`，**不要自己写 `requests`**。

```bash
python scm.py call --path <端点> [--body '<JSON>' | --body @payload.json] [--param k=v ...] \
                   [--host-key scm|pms] [--method post|get] [--ex <ex>] \
                   [--header k=v] [--drop <字段>] [--out <文件>]
```

| 参数 | 作用 |
|---|---|
| `--path` | 站内路径（必填，以 `/` 开头；拒绝 `://`、`..`） |
| `--body` | JSON 对象字符串或 `@文件`（UTF-8）；与 `--param` 合并，后者覆盖同名 |
| `--param` | `k=v` 可重复；值支持 JSON 数组/对象、bool、整数，其余按字符串 |
| `--ex` | SCM 公共参数 `ex`，**默认 `goodsOnShelves`，跨板块必须显式改**（见下表） |
| `--host-key` | `scm`（默认）/ `pms`（自动切 PMS 主机、独立凭证、`module` 头与 body 双 token） |
| `--method` | `post`（默认）/ `get`（直接导出 CSV 类 GET 接口，参数走 query） |
| `--header` | 覆盖请求头，可重复（PMS 其它 module 时用） |
| `--drop` | 从请求体删公共参数字段，可重复（**客户列表要 `--drop lastBuildTime`**） |
| `--out` | 同步 xlsx/CSV 文件流落盘；不给则报 `RESPONSE_INVALID` |

**`ex` 速查**（按目标文档取值，勿猜）：

| 板块 / 子板块 | `ex` | 额外口径 |
|---|---|---|
| 商品列表 / 写入 | `goodsOnShelves`（默认） | 批购包邮 `batchFsShelfDetail`；批量下架 `goodsOffShelves`；委托配送 `ConsignedGoods` |
| 订单 | `AllOrdersList` | `api_订单查询.md §2` |
| 客户列表 | `OldCustomerManagement` | **`version=1.0.0`、不带 `lastBuildTime`** → `--param version=1.0.0 --drop lastBuildTime` |
| 控销组 / 黑名单 | `ControlDrugstoreGroup` | `api_控销组.md` / `api_黑名单.md` |
| 数据·品种分析 | `ProductAnalysis` | `dateRange` 带时刻 |
| 数据·销售报表 | `NewSaleReportNested` | `startTime`/`endTime` Unix 秒 |
| 数据·店铺流量 | `StoreTraffic` | 自定义时间是纯日期 `YYYY-MM-DD` |
| 我的摇钱树·摇钱树销售流水 | `MyCashcowSaleLog` | 数组参数 `province/city/district/deliveryProvider`；时间为 **Unix 秒** |
| 我的摇钱树·我的品种 | `MyVariety` | 默认 `-1`/`0` = 全部；导出/写接口另见文档 |
| 我的摇钱树·区域划分查看 | `RegionDivision` | 无分页 |

**token 不用手工填**：SCM 自动取 `cms_token or token`（见 `references/通用/api_认证与公共约定.md §2.1`）并注入公共参数六件套；PMS 自动取 `pms-login` 落盘凭证，按 `references/商品/api_pms活动管理.md §1.2` 注入 header/body 双 token。凭证缺失分别给 `AUTH_REQUIRED` + `login` / `pms-login` 提示。

> **凭证判定**：`call` **不做**本地 24h 过期拦截、也不跑远端探针（`token` 可能已失效而 `cms_token` 仍有效），由接口业务码 `40000`/`40020` 判定并给登录提示；标准动线仍建议先 `status`。真机验证（2026-11-13）：SCM `getProviderInfo4List2`、PMS `getDayAdjustPriceCount` 均返回 `40001`。

**输出**（恒 JSON）：业务成功 `{"ok":true,"host","path","method","kind":"json","code":"40001","data":...}`；文件流 `{"ok":true,...,"kind":"file","path","bytes","contentType"}`。业务码非 `40001` 按本文 §3 统一映射为 `SkillError`（含 `40003` 限流、`40020` 会话失效提示），退出码沿用 §3。

示例（`--body` 照抄对应 `api_*.md` 的请求体）：

```bash
# 订单列表（参数见 api_订单查询.md §2）
python scm.py call --path /scm-order/wholesaleOrder/list --ex AllOrdersList --body @order_list.json

# 数据·品种分析（ex 必须换；dateRange 按用户需求替换，勿照抄抓包历史日期）
python scm.py call --path /scm-goods/drugsStat/saleReportDrugsStatList --ex ProductAnalysis \
  --body '{"tab":0,"dateRange":["<起 YYYY-MM-DD HH:mm:ss>","<止 YYYY-MM-DD HH:mm:ss>"]}'  # 日期按用户需求替换

# 同步导出落盘（数据板块 3 个 xlsx 接口同理）
python scm.py call --path /scm-goods/drugsStat/exportSaleReportDrugsStat \
  --ex ProductAnalysis --body @payload.json --out out.xlsx

# 客户列表（version / lastBuildTime 特例）
python scm.py call --path /scm-order/crm/list --ex OldCustomerManagement \
  --param version=1.0.0 --drop lastBuildTime --body '{"page":1,"pageSize":20}'

# PMS 活动管理（先 pms-status 校验）
python scm.py call --host-key pms \
  --path /pms-main/ykjWholesaleOperation/exportOneFixedWsList/v27280 \
  --body @pms.json --out onefixed.xlsx
```

> `call` 只负责「按文档发请求」；**写操作仍须先按本文 §10 取得授权**，且只做需求范围内的那一个接口。`⚪ 暂未开放` 板块没有参数文档，`call` 也不能臆造参数。


> `todo` 是 **CLI 状态**，不等于「功能不可用」：客户/数据已交付接口文档，可按文档直连；**只有完全没有参数文档的板块**才只做如实告知、不要猜测参数。

---

## 5. 错误处理模板

| 错误 | 话术 / 动作 |
|---|---|
| `AUTH_REQUIRED` / `AUTH_EXPIRED` / 退出码 3 | “凭证不可用，我先调起登录窗（`python scm.py login`）；请您在窗口内完成验证码/扫码，完成后我立即继续任务。” |
| `RATE_LIMITED`（40003） | “提交过于频繁，已触发限流；请等待约 10 分钟后再试，期间不要连续重试。” |
| `PARAM_INVALID`（40004） | “参数不合法：请检查 `storeType` 是否为数字、日期是否成对且格式 `YYYY-MM-DD HH:mm:ss`。” |
| `EXPORT_TIMEOUT` | “导出任务超时（默认 900 秒）；稍后在导出列表按 recordId 查看，或缩小筛选范围。” |
| `EXPORT_FAILED` | “导出任务持续处于 status=4 超过 600 秒；稍后复查 recordId 或联系运营确认导出服务。” |
| `EXPORT_EXPIRED` | “导出任务已过期、文件已清理；重新提交。” |
| `EXPORT_NO_URL` | “任务已完成但暂无下载地址；稍后复查 recordId。” |

> 以上失败的 hint 均含「勿重复提交」——重复提交会触发 `40003` 限流。`status=4` 是生成中的短暂态，实现会继续轮询，不要见到 4 就重提；可用 `export --poll-timeout <秒>` 调整等待。
| `MODULE_TODO` | “CLI 未封装（已登记 N 个端点）”；开放部分板块须补一句「接口文档已交付，可用 `scm.py call` 按 `references/<板块>/api_*.md` 直连（§4.1）」，完全未开放板块才说「暂不能查询」 |

### 5.1 凭证失败时的自查与调起（必须先做，再找用户）

| 步骤 | 命令 / 判据 | 处理 |
|---|---|---|
| 1 本地凭证状态 | `python scm.py status` 的 `reason` | `expired` → 调起登录；`missing` → 调起登录；其它 → 记录原文 |
| 2 凭证文件 | `status` 的 `credentialPath` 是否存在 | 不存在 → 调起登录；存在但过期 → 调起登录 |
| 3 账号来源 | `status` 的 `account`；或 `%LOCALAPPDATA%\scm-operations-query\accounts\` 归档文件名；或用户提供 | 不得硬编码 |
| 4 网络/代理 | 登录报连接超时 | 检查代理与 DNS，复测一次后再判断 |
| 5 **调起登录** | `python scm.py login [--account <账号>]` | **Agent 主动执行**；用户在弹窗内完成验证码/扫码；成功后复验 `status` 并继续原任务 |
| 5' **调起 PMS 登录** | `python scm.py pms-status` → 失败 `python scm.py pms-login` | **Agent 主动执行**；用户扫码；成功后复验 `pms-status`。**PMS 凭证独立于 SCM**，`reason=not_validated` 多为网络/限流，可重试而非立刻重登 |

> 自查与调起（连续 2 次）都失败后，才询问用户（提供账号/密码或排查环境）；验证码/扫码始终由用户在窗内完成。

---

## 6. 示例对话

### 示例 A：导出进行中的一口价商品

```text
用户：把进行中的一口价商品导出来

Agent：
1) python scm.py status
   → {"ok": true, ...}（退出码 0）
2) python scm.py modules
   → goods = ready
3) python scm.py export --status 进行中 --type 一口价 --out SCM_商品_进行中_一口价.csv
   → {"ok": true, "path": "...", "rows": 29, "recordId": ...}
4) 汇报：已导出到 <path>，共 29 行；筛选条件=状态「进行中」+ 类型「一口价」。
```

### 示例 B：查关键词活动

```text
用户：查一下来曲唑在售的活动

Agent：
python scm.py query --status 进行中 --keyword 来曲唑 --limit 20
→ 汇总 total 与 rows；说明筛选条件与条数。
```

### 示例 C：订单查询

```text
用户：帮我查今天的订单

Agent：
python scm.py modules → order = ready
python scm.py query --module order --param start=<今天> --param end=<今天> --limit 20
→ {"ok": true, "total": N, "rows": [...]}
汇报：今天共 N 单；列出前几条（订单号/客户/金额/状态）；说明筛选条件与页签。
```

### 示例 D：需要登录

```text
用户：查一下商品

Agent：
python scm.py status → 退出码 3（reason=expired，account=自营账号）
自查：凭证文件存在、网络可达 → 属正常过期
Agent 主动调起：python scm.py login --account 自营账号   ← 弹出登录窗
告知用户：请在窗口内输入验证码（或企微扫码）；密码可预填或在窗内输入
登录命令返回成功 → python scm.py status 复验（退出码 0）→ 继续原查询任务
（仅连续 2 次调起失败或无任何账号可用时，才询问用户）
```

---

## 7. 汇报模板

```text
【结果】成功 / 失败
【命令】python scm.py <command> ...
【条件】状态=...；类型=...；关键词=...
【产出】路径=...；行数=...（图片任务：本地文件=...；在线地址=...，1 小时内有效）
【备注】限流/异常/开放状态等
```

- 失败时**必须**给出原始 `error` 码与 `message`，不得声称成功；
- 导出 0 行时说明“0 行”，并建议核对筛选条件；
- 暂未开放板块给出 GUIDE 路径与端点数量；开放部分板块在结果里注明「按 `references/<板块>/api_*.md` 直连取数」。

---

## 8. 红线复述

1. 默认只读；写须授权，且仅限指定范围并留审计；
2. 不硬编码账号；
3. 不猜参数；
4. 限流退避；
5. 如实汇报；
6. 不代输验证码/扫码；
7. 不自行拼装鉴权：写接口复用 `scm.py` 的凭证（见 §10.5），不自建登录。

## 9. 图片处理（生图 v1.03）

当用户需要生成/编辑图片时：

0. **登录优先**：若任务需要 SCM 商品图、客户数据等登录资源，先 `python scm.py status`；失败先 `python scm.py login`，登录成功后继续原任务，不得跳过。
1. 发现资产：`python scm.py assets` → `ljgl`（场景）、`tpcl`（图片工具）；或 `python scm.py asset ljgl` / `asset tpcl`。
   - **先查场景**：`assets/ljgl/GUIDE.md` 命中「商品图」→ 按 `assets/tpcl/goods-image.md` 执行；
   - 支持：单图直接美化、双图（参考美化 / 换主体）、SCM 查商品取图；输出可直出，也可上传替换主图；
   - SCM 查询需先登录；查商品用 `--status 全部`（默认只查「进行中」）；查询未返回图片地址时请用户提供，不得拼接或猜测。
2. 读资产说明：`assets/tpcl/GUIDE.md`。
3. **读线上文档**：`https://st.cfdaili.top/md`（API 基址 `https://st.cfdaili.top/api`）。
   - 用 `web_fetch`，或 `python assets/tpcl/tpcl.py doc`。
   - 可用模型与档位：`python assets/tpcl/tpcl.py prices`（`0`=免费，`null`/`无`=不支持）。
   - 模型/画幅/档位/新增参数以线上文档与本账号 `prices` 为准，不要猜、不要依赖本地参数表。
4. 检查凭证：`python assets/tpcl/tpcl.py status`
   - 返回 `IMAGE_KEY_MISSING` / `IMAGE_KEY_INVALID` / `IMAGE_NO_CREDITS` 时，把 `purchaseUrl`（`https://www.kufaka.com/shop/qimeng`）给用户；用户购买并提供秘钥后执行 `set-key`。
5. 生成：按线上文档组装参数（同一参数只用一种写法）。
   `python assets/tpcl/tpcl.py generate --prompt "..." --out <目录> --model <prices 返回的模型> --size 1:1 --image-size 1K`
6. 汇报：`saved`（本地文件，优先交付）/ `images`（在线地址，1 小时内有效）/ `credits` / `remaining`；失败给原始 `error`。

示例：

```text
用户：帮我生成一张橘猫的图

Agent：
1) python scm.py asset tpcl
2) 读 https://st.cfdaili.top/md（或 tpcl.py doc）
3) python assets/tpcl/tpcl.py status
   → IMAGE_KEY_MISSING + purchaseUrl
4) 回复：请先购买秘钥 https://www.kufaka.com/shop/qimeng，购买后把秘钥发我。
5) 用户提供 sk-... 后：
   python assets/tpcl/tpcl.py set-key sk-...
   python assets/tpcl/tpcl.py generate --prompt "一只橘猫" --out ./out --param model=<prices 返回的可用模型> --param size=1:1
6) 汇报 saved 路径与图片 URL。
```

注意：
- 不打印完整秘钥；
- 不把线上文档参数写死到本地；
- 双图换主体：**先看图裁决角色**（不得凭顺序/文件名假定），然后 `--image` **主体图在前、框架图在后**（模型以第一张为底图，顺序反了只会换背景）；判不准时按用户发图顺序给选项，选项编号只用于沟通、不决定传参顺序；
- 交付以本地 `saved` 文件为主：本站托管图片与签名地址默认 **1 小时**有效（1 小时后自动删除），需留存时用 `--out` 及时下载。

---

## 10. 写操作（授权与审计）

**默认只读**：无人值守时只读；任何写操作（新增/编辑/删除/上下架/上传/替换）必须先获授权。

> 本节只约束"已路由到的板块"内的写操作授权。**板块是否可达由账号权限天然隔离**，Agent 先按 `references/sy.md §0` 判定账号并路由；目标板块/文档不在该账号体系内时不调用、不试探，如实告知。

### 10.1 三种授权

| 方式 | 用户怎么说 | Agent 怎么做 |
|---|---|---|
| **场景授权（默认）** | 按场景触发语提需求，如「查 1447939776，美化后替换」 | **视为同意按场景执行**（含场景内写步骤）；动手前一句话说明将写什么，然后执行 |
| 单次批准 | 临时需求：「可以改这个」 | 执行前说明「接口 + 对象 + 变更 + 影响」→ 用户同意 → 执行 |
| 提前授权 | 「这次允许你直接改主图」 | 在指定任务/范围内可无人值守执行；**超出范围先问** |

> 场景内写步骤已由文档固定（接口、范围、回滚、审计），风险可控；**未命中场景**时才需要单次批准。

### 10.2 执行前后必须做

```text
执行前：记录回滚信息（稳定直链可记 URL；**签名 URL 必须下载文件**）→ 复述「接口 / 对象 / 旧值 / 新值」→ 用户确认（或已在授权范围内）
执行中：只调用被授权的那一个接口，不顺带改价/库存/状态/上下架
执行后：重新查询核验结果 → **测试/复制产生的活动一律复验为已下架/已结束（不留活口）** → 写审计日志 → 汇报（含旧值、新值、接口、结果）
失败：用回滚信息还原 → 如实报告失败原因
```

### 10.3 审计日志

- 路径：`%LOCALAPPDATA%\scm-operations-query\write-audit.jsonl`（UTF-8，一行一条，追加写）
- 字段：`time` / `interface` / `target` / `params`（密钥、密码、token **脱敏**）/ `before` / `after` / `result` / `stage`（apply / rollback / re-apply）
- 写操作**必须**留档；读操作在任务汇报里列出命令与条数即可，不逐条落盘。

### 10.4 红线

- 未授权写入 = 违规；
- 授权范围内"顺手"改其它字段 = 违规；
- 写失败不留回滚值 = 违规；
- 越出账号可访问板块调用接口 = 违规（见 `references/sy.md §0`）；
- 测试/复制产生的活动未下架 = 违规（主流程失败也要收尾复验，不得留活口）。

### 10.5 写接口的调用方式

场景文档给出的写接口（如 `upload2Local`、`updateLogo`）若 `python scm.py` 没有对应命令，Agent **可以直接按文档的 HTTP 说明调用**，但必须：

- 复用 `scm.py` 已产出的凭证（`%LOCALAPPDATA%\scm-operations-query\credential.json` 中的 `token`、`cookies`、`provider_id_m`），**不得自建登录流程、不得自行拼装鉴权**；
- 只调用场景中列明的那一个接口，不扩大范围；
- 调用后按场景要求复验、写审计、必要时回滚。
