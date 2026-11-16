# 商品（goods）

> 状态：已实现 ｜ 已知端点 83 ｜ 能力：`query` / `export` / `dict`

## 1. 能做什么

| 能力 | 命令 | 说明 |
|---|---|---|
| 查列表 | `python scm.py query --status 进行中 --type 一口价 --keyword 来曲唑 --limit 20` | 分页查询活动 |
| 查计数 | `python scm.py query --count --status 进行中` | 9 个状态的计数 |
| 查统计 | `python scm.py query --stats --status 进行中` | 第二排 15 个统计字段 |
| 导出 | `python scm.py export --status 进行中 --type 一口价 --out out.csv` | 三段式导出并下载 |
| 导出全部状态 | `python scm.py export --all-status --type 一口价 --out out.csv` | `status=-1` + `tabCode=all` |
| 导出组单中心 | `python scm.py export --group-center --out gc.csv` | 独立接口，无筛选 |
| 字典 | `python scm.py dict --name priceTypes` | 动态值域 |

> **写操作（需授权）**：`scm.py` **没有**写命令。复制新建、下架/重上架/结束、单字段编辑、图片上传等 15 个写接口的路径与参数见 `references/商品/api_商品写入.md §1`；执行前须按 `AGENT_GUIDE.md §10` 取得授权、留回滚值与审计。**自营（自营账号）自动运营活动的生命周期/限购/控销在 SCM 侧被拦截**，须转 `references/商品/api_pms活动管理.md §2/§3`。

## 2. 参数速查（完整字段见 references）

| 参数 | 取值 |
|---|---|
| `--status` | `-1`/`0~8` 或中文：进行中/待开始/缺货下架/未上架/已下架/资质待审核/资质不通过/已结束/未动销下架/全部；**不传默认 `0`（进行中）**，按商品名找货请用 `全部`（不含已结束） |
| `--type` | 一口价/特价/限时特价/限时特价可用券/拼团/诊所拼团/批购包邮/赠品/连锁包邮，可重复 |
| `--condition` | 价格过低/可售不足7天/近效期/…/品种补贴/未动销且未调价即将下架（共 20 项） |
| `--keyword` | 综合搜索（活动ID/商品编码/商品名称/批准文号/商品ID/app名称/厂家/活动备注） |
| `--limit` | 每页条数，≤100 |
| `--param k=v` | 扩展筛选（可重复）：`--param isRestrict=1`、`--param busiScope=[1,2]`、`--param hasLogo=true`。整数（无前导零）转 int；前导零、`true/false`、数组/对象保持原值；**不覆盖** `--status/--keyword/--type/--condition` |

> 完整接口、参数、状态/类型/标签映射、导出列、字段台账：
> - `references/商品/sy.md`（板块索引：子板块地图 + 已实现功能 + 账号判定）
> - `references/商品/api_商品读取.md` / `references/商品/api_商品写入.md` / `references/商品/api_商品下载.md`（读取/写入/下载接口与参数）
> - `references/商品/zddz.md`（界面字段 ↔ API key、可改性、复验口径）
> - `references/商品/api_pms活动管理.md`（自营 PMS 出口，三段式：**读取** 列表/统计卡/筛选字典/行详情 → **写入** 下架·重上架/运营策略/活动期间/限购/定向/快速调价 → **导出** 同步 xlsx）
> - `references/通用/api_动态字典.md`（字典值域、能力开关）
> - `references/通用/api_导出任务.md`（任务轮询/下载/中断）

## 3. 限制与注意

1. 日期类筛选必须**成对**且格式 `YYYY-MM-DD HH:mm:ss`（用 `--param wsBeginDate=... --param wsEndDate=...`）。
2. `storeType` 传数字（传数组报 40004）。
3. 导出提交有限流：`40003` 时退避 10 分钟（实测 75s 可连续 9 次）。导出任务轮询默认 900 秒，`status=4` 是短暂态会继续轮询（勿见到 4 就重提）；可用 `--poll-timeout <秒>` 调整。
4. `status=-1`（全部状态）**不含已结束**。
5. 导出 CSV 为 **GBK**；列数随账号变化（64 基础列 + 动态价格列）。
6. `--stats` 仅按 `--status` 统计，忽略其它筛选（接口只收 `status`）；`--group-center` 不接受筛选参数。
7. 商品列表的「业务操作」（暂停/批量暂停/批量结束/批量编辑等）属**写操作**，须按 `AGENT_GUIDE.md` §10 取得授权后执行，且仅限需求范围。图片上传 / 改主图走 `assets/tpcl/goods-image.md` §6.2，无 `scm.py` 命令；下架 / 重上架 / 结束的参数、状态流与风险见 `references/商品/api_商品写入.md` §1.3，自营自动运营活动须转 `references/商品/api_pms活动管理.md` §2/§3。

## 4. 已知边界（不生效项）

`compCode`、`areaIds`、`areaExcludeIds` 查询不生效；`isInjection` 列表生效、导出不支持；`condition=18` 不生效。
