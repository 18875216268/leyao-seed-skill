# -*- coding: utf-8 -*-
"""方案C 护栏单元测试：默认注入时间维度 + IN 分批 + 透明合并总计 + 显式告警。

不依赖真实 BI / 元数据：mock 掉 DirectTransport 与 _build，
用构造的分组响应验证合并逻辑、调用方无感的「无维度纯汇总」形态与告警。
"""
import bi_client.query as qmod
from bi_client.query import (
    QueryService,
    QueryContext,
    _has_oversized_in,
    _oversized_in_list,
    _chunk_values,
    _resolve_default_date_dimension,
    _merge_guardrail,
    _naturalize,
    _distinct_warning,
)

_CANNED_GROUPS = [("2026-09-01", 100), ("2026-09-02", 100), ("2026-09-03", 100)]


def make_response(groups):
    row_meta = [{"name": "出库日期", "key": "m_dim", "fdId": "m_dim", "displayName": "出库日期"}]
    col_meta = [{"name": "含税金额", "key": "m_metric", "fdId": "m_metric", "displayName": "含税金额", "fmt_idx": 0}]
    row_values = [[{"title": g[0], "value": g[0], "v": g[0]}] for g in groups]
    data = [[{"v": g[1]}] for g in groups]
    return {
        "response": {
            "chartMain": {
                "row": {"meta": row_meta, "values": row_values},
                "column": {"values": [col_meta], "metricFieldFormat": {"numberFormat": [{}]}},
                "data": data,
                "count": len(groups),
                "hasMoreData": False,
            }
        }
    }


class FakeTransport:
    def __init__(self, *a, **k):
        pass

    def close(self):
        pass

    def bi_post(self, *a, **k):
        return "resp"

    def json(self, resp):
        return make_response(_CANNED_GROUPS)


_FAKE_DIM = {"name": "出库日期", "displayName": "出库日期", "key": "m_dim", "fdId": "m_dim"}
_FAKE_METRIC = {"name": "含税金额", "displayName": "含税金额", "key": "m_metric", "fdId": "m_metric"}
_FAKE_EFFECTIVE = {
    "dimensionFields": [_FAKE_DIM],
    "metricFields": [_FAKE_METRIC],
    "publicFilters": [],
    "publicSort": None,
    "page": 1,
    "pageSize": 100,
}


def _install_mocks(service):
    qmod.DirectTransport = FakeTransport
    # 固定的假 _build：返回含出库日期维度的 effective（与 make_response 行元数据一致）
    service._build = lambda *a, **k: ({"fake": True}, dict(_FAKE_EFFECTIVE), [])


def _make_context(filter_values=50000):
    metadata = {
        "dimensions": [
            {"name": "出库日期", "runtimeAvailable": True},
            {"name": "出库月份（月）", "runtimeAvailable": True},
        ],
        "metrics": [],
        "selectors": [],
        "columnFields": [],
        "metadataVersion": "test",
    }
    return QueryContext(credentials={}, metadata=metadata, default_date_range=("2026-09-01", "2026-09-30"))


def test_detection_helpers():
    plan_big = {"filters": {"spuid": [f"s{i}" for i in range(5000)]}}
    plan_small = {"filters": {"spuid": [f"s{i}" for i in range(10)]}}
    assert _has_oversized_in(plan_big) is True
    assert _has_oversized_in(plan_small) is False
    assert len(_oversized_in_list(plan_big)) == 1
    chunks = _chunk_values(list(range(5000)), 3000)
    assert len(chunks) == 2 and len(chunks[0]) == 3000 and len(chunks[1]) == 2000
    md = {"dimensions": [{"name": "出库日期", "runtimeAvailable": True}, {"name": "出库月份（月）", "runtimeAvailable": True}]}
    assert _resolve_default_date_dimension(md, ["2026-01-01", "2026-12-31"]) == "出库月份（月）"
    assert _resolve_default_date_dimension(md, ["2026-09-01", "2026-09-30"]) == "出库日期"
    print("PASS test_detection_helpers")


def test_guardrail_primary_injection():
    # filterValues 足够大 -> 主路径：注入维度 + 单次全量查询（3 组 ×100 = 300）
    profile = {
        "defaultDateFilter": {"name": "出库日期"},
        "cardId": "c", "datasetId": "d", "pageId": "p", "profileId": "pr", "cardName": "n",
        "limits": {"outputRows": 1000, "filterValues": 50000},
    }
    service = QueryService(profile, {})
    _install_mocks(service)
    context = _make_context()
    plan = {
        "id": "q1",
        "date": {"field": "出库日期", "start": "2026-09-01", "end": "2026-09-30"},
        "filters": {"spuid": [f"s{i:05d}" for i in range(5000)]},
        "metrics": ["含税金额"],
    }
    result = service.run_prepared(plan, context)
    assert result["summary"]["含税金额"]["raw"] == 300.0, result["summary"]
    assert result["rows"] == []
    assert result["effectiveQuery"]["dimensions"] == []
    assert result["totalCount"] == 1 and result["hasMoreData"] is False
    warn = result["warnings"][-1]
    assert "已自动注入「出库日期」维度" in warn, warn
    assert "单次全量查询" in warn, warn
    assert "单总计" in warn
    print("PASS test_guardrail_primary_injection")


def test_guardrail_fallback_merge_from_summary():
    # 无维度兜底路径：rows 为空、总计在 summary；_merge_guardrail 应从 summary 合并
    parsed_a = {"rows": [], "summary": {"含税金额": {"raw": 100.0}}}
    parsed_b = {"rows": [], "summary": {"含税金额": {"raw": 50.0}}}
    summary, period_groups, batches = _merge_guardrail([parsed_a, parsed_b], [_FAKE_METRIC])
    assert summary["含税金额"]["raw"] == 150.0, summary
    assert period_groups == 0 and batches == 2
    print("PASS test_guardrail_fallback_merge_from_summary")


def test_distinct_warning_helper():
    distinct = [{"name": "客户数", "aggrType": "CNT_DISTINCT"}]
    assert "跨周期" in _distinct_warning(distinct, period_groups=3, batches=1)
    assert "分批求和会重复计数" in _distinct_warning(distinct, period_groups=0, batches=2)
    assert _distinct_warning([{"name": "含税金额"}], period_groups=3, batches=1) == ""
    assert _distinct_warning(distinct, period_groups=1, batches=1) == ""
    print("PASS test_distinct_warning_helper")


def test_no_guardrail_when_dimension_present():
    plan = {
        "id": "q2",
        "date": {"field": "出库日期", "start": "2026-09-01", "end": "2026-09-30"},
        "dimensions": ["省份"],
        "filters": {"spuid": [f"s{i}" for i in range(5000)]},
        "metrics": ["含税金额"],
    }
    assert _has_oversized_in(plan) is True
    triggered = (not plan.get("dimensions")) and _has_oversized_in(plan)
    assert triggered is False, "有维度时不应触发护栏"
    print("PASS test_no_guardrail_when_dimension_present")


def test_merge_and_naturalize_units():
    from bi_client.result import parse_chart_main

    p1 = parse_chart_main(make_response(_CANNED_GROUPS), dimensions=[_FAKE_DIM], metrics=[_FAKE_METRIC], page=1, page_size=100)
    p2 = parse_chart_main(make_response(_CANNED_GROUPS), dimensions=[_FAKE_DIM], metrics=[_FAKE_METRIC], page=1, page_size=100)
    summary, period_groups, batches = _merge_guardrail([p1, p2], [_FAKE_METRIC])
    assert period_groups == 6 and batches == 2
    assert summary["含税金额"]["raw"] == 600.0
    natural = _naturalize(p1, summary, "WARN")
    assert natural["rows"] == []
    assert natural["effectiveQuery"]["dimensions"] == []
    assert natural["warnings"][-1] == "WARN"
    print("PASS test_merge_and_naturalize_units")


if __name__ == "__main__":
    test_detection_helpers()
    test_guardrail_primary_injection()
    test_guardrail_fallback_merge_from_summary()
    test_distinct_warning_helper()
    test_no_guardrail_when_dimension_present()
    test_merge_and_naturalize_units()
    print("ALL GREEN")
