---
name: 摇钱树业务线查询v1.0
description: "摇钱树业务线 BI 板块优化 skill（自包含，可独立移植）。覆盖摇钱树销售进度/库存报表/商务考核/货主利润表/补货建议/经营分析 6 个看板、142 张组件、41 个页面筛选器。把取数抽象为高层 DSL（card/date/filters/limit/all/dynamic_params/dynamic_field_filters），内置「页面默认筛选注入矩阵」（各页自动带默认日期，含销售进度 j837 强制带·导出禁带；不带→全表累计错数）、NOT_NULL 跳过、候选值实时获取与缓存、动态值禁硬编码原则。凭证经三窗口（环境变量/框架凭证文件/父登录器回退），本板不实现登录。触发词：摇钱树、钱树、子公司业务线、销售进度、库存报表、补货建议、货主利润表、商务考核、经营分析、各子公司、边际利润率、负利润、滞销。与「出库统计Ultra（通用/万能取数，非运营部专属）」区分：① 用户提及『摇钱树/钱树/子公司业务线』等业务线口径即路由本板；② 但若任务仅涉及『业务类型-摇钱树(YQS)』（把摇钱树作为通用数据里的一个业务类型筛选值），不归本板，应走通用取数(Ultra)；③ 其余涉及摇钱树业务线的，优先本板并先鉴权确认账号能取数。"
---

# 摇钱树业务线查询 — 板块优化 skill

> **框架生态提示**：本资产位于 `i7c4z1` 的 `vendor/optimizers/` 下 → 使用前先回主框架：上溯到含 `library/engine.py` 的包根，读其 `SKILL.md`〈最高准则〉→ `library/ROUTES.md` → 按 `processor/` 五步执行；独立安装态（不在 `library/assets/` 下）按本板独立使用即可。

版本：v1.1（知识基线 2026-09-24；对齐运行时 6+2 看板 / 142+2 组件 / 53 筛选器 / 456 字段；144 卡全量实测校准）

版本记录：
- v1.1（2026-09-24，基于采集记录抓包+144 卡全量实测）：①**修正默认口径**——所有页的卡都必须带页面默认筛选（销售进度 EQ 昨日宏、货主利润 BT 本月到昨天、经营分析/考核 FIRST_PICK 最新月、库存 EQ 今日、补货 FIRST_PICK 最新快照日、配送/人工 EQ 昨日），否则回退全表累计错数（旧文档「本月→昨天」仅对销售进度且形态写错，已删「真值 2.67 亿」错误表述——2.67 亿是 09-22 单日出库口径，非含税销售额）；②修复 `recommended_filters` 对负利润卡（数据集 r6cd9b22f）一刀切强制 j837 的 BUG（该卡日期字段=sc5733bd，实测修复后 23 行 OK）；③默认日期改动态计算（昨日/今日/本月1日运行时取，FIRST_PICK 类取候选最新值），删除硬编码日期；④`_extract` 兼容图表类响应（categories/series，此前维度丢失/数值 null）与系列重名；⑤`query.py`/`query_card` 支持 `dynamic_params`（分析维度等 PARAMETER 传参）与 `dynamic_field_filters`（配送/人工拆分卡必须带 5 个 dz，销售曲线日粒度 dz 已内置）；⑥新增「动态值禁硬编码」原则与「账号归属判定法」；⑦文档补 2 个未收录页（配送/人工成本维度拆分）与 3 张幽灵卡、53 筛选器默认值/纯探测全表。
- v1.0：首次接入。移植并修正已实测的取数/导出/候选逻辑；固化「查询必带、导出禁带 j837 出库日期」铁律；内置完整键组构造、NOT_NULL 跳过、候选值实时缓存；提供 `query.py`/`candidates.py`/`export.py` 三工具；登记 `vendor/SUBSKILL_ROUTING.md` §5。

## ⚠ 用户意图消歧（必须先判断，再路由）

本板是**采购二部·摇钱树项目部专属**业务线板块（销售进度/库存报表/补货建议/货主利润表-商务/商务考核/经营分析 6 看板）。但 BI 通用数据里还有一个叫「摇钱树」的**业务类型（YQS）**维度值——它和本板是两回事，务必分清：

- **业务类型-摇钱树（YQS）**：用户任务只是把「摇钱树」当作通用数据集里的一个筛选值（例如"按业务类型看摇钱树的出库"），**本板不适用** → 走通用取数（出库统计Ultra / `vendor/bi-cookie`），在通用数据里用「业务类型=摇钱树(YQS)」过滤即可。
- **摇钱树业务线（本板）**：用户要的是摇钱树项目部的专属看板数据（销售进度、库存报表、补货建议、货主利润表、商务考核、经营分析）→ **优先本板**，但必须先鉴权（见下）确认当前账号能取数。
- 拿不准时：先跑权限自检；若 `NO_PERMISSION`，明确告知用户"当前账号无摇钱树项目部数据权限"，**不要拿运营 token 硬跑本板，也不要把通用数据里 YQS 过滤的结果冒充本板数据**。

## 何时使用

- 查询「摇钱树业务线」（`q4e929703ce5247db98af47a`）下任意看板/卡片的数据：销售进度（KPI/各子公司/边际利润率/负利润+滞销）、库存报表、补货建议、货主利润表-商务、商务考核、经营分析。
- 需要候选值、筛选取数、分页翻页、导出 Excel 时**优先使用本板**。
- 其它业务线（非摇钱树）或本板字段覆盖不了的：**回退所属通道基础路径** `vendor/bi-cookie/` 直读直查。

## 凭证（凭证窗口：本板不实现登录，只消费凭证）

来源优先级（缺则 `AUTH_REQUIRED`，向调用方索取，不擅自登录）：
1. 环境变量 `BI_UID_TOKEN` + `BI_UID_TOKEN_SIG`；
2. 框架凭证文件 `%LOCALAPPDATA%\bi-operations-query\credential.json`（由父资产 `i7c4z1/scripts/login_bi.py` 扫码落库）；
3. 父资产 `i7c4z1/scripts/login_bi.py` 回退（同资产内，非跨资产）。

- 默认账号：**田浩然（LY110454）**（对摇钱树业务线有权限）。返回 `AUTH_*` 时先换凭证重试一次；不要因参数/权限/限流/网络错误触发换凭证。
- 获取方式：框架内按主框架〈登录流程〉处置，或由用户直接提供 token。**本板不实现登录、禁自写登录流程。**

## 查询（取数）

先读 [references/parameters.md](references/parameters.md)（142 卡 / 41 筛选器全表 + 取数铁律），再把需求写成 JSON 计划传给 `scripts/query.py`：

```text
python scripts/query.py --payload-file plan.json        # 推荐（免管道，cwd = 本板根 yqst01/）
echo '{"queries":[{"id":"t","card":"品种净利润","all":true}]}' | python scripts/query.py
```

计划格式：

```json
{
  "concurrency": 4,
  "queries": [
    {
      "id": "q1",
      "card": "品种净利润",                 // 卡片名称或 cardId
      "date": ["2026-09-01","2026-09-22"],  // 可选：覆盖页面默认日期（默认动态=页面宏口径，勿写死）
      "filters": {"业务类型": ["其他"]},     // 可选：按字段名追加/覆盖筛选（值须合法域值）
      "limit": 50, "all": true,             // 单页大小 / 是否翻页取全
      "dynamic_params": [],                 // 可选：PARAMETER 筛选器传参（分析维度/开始日期等完整 dp 对象）
      "dynamic_field_filters": []           // 可选：动态字段注入（dzId+key+sourceCdId；配送/人工拆分卡必带 5 个）
    }
  ]
}
```

- 卡片按名称（模糊）或 cardId 解析；字段名匹配卡片可传参筛选或驱动本卡的页面筛选器，自动构造完整键组。
- 输出 JSON：`results[].{ok,name,page,columns,rows,count,fetched,hasMoreData,effectiveFilters}`；`rows` 为 `[{列名: 值}]`。

## 取数口径（AI 必遵守）

1. **用户需求至上**：先理解再规划；口径不明时按方向给出建议（筛选/维度/指标/分析思路），歧义点给选项由用户定。
2. **最小充分口径**：以能完成需求的最小取数口径为准，不过度也不欠缺。
3. **默认口径（v1.1 修正）**：`recommended_filters` 按「页面默认筛选注入矩阵」自动注入——销售进度=EQ 昨日宏（j837；负利润卡=sc5733bd）、货主利润=BT 本月到昨天、经营分析/商务考核=FIRST_PICK 最新月、库存=EQ 今日、补货=FIRST_PICK 最新快照日、配送/人工=EQ 昨日；日期一律动态计算，**勿写死**。用户传 `date` 则覆盖默认。
4. **字段映射**：「限定哪些数据」= `filters`，「按什么分组」= 维度（空维度即汇总），「算什么」= 指标；Top N 用 `sort`+`desc/asc`（服务端不保证排序，调用方侧排）。
5. **全量取数**：`all:true` 固定 `filters` 只递增 `offset` 直到 `hasMoreData=false`，合并 `rows`，不把单页当全量。
6. **动态值禁硬编码**：商务/子公司/仓库/公司编码/目标的候选集全部由账号 RLS 实时决定，换账号即变——任何脚本/文档不得把当前账号实测值（商务名/子公司名/编码/目标额）写死；一律运行时经 `candidates.py` 探测。账号归属判定见下。

### 铁律（实测踩坑，必读）

- **每页都须带页面默认筛选**（`recommended_filters` 自动注入，勿绕过）：
  - 销售进度页出库明细集卡不带页面级「出库日期」`j837…` → 金额炸成千亿级（全表累计）；
  - 经营分析/货主利润等其它页卡不带各自默认筛选 → **同样回退全表累计**（实测：含税金额卡 1.245 亿 vs 9 月 941 万；销售曲线 3.66 亿 vs 890 万/月）；
  - 负利润卡（数据集 r6cd9b22f）日期字段是 `sc5733bd…`，对它强制 j837 会 1012（已按数据集区分）。
  - **口径警示**：出库金额（销售进度页「总金额」，单日 EQ 口径）≠ 含税销售额（项目 KPI/货主利润表口径）——两者不可互相当"真值"。
- **导出禁带页面级出库日期 j837**：带 → 任务 `1012 FAILED`。`export.py` 自动剥离。
- **`NOT_NULL` 自带筛选不可传参**（传则 `1012`）→ 跳过（`passable_filters` 已剔除）。
- **筛选值须合法域值**：乱填返回**空结果或 1012**（视字段而定，实测客户类型乱填→空集）——一律用 `candidates.py` 取；库存快照日（STRING 域值）写死"今天"会 1012，必须取候选最新。
- **完整键组**：`name/fdId/dsId/cdId/fdType/filterType/filterValue`（加 `originFilterType/sourceCdId` 更稳），缺键 `5001`。
- **动态参数**：经营分析「分析维度」不传 `dynamic_params` 会回退「省内外」；配送/人工拆分卡必须带全 5 个 `dynamic_field_filters`（dz），否则只回总计 1 行。`query.py` 计划字段 `dynamic_params` / `dynamic_field_filters` 透传。
- **响应两种结构**：透视类 `row/column/data`（取 `v`）；图表类（BASIC_BAR/MULTI_LINE/PIE）`categories+series[].data[].y`（`_extract` 已兼容）。

## 候选值（筛选项选项，实时获取+按用户缓存）

```text
python scripts/candidates.py --filter "业务类型"              # 取候选（缓存优先，TTL 24h）
python scripts/candidates.py --filter "业务类型" --refresh    # 强制重新实测
python scripts/candidates.py --filter "客户类型" --search 重   # 条件返回（按关键字取子集）
python scripts/candidates.py --list                           # 当前缓存概况
python scripts/candidates.py --list-all                       # 列出全部 41 个筛选器
```

- 候选值随公司/账号/业务变化，不内置；长清单（如商品名称 1000+）按 `--search` 关键字分片取（服务端 `exceedLimit` 非错误）。
- 缓存落盘 `resources/candidate_cache.json`（运行时数据，分享本板前可删）。

## 导出（筛选后定制视图 → Excel）

```text
python scripts/export.py --card "商务考核数据" --out 导出.xlsx
python scripts/export.py --card <cardId> --payload-file body.json --out 导出.xlsx
python scripts/export.py --task <taskId> --out 续传.xlsx       # 超时/中断续传
```

- 链路与观远 UI「离线导出」一致：`提交→轮询(FINISHED)→下载`。
- **请求体 `filters` 自动剥离 j837**（带→任务 1012）；结果即筛选后小表（KB 级）。
- 需要「明细+卡片默认布局」的大表时，按 `vendor/SUBSKILL_ROUTING.md` §2 板块降级，用通道导出器 `vendor/bi-cookie/scripts/bi_export.py --card <id> --payload-file body.json`（只带 `filters`、不带 `zoneFilter`）。

## 权限自检（选板必验 · 硬规则）

数据权限按**账号/项目部**隔离：同一 BI token，运营账号取不了摇钱树项目部数据，摇钱树项目部账号也取不了其它项目部数据（同平台同账号体系，但数据权限不互通）。因此**选本板后、正式取数前，必须先验权限**：

```text
python scripts/probe.py     # 输出 {"permission":"ACCESSIBLE|NO_PERMISSION|AUTH_EXPIRED|NETWORK|UNKNOWN"}
```

- `ACCESSIBLE` → 继续本板正常取数/导出/解读流程（下游流程不变）。
- `NO_PERMISSION` → 本板对当前账号不可用：告知用户"当前账号无摇钱树项目部数据权限"，建议换采购二部账号重登（`login_bi` 重登），或改取用户有权限的板块；**绝不跨项目部替选**（如拿运营数据冒充）。
- `AUTH_EXPIRED` → 按框架〈登录流程〉换凭证重试一次。
- `NETWORK` → 重试，非权限问题。

> 注意：BI 的无权限响应伪装成 HTTP 500 + `error_code:1004 无权访问`，不是服务端抖动——自检已按此识别，AI 勿误判为重试。

## 账号归属判定（无用户信息接口 · 运行时探测）

BI 无「账号→所属子公司」查询接口；权限是**数据集级行级权限（RLS）**，体现为候选值与取数结果按账号收窄。判定法（方法通用，结果随账号变，**禁止硬编码任何具体值**）：

```text
1. POST /api/selector/sad0d6e8534c444bfabf2755/data   body={"fieldQuery":{"offset":0,"limit":1000},"filters":[]}
   → sd101「公司名」唯一非空值 = 账号所属子公司（绩效/提成口径）
2. 交叉验证：mc4e04a8480f24497b7b3041（经营分析·子公司名称）应一致
3. 辅证：公司编码前缀 / 仓库名称（配送·人工页）/ 商务经理=本人 / 商务总监=组织上级
4. 权威定论需 BI 管理后台（用户管理→角色/数据权限；数据集→行级权限规则）
```

⚠ 业务线数据集（出库明细/库存/补货快照）候选多为 20 家子公司全量——那是业务线读权限，**不是账号归属**。

## 边界

- 本板自包含：API 契约（`references/api查询文档.md`）、参数文档（`references/parameters.md`）、锚点（`resources/profile.json`）、数据快照（`data/cards.json`/`selectors.json`/`fields.json`）、引擎（`scripts/`）。
- 数据快照会过期：跑 `python scripts/fetch_cards.py --out data --with-candidates` 刷新——**凭证自动读框架凭证文件（login_bi.py 落库），零配置**；目录树内页面/卡片/筛选器声明（含 defaultValue、筛选器→卡片映射 targetFields）与候选值全部动态重拉。页面更新 → 重跑即跟进，`recommended_filters` 的注入矩阵按"快照优先、内置常量兜底"自动对齐。⚠ 目录树外页面（当前：配送/人工成本维度拆分 2 页）不随 folder 拉取，需按其 pgId/卡 id 直调（见 parameters.md §五注记）。
- 本板只访问 `https://bi.leyopharm.com` 业务端点；不实现登录、不弹窗、不写/不加密凭证。

## 已知局限（实测 2026-09-24，客观约束）

- **CUSTOM 复杂报表 2 张**：各子公司进度对比（`ce2dabe2…`）、各子公司拼团/批购/整件购销售（`dcc02551…`）——标准查询报 `5001 complexReport_folder`，属页面联动视图。
- **1 张卡空筛选即错**：随心购组合图 `w0890cbf…` 需自身时间筛选，空 filters 报 `5001 None.get`。
- **1 张卡响应无 chartMain**：整体补货表_副本 `mb3333549…`（metric 区动态 dzId），需专用解析。
- **2 张 DATA_GRID 特例**：月目标及达成 `bdb3381c…`/`m59363ca…` 返回 count=21 但 rows=0（结构特例，需人工核对）。
- **库存快照集瞬时 1012**：新快照导入窗口期，k568af327 数据集整组卡连**正确请求**也报 `1012`（抓包原样重放亦然），快照就绪后自动恢复——勿误判为参数错误而改请求。
- **幽灵引用 3 张**：`kdd957f1…`/`te84cbe61…`/`x2152318…` 只存在于筛选器 targetCdIds，页面已无组件（404），遍历绑定关系时过滤。
- **快照未收录**：配送/人工成本维度拆分 2 页（pgId `o0468c1f…`/`kc5e8e43…`）及其 12 个筛选器不在 cards.json/selectors.json——取数直调 cardId（dz 需求见 §铁律），重跑 `fetch_cards.py` 若目录树可见可自动收录。
- 量级异常 0 张：页面默认筛选注入矩阵（含全表累计形态）已从根上消除「千亿/亿级炸数」。
