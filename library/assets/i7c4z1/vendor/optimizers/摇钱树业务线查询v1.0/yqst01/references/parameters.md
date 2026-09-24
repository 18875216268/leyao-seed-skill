# 摇钱树业务线 · 参数文档（板块优化板 yqst01）v1.1

> **快速导航**：§〇 动态值禁硬编码（最高优先）→ §一 取数铁律 → §二 页面默认筛选注入矩阵 → §三 dynamicParams/dynamicFieldFilters 机制 → §四 错误码 → §五 卡片全表（按 cardId 查）→ §六 筛选器全表（按 selectorId 查）→ §七 账号归属判定 → §八 字段字典。
> **Agent 查询路径**：日常取数只读 `app.md`（一屏速查）+ 本文件 §一/§二；按卡查参数 → §五→§六；候选值/账号归属 → §七；全量字段程序读 `data/fields.json`。页面/卡片/筛选器有更新 → 重跑 `fetch_cards.py` 刷新快照（注入矩阵自动跟进）。

> 数据源 `data/cards.json` / `data/selectors.json`（142 张组件 / 41 个筛选器快照 + 2026-09-24 实测增补）。
> 本板是「BI查询」资产 `i7c4z1` 下、针对**摇钱树业务线**的板块优化板；取数入口见 `app.md` 与 `scripts/query.py`。
> v1.1 修订（2026-09-24，基于采集记录抓包 + 144 卡全量实测）：默认口径全面修正、新增页面默认筛选注入矩阵、动态值禁硬编码原则、dynamicParams/dynamicFieldFilters 机制、账号归属判定、2 个未收录页与 3 张幽灵卡。

---

## 〇、动态值禁硬编码（必读 · 最高优先）

**商务经理/运营商务/商务总监、子公司/公司名/公司编码、仓库名称、销售与利润目标**等一切账号域的值，全部由账号 RLS（数据集级行级权限）实时决定——换账号、换角色、权限重配、组织调整都会变。

- ❌ 禁止把任何账号的实测值写进代码或文档常量（反例：田浩然 / 重庆央拓 / 3364 / 央拓重庆仓 / B组-罗芬 / 目标 1358.65 万）。
- ✅ 一律运行时调 `POST /api/selector/{sid}/data`（`filters=[]`）实时获取候选；账号归属用「账号归属判定法」（见 §七）。
- 重要性：①换账号部署立即失效；②**静默错数**（拿 A 账号的子公司集合跑 B 账号 → 空结果或错口径）；③目标/提成类值随月份滚动，写死必过期。
- 本文档所有标注【账号相关】的具体值，仅为 2026-09-24 田浩然（LY110454）账号的实测样本，仅作示意。

**两套候选集合并存属正常**：业务线数据集（出库明细/库存/补货快照）对多数账号放开 20 家子公司全量；项目/绩效数据集（sd101/商务看板/配送·人工成本集）按账号收窄到归属公司。前者≠账号归属。

## 一、取数铁律（必读，实测踩坑）

1. **每页卡片都必须带该页筛选器的默认值等价筛选，否则服务端回退全表累计错数**（实测：经营分析含税金额卡不带月份 → 1.245 亿全表 vs 9 月 941 万；销售曲线 → 3.66 亿 vs 890 万/月）。`scripts/common.py` 的 `recommended_filters` 已按 §二矩阵自动注入，**勿绕过**。
2. **`NOT_NULL` 类型的卡片自带筛选不可传参**（传则 `1012`）→ 跳过（`passable_filters` 已剔除）。
3. **筛选值须为合法域值**：乱填返回**空结果或 1012**（视字段而定，实测客户类型乱填→空集）——优先用 `scripts/candidates.py` 实时获取。⚠ 库存快照日期（导入时间）是 STRING 域值——写死"今天"会 1012（当天未必有快照），必须取候选最新值（代码已按 FIRST_PICK 处理）。
4. **`filters[]` 须为完整键组**：`name/fdId/dsId/cdId/fdType/filterType/filterValue`，缺键返回 `5001`；加 `originFilterType/sourceCdId` 与页面下发一致更稳。
5. **`hasMoreData=true` 必须翻页**：固定 filters 只递增 `offset` 直到 false（实测 l40c8e74 count=6258，offset 0/50/100 各回 50 行）。
6. **两种响应结构都要兼容**（`_extract` 已处理）：透视类 `chartMain.row/column/data`（单元格取 `data[i][j].v`）；图表类（BASIC_BAR/MULTI_LINE/PIE）`chartMain.categories[] + series[].data[].y`。DATA_GRID 类（月目标及达成 2 卡）可能出现 count>0 而 rows=0，属结构特例，需人工核对。

## 二、页面默认筛选注入矩阵（`recommended_filters` 自动执行 · 实测验证）

| 页面 | 数据集 | 注入筛选 | 默认值（动态） | 实测验证 |
|---|---|---|---|---|
| 摇钱树销售进度 | ufef96ceb…（出库明细） | 出库日期 `j837cb1313…` | EQ `{{{yesterday}}}`（昨日） | 10 卡 OK；不带→千亿级 |
| 摇钱树销售进度 | r6cd9b22f…（负利润滞销，仅负利润卡 `r1e015a0c…`） | 日期 `sc5733bd07fa…` | EQ 昨日 | 23 行 OK；**对它强制 j837 会 1012** |
| 摇钱树货主利润表-商务 | f0a3a48a… / v5d3ef958… | 出库日期 `rfa1e0f57…` / `h7bd36ff0…` | BT 本月1日→昨天（宏"本月到昨天"） | 85 行总计 985 万 = 944.87+09-23 ✓ |
| 摇钱树经营分析看板 | adaa03de… | 出库日期 `a98b0457…_month` | IN 最新月（FIRST_PICK，值形如 2026-09） | 6 行客户类型 ✓；不带→全表 1.245 亿 |
| 摇钱树商务考核数据 | sd101… | 出库月份 `nde0c223…` | IN 最新月（FIRST_PICK，值形如 2026-09-01） | 提成卡目标 13586537 ✓ |
| 摇钱树库存报表 | e793470f… | 日期 `pf53227b…` | EQ `{{{today}}}` | 21 行 ✓ |
| 摇钱树补货建议表 | k568af327… | 导入时间 `v5e981858…` | IN 最新快照日（FIRST_PICK 候选第一项**取最新**） | 设计正确；快照导入窗口期服务端整体 1012（连抓包原样重放也 1012），等就绪自动恢复 |
| 配送/人工成本维度拆分（未收录页） | fcd5f335… | 出库日期 `q85ef288…` | EQ 昨日（ADV_FILTER YESTERDAY） | 1 行总计 ✓ |

> 矩阵未覆盖的卡（历史峰值/货主近期/对应品种等）页面本就不下发日期，勿自行添加。
> FIRST_PICK 实现说明：`_first_pick_value` 取候选值**最大值**（最新），带 300s 缓存；候选取不到则跳过注入（传空值会 1012）。

## 三、dynamicParams 与 dynamicFieldFilters（查准的另外两把钥匙）

1. **`dynamicParams`（PARAMETER 筛选器传参）**：元素为完整 dp 对象（`dpId/name/valueType/defaultValue(=所选值)/optionValue/sourceCdId/inheritParent/multiple`）。
   - 经营分析页「分析维度」（`dpId=h24cff5ad…`，sourceCdId `d4abe6f9…`）：**不带时维度回退「省内外」**；带 `defaultValue=客户类型` → 6 行客户类型 ✓。可选维度：省内外/环数标签/业务类型/客户类型/活动类型。
   - 补货页：`开始日期`（`dpId=a320169b…`，默认 today）+ `分析维度`（`dpId=h24cff5ad…`，默认「动销金额区间」）。
   - `query.py` 计划字段 `"dynamic_params": [...]` 透传。
2. **`dynamicFieldFilters`（动态字段注入）**：`{dzId, key, sourceCdId}`。
   - 配送/人工成本拆分卡（`hcaa024eb…`/`lacdb43ec…`）**必须带全 5 个 dz 键**，否则只回总计 1 行（带→109 行=页面一致）。
   - 销售曲线 `v9c23bc…` 的「日/周/月」粒度 dz（`dzId=TwAMPKTY…`，key `GEHhqq…`=日）：不带则按月聚合回 1 行；`CARD_DZ_DEFAULTS` 已内置自动附加。
   - `query.py` 计划字段 `"dynamic_field_filters": [...]` 透传。

## 四、错误码速查

| 码 | 含义 | 处置 |
|---|---|---|
| `5001` | 请求体键名/方法错 | 用完整键组；CUSTOM 复杂报表卡本就报此错 |
| `1012` | 非法过滤参数 | NOT_NULL 误传 / 值不在域（如快照日写死今天）/ **库存快照集新快照导入窗口（连正确请求也报，等就绪重试）** |
| `1004` | 无权访问 | 换有权账号（伪装 HTTP 500，勿当抖动重试） |
| `401`/`1017` | 凭证过期/被顶 | 重扫 `login_bi.py` |
| `40002` | 查询超时 | 收窄日期/降 limit/减维度 |
| `14001` | 数据量 >120MB | 加日期过滤 |

## 五、全量卡片主表（142 张）

> **受页面默认筛选驱动**＝该卡查询时由 `recommended_filters` 自动注入对应页面默认筛选（§二矩阵）；**自身日期字段**＝页面筛选器给该卡提供的其它日期字段（导出可用）。

| 页面 | 卡片 | cdType | chartType | cardId | 数据集 | 筛选数 | 维度 | 指标 | 受页面默认筛选驱动 | 自身日期字段 | 卡片筛选参数 |
|---|---|---|---|---|---|---:|---:|---:|:--:|---|---|
| 摇钱树销售进度 | 拼团金额 环比 同比 | CHART | KPI_CARD | `g5c849398cf6f490ba0e9a5c` | `ufef96cebcac14ff38494bb2` | 0 | 0 | 3 | 是(j837) | 日期 | — |
| 摇钱树销售进度 | 总金额 环比 同比 | CHART | KPI_CARD | `m8f1d3148ff71417680a00c6` | `ufef96cebcac14ff38494bb2` | 0 | 0 | 5 | 是(j837) | 日期 | — |
| 摇钱树销售进度 | 进度指标卡 | CHART | KPI_CARD | `e8d318ee9de154560afa811a` | `ufef96cebcac14ff38494bb2` | 0 | 0 | 3 | 是(j837) | 日期 | — |
| 摇钱树销售进度 | 各子公司月进度 | CHART | BASIC_BAR | `qc1fa1ce1a8214786b139673` | `ufef96cebcac14ff38494bb2` | 0 | 1 | 1 | 是(j837) | 日期 | — |
| 摇钱树销售进度 | 各子公司进度对比 | CUSTOM | - | `ce2dabe25516641cd91dda0b` | `-` | 0 | 0 | 0 | 是(j837) | — | — |
| 摇钱树销售进度 | 各子公司金额同环比 | CHART | GROUPED_COLUMN | `e0b71fce0686f4548a9a412b` | `ufef96cebcac14ff38494bb2` | 0 | 1 | 2 | 是(j837) | 日期 | — |
| 摇钱树销售进度 | 一口价金额 环比 同比 | CHART | KPI_CARD | `hcc045542a1bc4fe3b25bfd6` | `ufef96cebcac14ff38494bb2` | 0 | 0 | 3 | 是(j837) | 日期 | — |
| 摇钱树销售进度 | 批购包邮金额 环比 同比 | CHART | KPI_CARD | `ia7c0520b9e3549399c96651` | `ufef96cebcac14ff38494bb2` | 0 | 0 | 3 | 是(j837) | 日期 | — |
| 摇钱树销售进度 | 各子公司拼团、批购、整件购销售 | CUSTOM | - | `dcc02551cd4a24e788e6b0cd` | `-` | 0 | 0 | 0 | 是(j837) | — | — |
| 摇钱树销售进度 | 整件购 环比 同比 | CHART | KPI_CARD | `b7213a4badb81418286a4640` | `ufef96cebcac14ff38494bb2` | 0 | 0 | 3 | 是(j837) | 日期 | — |
| 摇钱树销售进度 | 包邮类活动出库金额 环比 同比 | CHART | KPI_CARD | `jbca3fb2d32c34854b524aba` | `ufef96cebcac14ff38494bb2` | 0 | 0 | 3 | 是(j837) | 日期 | — |
| 摇钱树销售进度 | 智能洞察 | INTELLIGENT_INSIGHT | - | `r209d4612bb2249339423486` | `-` | 0 | 0 | 0 | 是(j837) | — | — |
| 摇钱树销售进度 | 负利润+滞销费进度 | CHART | PIVOT_TABLE | `r1e015a0c1889460694cc932` | `r6cd9b22f9c544148adc0d6a` | 0 | 2 | 5 | 是(**sc5733bd**，非 j837) | 日期 | — |
| 摇钱树销售进度 | 边际利润率 | CHART | PIVOT_TABLE | `l36e423cbb49847a6b9cb07b` | `ufef96cebcac14ff38494bb2` | 0 | 1 | 4 | 是(j837) | 日期 | — |
| 摇钱树销售进度 | 未命名的文本卡片 2024-09 17:36_副本 | TEXT | - | `i0a8a9503185046978ce560a` | `-` | 0 | 0 | 0 | 是(j837) | — | — |
| 摇钱树销售进度 | 月目标及达成 | CHART | DATA_GRID | `bdb3381cf6ad94260be55922` | `ufef96cebcac14ff38494bb2` | 0 | 2 | 16 | 是(j837) | 日期 | — |
| 摇钱树销售进度 | 月目标及达成 | CHART | DATA_GRID | `m59363ca95b734fc0b3f6b1a` | `ufef96cebcac14ff38494bb2` | 0 | 2 | 24 | 是(j837) | 日期 | — |
| 摇钱树库存报表 | 近30天动销金额>=3000品种库存金额变化_分子公司 | CHART | GROUPED_COLUMN_WITH_LINE | `oe8525ab33e5348adab3558d` | `e793470f623d14c2b9cf135a` | 0 | 1 | 2 | 是(日期=today) | 日期 | — |
| 摇钱树库存报表 | 低效品种占比_分子公司 | CHART | GROUPED_COLUMN_WITH_LINE | `c66a81dc9d2294083908e26e` | `e793470f623d14c2b9cf135a` | 0 | 1 | 1 | 是(日期=today) | — | — |
| 摇钱树库存报表 | 今日库存金额百分比堆积面积图_分子公司 | CHART | PERCENT_STACKED_AREA | `kde4bae6d34184ca7a361e5c` | `e793470f623d14c2b9cf135a` | 0 | 1 | 7 | 是(日期=today) | — | — |
| 摇钱树库存报表 | 今日在库品种数百分比堆积面积图_分子公司 | CHART | PERCENT_STACKED_AREA | `ge8cdf459786e413ea1e7c7a` | `e793470f623d14c2b9cf135a` | 0 | 1 | 7 | 是(日期=today) | — | — |
| 摇钱树库存报表 | 本月入库金额 | CHART | PIVOT_TABLE | `f5e528b3bbdfb477eb1fbf17` | `g4a9d648ff9e74bbb8fc4969` | 0 | 2 | 1 |  | — | — |
| 摇钱树库存报表 | 库存金额指标卡 | CHART | KPI_CARD | `g0afe070225ee4c6d857d474` | `e793470f623d14c2b9cf135a` | 0 | 0 | 3 | 是(日期=today) | 日期 | — |
| 摇钱树库存报表 | 各子公司库存金额 | CHART | PIVOT_TABLE | `v7ecfbc9779dd4f93a088e7b` | `e793470f623d14c2b9cf135a` | 0 | 2 | 14 | 是(日期=today) | 日期 | — |
| 摇钱树库存报表 | 低效品种库存金额指标卡 | CHART | KPI_CARD | `r713e3852371d4bae8d4c6d8` | `e793470f623d14c2b9cf135a` | 0 | 0 | 3 | 是(日期=today) | 日期 | — |
| 摇钱树库存报表 | 低效品种数指标卡 | CHART | KPI_CARD | `t292b8767a3794b358d06726` | `e793470f623d14c2b9cf135a` | 0 | 0 | 3 | 是(日期=today) | 日期 | — |
| 摇钱树库存报表 | 动销>=3000品种指标卡 | CHART | KPI_CARD | `h2a66e75d9e4b4c10b565595` | `e793470f623d14c2b9cf135a` | 0 | 0 | 3 | 是(日期=today) | 日期 | — |
| 摇钱树库存报表 | 各商务库存金额 | CHART | PIVOT_TABLE | `o887f5d9d8a7d458e9ea2e54` | `d8465cfc4bebc4e33866337a` | 0 | 1 | 10 |  | 日期 | — |
| 摇钱树库存报表 | 库存金额百分比堆积面积图_单子公司 | CHART | PERCENT_STACKED_AREA | `t81acd235302545419bd78f9` | `e793470f623d14c2b9cf135a` | 0 | 1 | 7 | 是(近15天BT) | 日期 | — |
| 摇钱树库存报表 | 在库品种数百分比堆积面积图_单子公司 | CHART | PERCENT_STACKED_AREA | `e1d7e298f4f1d49ecb1949f7` | `e793470f623d14c2b9cf135a` | 0 | 1 | 7 | 是(近15天BT) | 日期 | — |
| 摇钱树库存报表 | 各子公司品种数 | CHART | PIVOT_TABLE | `f8537637f1d3346ce9e7a518` | `e793470f623d14c2b9cf135a` | 0 | 2 | 12 | 是(日期=today) | 日期 | — |
| 摇钱树库存报表 | 在途金额指标卡 | CHART | KPI_CARD | `hbbcbeab9704b4c448dd214a` | `e793470f623d14c2b9cf135a` | 0 | 0 | 3 | 是(日期=today) | 日期 | — |
| 摇钱树库存报表 | 库存金额目标 | CHART | KPI_CARD | `l202ce74bde1e4bef919d78d` | `e793470f623d14c2b9cf135a` | 0 | 0 | 3 | 是(日期=today) | 日期 | — |
| 摇钱树商务考核数据 | 绩效 | CHART | PIVOT_TABLE | `n0b88b4ab6c894c3dab05b7a` | `sd101dc3b2d874ea1ab2a979` | 1 | 4 | 10 | 是(出库月份FIRST_PICK) | — | 对应本省本仓ID(LONG) |
| 摇钱树商务考核数据 | 提成 | CHART | PIVOT_TABLE | `k60c6237f22c749119dfe569` | `sd101dc3b2d874ea1ab2a979` | 1 | 4 | 11 | 是(出库月份FIRST_PICK) | — | 对应本省本仓ID(LONG) |
| 摇钱树商务考核数据 | 提成_分摊_本外仓销售 | CHART | PIVOT_TABLE | `s6e6901975998456c8eaf136` | `sd101dc3b2d874ea1ab2a979` | 1 | 2 | 32 | 是(出库月份FIRST_PICK) | — | 对应本省本仓ID(LONG) |
| 摇钱树商务考核数据 | 提成_分摊_边额 | CHART | PIVOT_TABLE | `g0be68262ba914517940cee9` | `sd101dc3b2d874ea1ab2a979` | 1 | 2 | 26 | 是(出库月份FIRST_PICK) | — | 对应本省本仓ID(LONG) |
| 摇钱树商务考核数据 | 未命名的文本卡片 2024-09 17:36_副本 | TEXT | - | `q52d56daea9de4aa0b5bf14a` | `-` | 0 | 0 | 0 |  | — | — |
| 摇钱树商务考核数据 | 商务考核数据 | CHART | PIVOT_TABLE | `k841328c83e2d47b6b6eec5f` | `d53dcd124011c41e8ba4984c` | 1 | 3 | 23 |  | — | 运营商务(STRING) |
| 摇钱树货主利润表-商务 | 活动类型净利润 | CHART | PIVOT_TABLE | `dc89c6232d38148178762f40` | `f0a3a48ad2cb34a6a976ce0b` | 0 | 2 | 11 | 是(本月到昨天) | 时间选择 | — |
| 摇钱树货主利润表-商务 | 品种净利润 | CHART | PIVOT_TABLE | `l40c8e74f45804f81812a7cc` | `f0a3a48ad2cb34a6a976ce0b` | 1 | 4 | 14 | 是(本月到昨天) | 时间选择 | 出库日期(DATE) |
| 摇钱树货主利润表-商务 | 销售曲线 | CHART | MULTI_LINE | `v9c23bcf1c8794fa180b1ccb` | `v5d3ef95807bf49288b37ea3` | 0 | 3 | 1 | 是(本月到昨天+日粒度dz) | 时间选择 | — |
| 摇钱树货主利润表-商务 | 客户类型净利润 | CHART | PIVOT_TABLE | `lc052a34a111f4b9e9aa808e` | `f0a3a48ad2cb34a6a976ce0b` | 0 | 2 | 11 | 是(本月到昨天) | 时间选择 | — |
| 摇钱树货主利润表-商务 | 货主净利润 | CHART | PIVOT_TABLE | `ea6bc6c111ba24410aba0ad8` | `f0a3a48ad2cb34a6a976ce0b` | 0 | 3 | 11 | 是(本月到昨天) | 时间选择 | — |
| 摇钱树货主利润表-商务 |   | CHART | PIVOT_TABLE | `o8421bd92b8764023af85004` | `hb2a4138ca5b44cd48558d5d` | 1 | 6 | 13 |  | 时间选择 | 业务类型(STRING) |
| 摇钱树货主利润表-商务 |   | CHART | GROUPED_COLUMN_WITH_LINE | `w0890cbf3b50c48b3b8c74af` | `hb2a4138ca5b44cd48558d5d` | 1 | 4 | 3 |  | 时间选择 | 业务类型(STRING) |
| 摇钱树货主利润表-商务 | 历史销售峰值 | CHART | PIVOT_TABLE | `qf28fe2e89f6742e6a3554fb` | `e92fafb560cd9433ca4a7fb6` | 0 | 2 | 2 |  | — | — |
| 摇钱树货主利润表-商务 | 历史销售峰值 | CHART | PIVOT_TABLE | `kc476e3b6eb2e43e38313c6f` | `na12943e166a84f8ba11c7b9` | 0 | 2 | 2 |  | — | — |
| 摇钱树货主利润表-商务 | 商务经理销售峰值前五名 | CHART | PIVOT_TABLE | `wb60f1578e5f84cb0a56d2c7` | `k0573143162774aafbf2b1e5` | 0 | 2 | 2 |  | — | — |
| 摇钱树货主利润表-商务 | 对应品种 | DRILL | PIVOT_TABLE | `h15abed23f2494d158d12e12` | `ta8db4060afc74e63acae921` | 1 | 6 | 14 |  | — | 近30天有销售或者仍在库(DOUBLE) |
| 摇钱树货主利润表-商务 | 货主近期数据 | CHART | PIVOT_TABLE | `hc04d154abc4641289d14647` | `ta8db4060afc74e63acae921` | 1 | 2 | 13 |  | — | 本季度有销售或仍在库(DOUBLE) |
| 摇钱树补货建议表 | AI智能洞察 | INTELLIGENT_INSIGHT | - | `b04f8697f3d084b0ea18b56a` | `-` | 0 | 0 | 0 |  | — | — |
| 摇钱树补货建议表 | 库存明细表 | CHART | PIVOT_TABLE | `i5c69e378c88b4f45aa1886a` | `k568af327ec2c42c4b687a06` | 1 | 13 | 13 | 是(导入时间FIRST_PICK) | 导入时间 | 当前除占用库存(DOUBLE) |
| 摇钱树补货建议表 | 整体补货表_副本 | CHART | PIVOT_TABLE | `mb3333549b9694e46bc762f8` | `k568af327ec2c42c4b687a06` | 3 | 13 | 19 | 是(导入时间FIRST_PICK) | — | 补货标签(STRING)、近30天销售数量(DOUBLE)、建议补货量(DOUBLE) |
| 摇钱树补货建议表 | 动销金额分层环比情况 | CHART | GROUPED_COLUMN_WITH_LINE | `s36621e67996f46c0a2af345` | `k568af327ec2c42c4b687a06` | 0 | 1 | 3 | 是(导入时间FIRST_PICK) | — | — |
| 摇钱树补货建议表 | 指标卡-当前库存金额 | CHART | KPI_CARD | `ued8edab976d54e668e189ac` | `k568af327ec2c42c4b687a06` | 0 | 0 | 3 |  | — | — |
| 摇钱树补货建议表 | 指标卡-30天缺货率 | CHART | KPI_CARD | `t82607ca4dece45cc9faf351` | `k568af327ec2c42c4b687a06` | 0 | 0 | 3 |  | — | — |
| 摇钱树补货建议表 | 指标卡-高效品种库存 | CHART | KPI_CARD | `pfc7de8db55cb493cbe147d1` | `k568af327ec2c42c4b687a06` | 0 | 0 | 3 |  | — | — |
| 摇钱树补货建议表 | 指标卡-低效品种库存金额 | CHART | KPI_CARD | `h91b7228bbc0c4c56951679f` | `k568af327ec2c42c4b687a06` | 0 | 0 | 3 |  | — | — |
| 摇钱树补货建议表 | 未命名的文本卡片 2026-30 14:30 | TEXT | - | `te0793c412d264d62be8642d` | `-` | 0 | 0 | 0 |  | — | — |
| 摇钱树补货建议表 | 动销金额区间分层 | CHART | PIVOT_TABLE | `p4f280b7a83c14a389e293ea` | `k568af327ec2c42c4b687a06` | 0 | 1 | 7 | 是(导入时间FIRST_PICK) | — | — |
| 摇钱树补货建议表 | 库存金额分层环比情况 | CHART | GROUPED_COLUMN_WITH_LINE | `vcdb074236ac142e4bc8a49d` | `k568af327ec2c42c4b687a06` | 0 | 1 | 2 |  | — | — |
| 摇钱树补货建议表 | 具体明细 | CHART | PIVOT_TABLE | `h28e3ed9b8c644b0fbf0ed7f` | `k568af327ec2c42c4b687a06` | 0 | 1 | 7 | 是(导入时间FIRST_PICK) | — | — |
| 摇钱树补货建议表 | 库存金额环比 | CHART | GROUPED_COLUMN_WITH_LINE | `o40ed3581d49d4547bd17c46` | `k568af327ec2c42c4b687a06` | 0 | 1 | 2 |  | — | — |
| 摇钱树补货建议表 | 整体补货表 | CHART | PIVOT_TABLE | `jc819ea09878643d9b3e78e9` | `k568af327ec2c42c4b687a06` | 3 | 13 | 19 | 是(导入时间FIRST_PICK) | 导入时间 | 可售天数(DOUBLE)、近30天销售数量(DOUBLE)、建议补货量(DOUBLE) |
| 摇钱树补货建议表 | 核心紧缺型 | CHART | PIVOT_TABLE | `l4d4a113578de482d9964ed5` | `k568af327ec2c42c4b687a06` | 4 | 13 | 14 | 是(导入时间FIRST_PICK) | 导入时间 | 可售天数(DOUBLE)、近30天销售数量(DOUBLE)、建议补货量(DOUBLE)、品种标签(STRING) |
| 摇钱树补货建议表 | 销售紧缺型 | CHART | PIVOT_TABLE | `h47241d5724cc4d22b754da7` | `k568af327ec2c42c4b687a06` | 4 | 13 | 14 | 是(导入时间FIRST_PICK) | 导入时间 | 可售天数(DOUBLE)、近30天销售数量(DOUBLE)、建议补货量(DOUBLE)、品种标签(STRING) |
| 摇钱树补货建议表 | 利润紧缺型 | CHART | PIVOT_TABLE | `j8852564dd07a4f4f80680b9` | `k568af327ec2c42c4b687a06` | 4 | 13 | 14 | 是(导入时间FIRST_PICK) | 导入时间 | 可售天数(DOUBLE)、近30天销售数量(DOUBLE)、建议补货量(DOUBLE)、品种标签(STRING) |
| 摇钱树经营分析看板 | （73 张，含 KPI 区 11 / 分析维度参数图 8 / 流向·分层·结构·趋势 / 增掉量 6 / 未动销 2 / 品种明细 DRILL 家族约 24 / 货主明细 3 / 文本 2） | | | 详见 `data/cards.json`（pgId `vfab00567d6564534a037484`） | `adaa03de09dd84a74a5c19e5` / `sef35be7c05464105b147da3` | | | | **是(月份 FIRST_PICK，47 卡)** / 分析维度 dp 默认客户类型 | 月份/时间区间/周销售区间 | 各卡见快照 |

> 未收录 2 卡（页面存在于目录树外，快照未抓到，取数直调 cardId 即可）：
> `hcaa024eb487b423e9cfd6a9` 配送成本维度拆分（PIVOT，仓库名称×区域×客户类型×业务标签×活动类型，**必须带 5 个 dynamicFieldFilters**）；`lacdb43ecf1984f15b292c21` 人工成本维度拆分（GROUPED_TABLE，同维度，dzId=okVJHF…）。页面 pgId：配送 `o0468c1fe40294c67bf22ebb`、人工 `kc5e8e43ecbd444c8a905ca2`。
> 幽灵引用 3 张（只在筛选器 targetCdIds 出现、页面无组件，取数 404，遍历时过滤）：`kdd957f1d7f42431e824ca6a`、`te84cbe6168864ea1bf99085`、`x2152318fa0cc4128809ef2a`。

## 六、页面级筛选器全表（41 快照 + 12 未收录页 = 53）

> 【账号相关】=候选集随账号 RLS 变化，**禁硬编码**，用 `candidates.py` 实时取；【动态】=FIRST_PICK/宏随时间滚。
> 纯探测列=2026-09-24 实测（`filters=[]`）。

| 筛选器 | 页面 | 类型 | 多选 | 源字段(fdId) | 默认值机制 | 默认值实测 | 候选值(存/总) | 绑定卡 | selectorId |
|---|---|---|:--:|---|---|---|---|---:|---|
| 日期 | 销售进度 | CALENDAR | 否 | SELECTOR_FPH | TIME_MACRO | EQ [{{{yesterday}}}] | 无候选(宏类) | 15 | `nf01a97271a544e08a8f59f4` |
| 日期 | 库存报表 | CALENDAR | 否 | SELECTOR_FPH | TIME_MACRO | EQ [{{{today}}}] | 无候选(宏类) | 11 | `c86ab2970ac9747faa0681c7` |
| 日期(近15天) | 库存报表 | CALENDAR | 否 | SELECTOR_FPH | TIME_MACRO | BT [today-14d, today] | 无候选(宏类) | 2 | `ea06d203bb0a34d8e9e4a9b1` |
| 公司名称 | 库存报表 | DS_ELEMENTS | 否 | 公司名称(`n7d6dbab613ae4f71a856c58`) | FIRST_PICK | 候选第一项【动态】 | 20/20 | 2 | `l361af44d61f149cd9eaf5be` |
| 时间选择 | 货主利润表 | TIME_MACRO | 否 | - | TIME_MACRO | 本月到昨天 | 无候选(宏类) | 15 | `hcea82ee355624105adf8fdc` |
| 子公司名称 | 货主利润表 | DS_ELEMENTS | 是 | 子公司名称(`e86f20d40ee774838b79a0ef`) | FIXED_VALUE | 空（不筛） | 20/20 | 8 | `hc3c7c89de095498498a4f11` |
| 摇钱树货主名称 | 货主利润表 | DS_ELEMENTS | 是 | (`k81aa164d2c8e48efa7f44d6`) | FIXED_VALUE | 空 | 100/193 | 8 | `a2dbfc383a53446bcb961132` |
| 商品名称 | 货主利润表 | DS_ELEMENTS | 是 | (`dde2a3bbbb0294aee8133e6e`) | FIXED_VALUE | 空 | 100/1000 | 6 | `i1805095a0ba04845879e018` |
| 客户类型 | 货主利润表 | DS_ELEMENTS | 是 | (`l41357b2d3667478b82734d2`) | FIXED_VALUE | 空 | 7/7 | 8 | `x52169347744c401fa4eac70` |
| 活动类型分类 | 货主利润表 | DS_ELEMENTS | 是 | (`f843e49e1a6f248c58a0e58c`) | FIXED_VALUE | 空 | 6/6 | 15 | `q76547603eb944316b17b0f1` |
| 商务经理 | 货主利润表 | DS_ELEMENTS | 是 | (`pa48ec0a1b956477fb39ef92`) | FIXED_VALUE | 空 | 1/1【账号相关】 | 14 | `u49129990e4b14728ab14751` |
| 客户是否支付运费 | 货主利润表 | DS_ELEMENTS | 否 | (`pa1dfc338e5ad4b5cb31485c`) | FIXED_VALUE | 空 | 0/0 | 2 | `l1ffa33d3cfaa4f29a0dc4dc` |
| 出库月份 | 商务考核 | DS_ELEMENTS | 是 | (`nde0c223767cb4308be1767d`) | FIRST_PICK | 最新月【动态】 | 9/9 | 4 | `j5b899f883ec2407fb6db514` |
| 公司名 | 商务考核 | DS_ELEMENTS | 是 | (`e741800344f464ed09512718`) | FIXED_VALUE | 空 | 2/2【账号相关·归属判定口】 | 7 | `sad0d6e8534c444bfabf2755` |
| 运营商务 | 商务考核 | DS_ELEMENTS | 是 | (`h6e7c4f739241480d8ebd091`) | FIXED_VALUE | 空 | 1/1【账号相关】 | 6 | `mc45f44f8dd5343f995f1d73` |
| 日期选择(backlog) | 补货建议 | DS_ELEMENTS | 否 | 导入时间(`v5e9818581d114ec0809a757`) | FIRST_PICK | 最新快照日【动态】 | 100/255 | 0 | `nfb156dddf184427480e4d80` |
| 日期选择 | 补货建议 | PARAMETER | 否 | - | TIME_MACRO | {{{today}}} | - | 0 | `v1913dd6e8d2b4758b71d67b` |
| 分析维度 | 补货建议 | PARAMETER | 否 | - | FIXED_VALUE | [动销金额区间] | 4/4 | 0 | `g45ecd397550f4c87a7043b3` |
| 补货时间 | 补货建议 | DS_ELEMENTS | 否 | 导入时间(`v5e9818581d114ec0809a757`) | TIME_MACRO | IN [{{{today}}}]→候选最新 | 100/255 | 5 | `debb04b5f2d0a497499271fa` |
| 公司名称 | 补货建议 | DS_ELEMENTS | 否 | 公司名称(`kf4615969b53147a09554fea`) | FIXED_VALUE | 空 | 1/1 | 0 | `s649611eb371742d8a8f5e6a` |
| 摇钱树货主名称 | 补货建议 | DS_ELEMENTS | 否 | (`s4ee92ce2c73b4611b335ad1`) | FIXED_VALUE | 空 | 100/1000 | 0 | `xca32167c03a7471ea810f54` |
| 月份选择 | 经营分析 | DS_ELEMENTS | 是 | 月(`a98b0457d2c174976a01fe60_month`) | FIRST_PICK | 最新月【动态】 | 22/22 | 47 | `n71de3fc24fc141bb8791c4a` |
| 分析维度 | 经营分析 | PARAMETER | 否 | - | FIXED_VALUE | [客户类型]【账号相关维度语义】 | 6/6 | 0 | `d4abe6f9d592d40d88019e14` |
| 时间区间 | 经营分析 | CALENDAR | 否 | SELECTOR_FPH | 未抓到声明 | 实测 BT[2026-01,2026-09] | 无候选(宏类) | 1 | `iff1fe185a68e43d9b3ae7e2` |
| 周销售日期区间 | 经营分析 | CALENDAR | 否 | 日期筛选_副本_副本(SELECTOR_FPH) | 未抓到声明 | 实测 BT[2026-01-01,09-22] | 无候选(宏类) | 3 | `n1e24de888f8344c3b2c1d1e` |
| 子公司名称 | 经营分析 | DS_ELEMENTS | 是 | 子公司名称(`jb41ea096128e4262bbc36f5`) | 未抓到声明 | 默认空 | 2/2【账号相关·归属判定口】 | 69 | `mc4e04a8480f24497b7b3041` |
| 摇钱树货主名称 | 经营分析 | DS_ELEMENTS | 是 | (`w831869ecf4f74bc4bb739fb`) | 未抓到声明 | - | 100/607 | 65 | `l572a34f53850433f9fd4703` |
| 商品名称 | 经营分析 | DS_ELEMENTS | 是 | (`j7ba6274e1f4f4bb9b4ce340`) | 未抓到声明 | - | 100/1000 | 61 | `bfcf06b939ace4de58981d32` |
| 乐药编码 | 经营分析 | DS_ELEMENTS | 是 | (`ga864d13081cc4f6783b27d1`) | 未抓到声明 | - | 100/1000 | 59 | `p91ac9208d04b4d1583f0590` |
| 省内外 | 经营分析 | DS_ELEMENTS | 是 | (`c723800431730451a820dcec`) | 未抓到声明 | - | 3/3 | 51 | `ib13d4074904b4d8f9586366` |
| 商品编码 | 经营分析 | DS_ELEMENTS | 是 | ERP商品编码(`b763b030f4589485596cada5`) | 未抓到声明 | - | 100/1000 | 59 | `ecba873bef2a84002b623767` |
| 是否本仓 | 经营分析 | DS_ELEMENTS | 是 | (`q304df678772f46948df19b3`) | 未抓到声明 | - | 3/3 | 63 | `h9a0b5026ce314faaa2044d7` |
| 药品id | 经营分析 | DS_ELEMENTS | 是 | (`vdfb13cb121b248eba36de00`) | 未抓到声明 | - | 100/1000 | 59 | `q5b6cc44e93144658bafe1c1` |
| 活动类型 | 经营分析 | DS_ELEMENTS | 是 | (`x8ee62a5707ff45d9801924a`) | 未抓到声明 | - | 8/8 | 48 | `taf241f244590412c881cae4` |
| 客户类型 | 经营分析 | DS_ELEMENTS | 是 | (`x70e25c3fa1ee4b5a9900458`) | 未抓到声明 | - | 8/8 | 51 | `b2cc06c72bb004274a53c30c` |
| 增掉量参数 | 经营分析 | PARAMETER | 否 | - | 未抓到声明 | - | 2/2 | 0 | `c65e2b1d299c3463ab109679` |
| 商务经理 | 经营分析 | DS_ELEMENTS | 是 | (`s5d2d754f36d34173b63c82f`) | 未抓到声明 | - | 33/33【值集随组织变化】 | 65 | `k714cc33abfd24badb320641` |
| 商务总监 | 经营分析 | DS_ELEMENTS | 是 | (`p3c927bca3be14f6b8ec2416`) | 未抓到声明 | - | 1/1【账号相关】 | 71 | `caea28f67e94442f0858ee51` |
| 公司编码 | 经营分析 | DS_ELEMENTS | 是 | (`j034ffc60a755499288226a3`) | 未抓到声明 | - | 100/1000【账号相关】 | 61 | `wd0e42b3e89714db5a2b529d` |
| 是否金钱豹订单 | 经营分析 | DS_ELEMENTS | 是 | 金钱豹标签(`a761d665c48c54061ad31c96`) | 未抓到声明 | - | 2/2 | 59 | `l35887930f7d54c7094e41cd` |
| 出库日期 | 配送成本拆分 | CALENDAR | 否 | 出库日期 | ADV_FILTER | BT [YESTERDAY] | 无候选(宏类) | 1 | `r96bbd66f20be49198f66204` |
| 仓库名称 | 配送成本拆分 | DS_ELEMENTS | 否 | 仓库名称 | 未抓到声明 | 默认空 | 1【账号相关】 | - | `kf0f01799595a4423885eb66` |
| 区域 | 配送成本拆分 | DS_ELEMENTS | 否 | 区域 | 未抓到声明 | 默认空 | 2(市内/省外) | - | `t6f32e40611a043bfa4d9b07` |
| 客户类型 | 配送成本拆分 | DS_ELEMENTS | 是 | 客户类型 | 未抓到声明 | 默认空 | 8 | - | `o308bb23462854987858ad6c` |
| 业务标签 | 配送成本拆分 | DS_ELEMENTS | 是 | 业务标签 | 未抓到声明 | 默认空 | 5(控销/摇钱树/普通/集采/首推) | - | `c785fd4f110864dfd923f5da` |
| 活动类型 | 配送成本拆分 | DS_ELEMENTS | 是 | 活动类型 | 未抓到声明 | 默认空 | 4(批购包邮/普通单/药慧拼(拼团)/连锁采购专区) | - | `x7227d5d11a7e4422bcdbd52` |
| 出库日期 | 人工成本拆分 | CALENDAR | 否 | 出库日期 | ADV_FILTER | BT [YESTERDAY] | 无候选(宏类) | 1 | `ncdfd57827f544480af2ac65` |
| 仓库名称 | 人工成本拆分 | DS_ELEMENTS | 否 | 仓库名称 | 未抓到声明 | 默认空 | 1【账号相关】 | - | `ua1564ed2ae0a4026a989742` |
| 区域 | 人工成本拆分 | DS_ELEMENTS | 否 | 区域 | 未抓到声明 | 默认空 | 2 | - | `l6a8897c054c74fcb861156e` |
| 客户类型 | 人工成本拆分 | DS_ELEMENTS | 是 | 客户类型 | 未抓到声明 | 默认空 | 8 | - | `v1044d91200da499db092e31` |
| 业务标签 | 人工成本拆分 | DS_ELEMENTS | 是 | 业务标签 | 未抓到声明 | 默认空 | 5 | - | `xe10846af52374a06b87cbe0` |
| 活动类型 | 人工成本拆分 | DS_ELEMENTS | 是 | 活动类型 | 未抓到声明 | 默认空 | 4 | - | `l90a99f2e78c34e748771f17` |

## 七、账号归属判定（无用户信息接口，运行时探测）

```text
1. POST /api/selector/sad0d6e8534c444bfabf2755/data   body={"fieldQuery":{"offset":0,"limit":1000},"filters":[]}
   → sd101「公司名」唯一非空值 = 账号所属子公司（绩效/提成口径）
2. 交叉验证：mc4e04a8480f24497b7b3041（经营分析·子公司名称）应一致
3. 辅证：公司编码前缀 / 仓库名称（配送/人工页）/ 商务经理=本人 / 商务总监=组织上级
   （具体值均随账号变化；当前账号样本：3364=重庆央拓、B组-罗芬）
4. 权威定论需 BI 管理后台（用户管理→角色/数据权限；数据集管理→行级权限规则）
```

## 八、字段字典

完整字段字典（fdId→名称/类型/角色/数据集）在 `data/fields.json`（程序读取）。取数单元格取值用 `v`；图表类用 `series[].data[].y`；`hasMoreData=true` 必须翻页取全。
