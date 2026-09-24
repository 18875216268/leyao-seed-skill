#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""摇钱树 · 取数 CLI（高层 DSL）。

输入一个 UTF-8 JSON 计划（--payload-file 或 stdin 二选一）：
{
  "concurrency": 4,                 # 独立查询并发（默认 4，最大 30）
  "queries": [
    {
      "id": "q1",
      "card": "品种净利润",           // 卡片名称或 cardId（含「未命名」也按名称模糊匹配）
      "date": ["2026-09-01","2026-09-22"],  // 可选：覆盖默认日期（仅销售进度页生效，强制出库日期过滤）
      "filters": {"业务类型": ["其他","商业公司"]},  // 可选：按字段名追加/覆盖筛选（值须为合法域值）
      "limit": 50,                  // 单页大小（默认 50，最大 100）
      "all": true,                  // 是否翻页取全（默认 false：只取首页）
      "dynamic_params": [ … ],      // 可选：PARAMETER 筛选器传参（分析维度/开始日期等完整 dp 对象；
                                    //   经营分析/补货页部分卡必须带，如 gae7d 不带则维度回退「省内外」）
      "dynamic_field_filters": [ … ] // 可选：动态字段注入（dzId+key+sourceCdId）；
                                    //   配送/人工成本拆分卡必须带全 5 个，否则只回总计 1 行
    }
  ]
}

输出 JSON：{ "ok": true, "results": [ {id, ok, name, page, columns, rows, count, fetched, hasMoreData, effectiveFilters} ] }
独立查询失败不影响其它项；rows 为 [{列名: 值}] 列表。

示例：
  python scripts/query.py --payload-file plan.json
  echo '{"queries":[{"id":"t","card":"品种净利润","all":true}]}' | python scripts/query.py
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402


def _build_filters(card, sels, q, session=None):
    fl = C.recommended_filters(card, sels, q.get("date"), session=session)
    by_name = {f["name"]: f for f in fl if f.get("name")}
    for name, vals in (q.get("filters") or {}).items():
        try:
            by_name[name] = C._named_filter(card, sels, name, vals if isinstance(vals, list) else [vals])
        except KeyError as e:
            return None, str(e)
    return list(by_name.values()), None


def _run_one(q):
    qid = q.get("id", "?")
    card = C.find_card(q.get("card") or "")
    if not card:
        return {"id": qid, "ok": False, "detail": f"未找到卡片「{q.get('card')}」"}
    sels = C.load_selectors()
    fl, err = _build_filters(card, sels, q, session=C.resolve_session())
    if err:
        return {"id": qid, "ok": False, "cardId": card.get("cardId"),
                "name": card.get("name"), "detail": f"筛选解析失败：{err}"}
    res = C.query_card(card, fl, limit=min(int(q.get("limit", 50)), 100),
                       all_pages=bool(q.get("all")), session=C.resolve_session(),
                       dynamic_params=q.get("dynamic_params") or None,
                       dynamic_field_filters=q.get("dynamic_field_filters") or None)
    res["id"] = qid
    return res


def main():
    ap = argparse.ArgumentParser(description="摇钱树取数 CLI")
    ap.add_argument("--payload-file", help="JSON 计划文件路径")
    ap.add_argument("--out", help="结果落盘 JSON 路径（不指定则 stdout）")
    a = ap.parse_args()

    if a.payload_file:
        plan = json.loads(Path(a.payload_file).read_text(encoding="utf-8"))
    else:
        plan = json.loads(sys.stdin.read())
    queries = plan.get("queries", [])
    conc = min(int(plan.get("concurrency", 4)), 30)

    results = []
    if conc <= 1 or len(queries) <= 1:
        for q in queries:
            results.append(_run_one(q))
    else:
        with ThreadPoolExecutor(max_workers=conc) as ex:
            results = list(ex.map(_run_one, queries))

    out = {"ok": all(r.get("ok") for r in results), "results": results}
    text = json.dumps(out, ensure_ascii=False, indent=2)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"[query] 已写入 {a.out}（{len(results)} 项）")
    else:
        print(text)


if __name__ == "__main__":
    main()
