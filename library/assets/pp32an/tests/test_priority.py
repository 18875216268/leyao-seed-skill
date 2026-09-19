#!/usr/bin/env python3
"""优先链与早停（核心语义）：池结果**足够** → 云智库 skipped；池不足 / 空 → 云智库被调用；--expand 两库都取。"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["LEYAO_KB_HOME"] = tempfile.mkdtemp(prefix="kb_test_priority_")
SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))

import resolve  # noqa: E402
import source_loader  # noqa: E402

POOL_ITEM = {"answer": "缺货率：缺货品种数/考核品种数", "title": "术语：缺货率", "source": "pool",
             "trust": "authority", "confidence": 0.9, "version": 1, "freshness": 1,
             "evidence": ["pool#1"], "tags": ["term"], "score": 0.9}
LEYOU_ITEM = {"answer": "缺货率：云智库版口径说明（同一主题的另一个来源）……", "title": "缺货率（云智库）",
              "source": "leyou", "trust": "reference", "confidence": 0.6,
              "evidence": ["leyou#x"], "tags": [], "score": 0.0}
JUNK_ITEM = {"answer": "盘点流程：定期盘点门店库存……", "title": "盘点流程", "source": "leyou",
             "trust": "reference", "confidence": 0.6, "evidence": ["leyou#junk"], "tags": [], "score": 0.0}
CALLS = {"pool": 0, "leyou": 0}


class TestPriority(unittest.TestCase):
    def setUp(self):
        CALLS["pool"] = CALLS["leyou"] = 0
        source_loader.pool_search = self._pool
        source_loader.leyou_search = self._leyou
        self.pool_result = {"ok": True, "items": [dict(POOL_ITEM)], "ms": 12}
        self.leyou_result = {"ok": True, "items": [dict(LEYOU_ITEM)], "ms": 30}

    def _pool(self, *a, **k):
        CALLS["pool"] += 1
        return dict(self.pool_result)

    def _leyou(self, *a, **k):
        CALLS["leyou"] += 1
        return dict(self.leyou_result)

    def test_pool_hit_skips_leyou(self):
        r = resolve.ask("缺货率是什么", need_type="term", no_cache=True)
        self.assertTrue(r["ok"])
        self.assertEqual(CALLS["leyou"], 0, "池结果足够时不得调用云智库（早停语义）")
        self.assertTrue(r["early_stop"])
        ley = [l for l in r["path"] if l["layer"] == "leyou"][0]
        self.assertTrue(ley.get("skipped"))

    def test_pool_empty_then_leyou(self):
        self.pool_result = {"ok": True, "items": [], "ms": 8}
        # 本用例需避开用户区记忆里的"缺货率"：换冷门主题 + 配套的云智库条目
        self.leyou_result = {"ok": True, "ms": 30, "items": [
            {"answer": "毛利分析课程要点（云智库版）……", "title": "毛利分析课程",
             "source": "leyou", "trust": "reference", "confidence": 0.6,
             "evidence": ["leyou#c"], "tags": [], "score": 0.0}]}
        r = resolve.ask("毛利分析课程", need_type="course", no_cache=True)
        self.assertTrue(r["ok"])
        self.assertEqual(CALLS["leyou"], 1, "公共池空时必须走云智库兜底")
        self.assertEqual((r["best"] or {}).get("source"), "leyou")
        self.assertFalse(r["early_stop"])

    def test_expand_calls_both(self):
        r = resolve.ask("缺货率是什么", need_type="term", expand=True, no_cache=True)
        self.assertEqual(CALLS["leyou"], 1, "--expand 时不早停，两库都取")
        srcs = {p["source"] for p in r["possibilities"]}
        self.assertTrue({"pool", "leyou"} <= srcs, "两库结果都应出现（可另有本地记忆）")
        self.assertFalse(r["early_stop"])

    def test_exact_cache_hit_skips_sources(self):
        resolve.ask("缺货率是什么", need_type="term", no_cache=True)   # 先写缓存
        baseline = CALLS["pool"]
        r = resolve.ask("缺货率是什么！！", need_type="term")            # 规范化后同键
        self.assertTrue(r["ok"])
        self.assertEqual(CALLS["pool"], baseline, "精确缓存命中不得再打源")
        self.assertEqual(r["possibilities"][0].get("cache"), "exact")

    def test_leyou_junk_filtered_to_abstain(self):
        """云智库返回**全无关**条目（rel=0，实测乱词场景）→ 必须被过滤 → 如实拒答。

        背景：云智库对任意词都会返回若干结果（rel=0 的垃圾）；若不滤会挡住"如实拒答"。
        """
        self.pool_result = {"ok": True, "items": [], "ms": 5}
        self.leyou_result = {"ok": True, "items": [dict(JUNK_ITEM)], "ms": 5}
        r = resolve.ask("完全无关的查询ZZZ", need_type="term", no_cache=True)
        self.assertFalse(r["ok"], "全无关结果必须拒答（不得假命中）")
        self.assertEqual(r["reason"], "no_match")

    def test_no_cache_skips_cache_layer(self):
        resolve.ask("缺货率是什么", need_type="term", no_cache=True)
        r = resolve.ask("缺货率是什么", need_type="term", no_cache=True)
        self.assertFalse([l for l in r["path"] if l["layer"].startswith("cache")], "no-cache 时不应出现缓存层")

    def test_weak_hit_not_early_stop(self):
        """弱命中（单条正文命中 < 0.8）不算"足够"：不早停、继续兜底云智库（2026-09-19 质量门槛）。"""
        self.pool_result = {"ok": True, "ms": 9, "items": [
            {"answer": "结算说明：供应商账期按合同约定执行，含账期与对账周期……", "title": "结算流程",
             "source": "pool", "trust": "reference", "confidence": 0.5,
             "evidence": ["pool#weak"], "tags": [], "score": 0.5}]}
        self.leyou_result = {"ok": True, "ms": 20, "items": []}
        r = resolve.ask("供应商账期是什么", need_type="term", no_cache=True)
        self.assertEqual(CALLS["leyou"], 1, "弱命中不得早停：必须继续兜底云智库")
        self.assertFalse(r["early_stop"])
        self.assertTrue(any("较弱" in s or "换词" in s for s in r["suggestions"]),
                        "不足态必须给继续换词提示")


if __name__ == "__main__":
    unittest.main(verbosity=2)
