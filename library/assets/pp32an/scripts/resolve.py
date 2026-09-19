#!/usr/bin/env python3
"""优先链调度（本 skill 的核心）：精确缓存 → 语义缓存 → 本地记忆 → 公共池 → 云智库 → 拒答。

约定（设计 v2）：
- **早停（仅在结果足够时）**：达到质量门槛（非"不足"态）才跳过后续源——"公共池优先、不足才走云智库"即由此保证；不足态不早停、继续兜底；
- `--expand`：不早停，公共池与云智库都取（多可能性/交叉验证）；
- 预算：总预算来自 registry.budget_seconds，逐层超时来自各资产 timeout_s；到点即停并如实记录；
- 每次 ask 写 ask-log（query_id 锚点）→ 供 feedback/reflect 闭环；
- 命中后把结果写入缓存与本地记忆（越用越快、越用越准）；**不足态不写**（防低质答案被固化）。
"""
from __future__ import annotations

import time
from datetime import datetime

import cache
import feedback
import infer as infer_mod
import memory
import query_norm
import rank
import registry as reg
import source_loader
from common import CN, sha1

MEMORY_RELEVANCE_FLOOR = 0.25      # 本地记忆入选下限（低于视为不相关，避免"什么都像"）
ANSWER_TRUNC = 300                 # 默认返回摘要长度（--full 展开）
INSUFFICIENT_RELEVANCE = 0.8       # "不足"门槛：仅 1 条命中且本地相关低于此值 → 不得早停/缓存


def _insufficient(merged: list) -> bool:
    """"不足"判定：结果是否**可信到可以早停 + 写缓存/记忆**（否则给换词提示）。

    判据（实测校准 2026-09-19）：
    1. 无任何"像样命中"（relevance < MEMORY_RELEVANCE_FLOOR）→ 不足；
    2. 仅 1 条命中：该条必须够强（≥ INSUFFICIENT_RELEVANCE）→ 否则算"短词碰巧命中"→ 不足；
    3. ≥2 条像样命中（互相印证）→ 非不足。

    实测样本：
    - "单3" → 仅 1 条 0.65（"条目单价"：两字符在长文里碰巧出现）→ 不足 ✓ 不固化、给提示；
    - "缺货率是什么" → 1 条 1.0（标题直接命中）→ 非不足 ✓ 早停 + 缓存；
    - "省外单三" → 补足召回多条有分 → 非不足 ✓。
    注：relevance_of 对"正文命中"一律给 0.65，只看最高分会把噪声误判为强相关；
    因此"唯一命中"必须达到 0.8 才算数，多条命中则互相印证即可。
    """
    if not merged:
        return True
    rels = [float((m.get("score_parts") or {}).get("relevance_raw", 0.0)) for m in merged]
    hits = [r for r in rels if r >= MEMORY_RELEVANCE_FLOOR]
    if not hits:
        return True
    if len(hits) == 1:
        return hits[0] < INSUFFICIENT_RELEVANCE
    return False


def _query_id(norm: str) -> str:
    return "q_%s_%s" % (datetime.now(CN).strftime("%Y%m%d%H%M%S"), sha1(norm)[:4])


def _poss(m: dict) -> dict:
    """本地记忆 → 可能性结构。"""
    return {"answer": m.get("a", ""), "title": m.get("q", ""), "source": "memory",
            "trust": m.get("trust") or "local", "confidence": min(1.0, round(m.get("score", 0) / 3.0, 3)),
            "version": m.get("version"), "freshness": m.get("freshness"),
            "evidence": m.get("evidence") or ["memory#%s" % m.get("id")],
            "tags": m.get("tags") or [], "score": m.get("score", 0.0), "memory_id": m.get("id")}


def _from_cache(entry: dict, kind: str, confidence: float) -> dict:
    """缓存命中 → 恢复**完整条目**（实测教训：只存 answer 会丢 title/version/confidence ✗）。"""
    best = dict(entry.get("best") or {})
    best.setdefault("answer", entry.get("answer", ""))
    best.setdefault("source", entry.get("source", "cache"))
    best.setdefault("trust", entry.get("trust", ""))
    best.setdefault("evidence", entry.get("evidence") or [])
    best["confidence"] = confidence
    best["cache"] = kind
    best["cached_at"] = entry.get("at") or ""    # 透出缓存写入时间（陈旧度可审计）
    best["score"] = 1.0 if kind == "exact" else round(confidence, 4)
    best.setdefault("title", "")
    return best


def _finalize(out: dict, t0: float, limit: int, full: bool, query_id: str,
              path: list, early_stop: bool, suggestions: list) -> dict:
    items = out.get("items") or []
    total = len(items)
    items = items[:limit]
    for it in items:
        if not full:
            it["answer"] = str(it.get("answer") or "")[:ANSWER_TRUNC]
    elapsed = int((time.perf_counter() - t0) * 1000)
    return {
        "ok": True, "plugin": "leyao-knowledge", "protocol": "1.0",
        "problem": out.get("problem", ""), "need_type": out.get("need_type", ""),
        "answer": (items[0].get("answer") if items else ""),
        "best": items[0] if items else {},
        "possibilities": items,
        "path": path, "resolved": True, "early_stop": early_stop,
        "elapsed_ms": elapsed, "query_id": query_id,
        "has_more": total > len(items), "next_offset": len(items) if total > len(items) else None,
        "total_count": total,
        "suggestions": suggestions,
        "need_type_why": out.get("need_type_why", ""),
        "time_hint": out.get("time_hint", ""),
    }


def ask(problem: str, *, need_type: str | None = None, expand: bool = False,
        no_cache: bool = False, limit: int = 20, full: bool = False,
        tier: str | None = None, kind: str | None = None,
        only: str | None = None, deep: bool = False) -> dict:
    """only="pool"|"leyou" 限定单源查询；deep=True 启用深词（2-gram）多候选检索。"""
    t0 = time.perf_counter()
    data = reg.load()
    budget = reg.budget_seconds(data)
    norm_info = query_norm.normalize(problem)
    norm, solved_by = norm_info["norm"], None
    terms = query_norm.search_terms(problem, deep=deep)   # 检索词（核心 + 拆分回退 + 别名；deep 加 2-gram）
    gate = [query_norm.core_term(problem) or problem]   # 本地相关性门槛/排序只用**核心词**（防别名跑题命中）
    if not need_type:
        inf = infer_mod.infer(problem)
        need_type, nt_why = inf["need_type"], inf["why"]
    else:
        nt_why = "调用方显式指定"
    query_id = _query_id(norm)
    path, suggestions = [], []

    def left() -> float:
        return budget - (time.perf_counter() - t0)

    # ---------- L0 缓存 ----------
    if not no_cache:
        hit = cache.get(norm, need_type)
        path.append({"layer": "cache-exact", "ok": bool(hit), "ms": 2})
        if hit:
            return _finalize({"problem": problem, "need_type": need_type, "need_type_why": nt_why,
                              "time_hint": norm_info["time_hint"],
                              "items": [_from_cache(hit["entry"], "exact", 1.0)]},
                             t0, limit, full, query_id, path, True, suggestions)
        th = reg.semantic_threshold(data)
        sem = cache.get_semantic(norm, need_type, th)
        path.append({"layer": "cache-semantic", "ok": bool(sem), "ms": 3,
                     "threshold": th, "similarity": sem.get("similarity")})
        if sem:
            return _finalize({"problem": problem, "need_type": need_type, "need_type_why": nt_why,
                              "time_hint": norm_info["time_hint"],
                              "items": [_from_cache(sem["entry"], "semantic",
                                                    float(sem.get("similarity", 0.9)))]},
                             t0, limit, full, query_id, path, True, suggestions)

    # ---------- L1 本地记忆 ----------
    t = time.perf_counter()
    mems = [m for m in memory.all_active() if m.get("need_type") in (need_type, "search", "")]
    scored = rank.score_memories(mems, norm) if mems else []
    picked = [m for m in scored
              if m.get("score_parts", {}).get("relevance_raw", 0) >= MEMORY_RELEVANCE_FLOOR]
    path.append({"layer": "memory", "ok": bool(picked), "ms": int((time.perf_counter() - t) * 1000)})
    mem_items = [_poss(m) for m in picked]
    used_mids = [m.get("id") for m in picked[:limit]]
    for mid in used_mids:
        memory.touch(mid)

    # ---------- L2 公共池（共享池 + 注入池一次全取；口径只走注入池） ----------
    pool_items, pool_err, pool_attempts = [], "", 0
    pool_asset = next((a for a in reg.by_need(need_type, data) if a.get("kind") == "pool"), None)
    if only == "leyou":
        path.append({"layer": "pool", "ok": False, "skipped": True, "why": "--only leyou 指定单源"})
    elif pool_asset and left() > 1:
        t = time.perf_counter()
        # 口径（caliber）只查注入库（tier=inject）——对齐池侧语义：口径必须权威
        tier_eff = tier or ("inject" if need_type == "caliber" else None)
        # 池的重试窗口与总预算挂钩（2026-09-19）：默认给池 60% 预算、留 40% 给兜底；
        # --only pool 时（无兜底）用全预算。
        r = source_loader.pool_search(problem, need_type, pool_asset, min(limit * 2, 40),
                                      tier_eff, terms, kind, max_terms=(6 if deep else 3),
                                      deadline=t0 + budget * (1.0 if only == "pool" else 0.6))
        raw_items = r.get("items") or []
        # 相关性门槛：低相关命中视为"空"（否则会阻止云智库兜底）；--expand 时保留全收集。
        # 回退词命中的条目：用其命中词自证相关（实测 2026-09-19："单三"定义条目对整词
        # "省外单三"的相关仅约 0.08，会被整词门槛误拦——回退词是原词的核心残余，非跑题别名）。
        fb_terms = set(query_norm.fallback_terms(gate[0] if gate else problem))

        def _keep(it: dict) -> bool:
            rel = rank.relevance_of(gate, it)
            mt = str(it.get("matched_term") or "")
            if mt and mt in fb_terms:
                rel = max(rel, rank.relevance_of([mt], it))
            return rel >= rank.REMOTE_RELEVANCE_FLOOR

        pool_items = ([it for it in raw_items if _keep(it)] if not expand else raw_items)
        pool_err = r.get("error") or ""
        pool_attempts = int(r.get("attempts") or 0)
        path.append({"layer": "pool", "ok": bool(pool_items), "ms": r.get("ms"),
                     "raw": len(raw_items), "kept": len(pool_items),
                     "tried": r.get("tried"), "attempts": pool_attempts,
                     "error": pool_err or None})

    # ---------- 合并：早停判定（含"不足态"质量门槛） ----------
    merged = rank.fuse(gate, mem_items, pool_items)
    insufficient = _insufficient(merged)         # 仅 1 条且低相关 → 不算"已解决"，继续兜底
    early = bool(merged) and not expand and not insufficient   # 只有"因命中而跳过后续源"才算早停
    if early:
        solved_by = "memory" if mem_items and merged[0].get("source") == "memory" else "pool"
        path.append({"layer": "leyou", "ok": False, "skipped": True, "why": "early_stop 已命中"})
    else:
        # ---------- L3 云智库（兜底） ----------
        ley_asset = next((a for a in reg.by_need(need_type, data) if a.get("kind") == "cli"), None)
        if only == "pool":
            path.append({"layer": "leyou", "ok": False, "skipped": True, "why": "--only pool 指定单源"})
        elif ley_asset and left() > 1:
            t = time.perf_counter()
            r = source_loader.leyou_search(problem, ley_asset)
            raw_ley = r.get("items") or []
            # 相关性过滤（与池同思路）：云智库对任意词都会返回结果，**rel=0 的必须丢弃**——
            # 否则乱词查询永远"有结果"，挡住"如实拒答"（实测 2026-09-19：乱词 5 条垃圾全部来自
            # 云智库且 rel=0.0；而合法命中如"返利政策" rel≈0.03-0.04 → 用"大于 0"可零误杀地区分）。
            ley_items = [it for it in raw_ley if rank.relevance_of(gate, it) > 0]
            path.append({"layer": "leyou", "ok": bool(ley_items), "ms": r.get("ms"),
                         "raw": len(raw_ley), "kept": len(ley_items),
                         "reason": r.get("reason"), "error": (r.get("error") or "")[:160] or None})
            if r.get("reason") == "LOGIN_REQUIRED":
                suggestions.append(r.get("next") or "云智库未登录：请人工完成扫码登录后重试")
            merged = rank.fuse(gate, mem_items, pool_items + ley_items)
        else:
            path.append({"layer": "leyou", "ok": False, "skipped": True, "why": "need_type 无覆盖 / 预算不足"})

    if merged:
        best = merged[0]
        # 低质"不足"态不写精确缓存（实测：防不完整/误召回答案被 2ms 锚定复读，2026-09-19）
        if not _insufficient(merged):
            cache.put(norm, need_type, {"answer": best.get("answer", ""), "best": best,
                                        "source": best.get("source"), "trust": best.get("trust"),
                                        "version": best.get("version"),
                                        "evidence": best.get("evidence") or []})
        # 不足态提示：给出**具体候选词**（组合词拆开后的词 / 别名），引导继续（不轻易放弃）
        if _insufficient(merged):
            alts = [t for t in terms[1:] if t and t != problem]
            suggestions.append(
                "命中较弱（较相关的仅 1 条），可能不是你要的；建议继续换词再查："
                + ("拆开查 " + "、".join("『%s』" % a for a in alts[:2]) + "，或 " if alts else "")
                + "--deep（深词多候选）/ --expand（同时问两库）"
            )
        # 首次出现的有效答案进本地记忆（越用越准：后续可被 adopt 晋升）；
        # "不足"态不写记忆（同缓存原则：防低质/不完整答案被固化，2026-09-19）
        added_id = None
        if (not _insufficient(merged)
                and not any(m.get("q") and m.get("q")[:40] == problem[:40] for m in memory.all_active())):
            added = memory.add(problem, best.get("answer", ""), need_type,
                               source=best.get("source", ""), trust=best.get("trust", ""),
                               version=best.get("version"), freshness=best.get("freshness"),
                               evidence=best.get("evidence") or [], tags=best.get("tags") or [])
            added_id = added.get("id")
        # ask-log 锚点必须包含本次新增的记忆 id —— 否则 feedback 无处挂账（闭环断链）；
        # 若 best 来自公共池，同时记录 pool_id —— 供采纳价值信号上报（对齐池侧 record_adopt 机制）
        feedback.log_ask(query_id, norm, need_type, True,
                         sorted({i.get("source", "") for i in merged if i.get("source")}),
                         used_mids + ([added_id] if added_id else []),
                         pool_id=(best.get("pool_id") or None) if best.get("source") == "pool" else None)
        return _finalize({"problem": problem, "need_type": need_type, "need_type_why": nt_why,
                          "time_hint": norm_info["time_hint"], "items": merged},
                         t0, limit, full, query_id, path, early, suggestions)

    # ---------- L4 拒答（继续深入的路都在建议里；**最后一步 = 询问用户**） ----------
    alts = [t for t in terms[1:] if t and t != problem]
    if alts:
        suggestions.append("继续换词再查——试试拆开/更常用的词：" + "、".join("『%s』" % a for a in alts[:2]))
    suggestions += ["换词工具：--deep（深词多候选）｜--expand（同时问两库）",
                    "换 --need-type（term / caliber / policy / course / search）",
                    "以上均无命中：**向用户确认**说法/背景（或请维护者补池）"]
    if pool_err:
        suggestions.append("公共池报错（已尝试 %d 次）：%s（可稍后重试）"
                           % (pool_attempts or 1, pool_err[:80]))
    feedback.log_ask(query_id, norm, need_type, False, [], used_mids)
    return {"ok": False, "plugin": "leyao-knowledge", "protocol": "1.0",
            "problem": problem, "need_type": need_type, "need_type_why": nt_why,
            "answer": "", "best": {}, "possibilities": [],
            "path": path, "resolved": False, "early_stop": False,
            "elapsed_ms": int((time.perf_counter() - t0) * 1000), "query_id": query_id,
            "has_more": False, "next_offset": None, "total_count": 0,
            "reason": "no_match", "suggestions": suggestions,
            "time_hint": norm_info["time_hint"]}


def check(problem: str) -> dict:
    """口径校验：只认 authority（研究依据：单一权威源 / 知识冲突显式处理）。"""
    out = ask(problem, need_type="caliber", limit=10, expand=True)
    auth = [p for p in out.get("possibilities", []) if p.get("trust") == "authority"]
    out["authority_found"] = bool(auth)
    if not auth:
        out["ok"] = False
        out["reason"] = out.get("reason") or "no_authority"
        out["suggestions"] = (out.get("suggestions") or []) + ["未找到权威口径：请向维护者确认后补入公共池（authority）"]
    return out
