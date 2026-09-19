# 设计说明（自包含 · 供独立分发）

> 本文件是 `leyao-knowledge` 的自包含设计摘要；调研出处与取舍依据见实现注释中的一句式引用（Anthropic Contextual Retrieval / Generative Agents / LongMemEval / MCP Design Patterns / GPT Semantic Cache）。

## 一、定位

只做"查知识"：**运营知识库（公共池）优先 → 乐药云智库兜底**；返回可解释答案 + 分层审计；无命中如实拒答。

## 二、优先级链（resolve.py）

```
精确缓存(≈0ms) → 语义缓存(相似度≥0.85) → 本地记忆(三因子)
→ 公共池(★；共享池+注入池一次全取、trust 排序；口径只走注入池) → 云智库 → 拒答(建议 → 向用户确认)
```
- **早停（仅在结果足够时）**：池结果达到质量门槛（≥2 条相关或 1 条强命中）→ 跳过云智库（保证"快"）；**不足态不早停**（继续兜底）；`--expand` 关闭早停（两库都取）；`--deep` 深词（2-gram）多候选；`--only pool|leyou` 限定单源（**优先级链≠降级链**：可按情况指定/并发）；
- **相关性过滤**：池结果按整词门槛过滤（`_keep`）；**云智库结果同经过滤（rel=0 的丢弃）**——防"对任意词都有返回"的垃圾挡住如实拒答（实测 2026-09-19：乱词 5 条垃圾全部来自云智库且 rel=0）；
- **口径例外**：`need_type=caliber` 只查注入库（`tier=inject`）——口径必须权威（对齐池侧语义）；
- **预算**：`registry.budget_seconds`（默认 20s）+ 各源 `timeout_s`（池 6s / 云智库 12s）；**池侧重试窗口与预算挂钩**（默认 ≤60% 预算，`--only pool` 用全预算；慢挂到点即收口，实测 5.6s 返回）+ **链路故障降级**（首词网络全败 → 后续词单次尝试，实测 5 次请求 vs 旧 9 次）；
- `path[]` 逐层审计（命中/跳过/耗时/原因），失败**不静默**。

## 三、三条目标对应的机制

| 目标 | 机制 | 依据（一句式） |
| --- | --- | --- |
| **准确** | 查询规范化+同义词（`ALIASES`）+时间感知；两路召回融合；**单一 authority**；冲突显式并列；拒答；两段分测（Recall@k 与 rubric） | LongMemEval：查询侧扩展 +11.3% recall；检索增益≠端到端增益；Anthropic：混合+重排失败率 −67% |
| **快速** | 精确缓存 + 语义缓存（无模型相似度，阈值可校准）+ 早停 + 单请求全取 + 预算 | GPT Semantic Cache：0.8 阈值命中 61.6–68.8%、阳性命中 92.5–97.3% |
| **越用越聪明** | 记忆对象（importance/evidence/adopt/fail）+ 三因子检索 + feedback 闭环（晋升/存疑 + 池侧采纳上报）+ reflect（带证据洞察）+ 冷存不删 + 沉淀上传（显式 `contribute`：本地质量闸 → 池侧三层闸+帕累托） | Generative Agents：recency(0.995^h)+importance+relevance 等权；反思=带证据的高层洞察 |

## 四、协议 1.0（返回字段）

`ok / plugin / protocol / problem / need_type / need_type_why / answer / best / possibilities[] / path[] / resolved / early_stop / elapsed_ms / query_id / has_more / next_offset / total_count / suggestions / time_hint`
未命中额外含 `reason`（`no_match` / `no_authority`）。

## 五、边界

- 不弹窗（云智库未登录→`LOGIN_REQUIRED`+指引）；不编造（拒答）；运行数据不写包内（挂载态 → `<包父级>/.leyao-data/data/assets/<id>/`；独立态 → 默认 `~/.leyao-kb/`，`LEYAO_KB_HOME` 可覆盖）；
- 语义缓存为**无模型降级版**（阈值默认 0.85，需按真实语料校准；embedding 版为可选增强）；
- **缓存有界陈旧**：桶级 TTL（口径/制度/术语/课程 24h、搜索 1h）+ **拒答即失效**（防"错答被语义缓存复利"）+ 命中透出 `cached_at`/`version`；漂移检测 / embedding 版本键控为可选增强——依据：Tian Pan《Cache Invalidation for AI》(2026) · GPT Semantic Cache；
- 不做向量库、多智能体；知识写入（submit/inject）必须显式（`contribute`），仅采纳价值信号随 feedback 自动上报（失败静默）。

## 六、业界依据（三轮调研映射 · 16 源）

> 每条设计决策可溯源（非拍脑袋）；对齐点：**A 默认多查** ← 强约束领域检索收益最大；**B 查得中** ← 查询改写/中文检索；**C 查得全** ← 交错迭代；**D 查得准** ← 充分性门控；**E 有界出口** ← 有界停止 + 弃权/澄清四分类；**工具面** ← "工具即契约"。

| 主题 | 来源 | 采纳结论 |
| --- | --- | --- |
| 技能结构 | Anthropic Agent Skills 官方（2025-10） | 渐进式披露三层 + 四条准则（从评估开始/为规模化/站模型视角/迭代）——本资产结构同构 |
| 何时检索 | Adaptive-RAG（NAACL'24, 2403.14403） | 按查询复杂度路由（直答/单步/多步）→ 强约束业务域取"多查"侧 |
| 自适应自评 | Self-RAG（ICLR'24） | IsRel/IsSup/IsUse → `_keep` 门槛 / `_insufficient` / 拒答三件套 |
| 多轮交错 | IRCoT（2212.10509）· Search-R1（2503.09516） | 检索与推理交错、多轮重建查询 → 规范 C |
| 纠错闭环 | Corrective RAG · Agentic RAG 综述（2501.09136） | 相关性评估→查询重构→补充→合成；**迭代要有界**（停止条件+显式阈值）→ 规范 E |
| 轮数收益 | 多轮 RAG 停止专题（2608.13237）· Stop-RAG（2510.14337） | 第 1 轮最大、2–3 轮增量、4 轮后递减；值驱动停止 → "≥3 轮无果转出口" |
| 查询改写 | HyDE / Query2doc / 查询优化综述（2412.17558） | 短 query 召回差 → 换表述/扩写 → 规范 B"换词四法" |
| 中文检索 | BM25+jieba / N-gram→BM25 实践 | 关键词检索擅长专业名词；N-gram 中文兜底 → `--deep` |
| 充分性 | Sufficient Context（ICLR'25, 2411.06037） | 相关≠充分；模型不会自判"够不够"→ **外部显式门控**；充分→答/部分→澄清+重查/不充分→弃权；企业域弃权代价≪幻觉 |
| 出口设计 | AwN（Learning to Ask）· 会话澄清（2112.07308） | 澄清四类（缺信息/歧义/有误/超能力）+ 效率约束 → 规范 E |
| 弃权能力 | 弃权综述（TACL'25）· AbstentionBench（2506.09038） | 弃权是独立能力、需显式设计（推理模型更爱硬答）→ 出口写成硬规范 |
| 上下文工程 | Anthropic《Effective Context Engineering》（2025-09） | "最小高信号 token 集"；**工具即契约**（宁精简勿臃肿）；预取→即时检索 |
| 记忆 | Generative Agents · LongMemEval（既有） | 三因子检索；查询侧扩展 +11.3% recall |
| 缓存 | GPT Semantic Cache · Cache Invalidation for AI（2026，既有） | 语义缓存阈值 + 拒答即失效 |
