#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""摇钱树业务线查询 · 公共底座（自包含引擎）。

提供：凭证解析 / 会话 / 卡片·筛选器加载 / 筛选键组构造（含 j837 出库日期强制规则）
/ 取数（分页翻页）/ 候选值（实时+缓存）/ 导出（三步链，禁用 j837）。

凭证解析（本板不实现登录，只消费凭证；框架登录流程与原有/Ultra 完全一致：
  登录统一由父资产 i7c4z1/scripts/login_bi.py 负责，落盘到共享 credential.json，
  本板与其读同一文件、挂同一组 uIdToken+uIdToken.sig Cookie）：
  1) 环境变量 BI_UID_TOKEN + BI_UID_TOKEN_SIG      —— 可移植覆盖（最高优先）
  2) 框架凭证文件 %LOCALAPPDATA%\\bi-operations-query\\credential.json（框架主路径，直连）
  3) 本板 resources/credential.local.json          —— 独立部署手动覆盖（standalone）
  4) 父资产 i7c4z1 登录器 scripts/login_bi.py      —— verify_credential 兜底（绝不弹窗）
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import date as _date, timedelta as _timedelta
from pathlib import Path

import requests  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                      # 优化板根（yqst01/）
DATA = ROOT / "data"                    # cards.json / selectors.json / fields.json 快照
RES = ROOT / "resources"

BASE = "https://bi.leyopharm.com"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
      "Referer": BASE + "/", "Accept": "application/json"}
J = {**UA, "Content-Type": "application/json"}

PAGE_DATE_FDID = "j837cb1313e434000bb42295"
PAGE_DATE_DSID = "ufef96cebcac14ff38494bb2"
SALES_PAGE = "摇钱树销售进度"
# 负利润+滞销费卡（数据集 r6cd9b22f）日期字段是 sc5733bd，页面给它的也是该字段；
# 对它强制 j837 会 1012（实测），必须按数据集区分。
NEG_PROFIT_DS = "r6cd9b22f9c544148adc0d6a"
NEG_PROFIT_DATE_FDID = "sc5733bd07fa24ac1b39459d"


def default_date_range() -> list:
    """默认日期 = 页面筛选器宏 {{{yesterday}}}（昨日单日，动态计算，勿写死）。

    返回 1 元素列表 → 构造 EQ；调用方传 2 元素日期则 BT。
    页面真实默认（抓包 2026-09-23）就是 EQ 昨日，不是「本月→昨天」。"""
    return [(_date.today() - _timedelta(days=1)).isoformat()]


PROFILE = json.loads((RES / "profile.json").read_text(encoding="utf-8")) if (RES / "profile.json").is_file() else {}


# ----------------------------------------------------------------- 凭证 / 会话
def _cookie_pairs() -> dict:
    """统一凭证解析（框架内直连 + 独立部署覆盖，所有 tier 在各自场景下均有意义）：

    1) 环境变量 BI_UID_TOKEN / BI_UID_TOKEN_SIG        —— 可移植覆盖（最高优先）
    2) 共享凭证文件 %LOCALAPPDATA%\\bi-operations-query\\credential.json
       —— login_bi 真写它，框架模式主路径（直连，无需 import 父模块）
    3) 本板 resources/credential.local.json            —— 独立部署时手动放入（standalone 覆盖）
    4) 父资产 i7c4z1 login_bi.verify_credential        —— 兜底/未来兼容，绝不弹窗、绝不重登

    相对出库统计Ultra 的优化：框架主路径改为直读共享文件（tier-2），不再依赖
    tier-3 的 Python import 回退；tier-3 仅作冗余兜底，tier-3 同 Ultra 的 verify_credential 策略。
    """
    # 1) 环境变量
    tok = os.environ.get("BI_UID_TOKEN", "").strip()
    sig = os.environ.get("BI_UID_TOKEN_SIG", "").strip()
    if tok:
        return {"uIdToken": tok, "uIdToken.sig": sig}
    # 2) 共享凭证文件（框架主路径，login_bi 实际落盘处）
    cf = Path(os.environ.get("LOCALAPPDATA", "")) / "bi-operations-query" / "credential.json"
    if cf.is_file():
        try:
            d = json.loads(cf.read_text(encoding="utf-8-sig"))  # utf-8-sig 兼容 BOM
            if d.get("token"):
                return {"uIdToken": d["token"], "uIdToken.sig": d.get("tokenSig", "")}
        except Exception:
            pass
    # 3) 本板独立部署覆盖（脱离父资产时手动放入）
    local = RES / "credential.local.json"
    if local.is_file():
        try:
            d = json.loads(local.read_text(encoding="utf-8-sig"))
            t = d.get("token") or d.get("uIdToken")
            if t:
                return {"uIdToken": t, "uIdToken.sig": d.get("tokenSig") or d.get("uIdToken.sig", "")}
        except Exception:
            pass
    # 4) 父资产登录器兜底（与出库统计Ultra 同策略：仅验证复用）
    for lvl in range(6):
        cand = HERE.parents[lvl] / "scripts" / "login_bi.py"
        if cand.is_file():
            sys.path.insert(0, str(cand.parent))
            try:
                import login_bi  # type: ignore
                res = login_bi.verify_credential(validate_remote=False)
                if res.get("authenticated"):
                    return {"uIdToken": res.get("token") or "",
                            "uIdToken.sig": res.get("tokenSig") or ""}
            except Exception:
                pass
            break
    return {}


def resolve_session() -> requests.Session:
    s = requests.Session()
    s.trust_env = False
    for k, v in _cookie_pairs().items():
        if v:
            s.cookies.set(k, v, domain="bi.leyopharm.com", path="/")
    if not s.cookies.get("uIdToken"):
        raise RuntimeError(
            "AUTH_REQUIRED：未找到 BI 凭证。请先 `python <i7c4z1>/scripts/login_bi.py` 扫码，"
            "或设置 BI_UID_TOKEN + BI_UID_TOKEN_SIG。本板不实现登录。")
    return s


# ----------------------------------------------------------------- 数据加载
def load_cards() -> list:
    return json.loads((DATA / "cards.json").read_text(encoding="utf-8")).get("cards", [])


def load_selectors() -> list:
    return json.loads((DATA / "selectors.json").read_text(encoding="utf-8")).get("selectors", [])


def find_card(q: str) -> dict | None:
    cards = load_cards()
    q = q.strip()
    if any(c["cardId"] == q for c in cards):
        return next(c for c in cards if c["cardId"] == q)
    exact = [c for c in cards if (c.get("name") or "") == q]
    if exact:
        return exact[0]
    part = [c for c in cards if q in (c.get("name") or "")]
    return part[0] if part else None


def find_selector(q: str) -> dict | None:
    sels = load_selectors()
    q = q.strip()
    if any(s["selectorId"] == q for s in sels):
        return next(s for s in sels if s["selectorId"] == q)
    exact = [s for s in sels if (s.get("name") or "") == q]
    if exact:
        return exact[0]
    part = [s for s in sels if q in (s.get("name") or "")]
    return part[0] if part else None


# ----------------------------------------------------------------- 筛选键组
def cand_value_map(card: dict, sels: list) -> dict:
    """字段名 → 该字段合法取值（取自驱动本卡的筛选器候选值）。"""
    m = {}
    for x in sels:
        if card["cardId"] not in (x.get("targetCdIds") or []):
            continue
        for sf in (x.get("sourceFields") or []):
            vals = x.get("candidates") or []
            if vals and sf.get("name"):
                m.setdefault(sf["name"], vals[0])
    return m


def passable_filters(card: dict) -> list:
    """卡片声明中可传参的筛选项（剔除 NOT_NULL 内部行级过滤，传则 1012）。"""
    return [f for f in card.get("filters", [])
            if (f.get("filterType") or "").upper() != "NOT_NULL"]


def page_date_filter(card_id: str, val=None) -> dict:
    """摇钱树销售进度页·出库日期（fdId=j837…）强制过滤。val 为 2 元组→BT，1 元组→EQ。"""
    v = list(val) if val else default_date_range()
    ft = "BT" if len(v) > 1 else "EQ"
    return {"name": "出库日期", "fdId": PAGE_DATE_FDID, "dsId": PAGE_DATE_DSID,
            "cdId": card_id, "fdType": "DATE", "filterType": ft,
            "filterLevel": "DETAIL", "filterValue": v}


def build_filter(f: dict, hint: dict | None = None) -> dict:
    ft = (f.get("filterType") or "IN").upper()
    item = {"name": f["name"], "fdId": f["fdId"], "dsId": f["dsId"], "cdId": f["cdId"],
            "fdType": f["fdType"], "filterLevel": f.get("filterLevel") or "DETAIL"}
    item["filterType"] = "BT" if f.get("fdType") == "DATE" else ft
    if f.get("fdType") == "DATE":
        y = default_date_range()[0]
        item["filterValue"] = [y, y]  # BT 单日（与页面口径一致，动态）
    else:
        hv = (hint or {}).get(f["name"])
        item["filterValue"] = f.get("filterValue") or (
            [hv] if hv is not None else
            ([1] if f.get("fdType") in ("DOUBLE", "LONG", "INT", "DECIMAL", "FLOAT") else ["其他"]))
    return item


# 页面默认筛选注入矩阵（来源=2026-09-23 抓包各页筛选器声明与下发请求，schema 级常量）。
# ⚠ 核心：所有页的卡取数都必须带该页筛选器的默认值等价筛选，否则服务端回退全表累计
#   （实测：经营分析 gae7d 不带月份→1.245亿全表 vs 9月941万；销售曲线→3.66亿 vs 890万/月）。
# 账号域值（商务/子公司等）不在此列——那些必须运行时探测，禁硬编码。
PAGE_DATE_RULES = {
    "摇钱树货主利润表-商务": {  # 时间选择宏「本月到昨天」
        "f0a3a48ad2cb34a6a976ce0b": {"name": "出库日期", "fdId": "rfa1e0f57fb5744d2a2a47ac", "fdType": "DATE", "mode": "month_to_yesterday"},
        "v5d3ef95807bf49288b37ea3": {"name": "出库日期", "fdId": "h7bd36ff0d05048ad8ef3a78", "fdType": "DATE", "mode": "month_to_yesterday"},
    },
    "摇钱树经营分析看板": {  # 月份选择 FIRST_PICK=候选最新月（值形如 YYYY-MM）
        "adaa03de09dd84a74a5c19e5": {"name": "出库日期", "fdId": "a98b0457d2c174976a01fe60_month", "fdType": "SUB_DATE", "mode": "first_pick", "selector": "n71de3fc24fc141bb8791c4a"},
    },
    "摇钱树商务考核数据": {  # 出库月份 FIRST_PICK=候选最新月（值形如 YYYY-MM-01）
        "sd101dc3b2d874ea1ab2a979": {"name": "出库月份", "fdId": "nde0c223767cb4308be1767d", "fdType": "DATE", "mode": "first_pick", "selector": "j5b899f883ec2407fb6db514"},
    },
    "摇钱树库存报表": {  # 日期 EQ 宏{{{today}}}
        "e793470f623d14c2b9cf135a": {"name": "日期", "fdId": "pf53227b788034f9485cb8af", "fdType": "DATE", "mode": "today"},
    },
    "摇钱树补货建议表": {  # 补货时间 FIRST_PICK=候选最新快照日（STRING 域值，写死今天会 1012）
        "k568af327ec2c42c4b687a06": {"name": "导入时间", "fdId": "v5e9818581d114ec0809a757", "fdType": "STRING", "mode": "first_pick", "selector": "debb04b5f2d0a497499271fa"},
    },
    "配送成本维度拆分": {  # 出库日期 BT YESTERDAY
        "fcd5f3350f4634607987b1f6": {"name": "出库日期", "fdId": "q85ef288283aa48c98b1692d", "fdType": "DATE", "mode": "yesterday"},
    },
    "人工成本维度拆分": {
        "fcd5f3350f4634607987b1f6": {"name": "出库日期", "fdId": "q85ef288283aa48c98b1692d", "fdType": "DATE", "mode": "yesterday"},
    },
}


_FP_CACHE = {}


def _first_pick_value(sel_id: str, session=None, ttl: int = 300) -> list:
    """FIRST_PICK 语义：取筛选器候选值第一项（页面默认值的权威来源，随账号/时间动态）。

    带进程内 TTL 缓存；候选为空/接口失败返回 []（调用方应跳过注入而非传空值→1012）。"""
    now = time.time()
    hit = _FP_CACHE.get(sel_id)
    if hit and now - hit[0] < ttl:
        return hit[1]
    s = session or resolve_session()
    val = None
    try:
        st, txt = _post(s, f"/api/selector/{sel_id}/data",
                        {"fieldQuery": {"offset": 0, "limit": 1000}, "filters": [], "treeFilters": [],
                         "dynamicParams": [], "layerTreeFilters": []}, 60)
        if st == 200:
            j = json.loads(txt)
            vals = [x.get("value") for x in (j.get("result") or [])
                    if isinstance(x, dict) and x.get("value") is not None]
            if vals:
                # FIRST_PICK 页面语义=默认选中最新（抓包：候选含历史时默认=最新快照日/最新月）
                val = max(str(v) for v in vals)
    except Exception:
        val = None
    fv = [val] if val is not None else []
    _FP_CACHE[sel_id] = (now, fv)
    return fv


_SEL_BINDINGS = None


def _selector_bindings() -> list:
    """读取 selectors.json 的筛选器声明（含 defaultValue/sourceFields/targetFields 映射）。"""
    global _SEL_BINDINGS
    if _SEL_BINDINGS is None:
        try:
            data = json.loads((DATA / "selectors.json").read_text(encoding="utf-8"))
            sels = data.get("selectors") if isinstance(data, dict) else data
            _SEL_BINDINGS = sels or []
        except Exception:
            _SEL_BINDINGS = []
    return _SEL_BINDINGS


def _mkf(name, fdId, dsId, fdType, ft, fv, card_id) -> dict:
    return {"name": name, "fdId": fdId, "dsId": dsId, "cdId": card_id,
            "fdType": fdType, "filterType": ft, "filterLevel": "DETAIL", "filterValue": fv}


def _snapshot_date_filter(page: str, card_id: str, session=None, override=None):
    """v1.1 动态化：从 selectors.json 快照解析本卡的页面默认日期筛选。

    页面更新后重跑 fetch_cards.py，注入即自动跟进（无需改代码）；
    override（用户显式 date）非 None 时直接以其实值构造（BT/EQ 按元素数）；
    解析不到返回 None → 落到 PAGE_DATE_RULES 常量兜底。"""
    y = default_date_range()[0]
    t = _date.today().isoformat()
    ms = _date.today().replace(day=1).isoformat()
    for s in _selector_bindings():
        if s.get("pageName") != page:
            continue
        if card_id not in (s.get("targetCdIds") or []):
            continue
        dv = s.get("defaultValue")
        stp = s.get("selectorType")
        nm = str(s.get("name") or "")
        # 日期类筛选器：CALENDAR/TIME_MACRO，或 FIRST_PICK 的月/日期/时间字段
        dateish = stp in ("CALENDAR", "TIME_MACRO") or (
            isinstance(dv, dict) and dv.get("valueType") == "FIRST_PICK"
            and any(k in nm for k in ("日期", "月份", "时间")))
        if not dateish:
            continue
        fd = next((tf for tf in (s.get("targetFields") or []) if tf.get("cdId") == card_id), None)
        if not fd or not fd.get("fdId"):
            continue
        fdId, dsId = fd["fdId"], fd.get("dsId")
        fdType = "SUB_DATE" if str(fdId).endswith(("_month", "_week")) else "DATE"
        if override is not None:  # 用户显式 date 优先（格式需与字段匹配，如月字段传 YYYY-MM）
            ft = "BT" if len(override) > 1 else "EQ"
            return _mkf(fd.get("name") or nm, fdId, dsId, fdType, ft, list(override), card_id)
        if stp == "TIME_MACRO" and not isinstance(dv, dict):
            if "本月" in nm and "昨天" in nm:
                return _mkf(fd.get("name") or nm, fdId, dsId, fdType, "BT", [ms, y], card_id)
            continue
        expr0 = str((dv.get("expr") or [""])[0]) if isinstance(dv, dict) else ""
        if "yesterday" in expr0 or expr0 == "YESTERDAY":
            return _mkf(fd.get("name") or nm, fdId, dsId, fdType, "EQ", [y], card_id)
        if "today" in expr0 and "- 14" not in expr0:
            return _mkf(fd.get("name") or nm, fdId, dsId, fdType, "EQ", [t], card_id)
        if "- 14" in expr0:
            d14 = (_date.today() - _timedelta(days=14)).isoformat()
            return _mkf(fd.get("name") or nm, fdId, dsId, fdType, "BT", [d14, t], card_id)
        if isinstance(dv, dict) and dv.get("valueType") == "FIRST_PICK":
            fv = _first_pick_value(s.get("selectorId"), session)
            if fv:
                return _mkf(fd.get("name") or nm, fdId, dsId, fdType, "IN", fv, card_id)
            return None  # 候选取不到→交兜底/跳过，不传空值
    return None


def _page_default_filter(page: str, ds: str, card_id: str, session=None, override=None):
    """页面默认筛选常量兜底（快照映射 _snapshot_date_filter 优先）。

    动态：today/yesterday/本月1日运行时计算；FIRST_PICK 取候选最新值；
    override（用户显式 date）非 None 时直接以其实值构造。"""
    r = PAGE_DATE_RULES.get(page, {}).get(ds)
    if not r:
        return None
    if override is not None:
        ft = "BT" if len(override) > 1 else "EQ"
        return _mkf(r["name"], r["fdId"], ds, r["fdType"], ft, list(override), card_id)
    y = default_date_range()[0]
    t = _date.today().isoformat()
    mode = r["mode"]
    if mode == "first_pick":
        fv = _first_pick_value(r["selector"], session)
        if not fv:
            return None  # 候选取不到→不注入（传空/错值会 1012）
        ft = "IN"
    elif mode == "month_to_yesterday": ft, fv = "BT", [_date.today().replace(day=1).isoformat(), y]
    elif mode == "today": ft, fv = "EQ", [t]
    elif mode == "yesterday": ft, fv = "EQ", [y]
    else:
        return None
    return {"name": r["name"], "fdId": r["fdId"], "dsId": ds, "cdId": card_id,
            "fdType": r["fdType"], "filterType": ft, "filterLevel": "DETAIL", "filterValue": fv}


# 卡级动态维度默认（dynamicFieldFilters）：销售曲线的「日/周/月」粒度 dz——
# 不带则按月聚合回 1 行（实测）；key=GEHhqq… 即「日」。抓包 2026-09-23 权威。
CARD_DZ_DEFAULTS = {
    "v9c23bcf1c8794fa180b1ccb": [
        {"dzId": "TwAMPKTYKEzTCwBDnBPBAFty", "key": "GEHhqqTcDSKstnmBnaNDGtFy",
         "sourceCdId": "v9c23bcf1c8794fa180b1ccb"}],
}


def recommended_filters(card: dict, sels: list, date_range: list | None = None, session=None) -> list:
    """一张卡的推荐查询过滤：页面默认筛选（按页×数据集注入）+ 卡片自身可传参筛选。

    规则（实测 2026-09-24）：
    - 销售进度页：出库明细集卡强制 j837（EQ 昨日宏；不带→千亿级）；负利润滞销集卡
      用 sc5733bd（对它强制 j837 会 1012）；
    - 其它页：按 PAGE_DATE_RULES 注入页面默认日期（货主=本月到昨天、经营分析=最新月、
      考核=最新月、库存=今日、补货=今日快照、配送/人工=昨日）；不带→全表累计错数；
    - 页面口径与卡片自带日期筛选同字段时，以页面口径替换（避免重复/口径打架）；
    - 未命中矩阵的卡（峰值/货主近期等）不注入，维持原行为。
    ⚠ 账号域值（商务/子公司等）永不在此硬编码——运行时经 candidates.py 探测。
    """
    hint = cand_value_map(card, sels)
    dr = list(date_range) if date_range else default_date_range()
    ovr = list(date_range) if date_range else None  # 用户显式 date → 覆盖页面默认值
    fl = []
    page, ds = card.get("pageName"), card.get("dsId")
    if page == SALES_PAGE:
        if ds == NEG_PROFIT_DS:
            ft = "BT" if len(dr) > 1 else "EQ"
            fl.append({"name": "日期", "fdId": NEG_PROFIT_DATE_FDID, "dsId": NEG_PROFIT_DS,
                       "cdId": card["cardId"], "fdType": "DATE", "filterType": ft,
                       "filterLevel": "DETAIL", "filterValue": dr})
        else:
            fl.append(page_date_filter(card["cardId"], dr))
    pf = passable_filters(card)
    inj = _snapshot_date_filter(page, card["cardId"], session, override=ovr) or \
        _page_default_filter(page, ds, card["cardId"], session, override=ovr)
    if inj:
        pf = [f for f in pf if f.get("fdId") != inj["fdId"]]
        fl.append(inj)
    fl += [build_filter(f, hint) for f in pf]
    return fl


def _named_filter(card: dict, sels: list, name: str, values: list) -> dict:
    """把用户按「字段名」指定的筛选解析为完整键组（优先命中卡片声明，其次页面筛选器驱动字段）。"""
    for f in passable_filters(card):
        if f.get("name") == name:
            item = build_filter(f)
            item["filterValue"] = values
            return item
    for x in sels:
        if card["cardId"] not in (x.get("targetCdIds") or []):
            continue
        for tf in (x.get("targetFields") or []):
            if tf.get("name") == name:
                ft = (tf.get("filterType") or "IN").upper()
                return {"name": name, "fdId": tf["fdId"], "dsId": tf["dsId"],
                        "cdId": card["cardId"], "fdType": tf.get("fdType", "STRING"),
                        "filterLevel": "DETAIL", "filterType": ft, "filterValue": values}
    raise KeyError(f"字段「{name}」既不是卡片可传参筛选，也不是驱动本卡的页面筛选器字段")


# ----------------------------------------------------------------- 请求壳
def _post(s, path, body, timeout=130):
    r = s.post(BASE + path, headers=J, json=body, timeout=timeout)
    return r.status_code, r.text


def _get(s, path, timeout=60):
    r = s.get(BASE + path, headers=UA, timeout=timeout, allow_redirects=False)
    return r.status_code, r.text


def _base_body(filters, limit=50, offset=0, view="GRAPH",
               dynamic_params=None, dynamic_field_filters=None):
    return {"filters": filters or [], "treeFilters": [],
            "dynamicParams": dynamic_params or [],
            "dynamicFieldFilters": dynamic_field_filters or [],
            "combinationFilters": [], "layerTreeFilters": [],
            "view": view, "isUniversalStructure": False, "offset": offset, "limit": limit}


def _scalar(v):
    if isinstance(v, dict):
        for k in ("v", "value", "title", "name"):
            if k in v:
                return v[k]
        return v
    return v


def _extract(cm: dict):
    row = cm.get("row") or {}
    rmeta = row.get("meta") or []
    rvals = row.get("values") or []
    col = cm.get("column") or {}
    cvals = col.get("values") or []
    metric_names = []
    for cv in cvals:
        if isinstance(cv, list) and cv and isinstance(cv[0], dict):
            metric_names.append(cv[0].get("title") or cv[0].get("name"))
        elif isinstance(cv, dict):
            metric_names.append(cv.get("title") or cv.get("name"))
    data = cm.get("data") or []
    dim_names = [(m.get("name") or f"维度{i + 1}") for i, m in enumerate(rmeta)]
    rows = []
    for i, dr in enumerate(data):
        rec = {}
        rv = rvals[i] if i < len(rvals) else []
        for j, m in enumerate(dim_names):
            rec[m] = _scalar(rv[j]) if j < len(rv) else None
        cells = dr if isinstance(dr, list) else []
        for j, mn in enumerate(metric_names):
            rec[mn] = _scalar(cells[j]) if j < len(cells) else None
        rows.append(rec)
    # 图表类（BASIC_BAR/MULTI_LINE/PIE 等）：数据在 categories[] + series[].data[].y；
    # 实测（2026-09-24，gae7d 含税金额卡）此前落入 KPI 兜底导致维度标签丢失、数值 null。
    if not rows and not dim_names and not metric_names:
        cats = cm.get("categories") or []
        series = cm.get("series")
        if isinstance(series, list) and series and cats:
            dim_name = None
            for c in ((cm.get("meta") or {}).get("categories") or []):
                if isinstance(c, dict) and c.get("name"):
                    dim_name = c["name"]
                    break
            dim_name = dim_name or "分类"
            col_names, seen = [], {}
            for s in series:
                n = str(s.get("name") or s.get("title") or f"系列{len(col_names)+1}")
                seen[n] = seen.get(n, 0) + 1
                col_names.append(n if seen[n] == 1 else f"{n}#{seen[n]}")
            rows = []
            for i, cat in enumerate(cats):
                rec = {dim_name: _scalar(cat)}
                for j, s in enumerate(series):
                    d = s.get("data") or []
                    pt = d[i] if i < len(d) else None
                    rec[col_names[j]] = pt.get("y") if isinstance(pt, dict) else _scalar(pt)
                rows.append(rec)
            return rows, [dim_name], col_names
    # KPI / 单值卡：数值在 series[].value，无 row/column/data（如销售进度页 KPI 卡）
    if not rows and not dim_names and not metric_names:
        series = cm.get("series")
        if isinstance(series, list) and series:
            rows = [{"指标": s.get("name"), "数值": s.get("value")} for s in series]
            dim_names, metric_names = ["指标"], ["数值"]
    return rows, dim_names, metric_names


# ----------------------------------------------------------------- 取数
def query_card(card: dict, filters: list, *, limit=50, all_pages=False,
               view="GRAPH", timeout=130, session=None,
               dynamic_params=None, dynamic_field_filters=None) -> dict:
    """取数（自动翻页）。

    dynamic_params：PARAMETER 筛选器传参（分析维度/开始日期等）——经营分析/补货页
      部分卡必须带（如 gae7d 不带则分析维度回退「省内外」）。元素为完整 dp 对象。
    dynamic_field_filters：动态字段注入（dzId+key+sourceCdId）——配送/人工成本
      拆分卡必须带全 5 个，否则只回总计 1 行（实测）。
    """
    s = session or resolve_session()
    cid = card["cardId"]
    if dynamic_field_filters is None:
        dynamic_field_filters = CARD_DZ_DEFAULTS.get(cid)  # 卡级动态维度默认（如销售曲线按日）
    all_rows, dims, metrics = [], [], []
    offset, pages = 0, 0
    count = None
    has_more = True
    while True:
        st, txt = _post(s, f"/api/card/{cid}/data",
                        _base_body(filters, limit, offset, view,
                                   dynamic_params=dynamic_params,
                                   dynamic_field_filters=dynamic_field_filters), timeout)
        if st != 200:
            return {"ok": False, "cardId": cid, "http": st, "detail": txt[:240]}
        j = json.loads(txt)
        inner = j.get("response", j) if isinstance(j, dict) else j
        cm = (inner or {}).get("chartMain") or {}
        rows, dims, metrics = _extract(cm)
        all_rows.extend(rows)
        count = cm.get("count")
        if count is None:
            count = len(all_rows)
        has_more = cm.get("hasMoreData", False)
        if not all_pages or not has_more:
            break
        offset += limit
        pages += 1
        if pages > (PROFILE.get("limits", {}).get("maxPage", 10000)):
            break
    return {"ok": True, "cardId": cid, "name": card.get("name"), "page": card.get("pageName"),
            "columns": dims + metrics, "rows": all_rows, "count": count,
            "fetched": len(all_rows), "hasMoreData": has_more,
            "effectiveFilters": filters}


# ----------------------------------------------------------------- 权限自检
def _dig_error(txt):
    """从 BI 错误响应体里抠出 error_code / error_message（兼容多种形态）。"""
    try:
        j = json.loads(txt)
    except Exception:
        return None, None
    if not isinstance(j, dict):
        return None, None
    ec = (j.get("error_code")
          or (j.get("error") or {}).get("status")
          or j.get("response", {}).get("errorCode")
          or j.get("response", {}).get("error_code"))
    msg = (j.get("error_message")
           or (j.get("error") or {}).get("message")
           or j.get("response", {}).get("errorMsg"))
    return ec, msg


def verify_board_permission(session=None, probe_card=None):
    """板块级权限自检：用当前凭证对一张代表卡做 limit=1 轻量探测。
    返回：ACCESSIBLE / NO_PERMISSION / AUTH_EXPIRED / NETWORK / UNKNOWN。
    注意 BI 无权限伪装成 HTTP 500 + error_code=1004，必须解析响应体，
    不能只看状态码（否则误判为服务端抖动而重试）。
    """
    s = session or resolve_session()
    cards = load_cards()
    if not cards:
        return "UNKNOWN"
    card = probe_card or cards[0]
    sels = load_selectors()
    try:
        fl = recommended_filters(card, sels) if sels else []
    except Exception:
        fl = []
    try:
        st, txt = _post(s, f"/api/card/{card['cardId']}/data",
                        _base_body(fl, 1, 0, "GRAPH"), timeout=60)
    except Exception:
        return "NETWORK"
    if st == 200:
        return "ACCESSIBLE"
    code, msg = _dig_error(txt)
    if code == 1004 or "无权访问" in (msg or ""):
        return "NO_PERMISSION"
    if st in (401, 403) or code in (1002, 1003, 1005, 1006):
        return "AUTH_EXPIRED"
    return "UNKNOWN"


# ----------------------------------------------------------------- 候选值
def get_candidates(name: str, *, search=None, refresh=False, session=None) -> dict:
    sel = find_selector(name)
    if not sel:
        return {"ok": False, "detail": f"未找到筛选器「{name}」"}
    sid = sel["selectorId"]
    cache_file = RES / "candidate_cache.json"
    cache = {}
    if cache_file.is_file():
        try:
            cache = json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            cache = {}
    key = f"{name}::{search or ''}"
    if not refresh and key in cache and (time.time() - cache[key].get("ts", 0) < 86400):
        return {"ok": True, "selectorId": sid, "cached": True,
                "values": cache[key].get("values", []), "count": cache[key].get("count")}
    s = session or resolve_session()
    body = {"search": search} if search else {}
    st, txt = _post(s, f"/api/selector/{sid}/data", body, timeout=60)
    if st != 200:
        return {"ok": False, "selectorId": sid, "http": st, "detail": txt[:240]}
    j = json.loads(txt)
    inner = j.get("response", j) if isinstance(j, dict) else j
    vals = [x.get("value") for x in (inner.get("result") or []) if isinstance(x, dict)]
    if not vals:  # 某些接口把列表放在外层
        vals = [x.get("value") for x in (inner.get("data") or []) if isinstance(x, dict)]
    cache[key] = {"values": vals, "count": inner.get("count"), "ts": time.time()}
    cache_file.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return {"ok": True, "selectorId": sid, "cached": False, "values": vals,
            "count": inner.get("count"), "serverTruncated": bool(inner.get("exceedLimit"))}


# ----------------------------------------------------------------- 导出（禁用 j837）
def export_card(card: dict, filters: list, out_path: str, *, timeout=600, session=None) -> dict:
    s = session or resolve_session()
    cid = card["cardId"]
    # 导出任务拒绝页面级出库日期 j837（报 1012 FAILED）→ 强制剥离
    fl = [f for f in (filters or []) if f.get("fdId") != PAGE_DATE_FDID]
    body = _base_body(fl, limit=100)
    st, txt = _post(s, f"/api/write/file/{cid}?typeOp=EXCEL", body, timeout=60)
    if st != 200:
        return {"ok": False, "step": "① 提交", "http": st, "detail": txt[:240]}
    j = json.loads(txt)
    inner = j.get("response", j) if isinstance(j, dict) else j
    tid = inner.get("taskId")
    if not tid:
        return {"ok": False, "step": "① 提交", "detail": inner.get("message") or txt[:200]}
    # 轮询
    status = None
    r2 = None
    for _ in range(60):
        time.sleep(3)
        r2 = s.get(f"{BASE}/api/task/{tid}", headers=UA, timeout=60)
        j2 = r2.json().get("response", r2.json()) if r2.status_code == 200 else {}
        status = j2.get("status")
        if status in ("FINISHED", "FAILED", "CANCELLED"):
            break
    if status != "FINISHED":
        return {"ok": False, "step": "② 轮询", "status": status,
                "detail": str(j2)[:240] if r2 else "轮询无响应"}
    # 下载
    r3 = s.post(f"{BASE}/api/export/file/common/{tid}", headers=J,
                json={"downloadFileName": card.get("name") or cid}, timeout=timeout)
    ok = r3.content[:2] == b"PK"
    if not ok:
        return {"ok": False, "step": "③ 下载", "http": r3.status_code, "detail": r3.text[:240]}
    Path(out_path).write_bytes(r3.content)
    return {"ok": True, "taskId": tid, "out": out_path, "bytes": len(r3.content)}
