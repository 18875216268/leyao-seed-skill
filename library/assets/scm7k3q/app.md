---
name: "ysb-yunxiaozhu"
version: "0.1.1"
display_name: "药师帮运小助"
display_name_en: "YunXiaozhu"
description: "药师帮Scm系统商家助手，可协助用户进行商品查询、订单查询、链接管理（上下架）、控销管理（控销组增删）、商品图美化（P图、换图）及销售数据分析（销售漏斗分析），帮助商家快速排查链接问题，并提升店铺运营效率。"
description_zh: "药师帮Scm系统商家助手，可协助用户进行商品查询、订单查询、链接管理（上下架）、控销管理（控销组增删）、商品图美化（P图、换图）及销售数据分析（销售漏斗分析），帮助商家快速排查链接问题，并提升店铺运营效率。"
description_en: "Yiyaobang SCM merchant assistant. Supports product queries, order queries, link management (list / delist), controlled-sales management (create and delete control groups), product image beautification (retouch / replace), and sales analysis (sales funnel). Helps merchants troubleshoot link issues quickly and improve store operation efficiency."
triggers: "导出进行中的一口价商品；查来曲唑有哪些活动；看看 SCM 凭证还有效吗；查今天的订单；把自营活动下架；给药店做一条订单链接；改活动备注或限购；把这两张图美化一下；查摇钱树销售流水；查我的品种；看区域划分"
examples_zh:
  - "把进行中的一口价商品导出来"
  - "查一下来曲唑在售的活动"
  - "帮我分析今日销售"
examples_en:
  - "Export all active fixed-price products"
  - "What campaigns does letrozole have?"
  - "Analyze today's sales"
license: "MIT"
compatibility: "Python 3.10+；依赖 requests；凭证默认复用 %LOCALAPPDATA%\\scm-operations-query"
metadata:
  author: "SCM Skill"
  architecture: "分层：app.md(路由) → modules/<板块>/GUIDE.md(能力) → references/*.md(参数)；core 为登录/HTTP/导出任务；assets 为可选工具与场景"
---

# SCM 商家后台助手

> **框架生态提示**：本资产位于某包的 `library/assets/` 下 → 使用前**先回主框架**：上溯到含 `library/engine.py` 的包根，读其 `SKILL.md` 的〈最高准则〉→ `library/ROUTES.md` → 用户区记忆 / 默认资产卡 → 按 `processor/` 五步执行；**独立安装态**（本目录不在 `library/assets/` 下）不受此限——按本资产独立使用即可。

## 登录（唯一入口 · 变量填充版）

> **与主框架衔接（硬）**：触发条件、入口链（取资产路径 → 判「凭证已在位？」→〈登录流程〉/〈验证流程〉 → 作用<业务域>）、失败兜底、通用红线——**一律以主框架 `processor/PROCESSOR.md`〈资产使用准则〉④ 为准**；**本节只填本资产的变量值，不复述流程**。

**变量 1 · 验证动作（只读 · 绝不弹窗）**
python scripts/scm_login.py --status          # SCM 凭证，有效→复用；无效→变量 3
python scm.py status                          # 业务侧状态（含账号/公司/过期口径）
python scm.py pms-status --no-remote          # PMS 凭证（只读，经 core/pms_client 消费主技能凭证）

**变量 2 · 凭证落点（唯一仓库）**
%LOCALAPPDATA%\scm-operations-query\credential.json（24h 过期 + accounts/ 归档；`SCM_OPERATIONS_HOME` / CLI `--cred-dir` 覆盖）
· PMS 凭证：**由主技能 `p3nes3/scripts/pms_login.py` 产出**，落 `%LOCALAPPDATA%\pms-operations-query\credential.json`；本资产经 `core/pms_client.py` **只读消费**（不 import 主技能代码、不读其仓库内部）
· 取用：**有登录器时一律经其工具**（`--status` / `stored_token()`）✓；**禁止 AI 自行获取**（自读 / 自解 / 自拼凭证 ✗）；**令牌明文不得回显** ✗

**变量 3 · 登录器（存在独立登录器 → 必须调用；登录＝一条命令，黑盒使用）**
python scripts/scm_login.py --reuse           # SCM 登录（原生窗）：账密 + 人工验证码 → 免扫码直登 / 企微扫码二次验证
python scripts/scm_login.py --check           # 环境自检：依赖 tkinter（标准库）
python scm.py pms-login                       # PMS 登录：**子进程委托主技能 pms_login.py --reuse**（弹窗能力不变，登录器唯一真源在主技能）
· **位置**：`library/assets/scm7k3q/scripts/scm_login.py`（相对包根）——**在资产根执行**；异 cwd 脚本路径写全即可（参数与 cwd 无关）。
· **登录动作全部由登录器本体完成**（弹窗 / 验证码 / 换证 / 落库）✓；agent 只管等待用户完成登录 → 成功后经其工具取凭证 ✓。
· **唯一路径（硬默认）**：登录＝调起原生窗（`--reuse`）；**本登录器不提供无界面 / 出码模式**；弹窗失败 → `--check` 修复环境 → 重试 → 仍失败 → 询问用户。
· **禁止自写 / 自组装**：不得读源码后另写登录流程、自取验证码/二维码、自拼鉴权、**组装内部类（`LoginFlow` 等）** ✗；对外取凭证只经门面（CLI `--status` / Python 四函数 `relogin / verify_credential / get_credential / is_authenticated`）✓。
· **用户已指定 / 提供凭证或登录方式 → 按其走**（不受上列限制 ✓）。

**变量 4 · 业务域适用表（本资产唯一权威）**

| 凭证来源 | 本资产 SCM 全板块 | 转PMS / 订单链接 / 自营活动管理 |
| --- | --- | --- |
| **SCM 凭证（scripts/scm_login.py 产出）** | ✓ 原生可用 | ✗ 不可用 |
| **PMS 凭证（主技能 pms_login.py 产出，本资产只读消费）** | ✗ 不可用 | ✓ 原生可用 |

· 两套凭证**不得交叉使用** ✗；参数 / 权限 / 限流 / 网络类报错**不触发登录** ✗。

**变量 5 · 重试上限**：登录 / 重登**连续 2 次**失败后询问用户（与 §2.1 L111 及 `AGENT_GUIDE.md` 一致 ✓；按〈问题未解决流程〉：询问用户 → 按决定继续 ✓）。

> 命令路径：均为**资产根相对路径**（cwd＝本 `app.md` 所在目录）✓。

## 凭证消费（供任何子技能复用 · 发送 key）

本资产登录器产出完整凭证（`scripts/scm_login.py --status` 的 stdout 即完整 JSON）。**任何子技能需要 SCM 凭证时按下列任一入口消费**，无需自行登录：

1. `--token <token>`（显式注入，最高优先）；
2. 环境变量 `SCM_TOKEN`（注入一次即全程可用，推荐）；
3. `--credential-file PATH` / 环境变量 `SCM_CREDENTIAL_FILE`（外部凭证 JSON，字段含 `token` 或 `cms_token`）；
4. 本资产登录器本地凭证仓（本地只读，失效且允许交互才弹窗）。

· **取用出口**：`python -c "import sys; sys.path.insert(0,'scripts'); import scm_common; print(scm_common.stored_token())"`（本地只读、绝不弹窗）。
· **子技能纪律**：只声明消费入口、**不读本资产凭证仓、不实现登录**；凭证由 Agent 经〈登录总决策链〉取用后传参（`--token` / `SCM_TOKEN` / `--credential-file`）——与主框架子资产消费范式（PMS `psol5x` / BI `h4dsa6`）一致 ✓。
· `python scm.py call --token ...` 等取数命令支持 key 直注，绕过登录（便于子技能复用与无人值守）。


> **按账号路由（第一步）**：自营与摇钱树是两套独立权限体系、系统天然隔离板块。动手前先 `python scm.py status` 判定账号 → 按 `references/sy.md §0` 路由到该账号可访问的板块与文档；越界板块不猜测、不调用，如实告知。

## 1. 能做什么 / 不能做什么

| 能做 | 不能做 |
|---|---|
| 登录、校验凭证、多账号切换 | 未经授权的写操作 |
| 经授权的写操作（如替换商品主图，见 `assets/tpcl/goods-image.md` §6.2）：限用户指定范围并留审计 | 授权范围外的改动（如顺带改价/库存/上下架） |
| 商品活动查询（状态/类型/标签/关键词） | 采集未实现板块的参数（仅登记端点） |
| 订单查询（列表 / 页签计数）+ 导出/详情（按 `api_订单导出.md` / `api_订单详情.md` 直连） | 越出账号可访问板块调用接口 |
| 摇钱树板块查询（销售流水 / 我的品种 / 区域划分查看，**仅摇钱树账号**，按 `references/我的摇钱树/api_*.md` 直连） | 用自营凭证调用摇钱树板块 |
| 商品导出 CSV（指定状态/全部状态/组单中心，仅 `goods`） | 绕过登录或自动识别验证码 |
| 读取动态字典（价格档位/供货对象等） | 高频并发提交导出（受限流） |
| 图片处理与商品图美化（生图 / 换主体 / 自设计框架） | 训练或微调模型 |

## 2. 前置

- 运行依赖：Python 3.10+ 与 `requests`。
- **两套凭证、互不影响**：
  - SCM：`%LOCALAPPDATA%\scm-operations-query\credential.json`（24h 过期；`--cred-dir`/`SCM_OPERATIONS_HOME` 可覆盖）
  - PMS：`%LOCALAPPDATA%\pms-operations-query\credential.json`（无固定过期，远端实时校验；自营「转PMS」必需）
- 登录需要**人工输入验证码 / 企微扫码**，无法由 Agent 代输。SCM 登录器：`scripts/scm_login.py`（独立可跑）；PMS 凭证由 `scm.py pms-login` 子进程委托主技能登录器产出、本资产 `core/pms_client.py` 只读消费。

## 2.1 任务规则（任何任务）

**登录**

- 任务所需资源若需要登录，Agent **必须主动调起登录**：`python scm.py login [--account <账号>]`；账号优先取 `status` 返回的 `account` 或本地归档 `accounts/`，也可由用户提供；无账号时可省略，在弹窗内输入；
- 人工环节只有一项：**在弹窗内输入验证码（或企微扫码）**；密码可用 `--password` 或环境变量预填，也可弹窗输入；
- 登录命令成功返回后，Agent **立即复验 `status` 并继续原任务**；
- **不得**只回复"请您运行 login"然后中止任务，不得跳过登录改用其它来源；
- 登录遇阻**不得放弃**：先自行排查（错误码、凭证路径、网络/代理），再重试调起；连续 2 次失败，再询问用户。
- **PMS 登录**（仅涉及自营活动管理/转PMS 时）：`python scm.py pms-status` 校验 → 失败 `python scm.py pms-login`（用户扫码）→ 复验。**勿用 SCM 凭证调 PMS 接口**。

**场景与资产**

- **场景优先**：任务开始前先 `python scm.py assets`；`ljgl` 有对应高频场景则按其 GUIDE 执行，无匹配再自行规划；
- **资产优先**：中途卡点需要外部方法/工具时，先查 `assets/` 是否有现成资产可用，或从中获取思路；没有再用自行方案；
- **允许调研**：自行规划时鼓励联网检索文章/论文/类似案例；但接口参数仍以 `references/` 与线上文档为准，不得臆造；
- **求助时机**：自行思考后仍有歧义或无法解决，再询问用户；需要用户选择时，选项顺序必须与用户输入顺序一致（如「第 1 张/第 2 张」），不得重排。

**写操作（分级授权）**

- **默认只读**：无人值守时 Agent 可自由执行读操作，**不得执行任何写操作**（新增/编辑/删除/上下架/上传/替换）；
- **写需授权**，三选一：
  - **场景授权（默认）**：用户按某个场景的触发语提出需求（如「查 X 商品，美化后替换」），即视为同意按该场景执行，**含场景内的写步骤**；Agent 只需动手前一句话说明将写什么；
  - 单次批准：临时需求，执行前说明「接口 + 目标对象 + 变更内容 + 影响」，用户同意后执行；
  - 提前授权：用户事先声明允许在**本次任务/指定范围**内无人值守读写，Agent 可在该范围内自行执行；
- 已授权仍必须：**只做需求范围内的写**（不顺带改价/库存/状态）；执行前留存**回滚信息**（如旧值），失败即回滚并如实报告；每次写操作写**审计日志**（时间/接口/对象/参数脱敏/结果/回滚值）到 `%LOCALAPPDATA%\scm-operations-query\write-audit.jsonl`；
- 超出授权范围或无法判断是否在范围内 → **先问，不执行**。

## 3. 标准动线（6 步）

| 步 | 命令 | 说明 |
|---|---|---|
| 1 | `python scm.py status` | 凭证是否可用（token + cmsToken 双校验），失败退出码 3 |
| 2 | `python scm.py login [--account <账号>]` | 步 1 失败时由 **Agent 主动调起**；用户在弹窗内完成验证码/扫码；成功后回到步 1 复验并继续任务 |
| 3 | `python scm.py modules` | 确认目标板块状态（ready / todo） |
| 4 | `python scm.py query --module <板块> ...` | 查询（见目标板块 GUIDE）；`--module` 默认 `goods`，订单必须显式写 `--module order` |
| 5 | `python scm.py export --module goods ...` | **仅商品**导出并下载（返回 path/rows）；订单/客户/数据导出按各自 `api_*.md` 直连 |
| 6 | `python scm.py dict --name <字典名> \| --list` | 数据字典：枚举/下拉候选（`--list` 列全部字典）；参数取值不确定时先查字典，勿猜 |
| 7 | 汇报 | 如实说明：文件路径、行数、筛选条件；失败给原始错误码 |

> **文档已交付但 CLI 未封装**的接口（订单导出/详情、客户、数据、我的摇钱树、PMS 活动管理）：统一用 `python scm.py call --path <端点> --body '<JSON>'`，参数抄对应 `api_*.md`，**无需手写 HTTP**；完整参数与 `ex` 速查见 `AGENT_GUIDE.md §4.1`。

## 4. 板块路由（11 个，一个文件夹一个板块）

> **第 0 步（先于本表）**：自营/摇钱树两套权限体系、板块系统隔离，先按 `references/sy.md §0` 判定账号并确认目标板块/文档归属；越界不调用、不试探。本表是**技能 CLI 开放状态**，与账号可访问板块是两个维度。

| 板块 | id | 状态 | 先读 | 说明 |
|---|---|---|---|---|
| 商品 | `goods` | ✅ 已实现 | `modules/goods/GUIDE.md` → `references/商品/sy.md` | 查询/导出/字典；授权后写操作；自营自动运营活动转 PMS |
| 订单 | `order` | ✅ 只读查询 · 🟡 导出/详情开放部分 | `modules/order/GUIDE.md` → `references/订单/sy.md` | 〔自营专属〕列表/页签计数走 CLI；导出（6 端点已交付，部分参数待实测）与详情文档已交付，按 `api_订单导出.md`/`api_订单详情.md` 直连；CLI export 仍 `MODULE_TODO` |
| 售后 | `aftersale` | ⚪ 暂未开放 | `modules/aftersale/GUIDE.md` | 2 个端点 |
| 客户 | `customer` | 🟡 开放部分（文档已交付） | `modules/customer/GUIDE.md` → `references/客户/sy.md` | 客户列表/控销组/黑名单/**供货对象管理**已实测；CLI 未开放；26 个 IM 端点仅登记 |
| 数据 | `data` | 🟡 开放部分（文档已交付） | `modules/data/GUIDE.md` → `references/数据/sy.md` | 品种分析 16 + 销售报表 18 〔**通用**〕；店铺流量 2 〔**自营专属**〕；其余 12 个端点仅登记（共 48 个端点） |
| 我的摇钱树 | `cashcow` | 🟡 开放部分（文档已交付） | `modules/cashcow/GUIDE.md` → `references/我的摇钱树/sy.md` | 〔**摇钱树专属**〕销售流水 / 我的品种 / 区域划分查看；11 个端点已交付（含 2 导出 + 2 写，经实时抓包验证），按 `api_*.md` 直连；CLI 未开放；`ex` 取专属值（流水 `MyCashcowSaleLog` / 品种 `MyVariety` / 区域 `RegionDivision`） |
| 营销 | `marketing` | 🟡 开放部分（仅优惠券） | `modules/marketing/GUIDE.md` → `references/营销/api_优惠券管理.md` | 79 个端点中仅**优惠券系统**已交付文档（效期/作废/赠送/活动/创建，两种获取方式）；其余营销端点仅登记，CLI 返回 `MODULE_TODO` |
| 资质 | `qualification` | ⚪ 暂未开放 | `modules/qualification/GUIDE.md` | 4 个端点 |
| 店铺 | `shop` | ⚪ 暂未开放 | `modules/shop/GUIDE.md` | 52 个端点 |
| 资金 | `finance` | ⚪ 暂未开放 | `modules/finance/GUIDE.md` | 33 个端点 |
| 首页 | `home` | ⚪ 暂未开放 | `modules/home/GUIDE.md` | 57 个端点 |

> **取数出口**：`🟡 开放部分`（含订单导出/详情）一律用 `scm.py call`（`AGENT_GUIDE.md §4.1`）；`⚪ 暂未开放` 板块没有参数文档，不臆造参数。
> **状态口径**：`🟡 开放部分`＝接口文档已交付，Agent 按 `references/<板块>/api_*.md` 直接取数（CLI 仍返回 `MODULE_TODO`）；`⚪ 暂未开放`＝只有端点清单，如实告知并给 GUIDE 路径与端点数量，**不猜测参数**。本表是文档/取数状态，`modules` 命令里的 `status=todo` 只表示 CLI 未开放。**订单为混合态**：查询 CLI 可用，导出/详情属 🟡 开放部分。

## 5. 资产（可选，不影响主流程）

| 资产 | 路径 | 状态 |
|---|---|---|
| 图片处理 | `assets/tpcl/GUIDE.md` | 已接入（生图 v1.03） |
| 高频场景 | `assets/ljgl/GUIDE.md` | 已接入（2 个：商品图；**订单链接** 临时控销→复制活动→链接/二维码→定时下架） |

> 高频场景：先 `python scm.py scene` 看是否**已封装**——已封装直接 `python scm.py scene <场景> <动作> ...`（如 `scene ljgl create --store ... --drug ... --price 86 --stock 1500`）；未封装再 `python scm.py asset ljgl` 读索引按 GUIDE 执行。
> **订单链接**（触发语「给药店 X 做一条订单链接」）→ **已封装**：`python scm.py scene ljgl <动作>`，共 **25 个动作**（查询 6 / 创建 1 / SCM 单项改 4 / 控销组 6 / PMS 单项改 3 / 生命周期 4 / 辅助 1，速查见 `assets/ljgl/GUIDE.md §0`；动作清单以 `assets/ljgl/scene.json` 为唯一事实源）；**仅自营**，写操作须 `--confirm`（并遵守 `AGENT_GUIDE.md §10`）。
> 图片处理：先 `python scm.py asset tpcl` 读取 GUIDE；按 GUIDE 读取 `https://st.cfdaili.top/md`，再执行 `python assets/tpcl/tpcl.py ...`。若任务需要 SCM 商品图等登录资源，先 `python scm.py status`，失败先 `login`，登录成功后继续。

## 6. 渐进式披露（按需读，别一次读完）

```
app.md（本文件，路由）
   ├─ references/sy.md §0（第 0 步：账号→可访问板块/文档归属）
   └─ modules/<板块>/GUIDE.md（能力与命令）
        └─ references/*.md（完整参数、枚举、导出列）
```

**商品板块（按需读，别一次读完）**：先读 `references/商品/sy.md`（板块索引：子板块地图 + 已实现功能 + 账号判定）→ 读/写/下载分别进 `references/商品/api_商品读取.md` / `references/商品/api_商品写入.md` / `references/商品/api_商品下载.md` → 字段与可改性查 `references/商品/zddz.md` → 命中 `转PMS`（自营自动运营/限购/定向/价格审批/活动导出）再读 `references/商品/api_pms活动管理.md`（`§2` 读取 / `§3` 写入 / `§4` 导出）。

**订单板块（按需读）**：`references/订单/sy.md` → 查询 `api_订单查询.md §2` → 分页 `通用/api_认证与公共约定.md §9` → 字段 `订单/zddz.md §1.3`；导出/详情按 `api_订单导出.md`/`api_订单详情.md` 直连。

**客户板块（按需读）**：先读 `references/客户/sy.md`（子板块地图 + 已实现功能）→ 客户列表/控销组/黑名单分别进 `references/客户/api_客户列表.md` / `references/客户/api_控销组.md` / `references/客户/api_黑名单.md` → 字段与值域查 `references/客户/zddz.md`。

**我的摇钱树板块（按需读，仅摇钱树账号）**：先读 `references/我的摇钱树/sy.md`（子板块地图 + 归属标记 + 使用约定）→ 摇钱树销售流水 / 我的品种 / 区域划分查看分别进 `references/我的摇钱树/api_摇钱树销售流水.md` / `api_我的品种.md` / `api_区域划分查看.md` → 页面口径与字段对照查 `references/我的摇钱树/zddz.md`；`ex` 取**专属值**（流水 `MyCashcowSaleLog` / 品种 `MyVariety` / 区域 `RegionDivision`，与 L156 及 `AGENT_GUIDE.md` 一致），自营账号无此板块、越界不调用。

**营销板块·优惠券（按需读）**：`references/营销/api_优惠券管理.md`（效期/作废/赠送/活动/创建；两种获取方式=登录查询含二维码 / 共享库免权限；赠送作废的名称反查走 `客户/api_客户列表.md`；折扣 98/9.8/0.98=付98%降2点）→ 过滤规则查 `references/营销/过滤规则.md`。优惠券接口是**独立云函数体系**（非 SCM `/scm-*`），凭证由本资产登录器提供、共享券走数据库层。

- **通用调用器** `scm.py call`（文档已交付但 CLI 未封装时）→ `AGENT_GUIDE.md §4.1`；
- 需要公共参数/认证 → `references/通用/api_认证与公共约定.md`；字典值域 → `references/通用/api_动态字典.md`；导出任务轮询/下载 → `references/通用/api_导出任务.md`
- 需要全量端点 → `references/附录/接口总表.md`
- **写操作** → 先 `AGENT_GUIDE.md §10`（授权/回滚/审计），再按 `references/商品/api_商品写入.md §1`；自营自动运营活动走 `references/商品/api_pms活动管理.md §2/§3`
- 用户使用说明 → `USER_GUIDE.md`
- Agent 会话契约 → `AGENT_GUIDE.md`

## 7. 红线

1. **写需授权**：默认只读；未经批准不得执行写操作；已授权的写仅限用户指定范围，并留存回滚值与审计日志。
2. **不硬编码账号**：账号由用户提供或走已有凭证。
3. **不猜参数**：暂未开放板块只报端点，不编造参数；开放部分板块按已交付文档里的参数直连。
4. **限流**：导出提交遇 `40003` 必须退避 10 分钟，不得连续重试。
5. **如实汇报**：导出失败/0 行必须说明原因，不得声称成功。
6. **测试活动必下架**：为验证/复制而新建的活动，无论主流程成功或失败，收尾必须复验为**已下架/已结束**；未达成须显式告警，不得静默结束任务。
7. **不越界调用**：越出账号可访问板块调用接口 = 违规。

## 8. 网络与数据声明（审核必读）

本技能**只访问以下域名**，均为药师帮官方或其依赖方；**无遥测、无埋点、不上传用户数据**。

| 域名 | 用途 |
|---|---|
| `scm.ysbang.cn` | SCM 商家后台 API：商品活动 / 订单 / 客户 / 数据 / 控销组 |
| `pms.ysbang.cn` | PMS 活动管理 API：限购 / 定向 / 活动时间 / 上下架 |
| `img.ysbang.cn` | 商品图片 CDN（只读，用于取图美化） |
| `dian.ysbang.cn` | 下单链接承载页（**仅拼接 URL 与生成二维码，不发起请求**） |
| `auth.leyopharm.com` · `pms.leyopharm.com` | 部分账号体系的登录与活动域名 |
| `login.work.weixin.qq.com` | 企业微信扫码登录（**仅用户主动登录时**） |
| `st.cfdaili.top` | 可选资产 `tpcl`（图片处理）的第三方服务，**仅使用该资产时访问** |
| `www.kufaka.com` | 可选资产 `tpcl` 的额度页，**仅打印链接，不自动打开** |

**数据流向**：凭证仅写入本地（Windows `%LOCALAPPDATA%\scm-operations-query`，其他系统 `~/.config/scm-operations-query`）；
业务数据只存在于本机内存与用户指定的导出文件，**不上传任何第三方**。
**凭证安全**：不回显明文、不写入日志、不经任何接口下发。
**写操作**：全部需显式 `--confirm`；建组/复制/下架等均可在失败时逆序回滚。
