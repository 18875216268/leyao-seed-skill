# SCM 商家后台助手 · 用户文档

> 面向使用者（人）。Agent 调用契约见 `AGENT_GUIDE.md`；接口文档总索引见 `references/sy.md`。
> 版本：0.1.1 ｜ 当前完整覆盖：**商品**板块（查询/导出/字典，以及授权后的写操作与自营 PMS 出口）

---

## 1. 这是什么

一个药师帮 SCM 商家后台的命令行助手（**默认只读，写操作需你授权**）：

- 登录 SCM（账密 + 人工验证码，或企微扫码二次验证）；
- 校验凭证是否有效、支持多账号切换；
- 查询商品活动（按状态/类型/标签/关键词）；
- 导出 CSV（指定状态 / 全部状态 / 组单中心）；
- 读取动态字典（价格档位、供货对象等）。

**默认不做**：任何写操作（需你明确授权，且仅限指定范围）、绕过登录、自动识别验证码、高频并发导出。

---

## 2. 环境要求

| 项 | 要求 |
|---|---|
| Python | 3.10+ |
| 依赖 | `requests`（`pip install requests`） |
| 网络 | 可访问 `https://scm.ysbang.cn`（不走系统代理） |
| 系统 | Windows / macOS / Linux；登录弹窗需图形界面 |

---

## 3. 放置与运行

```bash
cd library/assets/scm7k3q
python scm.py modules        # 确认能跑通，列出 11 个板块
```

技能入口固定为 `scm.py`，所有命令输出 **JSON**（stdout），便于人看也便于程序解析。

---

## 4. 首次使用：登录

### 4.1 先查状态

```bash
python scm.py status
```

- 退出码 `0`：已有可用凭证，直接用；
- 退出码 `3`：凭证缺失/过期，需要登录。

### 4.2 登录（会弹窗）

```bash
python scm.py login --account <你的账号>
```

- 密码可预填：`--password <密码>` 或环境变量 `SCM_ACCOUNT` / `SCM_PASSWORD`；
- **验证码必须人工看图输入**；
- 若账号启用了企微扫码，会弹出二维码，用企业微信扫码确认。

### 4.3 凭证位置

| 用途 | 路径 |
|---|---|
| SCM 当前生效 | `%LOCALAPPDATA%\scm-operations-query\credential.json` |
| SCM 按账号归档 | `%LOCALAPPDATA%\scm-operations-query\accounts\credential_<账号>.json` |
| PMS 当前生效 | `%LOCALAPPDATA%\pms-operations-query\credential.json` |

- SCM 覆盖目录：`--cred-dir <目录>` 或环境变量 `SCM_OPERATIONS_HOME`；
- 凭证为**明文 JSON（含 token）**，请确保用户目录权限安全，**不要提交仓库或粘贴到聊天/日志**。

### 4.4 PMS 登录（仅自营活动管理需要）

SCM 与 PMS 是**两套独立凭证**，登录其一不影响另一个。只有当要把**自营活动**做下架/重上架、改运营策略、改限购/定向、调价或导出 PMS 活动列表时，才需要 PMS 凭证：

```bash
python scm.py pms-status     # 先查（不弹窗）
python scm.py pms-login      # 失效再登录（弹企微二维码）
```

- 扫码后凭证落 `%LOCALAPPDATA%\pms-operations-query\credential.json`，**无固定过期时间**，是否有效由远端实时校验；
- `pms-status` 返回 `reason=not_validated` 多为网络/限流，可稍后重试，**不代表凭证失效**；
- PMS 登录器实体在主技能 `p3nes3/scripts/pms_login.py`；本资产通过 `python scm.py pms-login` 委托调用、只读取落盘凭证（**不要外传含 token 的凭证**）。

### 4.5 多账号

```bash
python scm.py status --account 账号A
python scm.py query  --account 账号A --limit 5
```

不指定 `--account` 时使用「当前生效」凭证。

- **切换账号**：`python scm.py login`（不带 `--account`）→ 登录窗账号框为空，可填新账号；登录成功后「当前生效」凭证更新，同时按账号归档，旧账号不丢失；`python scm.py login --account 账号A` 可复用归档凭证切回。
- **数据隔离（实测 2026-11-07）**：不同 `providerId` 的账号数据互不可见。同一活动 ID 在另一账号体系下查询返回 `total=0` —— **换账号不能操作其它供应商的活动**。

---

## 5. 命令速查

| 命令 | 作用 |
|---|---|
| `python scm.py status` | 校验凭证（本地过期 + 远端 token/cmsToken） |
| `python scm.py login --account <账号>` | 登录（弹窗，人工验证码/扫码） |
| `python scm.py modules` | 列出 11 个板块与状态（ready / todo） |
| `python scm.py query ...` | 查询商品活动 |
| `python scm.py export ...` | 导出 CSV |
| `python scm.py dict --list` | 列出 11 类动态字典 |
| `python scm.py dict --name priceTypes` | 取某类字典 |
| `python scm.py assets` / `asset <名>` | 查看资产（tpcl / ljgl） |
| `python scm.py call --path <端点> ...` | 通用端点调用（按 `api_*.md` 直连；参数与 `ex` 速查见 `AGENT_GUIDE.md §4.1`） |

---

## 6. 商品查询

```bash
# 按状态 + 类型 + 关键词
python scm.py query --status 进行中 --type 一口价 --keyword 来曲唑 --limit 20

# 状态计数（9 个状态各多少）
python scm.py query --count --status 进行中

# 第二排统计（15 个字段）
python scm.py query --stats --status 进行中

# 翻页 + 扩展筛选
python scm.py query --page 2 --limit 50 --param isRestrict=1
```

### 参数

| 参数 | 取值 |
|---|---|
| `--status` | `-1`/`0~8` 或中文：进行中/待开始/缺货下架/未上架/已下架/资质待审核/资质不通过/已结束/未动销下架/全部 |
| `--type` | 一口价/特价/限时特价/限时特价可用券/拼团/诊所拼团/批购包邮/赠品/连锁包邮，可重复 |
| `--condition` | 20 项标签（价格过低/可售不足7天/近效期/…） |
| `--keyword` | 综合搜索（活动ID/商品编码/商品名称/批准文号/商品ID/app名称/厂家/活动备注） |
| `--limit` | 每页条数，≤100 |
| `--page` | 页码，从 1 开始 |
| `--param k=v` | 任意扩展筛选，可重复 |
| `--poll-timeout <秒>` | 仅 `export`：导出任务轮询超时（默认 900 秒）；`status=4` 属短暂态会持续轮询，导出服务异常时可缩短等待 |

> 完整筛选参数、接口与字段台账见 `references/商品/sy.md`、`references/商品/zddz.md`。

---

## 7. 商品导出

```bash
# 指定状态
python scm.py export --status 进行中 --type 一口价 --out out.csv

# 全部状态（不含已结束）
python scm.py export --all-status --out all.csv

# 组单中心活动（需账号开通）
python scm.py export --group-center --out group.csv
```

### 导出流程

```text
生成 sqlParams → 提交导出任务(recordId) → 轮询导出记录 → 下载 CSV（GBK）
```

返回 `{ok, path, rows, recordId}`。

### 注意

- CSV 为 **GBK** 编码；用 Excel 直接打开或按 GBK 解析；
- 列数随账号变化（64 基础列 + 动态价格列）；
- **限流**：遇 `40003` 需退避（红线要求 10 分钟），不要连续重试；
- `--all-status` **不含已结束**。

---

## 8. 输出与退出码

成功：

```json
{"ok": true, "total": 10000, "page": 1, "rows": [ ... ]}
```

失败：

```json
{"ok": false, "error": "MODULE_TODO", "message": "...", "hint": "...", "details": {...}}
```

| 退出码 | 含义 |
|---|---|
| `0` | 成功 |
| `1` | 业务错误 |
| `2` | 参数错误（含板块暂未开放 `MODULE_TODO`） |
| `3` | 凭证失效 |

---

## 9. 常见问题

| 现象 | 原因 / 处理 |
|---|---|
| `AUTH_REQUIRED` / 退出码 3 | 没有凭证 → `python scm.py login --account <账号>` |
| `AUTH_EXPIRED` | 凭证过期 → 重新登录 |
| `RATE_LIMITED`（40003） | 提交过频 → 等待 10 分钟再试 |
| `PARAM_INVALID`（40004） | 参数类型/名称错；`storeType` 传数字、日期需成对 |
| 导出 0 行 | 筛选过严或状态不符；核对条件后重试 |
| CSV 乱码 | 文件为 GBK，请按 GBK 打开 |
| `MODULE_TODO` | 仅表示 **CLI 未开放**；客户/数据/摇钱树可按 `references/<板块>/api_*.md` 直接取数；完全暂未开放板块查看 `modules/<板块>/GUIDE.md` |
| 图片处理无凭证 | 运行 `python assets/tpcl/tpcl.py status`，按返回的 `purchaseUrl` 购买后 `set-key` |
| 登录弹窗不出现 | 需要图形界面环境；检查 Python 是否带 tkinter |

---

## 10. 安全与红线

1. **默认只读**：写操作需你授权；授权后仅限指定范围，并留回滚值与审计日志；
2. **不硬编码账号**：账号由用户提供或复用已有凭证；
3. **不猜参数**：暂未开放板块只报端点；开放部分板块按已交付文档参数直连，不编造参数；
4. **限流退避**：`40003` 必须等待，不得连续重试；
5. **如实汇报**：导出失败/0 行必须说明原因。

---

## 11. 图片处理（生图 v1.03）

线上文档：`https://st.cfdaili.top/md`（API 基址 `https://st.cfdaili.top/api`）。
技能**不内置参数表**，使用前先读线上文档，参数以线上文档为准。

```bash
# 检查凭证（无凭证会返回购买链接）
python assets/tpcl/tpcl.py status

# 购买后录入秘钥（先校验再保存）
python assets/tpcl/tpcl.py set-key sk-...

# 文生图
python assets/tpcl/tpcl.py generate --prompt "一只橘猫" --out ./out

# 图生图 / 编辑
python assets/tpcl/tpcl.py generate --prompt "把背景换成夜晚的雪山" --image ./input.png --out ./out
```

- 购买地址：`https://www.kufaka.com/shop/qimeng`
- 本地凭证：`%LOCALAPPDATA%\scm-operations-query\image.json`
- 参数可用 `--param k=v` 透传；完整 JSON 可用 `--body`。

## 12. 板块状态（截至 2026-11-16）

| 板块 | 状态 | 说明 |
|---|---|---|
| 商品 `goods` | ✅ 已实现 | 查询 / 导出 / 字典；含 PMS 活动管理（转 PMS，`api_pms活动管理.md`） |
| 订单 `order` | ✅ 只读查询 · 🟡 导出/详情开放部分 | 〔自营专属〕列表/页签计数走 CLI；导出（6 端点已交付，部分参数待实测）与详情按 `references/订单/api_订单导出.md` / `api_订单详情.md` 直连；CLI export 未封装 |
| 客户 `customer` | 🟡 **开放部分**（文档已交付，CLI 未开放） | 客户列表/控销组/黑名单均已实测，可按 `references/客户/api_*.md` 直接取数 |
| 数据 `data` | 🟡 **开放部分**（文档已交付，CLI 未开放） | **品种分析**（13+3）与**销售报表**（15+3）＝两账号**通用**；**店铺流量**（2 端点，下载无接口）＝**仅自营**。见 `references/数据/sy.md`；其余子板块仅端点登记 |
| 我的摇钱树 `cashcow` | 🟡 **开放部分**（文档已交付，CLI 未开放） | **摇钱树专属**（自营账号无此板块）：摇钱树销售流水（4）/ 我的品种（5）/ 区域划分查看（2），共 11 端点（含 2 导出 + 2 写），已抓包验证；`ex` 取专属值（流水 `MyCashcowSaleLog` / 品种 `MyVariety` / 区域 `RegionDivision`）。见 `references/我的摇钱树/sy.md` |
| 售后 / 营销 / 资质 / 店铺 / 资金 / 首页 | ⚪ **暂未开放**（仅端点清单） | 已建 query/export 骨架（抛 `MODULE_TODO`）；端点清单见各自 GUIDE |

> **直连统一出口**：客户/数据/订单导出等「文档已交付但 CLI 未封装」的接口，用 `python scm.py call`（`AGENT_GUIDE.md §4.1`），无需手写 HTTP。
> **CLI 与文档是两种状态**：客户/数据的 `scm.py query` 仍返回 `MODULE_TODO`（CLI 未开放），但接口文档已交付，可直接按文档构造请求取数；**只有⚪暂未开放的 6 个板块**才既无 CLI 也无参数文档。
> `query.py` / `export.py` 的占位逻辑统一在 `modules/_skeleton.py`，新增实现时直接替换对应函数体即可。
