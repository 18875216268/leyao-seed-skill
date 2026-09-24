#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""摇钱树业务线 · BI 卡片与参数动态拉取器

产出（全部写入脚本所在目录）
    cards.json      卡片索引：卡片类型 / 筛选参数 / 维度 / 指标 / 数据集
    selectors.json  筛选器索引：筛选器类型 / 源字段键组 / 驱动哪些卡 / 候选值
    fields.json     字段字典：fdId → 名称 / 类型 / 角色
    cards.md        人读版卡片清单（含每卡筛选参数表）
    selectors.md    人读版筛选器清单（含候选值）
    parameters.md   人读版参数文档（数据集 / 筛选字段 / 维度指标字典 / 公式）
    _meta.json      本次拉取元信息

凭证来源（任选其一，按序尝试）
    1) 环境变量   BI_UID_TOKEN + BI_UID_TOKEN_SIG
    2) 采集文件   --capture <观远数据_采集结果*.json> 或 BI_CAPTURE_FILE
    3) 命令行     --token <uIdToken> --sig <uIdToken.sig>

用法
    python fetch_cards.py                      # 自动找凭证 + 自动定位「摇钱树业务线」
    python fetch_cards.py --with-candidates    # 同时拉取各筛选器的实时候选值
    python fetch_cards.py --folder <文件夹id>  # 指定其它目录

依赖：requests
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:  # pragma: no cover
    print("[fetch] 需要 requests：pip install requests", file=sys.stderr)
    sys.exit(2)

BASE = "https://bi.leyopharm.com"
HERE = Path(__file__).resolve().parent
FOLDER_NAME = "摇钱树业务线"
FOLDER_ID_DEFAULT = "q4e929703ce5247db98af47a"
CANDIDATES_MAX = 100        # 候选值入包上限：超过即截断，需要时按需动态获取
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": BASE + "/",
    "Accept": "application/json",
}


# ------------------------------------------------------------------ 凭证
def cookies_from_capture(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for c in (data.get("cookies") or []):
        if "leyopharm" in str(c.get("domain") or "") and c.get("name") in ("uIdToken", "uIdToken.sig"):
            out[c["name"]] = c["value"]
    if not out:
        for t in (data.get("auth_tokens") or []):
            if t.get("name") in ("uIdToken", "uIdToken.sig") and t.get("value"):
                out[t["name"]] = t["value"]
    return out


def resolve_cookies(a) -> dict:
    if a.token and a.sig:
        return {"uIdToken": a.token, "uIdToken.sig": a.sig}
    env_tok, env_sig = os.environ.get("BI_UID_TOKEN"), os.environ.get("BI_UID_TOKEN_SIG")
    if env_tok and env_sig:
        return {"uIdToken": env_tok, "uIdToken.sig": env_sig}
    # 框架凭证文件（login_bi.py 扫码落库；与 common.resolve_session 同源，agent 零配置刷新）
    cred = Path(os.environ.get("LOCALAPPDATA", "")) / "bi-operations-query" / "credential.json"
    if cred.is_file():
        try:
            cj = json.loads(cred.read_text(encoding="utf-8"))
            tok, sig = cj.get("token"), cj.get("tokenSig")
            if tok and sig:
                print(f"[fetch] 凭证来源：框架凭证文件 {cred}")
                return {"uIdToken": tok, "uIdToken.sig": sig}
        except Exception as exc:
            print(f"[fetch] 凭证文件解析失败（忽略，继续其它来源）：{exc}", file=sys.stderr)
    cand = []
    if a.capture:
        cand.append(Path(a.capture))
    if os.environ.get("BI_CAPTURE_FILE"):
        cand.append(Path(os.environ["BI_CAPTURE_FILE"]))
    cand += sorted(HERE.parent.glob("参考/观远数据_采集结果*.json"))
    cand += sorted(HERE.glob("*采集结果*.json"))
    for p in cand:
        if p and p.is_file():
            ck = cookies_from_capture(p)
            if ck:
                print(f"[fetch] 凭证来源：采集文件 {p}")
                return ck
    print("[fetch] 未找到凭证。请用 --token/--sig、--capture，或设置 BI_UID_TOKEN + BI_UID_TOKEN_SIG。",
          file=sys.stderr)
    sys.exit(3)


# ------------------------------------------------------------------ HTTP
class BI:
    def __init__(self, cookies: dict):
        self.s = requests.Session()
        self.s.trust_env = False
        self.s.cookies.update(cookies)
        self.n = 0

    def get(self, path: str, timeout: int = 60):
        self.n += 1
        r = self.s.get(BASE + path, headers=HEADERS, timeout=timeout, allow_redirects=False)
        if r.status_code != 200:
            raise RuntimeError(f"GET {path} → HTTP {r.status_code}: {r.text[:160]}")
        return r.json()

    def post(self, path: str, payload=None, timeout: int = 90):
        self.n += 1
        r = self.s.post(BASE + path, headers={**HEADERS, "Content-Type": "application/json"},
                        json=payload if payload is not None else {}, timeout=timeout)
        if r.status_code != 200:
            raise RuntimeError(f"POST {path} → HTTP {r.status_code}: {r.text[:160]}")
        return r.json()


def inner_of(j):
    return j.get("response", j) if isinstance(j, dict) else j


# ------------------------------------------------------------------ 解析
def field_dict(f: dict) -> dict:
    return {
        "name": f.get("name") or f.get("alias"),
        "fdId": f.get("fdId"),
        "fdType": f.get("fdType"),
        "metaType": f.get("metaType"),
        "aggrType": f.get("aggrType"),
        "isAggregated": f.get("isAggregated"),
        "calculationType": f.get("calculationType"),
        "formula": f.get("formula"),
        "dsId": f.get("dsId"),
        "key": f.get("key"),
    }


def collect_card(card: dict, page: dict, fields: dict) -> dict:
    content = card.get("content") or {}
    meta = (content.get("meta") or {}).get("chartMain") or {}
    zd = meta.get("zoneData") or {}
    cd_id = card.get("cdId")
    ds_id = content.get("dsId")
    dz = (content.get("dynamicZoneInfo") or {}).get("dzMappings") or []

    filters = []
    for f in (zd.get("filters") or []):
        if not isinstance(f, dict):
            continue
        filters.append({
            "name": f.get("name"),
            "fdId": f.get("fdId"),
            "dsId": f.get("dsId") or ds_id,          # 回退：声明未带 dsId 时用卡片数据集
            "cdId": f.get("cdId") or cd_id,
            "fdType": f.get("fdType"),
            "filterType": f.get("filterType") or f.get("originFilterType"),
            "filterLevel": f.get("filterLevel"),
            "filterValue": f.get("filterValue"),
            "macroName": f.get("macroName"),
        })

    entry = {
        "cardId": cd_id,
        "name": card.get("name"),
        "cdType": card.get("cdType"),
        "chartType": content.get("chartType") or card.get("chartType"),
        "pgId": card.get("pgId") or page.get("pgId"),
        "pageName": page.get("name"),
        "dsId": ds_id,
        "hasDrill": content.get("hasDrill"),
        "dynamicZone": bool(dz),
        "filters": filters,
        "dimensions": [field_dict(f) for f in (zd.get("row") or []) if isinstance(f, dict)],
        "metrics": [field_dict(f) for f in (zd.get("metric") or []) if isinstance(f, dict)],
        "columns": [field_dict(f) for f in (zd.get("column") or []) if isinstance(f, dict)],
        "updatedAt": int(time.time()),
    }
    for grp in ("filters", "dimensions", "metrics", "columns"):
        for f in entry[grp]:
            if f.get("fdId"):
                fields[f["fdId"]] = {
                    "fdId": f["fdId"], "name": f.get("name"), "fdType": f.get("fdType"),
                    "metaType": f.get("metaType"), "dsId": f.get("dsId"),
                }
    return entry


def collect_selector(card: dict, page: dict, bi: BI, with_candidates: bool) -> dict:
    content = card.get("content") or {}
    settings = card.get("settings") or {}
    af = settings.get("asFilter") or {}
    src, tgt = [], []
    for m in (af.get("columnMappings") or []):
        s = m.get("sourceField") or {}
        if s.get("fdId"):
            src.append({"name": s.get("name"), "fdId": s.get("fdId"), "dsId": s.get("dsId")})
        for t in (m.get("targetFields") or []):
            tgt.append({"cdId": t.get("cdId"), "name": t.get("name"),
                        "fdId": t.get("fdId"), "dsId": t.get("dsId")})
    cd_id = card.get("cdId")
    entry = {
        "selectorId": cd_id,
        "name": card.get("name"),
        "cdType": card.get("cdType"),
        "pgId": card.get("pgId") or page.get("pgId"),
        "pageName": page.get("name"),
        "selectorType": content.get("selectorType"),
        "filterType": content.get("filterType"),
        "multiSelect": content.get("multiSelect"),
        "defaultValue": content.get("defaultValue"),
        "source": content.get("source"),
        "sourceFields": src,
        "targetCdIds": af.get("targetCdIds") or [],
        "targetFields": tgt,
        "candidatesEndpoint": f"POST /api/selector/{cd_id}/data",
    }
    if with_candidates and cd_id:
        try:
            r = inner_of(bi.post(f"/api/selector/{cd_id}/data", {}))
            vals = [x.get("value") for x in (r.get("result") or []) if isinstance(x, dict)]
            entry["candidatesCount"] = r.get("count")
            entry["candidatesServerTruncated"] = bool(r.get("exceedLimit"))
            entry["candidates"] = vals[:CANDIDATES_MAX]
            entry["candidatesStored"] = min(len(vals), CANDIDATES_MAX)
            if len(vals) > CANDIDATES_MAX:
                entry["candidatesPackTruncated"] = True
                entry["candidatesNote"] = (
                    f"包内仅存前 {CANDIDATES_MAX} 项（服务端本次返回 {len(vals)}，总数 {r.get('count')}）；"
                    f"需要完整候选值时动态获取：{entry['candidatesEndpoint']}")
        except Exception as exc:
            entry["candidatesError"] = str(exc)[:120]
    return entry


# ------------------------------------------------------------------ 渲染
def render_cards_md(cards, pages, meta) -> str:
    L = ["# 摇钱树业务线 · 卡片清单", "",
         f"> 动态拉取于 {meta['generatedAt']} ｜ 看板 {meta['pageCount']} 个 ｜ 组件 {meta['cardCount']} 个"
         f"（CHART {meta['chartCount']}）｜ 筛选器 {meta['selectorCount']} 个"
         f" ｜ 目录：{meta['folderName']} (`{meta['folderId']}`)", ""]
    for pg in pages:
        cs = [c for c in cards if c["pgId"] == pg["id"]]
        L += [f"## {pg['name']}  (`{pg['id']}`) — {len(cs)} 个组件", "",
              "| 名称 | cdType | chartType | cdId | 数据集 | 筛选参数 | 维度 | 指标 | 动态维度 |",
              "|---|---|---|---|---|---:|---:|---:|:--:|"]
        for c in cs:
            L.append(f"| {c['name'] or '(未命名)'} | {c['cdType']} | {c['chartType'] or '-'} | "
                     f"`{c['cardId']}` | `{c['dsId'] or '-'}` | {len(c['filters'])} | "
                     f"{len(c['dimensions'])} | {len(c['metrics'])} | {'是' if c['dynamicZone'] else ''} |")
        L.append("")
        for c in cs:
            if c["filters"]:
                L += [f"**{c['name']}**（`{c['cardId']}`）筛选参数：", "",
                      "| 筛选字段 | fdId | dsId | fdType | filterType | filterLevel | 默认值 | 时间宏 |",
                      "|---|---|---|---|---|---|---|---|"]
                for f in c["filters"]:
                    dv = json.dumps(f.get("filterValue"), ensure_ascii=False) if f.get("filterValue") else "-"
                    L.append(f"| {f['name']} | `{f['fdId']}` | `{f['dsId']}` | {f['fdType']} | "
                             f"{f['filterType']} | {f['filterLevel'] or '-'} | {dv} | {f['macroName'] or '-'} |")
                L.append("")
    return "\n".join(L)


def render_selectors_md(sels, meta) -> str:
    L = ["# 摇钱树业务线 · 筛选器清单", "",
         f"> 动态拉取于 {meta['generatedAt']} ｜ 筛选器 {len(sels)} 个", "",
         "| 名称 | selectorType | filterType | 多选 | 源字段 | 候选值(包内/总数) | 驱动卡片数 | selectorId |",
         "|---|---|---|:--:|---|---:|---:|---|"]
    for s in sels:
        srcs = ", ".join(f"{x['name']}" for x in s["sourceFields"]) or "-"
        L.append(f"| {s['name']} | {s['selectorType'] or '-'} | {s['filterType'] or '-'} | "
                 f"{'是' if s['multiSelect'] else '否'} | {srcs} | "
                 f"{s.get('candidatesStored', '-')}/{s.get('candidatesCount', '-')} | "
                 f"{len(s['targetCdIds'])} | `{s['selectorId']}` |")
    L.append("")
    for s in sels:
        L += [f"## {s['name']}  (`{s['selectorId']}`)", "",
              f"- 所属看板：{s['pageName']}（`{s['pgId']}`）",
              f"- selectorType：`{s['selectorType']}` ｜ filterType：`{s['filterType']}` ｜ "
              f"多选：{'是' if s['multiSelect'] else '否'}",
              f"- 候选值接口：`{s['candidatesEndpoint']}`", ""]
        if s.get("sourceFields"):
            L += ["| 源字段 | fdId | dsId |", "|---|---|---|"]
            for x in s["sourceFields"]:
                L.append(f"| {x['name']} | `{x['fdId']}` | `{x['dsId']}` |")
            L.append("")
        if s.get("candidates"):
            notes = []
            if s.get("candidatesPackTruncated"):
                notes.append(f"包内仅存前 {len(s['candidates'])} 项")
            if s.get("candidatesServerTruncated"):
                notes.append("服务端返回已达上限")
            suffix = ("（" + "；".join(notes) + "）") if notes else ""
            L.append(f"- 候选值（总数 {s.get('candidatesCount')}）{suffix}："
                     f"{' / '.join(map(str, s['candidates']))}")
            L.append(f"- ⚙ 完整候选请**动态获取**：`{s['candidatesEndpoint']}`")
            L.append("")
        if s.get("targetFields"):
            L += ["驱动卡片（筛选器 → 目标字段）：", "", "| 目标卡 cdId | 目标字段 | fdId | dsId |",
                  "|---|---|---|---|"]
            for t in s["targetFields"]:
                L.append(f"| `{t['cdId']}` | {t['name']} | `{t['fdId']}` | `{t['dsId']}` |")
            L.append("")
    return "\n".join(L)


RULES = """## 零、使用铁律（全量巡检实测，务必先读）

1. **卡片自身筛选声明 ≠ 全部参数来源**。页面级**筛选器**（`selectors.json`）才是主要参数入口；
   补货/库存类看板的卡**必须带页面筛选器的日期**（如「补货时间」→ 字段 `导入时间`），否则命中 `40002 TASK.cancelTimeout`。
2. **`filterType == NOT_NULL` 的声明不可传参**：它是卡片**内部行级过滤**，传入会命中
   `1012 非法的过滤参数`。→ 正确做法：**跳过它**（用空体或只传其余可传项）。
3. **筛选值必须是合法域值**：乱填（如把「其他」传给 `业务类型`）同样命中 `1012`。
   → 值优先取**该字段的筛选器候选值**（`selectors.json[].candidates`，超 100 项按需动态取）。
4. **超重卡可减载**：命中 `40002` 时按序尝试「日期收窄到单日」→「剔除数值阈值型筛选」
   （如「近30天销售数量」「建议补货量」这类 `GT/LE` 阈值项）。
5. **并发下偶发 `500/5001` 属瞬时**：同一张卡串行复测即通（实测 1 例），
   **不要据此判定卡片不可用**；批处理请串行或失败后复测一次。
6. **分页**用 `offset` 递进（固定 filters，只递增 offset，直到 `hasMoreData=false`）；
   **排序**服务端不保证，务必**由调用方侧排序**；**导出**受服务端**导出审批**闸（见 README §4.5）。
"""


def render_parameters_md(cards, selectors, fields, meta) -> str:
    L = ["# 摇钱树业务线 · 参数文档", "", f"> 动态拉取于 {meta['generatedAt']}", "",
         RULES, "## 一、数据集", ""]
    ds = {}
    for f in fields.values():
        if f.get("dsId"):
            ds[f["dsId"]] = ds.get(f["dsId"], 0) + 1
    for c in cards:
        if c.get("dsId"):
            ds[c["dsId"]] = ds.get(c["dsId"], 0) + 1
    for k, v in sorted(ds.items(), key=lambda x: -x[1]):
        L.append(f"- `{k}`（引用 {v} 次）")
    L += ["", "## 二、卡片筛选字段（去重）", "",
          "| 筛选字段 | fdId | dsId | fdType | filterType | 出现卡片数 |", "|---|---|---|---|---|---:|"]
    agg = {}
    for c in cards:
        for f in c["filters"]:
            if not f["fdId"]:
                continue
            e = agg.setdefault(f["fdId"], {"name": f["name"], "fdId": f["fdId"], "dsId": f["dsId"],
                                           "fdType": f["fdType"], "filterType": f["filterType"], "n": 0})
            e["n"] += 1
    for e in sorted(agg.values(), key=lambda x: -x["n"]):
        L.append(f"| {e['name']} | `{e['fdId']}` | `{e['dsId']}` | {e['fdType']} | {e['filterType']} | {e['n']} |")
    L += ["", "## 三、筛选器（页面级）", "",
          "| 筛选器 | selectorId | 源字段 | fdId | dsId | 候选值数 |", "|---|---|---|---|---|---:|"]
    for s in selectors:
        for x in (s.get("sourceFields") or [{"name": "-", "fdId": "-", "dsId": "-"}]):
            L.append(f"| {s['name']} | `{s['selectorId']}` | {x['name']} | `{x['fdId']}` | "
                     f"`{x['dsId']}` | {s.get('candidatesCount', '-')} |")
    L += ["", "## 四、维度 / 指标 / 列（全量字段字典）", "",
          "| 名称 | 角色 | metaType | fdType | 聚合 | fdId | 数据集 |", "|---|---|---|---|---|---|---|"]
    seen = set()
    for c in cards:
        for role, key in (("维度", "dimensions"), ("指标", "metrics"), ("列", "columns")):
            for f in c[key]:
                sig = (f["fdId"], role)
                if not f["fdId"] or sig in seen:
                    continue
                seen.add(sig)
                L.append(f"| {f['name']} | {role} | {f['metaType']} | {f['fdType']} | "
                         f"{f['aggrType'] or ('聚合' if f['isAggregated'] else '-')} | `{f['fdId']}` | "
                         f"`{f['dsId'] or '-'}` |")
    L += ["", "## 五、指标公式", ""]
    hit = False
    for c in cards:
        for f in c["metrics"]:
            if f.get("formula"):
                hit = True
                L.append(f"- **{f['name']}**（`{f['fdId']}`）：`{f['formula']}` ← {c['name']}")
    if not hit:
        L.append("（本次拉取未含公式声明）")
    return "\n".join(L)


# ------------------------------------------------------------------ 主流程
def main() -> int:
    ap = argparse.ArgumentParser(description="摇钱树业务线 BI 卡片/参数动态拉取")
    ap.add_argument("--folder", default=FOLDER_ID_DEFAULT, help="目标文件夹 id")
    ap.add_argument("--folder-name", default=FOLDER_NAME, help="目标文件夹名称（用于目录树定位）")
    ap.add_argument("--capture", help="采集文件路径（作为凭证来源）")
    ap.add_argument("--token", help="uIdToken")
    ap.add_argument("--sig", help="uIdToken.sig")
    ap.add_argument("--with-candidates", action="store_true", help="同时拉取筛选器实时候选值")
    ap.add_argument("--out", default=str(HERE.parent / "data"), help="输出目录（默认优化板 data/）")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    log = (lambda *x: None) if a.quiet else (lambda *x: print(*x, flush=True))

    bi = BI(resolve_cookies(a))

    log("[fetch] 1/5 读取目录树 …")
    tree = bi.get("/api/page-v3", timeout=60)
    folder_id, pages = a.folder, None
    for k in (tree.get("contents") or []):
        if k.get("name") == a.folder_name or k.get("id") == a.folder:
            folder_id, pages = k.get("id"), (k.get("contents") or [])
    if not pages:
        log("[fetch] ✗ 目录树未命中目标文件夹（检查权限或 --folder）")
        return 4

    log(f"[fetch] 2/5 抓取 {len(pages)} 个看板的组件声明 …")
    cards, sels, fields = [], [], {}
    for pg in pages:
        detail = inner_of(bi.get(f"/api/page/{pg['id']}"))
        for c in (detail.get("cards") or []):
            if not c.get("cdId"):
                continue
            if c.get("cdType") == "SELECTOR":
                sels.append(collect_selector(c, detail, bi, a.with_candidates))
            else:
                cards.append(collect_card(c, detail, fields))

    need = [c for c in cards if not c["chartType"]]
    if need:
        log(f"[fetch] 3/5 补取 {len(need)} 张卡的 chartType …")
        for c in need:
            try:
                d = inner_of(bi.get(f"/api/card/{c['cardId']}"))
                c["chartType"] = d.get("chartType") or c["chartType"]
            except Exception:
                pass
    else:
        log("[fetch] 3/5 chartType 齐备，跳补取")

    meta = {
        "generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source": BASE, "folderName": a.folder_name, "folderId": folder_id,
        "pageCount": len(pages), "cardCount": len(cards) + len(sels),
        "chartCount": sum(1 for c in cards if c["cdType"] == "CHART"),
        "selectorCount": len(sels), "fieldCount": len(fields),
        "withCandidates": a.with_candidates, "requests": bi.n,
    }
    log("[fetch] 4/5 写入产物 …")
    (out / "cards.json").write_text(json.dumps({"meta": meta, "pages": pages, "cards": cards},
                                               ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "selectors.json").write_text(json.dumps({"meta": meta, "selectors": sels},
                                                   ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "fields.json").write_text(json.dumps({"meta": meta, "fields": fields},
                                                ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "cards.md").write_text(render_cards_md(cards, pages, meta), encoding="utf-8")
    (out / "selectors.md").write_text(render_selectors_md(sels, meta), encoding="utf-8")
    (out / "parameters.md").write_text(render_parameters_md(cards, sels, fields, meta), encoding="utf-8")

    log(f"[fetch] 5/5 完成：看板 {meta['pageCount']} · 组件 {meta['cardCount']}"
        f"（CHART {meta['chartCount']} · 筛选器 {meta['selectorCount']}）· 字段 {meta['fieldCount']}"
        f" · 请求 {meta['requests']} 次")
    return 0


if __name__ == "__main__":
    sys.exit(main())
