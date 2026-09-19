#!/usr/bin/env python3
"""查询侧增强（研究依据：LongMemEval 查询侧扩展 +11.3% recall）：

1) 规范化：全半角/标点/大小写（common.norm_text）；
2) 同义词与别名扩展：把口语词映射到库内常用词（可扩展表，非穷举）；
3) 时间感知：识别「今天/昨天/上个月/本月/今年/去年」→ 给出具体日期提示（用于建议与展示）。
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta

from common import CN, norm_text

# 别名/同义词表（**只扩不替换**：原文保留，扩展词用于召回；新词按真实未命中案例补充）
ALIASES = {
    "毛利": ["边际利润", "p4", "毛利额"],
    "口径": ["计算方式", "算法", "公式"],
    "制度": ["规定", "管理办法", "policy"],
    "术语": ["定义", "是什么意思"],
    "流程": ["步骤", "sop", "流程规范"],
    "缺货率": ["缺货品种占比"],
    "客户": ["门店", "药店"],
    "促销": ["活动", "促销活动"],
}

# 问句停用词（发检索前剥离；实测教训：整句"缺货率是什么"直发公共池会空 ✗）
QUESTION_WORDS = ("是什么", "什么意思", "是啥", "怎么算", "如何计算", "怎么计算", "怎么", "如何",
                  "有没有", "是否", "请问", "一下", "帮我查", "查一下", "给我", "找一下",
                  "呢", "吗", "啊", "的", "？", "?")

# 修饰词表（地域 / 时间）——用于**回退词**生成：组合词拆开（核心残余词 + 被剥离的修饰词）。
# 实测依据（2026-09-19）："省外单三"（＝"省外"＋"单三"）整词只召回 1 条（仅"提到该词"的条目），
# 定义条目（"术语：5万单三"）只有查"单三"才召回——拆开必须配合
# pool.search 的"补足式合并"（够数**且**有强命中才停）才真正生效（否则首词命中即停，回退词永远轮不到）。
# 扩展口径：按真实未命中案例补充（长词放前，避免残留尾缀）。
MODIFIERS = ("本月至今", "上月至今", "季度至今",
             "省外", "省内", "本地", "本市",
             "本月", "上月", "当月", "下月",
             "今日", "今天", "昨日", "昨天",
             "今年", "去年", "明年",
             "一季度", "二季度", "三季度", "四季度", "上半年", "下半年", "全年", "整月")


def core_term(text: str) -> str:
    """剥离问句后的**核心词**（不含别名扩展）——用于本地相关性门槛与排序。

    实测教训（2026-09-12）：别名扩展只该帮"服务器召回"，不能作为"本地判定相关"的依据
    （否则"毛利分析培训课程"会被"术语：边际利润"跑题命中 ✗）。
    """
    core = str(text or "").strip()
    for w in QUESTION_WORDS:
        core = core.replace(w, "")
    return core.strip()


def fallback_terms(text: str) -> list:
    """产出**回退候选词**（组合词拆开、分别尝试）：① 剥离修饰后的核心残余词 ② 被剥离的修饰词本身。

    实测依据（2026-09-19）："省外单三"是"省外"＋"单三"两个项目组合——整词只召回"提到该词"
    的条目；拆开后"单三"召回定义条目、"省外"召回地域相关条目（**组合词必须拆开多次尝试**）。
    表驱动、不硬截（避免噪声）；无修饰命中时返回空。
    """
    base = core_term(text) or str(text or "").strip()
    cur, mods = base, []
    for m in MODIFIERS:
        if m in cur and len(cur) - len(m) >= 2:
            cur = cur.replace(m, "")
            if len(m) >= 2:
                mods.append(m)
    out = []
    if cur != base and len(cur) >= 2:
        out.append(cur)          # 核心残余（如"单三"）
    out.extend(mods)             # 被剥离的修饰词（如"省外"）→ 作为独立概念再试一次
    return out


def search_terms(text: str) -> list:
    """产出**用于服务器检索**的词（按优先级）：
    ① 核心词（问句剥离后） ② 回退词（组合词拆开，如"省外单三"→"单三"＋"省外"）
    ③ 别名扩展 ④ 原文兜底（最多 3 个）。

    回退词实测依据（2026-09-19）：组合词（省外＋单三）必须**拆开分别检索**，
    否则只召回"提到整词"的条目、定义条目召回不到；
    配合 pool.search 的补足式合并（不再"首词命中即停"）才真正生效。
    """
    raw = str(text or "").strip()
    core = core_term(raw) or raw
    terms = [core]
    for t in fallback_terms(core)[:2]:   # 回退词（最多 2 个：核心残余 + 被剥离的修饰词，控预算）
        if t not in terms:
            terms.append(t)
    for t in expand(core):               # 别名扩展
        if t not in terms and t != raw:
            terms.append(t)
    if raw not in terms:
        terms.append(raw)
    return terms[:3]


_TIME_RULES = [
    (re.compile(r"今天|今日"), 0),
    (re.compile(r"昨天|昨日"), 1),
    (re.compile(r"前天"), 2),
]


def time_hint(text: str, now: datetime | None = None) -> str:
    """识别相对时间 → 返回「提示文本」（仅用于展示与建议，不改变查询语义）。"""
    now = now or datetime.now(CN)
    for rx, back in _TIME_RULES:
        if rx.search(text):
            return (now - timedelta(days=back)).strftime("%Y-%m-%d")
    m = re.search(r"上(个)?月", text)
    if m:
        first = now.replace(day=1)
        return (first - timedelta(days=1)).strftime("%Y-%m")
    if re.search(r"本月|当月", text):
        return now.strftime("%Y-%m")
    if re.search(r"去年", text):
        return str(now.year - 1)
    if re.search(r"今年", text):
        return str(now.year)
    return ""


def expand(text: str) -> list:
    """返回扩展查询词列表（原词在前，别名随后）。"""
    base = str(text or "").strip()
    n = norm_text(base)
    out = [base]
    for key, alts in ALIASES.items():
        if norm_text(key) in n:
            out.extend(a for a in alts if a not in out)
    return out


def normalize(text: str) -> dict:
    """统一入口：{raw, norm, expansions, time_hint}。"""
    return {
        "raw": str(text or "").strip(),
        "norm": norm_text(text),
        "expansions": expand(text),
        "time_hint": time_hint(text),
    }
