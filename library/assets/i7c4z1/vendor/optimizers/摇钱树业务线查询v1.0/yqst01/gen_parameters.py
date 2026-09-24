#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 references/parameters.md：摇钱树参数文档（142 卡主表 + 41 筛选器表 + 取数规则）。
数据源：data/cards.json / data/selectors.json（由 scripts/fetch_cards.py 动态刷新）。
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
cards = json.loads((DATA / "cards.json").read_text(encoding="utf-8"))["cards"]
sels = json.loads((DATA / "selectors.json").read_text(encoding="utf-8"))["selectors"]
PAGE_DATE_FDID = "j837cb1313e434000bb42295"
SALES = "摇钱树销售进度"
DATE_KW = ("日期", "时间")

# 卡片主表
rows = []
for c in cards:
    own_dt = [sf.get("name") for s in sels if c["cardId"] in (s.get("targetCdIds") or [])
              for sf in s.get("sourceFields", []) if any(k in (sf.get("name") or "") for k in DATE_KW)]
    fdesc = "、".join(f"{f['name']}({f['fdType']})" for f in c.get("filters", []) if f.get("name")) or "—"
    rows.append(
        f"| {c['pageName']} | {c['name'] or '(未命名)'} | {c['cdType']} | {c.get('chartType') or '-'} | "
        f"`{c['cardId']}` | `{c.get('dsId') or '-'}` | {len(c.get('filters', []))} | "
        f"{len(c.get('dimensions', []))} | {len(c.get('metrics', []))} | {'是' if c.get('dynamicZone') else ''} | "
        f"{'是(j837)' if c.get('pageName') == SALES else ''} | {'、'.join(own_dt) or '—'} | {fdesc} |")

# 筛选器表
sel_rows = []
for s in sels:
    srcs = "、".join(f"{x['name']}(`{x['fdId']}`)" for x in s.get("sourceFields", [])) or "-"
    trunc = "⚙超100截断" if s.get("candidatesPackTruncated") else ("⚠服务端截断" if s.get("candidatesServerTruncated") else "")
    sel_rows.append(
        f"| {s['name']} | {s.get('selectorType') or '-'} | {'是' if s.get('multiSelect') else '否'} | {srcs} | "
        f"{s.get('candidatesStored', '-')}/{s.get('candidatesCount', '-')} | {len(s.get('targetCdIds', []))} | "
        f"{trunc} | `{s['selectorId']}` |")

PROSE = f"""# 摇钱树业务线 · 参数文档（板块优化板 yqst01）

> 数据源 `data/cards.json` / `data/selectors.json`（{len(cards)} 张组件 / {len(sels)} 个筛选器）。
> 本板是「BI查询」资产 `i7c4z1` 下、针对**摇钱树业务线**的板块优化板；取数入口见 `app.md` 与 `scripts/query.py`。

---

## 一、取数参数铁律（必读，实测踩坑）

1. **查询必带、导出禁带页面级「出库日期」** `j837cb1313e434000bb42295`（dsId `ufef96cebcac14ff38494bb2`）。
   - 查询不带 → 销售进度页卡片回退到未收窄超大累计窗口，**金额炸成千亿级**（实测 1115 亿 vs 真值 2.67 亿）。
   - 导出带它 → 任务报 `1012 非法的过滤参数`、状态 FAILED。`scripts/export.py` 已自动剥离。
2. **`NOT_NULL` 类型的卡片自带筛选不可传参**（传则 `1012`）→ 跳过（见 `passable_filters`）。
3. **筛选值须为合法域值**（取候选值，避免 1012）；优先用 `scripts/candidates.py` 实时获取。
4. **`filters[]` 须为完整键组**：`name/fdId/dsId/cdId/fdType/filterType/filterValue`，缺键返回 `5001`。
5. 其它页（库存/补货/考核/利润/经营）**不**带 j837，只用卡片自身可传参筛选（其自带日期/阈值已在 `cards.json` filters[]）。

## 二、错误码速查

| 码 | 含义 | 处置 |
|---|---|---|
| `5001` | 请求体键名/方法错 | 用完整键组 |
| `1012` | 非法过滤参数（NOT_NULL/乱填值/j837 误用于导出） | 跳过 NOT_NULL、用合法域值、导出剥离 j837 |
| `1004` | 无权访问 | 换有权账号（本板默认账号 田浩然 LY110454） |
| `401`/`1017` | 凭证过期/被顶 | 重扫 `login_bi.py` |
| `40002` | 查询超时 | 收窄日期/降 limit/减维度 |
| `14001` | 数据量 >120MB | 加日期过滤 |

## 三、全量卡片主表（{len(cards)} 张）

> **受出库日期(j837)驱动**＝该卡在查询时**必须**带 j837（销售进度页取数卡）；**自身日期字段**＝页面筛选器给该卡提供的其它日期字段（导出可用）。

| 页面 | 卡片 | cdType | chartType | cardId | 数据集 | 筛选数 | 维度 | 指标 | 动态维度 | 受j837驱动 | 自身日期字段 | 卡片筛选参数 |
|---|---|---|---|---|---|---:|---:|---:|:--:|:--:|---|---|
{"\n".join(rows)}

---

## 四、页面级筛选器全表（{len(sels)} 个）

> 候选值只包内存前 100 项；`⚙超100截断`/`⚠服务端截断` 表示需 `scripts/candidates.py --filter <名> --search <关键字>` 按需现取。

| 筛选器 | 类型 | 多选 | 源字段(fdId) | 候选值(存/总) | 驱动卡片数 | 截断 | selectorId |
|---|---|:--:|---|---:|---:|:--:|---|
{"\n".join(sel_rows)}

---

## 五、字段字典

完整字段字典（fdId→名称/类型/角色/数据集）在 `data/fields.json`（程序读取）。`scripts/query.py` 取数时单元格取值用 `v`；`hasMoreData=true` 必须翻页取全。
"""

out = ROOT / "references" / "parameters.md"
out.write_text(PROSE, encoding="utf-8")
print(f"[gen] 已生成 {out}（{len(rows)} 卡 / {len(sel_rows)} 筛选器）")
