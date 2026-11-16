# -*- coding: utf-8 -*-
"""链接管理（ljgl）—— `python scm.py scene ljgl <动作>`。

协议（assets/GUIDE.md §2）：SCENE 与 scene.json.name 一致；main(argv)->int；顶层无副作用。

动作分 6 组（25 个）：
  查询   store / find / group-list / group-nostore / pms-find / list
  创建   create（一气呵成）
  SCM改  ws-desc / ws-stock / ws-ladder / reprice / group-create / group-update
         / group-del / group-add / group-remove / group-add-nostore
  PMS改  pms-limit / pms-area / pms-time
  生命周期 off / restart / end / schedule
  辅助   qr

真机铁律（勿改）：
  价格档位按 priceTypes 全量、unitPrice9 原值、价格传数字、oldData 字符串、
  ex=fixedPriceShelf、operationFlag 跟随源、wsDesc 走 editWsDesc + wsList 复验、
  下架 SCM paste 失败降级 PMS W1。
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core import credential  # noqa: E402
from core.errors import SkillError  # noqa: E402
from core.http import BASE, build_session, call_endpoint, public_params  # noqa: E402

SCENE = "ljgl"
_ACCOUNT = None
HERE = Path(__file__).resolve().parent
SKELETON = json.loads((HERE / "payload_skeleton.json").read_text(encoding="utf-8"))

LINK_TPL = ("https://dian.ysbang.cn/#/drugInfo?wholesaleid=%s"
            "&isAssemble=false&scene=1&trafficType=1")
GROUP_NAME_TPL = "%s临时控销"
GROUP_DESC_TPL = "agent临时控销！%s后可删除。"
WS_DESC_TPL = "WorkBuddy做单链接，%s后可下架。"
TEMPORARY_NAME_RE = re.compile(r"^\d+临时控销$")
TEMPORARY_DESC_RE = re.compile(r"^agent临时控销！\d{8}后可删除。$")
PRICE_TYPES = ("1", "2", "7", "8", "9")
PMS = "/pms-main/ykjWholesaleOperation/"
_CALL_STATE = [0.0]
_MIN_INTERVAL = 6.0


# ================================================================ 基础设施
def _emit(obj):
    print(json.dumps(obj, ensure_ascii=False))


def _ledger():
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    d = Path(base) / "scm-operations-query"
    d.mkdir(parents=True, exist_ok=True)
    return d / "link-records.jsonl"


def _record(rec):
    with _ledger().open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _call(path, payload=None, *, host="scm", ex="goodsOnShelves", method="post",
          headers=None, out=None, account=None, drop=()):
    gap = time.time() - _CALL_STATE[0]
    if gap < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - gap)
    try:
        return _call_inner(path, payload, host=host, ex=ex, method=method,
                           headers=headers, out=out, account=account, drop=drop)
    finally:
        _CALL_STATE[0] = time.time()


def _call_inner(path, payload, *, host, ex, method, headers, out, account, drop):
    payload = dict(payload or {})
    if host == "pms":
        from core import pms_client as pms
        cred = pms.load_credential() or {}
        token = str(cred.get("token") or "")
        if not token:
            raise SkillError("AUTH_REQUIRED", "没有 PMS 凭证", hint="python scm.py pms-login")
        ts = str(int(time.time()))
        hdrs = dict(pms.PMS_HEADERS)
        hdrs.update({"token": token, "timestamp": ts,
                     "content-type": "application/json",
                     "module": "goods_act_manage",
                     "__module__": "goods_act_manage"})
        hdrs.update(headers or {})
        payload.update({"token": token, "appVersion": pms.APP_VERSION,
                        "platform": "web", "timestamp": ts,
                        "buildTime": pms._build_time()})
        session = __import__("requests").Session()
        session.trust_env = False
        url = pms.PMS_BASE + path
    else:
        cred = credential.load(account or _ACCOUNT)
        if not cred:
            raise SkillError("AUTH_REQUIRED", "没有可用的 SCM 凭证",
                             hint="python scm.py login")
        session = build_session(cred)
        token = str(cred.get("cms_token") or cred.get("token") or "")
        payload = dict(public_params(token, ex), **payload)
        url = BASE + path
        hdrs = headers or None
    for k in drop:
        payload.pop(k, None)
    return call_endpoint(session, url, payload, method=method, headers=hdrs, out=out)


def _pms_provider_id():
    """PMS 凭证里字段是 provider_id（下划线），兼容 providerId/providers[0].id。"""
    from core import pms_client as pms
    cred = pms.load_credential() or {}
    pid = cred.get("provider_id") or cred.get("providerId")
    if not pid:
        provs = cred.get("providers") or []
        if isinstance(provs, list) and provs:
            pid = (provs[0] or {}).get("id")
    if not pid:
        raise SkillError("AUTH_REQUIRED", "PMS 凭证缺少 provider_id",
                         hint="python scm.py pms-login")
    return int(pid)


def _ws_page(**filters):
    body = {"pageNo": 1, "pageSize": 50, "notThroughStatus": 0, "saleStatType": 1}
    body.update(filters)
    r = _call("/scm-goods/wholesaleDrug/wsList", body)
    d = r.get("data") or {}
    return d.get("results") or [], d.get("totalRecord")


def _ws_list(**filters):
    return _ws_page(**filters)[0]


def _src_row(wid):
    rows = _ws_list(status=-1, wholesaleId=int(wid))
    return rows[0] if rows else {}


def _template(wid, wtype):
    r = _call("/scm-goods/wholesaleDrug/getWholesale",
              {"wholesaleId": int(wid), "wholesaleType": int(wtype),
               "ctype": 1, "copyId": 1, "mode": "copy"})
    d = r.get("data") or {}
    return (d.get("wholesaleInfo") or {}, d.get("drugInfo") or {},
            d.get("providerInfo") or {}, d.get("priceTypes") or [])


def _ts(text):
    """'YYYY-MM-DD HH:MM:SS' → Unix 秒；已是数字则原样。"""
    if text is None:
        return None
    s = str(text).strip()
    if s.isdigit():
        return int(s)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return int(time.mktime(time.strptime(s, fmt)))
        except ValueError:
            continue
    raise SkillError("PARAM_INVALID", "时间格式需 YYYY-MM-DD [HH:MM[:SS]]: %s" % text,
                     hint="例如 2026-11-14 00:00:01")


# ================================================================ 药店
def _store_rows(keyword):
    """完整行查询：纯数字=药店ID；否则先按名称模糊，未命中再按编码精确兜底。"""
    kw = str(keyword).strip()

    def q(**extra):
        body = {"page": 1, "pageSize": 20, "version": "1.0.0"}
        body.update(extra)
        r = _call("/scm-order/crm/list", body,
                  ex="OldCustomerManagement", drop=("lastBuildTime",))
        return (r.get("data") or {}).get("results") or []

    if kw.isdigit():
        return q(drugstoreBranchId=int(kw))
    rows = q(storeTitle=kw)
    if rows:
        return rows
    return q(providerCode=kw)          # 药店编码兜底


def _find_store(keyword):
    rows = _store_rows(keyword)
    out = [{"drugstoreBranchId": x.get("drugstoreBranchId"),
            "storeTitle": x.get("storeTitle"),
            "providerCode": x.get("providerCode")} for x in rows]
    if not out and str(keyword).strip().isdigit():
        out = [{"drugstoreBranchId": int(str(keyword).strip()),
                "storeTitle": "", "providerCode": ""}]
    return out


def _resolve_store(keyword):
    rows = _find_store(keyword)
    if not rows:
        raise SkillError("PARAM_INVALID", "药店未找到：%s" % keyword,
                     hint="用药店ID/全名/编码再试；名称需与系统一致")
    if len(rows) > 1:
        raise SkillError("PARAM_INVALID", "药店命中多条，请用更精确的名称/编码",
                         details={"rows": rows[:5]},
                         hint="优先用药店ID（纯数字）或编码精确定位")
    return rows[0]["drugstoreBranchId"], rows[0]


# ================================================================ 商品候选
SELF_WS_RE = re.compile(r"WorkBuddy做单链接|agent临时控销")


def _find_candidates(drug, include_self=False):
    """候选查询。默认过滤本场景自建的活动（wsDesc 带 WorkBuddy/agent），避免选错源。"""
    attempts = [{"provDrugCode": drug}, {"approval": drug},
                {"drugName": drug}, {"searchInfo": drug}]
    seen, out = set(), []
    for f in attempts:
        try:
            rows = _ws_list(status=-1, wholesaleType=[1, 4], **f)
        except SkillError as exc:
            if "RATE_LIMITED" in str(exc):
                break
            continue
        for x in rows:
            wid = x.get("wholesaleId")
            if wid in seen:
                continue
            seen.add(wid)
            desc = str(x.get("wsDesc") or "")
            if SELF_WS_RE.search(desc) and not include_self:
                continue
            out.append({"wholesaleId": wid, "wholesaleType": x.get("wholesaleType"),
                        "statusName": x.get("statusName"),
                        "provDrugCode": x.get("provDrugCode"),
                        "drugName": x.get("drugName"), "pack": x.get("pack"),
                        "factoryName": x.get("factoryName"),
                        "unitPrice": x.get("unitPrice"),
                        "stockAvailable": x.get("stockAvailable"),
                        "wsDesc": desc})
        if out:
            break
    # 按商品编码分组：同商品多活动合并，优先「进行中」，保留备选ID
    grouped = {}
    for x in out:
        grouped.setdefault(str(x.get("provDrugCode") or x.get("wholesaleId")), []).append(x)
    merged = []
    for code, items in grouped.items():
        items.sort(key=lambda i: (0 if i.get("statusName") == "进行中" else
                                  1 if i.get("statusName") == "待开始" else 2,
                                  -float(i.get("unitPrice") or 0)))
        best = dict(items[0])
        best["activityCount"] = len(items)
        best["alsoIds"] = [i["wholesaleId"] for i in items[1:5]]
        merged.append(best)
    merged.sort(key=lambda i: (0 if i.get("statusName") == "进行中" else 1,
                               -float(i.get("unitPrice") or 0)))
    return merged


def _special_on_sale():
    try:
        return _ws_page(status=0, wholesaleType=[4])[1]
    except SkillError:
        return -1


# ================================================================ 控销组
def _ensure_group(store_id, desc_date):
    name = GROUP_NAME_TPL % store_id
    r = _call("/scm-setting/saleControl/storeGroup",
              {"pageNo": 1, "pageSize": 10, "groupName": name},
              ex="ControlDrugstoreGroup")
    for x in (r.get("data") or {}).get("results") or []:
        if x.get("groupName") == name:
            return x.get("storeGroupId"), name, False
    _call("/scm-setting/saleControl/editStoreGroup",
          {"storeGroupId": None, "groupName": name,
           "groupDesc": GROUP_DESC_TPL % desc_date}, ex="ControlDrugstoreGroup")
    r2 = _call("/scm-setting/saleControl/storeGroup",
               {"pageNo": 1, "pageSize": 10, "groupName": name},
               ex="ControlDrugstoreGroup")
    for x in (r2.get("data") or {}).get("results") or []:
        if x.get("groupName") == name:
            return x.get("storeGroupId"), name, True
    raise SkillError("BUSINESS_ERROR", "建组后回查不到 storeGroupId",
                     hint="检查组名是否重名/已达上限；可先 group-list 确认")


def _add_store(group_id, store_id):
    r = _call("/scm-setting/saleControl/addStoreBatch",
              {"batchType": 0, "storeGroupId": int(group_id),
               "branchIdList": [int(store_id)]}, ex="ControlDrugstoreGroup")
    d = r.get("data") or {}
    rows = d.get("data") or []
    already = bool(rows) and all("已存在" in str(i[1]) for i in rows
                                 if isinstance(i, (list, tuple)) and len(i) > 1)
    if d.get("errorCount") and not already:
        raise SkillError("BUSINESS_ERROR", "药店加入控销组失败", details=d)
    return d.get("rightCount") or 0


def _group_meta(group_id):
    r = _call("/scm-setting/saleControl/storeGroup",
              {"pageNo": 1, "pageSize": 5, "groupIds": [int(group_id)]},
              ex="ControlDrugstoreGroup")
    for x in (r.get("data") or {}).get("results") or []:
        if str(x.get("storeGroupId")) == str(group_id):
            return x
    return {}


def _is_temporary_group(meta):
    return bool(TEMPORARY_NAME_RE.match(str(meta.get("groupName") or ""))) and \
        bool(TEMPORARY_DESC_RE.match(str(meta.get("groupDesc") or "")))


# ================================================================ payload
def _apply_prices(payload, wi, price_types, target):
    valid = {str(t.get("priceType")) for t in price_types} or set(PRICE_TYPES)
    payload["unitPrice"] = float(target)
    payload["chainPrice"] = float(target)
    for t in valid:
        if t == "9":
            payload["unitPrice9"] = wi.get("unitPrice9")
        else:
            payload["unitPrice" + t] = float(target)


def build_payload(wi, di, pi, src_row, price_types, *, group_id, area_id,
                  price, stock, limit, begin, end):
    payload = dict(wi)
    for k, dft in SKELETON["defaults"].items():
        payload.setdefault(k, dft)
    for k in SKELETON["from_drug_info"]:
        if payload.get(k) in (None, "") and di.get(k) not in (None, ""):
            payload[k] = di[k]
    for k in SKELETON["instance_fields"]:
        if src_row.get(k) is not None:
            payload[k] = src_row[k]
    if price is not None:
        _apply_prices(payload, wi, price_types, price)
    qty = limit if limit is not None else stock
    payload.update({
        "id": wi.get("wholesaleId") or wi.get("id"),
        "wholesaleId": wi.get("wholesaleId") or wi.get("id"),
        "mode": "copy", "copyid": 1, "copyId": 1, "checkExist": 0,
        "startdate": begin, "enddate": end,
        "restrictGroupId": int(group_id), "isRestrict": 1,
        "areaGroupId": int(area_id),
        "operationFlag": src_row.get("operationFlag") or 2,
        "oldData": json.dumps({"provDrugCode": wi.get("provDrugCode"),
                               "specification": wi.get("specification"),
                               "unit": wi.get("unit")}, ensure_ascii=False),
    })
    if qty is not None:
        payload["maxAmountPerStore"] = int(qty)
        payload["maxAmount"] = int(qty)
        payload["maxAmountPerUser"] = int(qty)
    if stock is not None:
        payload["autoSyncStock"] = 0
        payload["stockAvailable"] = int(stock)
    return payload


def _area_nationwide():
    r = _call("/scm-goods/wholesaleDrug/getAreaGroupDropList")
    data = r.get("data") or []
    if isinstance(data, dict):
        data = data.get("list") or []
    for x in data:
        if isinstance(x, dict) and str(x.get("nationwide")) == "1":
            return x.get("id"), x.get("groupName")
    raise SkillError("BUSINESS_ERROR", "未找到 nationwide=1 的全国商圈",
                     hint="该账号可能无商圈权限；确认凭证体系（仅自营）")


# ================================================================ 查询类
_STORE_NOISE = {"token", "platform", "version", "userId", "ua", "lastBuildTime"}


def act_store(a):
    rows = _store_rows(a.keyword)
    clean = [{k: v for k, v in x.items() if k not in _STORE_NOISE} for x in rows]
    _emit({"ok": bool(rows), "action": "store", "matched": len(rows),
           "rows": clean[:20],
           "hint": "" if rows else "未命中：用药店ID/全名/编码再试"})
    return 0 if rows else 1


def act_find(a):
    store = _find_store(a.store) if a.store else []
    cands = _find_candidates(a.drug, a.include_self) if a.drug else []
    hint = ""
    if len(cands) > 10:
        hint = ("候选较多（%d 个商品编码），建议改用国药准字/商品编码/规格精确查询"
                % len(cands))
    _emit({"ok": True, "action": "find",
           "store": {"matched": len(store), "rows": store[:5]},
           "candidates": cands, "special_on_sale": _special_on_sale(),
           "hint": hint,
           "rule": "特价在售>=215→一口价；否则按所选候选类型"})
    return 0


def act_group_list(a):
    r = _call("/scm-setting/saleControl/getBranchInfo",
              {"storeGroupId": int(a.group), "pageNo": 1, "pageSize": 100},
              ex="ControlDrugstoreGroup")
    data = r.get("data")
    rows = data if isinstance(data, list) else (data or {}).get("results") or []
    _emit({"ok": True, "action": "group-list", "group": a.group, "count": len(rows),
           "rows": [{"branchId": x.get("branchId"), "storetitle": x.get("storetitle"),
                     "provCode": x.get("provCode"), "addTime": x.get("addTime")}
                    for x in rows[:50]]})
    return 0


def act_group_nostore(a):
    r = _call("/scm-setting/saleControl/getNoOrderStore",
              {"storeGroupId": int(a.group), "fullName": a.name or ""},
              ex="ControlDrugstoreGroup")
    rows = r.get("data") or []
    _emit({"ok": True, "action": "group-nostore", "group": a.group,
           "count": len(rows), "rows": rows[:30]})
    return 0


def act_pms_find(a):
    pid = _pms_provider_id()
    path = (PMS + "pageOneFixedWsList/v27280" if a.type == 1
            else PMS + "getSpecialProductWholeSaleList/v27280")
    body = {"providerId": pid, "page": 1, "pageSize": 20}
    if a.id:
        body["wholesaleId"] = int(a.id)
    if a.code:
        body["provDrugCode"] = a.code
    r = _call(path, body, host="pms")
    d = r.get("data") or {}
    rows = d.get("results") or d.get("list") or []
    _emit({"ok": True, "action": "pms-find", "type": a.type,
           "total": d.get("total"), "count": len(rows), "rows": rows[:20]})
    return 0


def act_list(a):
    p = _ledger()
    rows = []
    if p.is_file():
        for line in p.read_text(encoding="utf-8").splitlines()[-a.limit:]:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    _emit({"ok": True, "action": "list", "ledger": str(p), "rows": rows})
    return 0


# ================================================================ 创建
def act_create(a):
    store = _find_store(a.store)
    if not store:
        raise SkillError("PARAM_INVALID", "药店未找到", hint="用药店名称/编码/ID 再试")
    if len(store) > 1:
        _emit({"ok": False, "error": "MULTI_STORE", "store": store[:5],
               "hint": "药店命中多条，请用更精确的名称/编码"})
        return 2
    store_id = store[0]["drugstoreBranchId"]

    if a.source:
        src_row = _src_row(a.source)
        if not src_row:
            raise SkillError("PARAM_INVALID",
                             "源活动不存在或无权访问：%s" % a.source,
                             hint="先用 find --drug <商品> 查可用活动ID")
        wid, wtype = int(a.source), src_row.get("wholesaleType") or 1
    else:
        cands = _find_candidates(a.drug, a.include_self)
        total_acts = sum(int(c.get("activityCount") or 1) for c in cands)
        if len(cands) != 1 or total_acts != 1:
            _emit({"ok": False, "error": "NEED_SOURCE", "candidates": cands,
                   "activity_total": total_acts,
                   "hint": "候选不唯一（或同商品有多个活动），请指定 --source <活动id>"})
            return 2
        wid, wtype = cands[0]["wholesaleId"], cands[0]["wholesaleType"]

    wi, di, pi, price_types = _template(wid, wtype)
    if not wi:
        raise SkillError("BUSINESS_ERROR", "取模板失败",
                     hint="确认源活动ID与类型（一口价=1 / 特价=4），或先用 find 查候选")
    area_id, area_name = _area_nationwide()
    if a.date and not re.match(r"^\d{4}-\d{2}-\d{2}$", str(a.date)):
        raise SkillError("PARAM_INVALID", "--date 需 YYYY-MM-DD",
                         hint="例如 2026-11-14；不要用斜杠")
    day = a.date or time.strftime("%Y-%m-%d")
    begin, end = "%s 00:00:01" % day, "%s 23:59:59" % day
    desc_date = (a.desc_date or day).replace("-", "")
    ws_desc = a.desc if a.desc is not None else WS_DESC_TPL % day.replace("-", "/")

    payload = build_payload(wi, di, pi, src_row, price_types,
                            group_id=a.group_id or 0, area_id=area_id,
                            price=a.price, stock=a.stock, limit=a.limit,
                            begin=begin, end=end)
    summary = {
        "ok": True, "action": "create", "dry_run": not a.confirm,
        "store": {"id": store_id, "title": store[0]["storeTitle"]},
        "source": {"wholesaleId": wid, "wholesaleType": wtype},
        "area": {"id": area_id, "name": area_name},
        "time": {"begin": begin, "end": end},
        "price": {"target": a.price, "unitPrice9_source": wi.get("unitPrice9")},
        "stock": a.stock, "limit": a.limit,
        "operationFlag": payload.get("operationFlag"),
        "payload_keys": len(payload), "planned_desc": ws_desc,
    }
    if not a.confirm:
        summary["hint"] = "dry-run：加 --confirm 才真正提交"
        _emit(summary)
        return 0

    group_id, group_name, created = _ensure_group(store_id, desc_date)
    payload["restrictGroupId"] = int(group_id)
    new_wid = None
    try:
        added = _add_store(group_id, store_id)
        r = _call("/scm-goods/wholesaleDrug/addWholesale", payload, ex="fixedPriceShelf")
        inner = r.get("data") or {}
        if isinstance(inner.get("data"), dict):
            inner = inner["data"]
        new_wid = inner.get("wholesaleId")
        if not new_wid:
            raise SkillError("BUSINESS_ERROR", "提交未回带新活动ID", details=r)
        v = _call("/scm-goods/wholesaleDrug/getWholesale",
                  {"wholesaleId": int(new_wid), "wholesaleType": wtype,
                   "ctype": 1, "copyId": 1, "mode": "edit"})
        vi = (v.get("data") or {}).get("wholesaleInfo") or {}
        if a.stock is not None:
            _call("/scm-goods/wholesaleDrug/editStock2",
                  {"drugId": vi.get("drugId") or wi.get("drugId"),
                   "id": int(new_wid), "manualSyncStock": 1,
                   "wholesaleType": wtype, "drugStock": int(a.stock)})
        desc_set = False
        try:
            _call("/scm-goods/wholesaleDrug/editWsDesc",
                  {"id": int(new_wid), "wsDesc": ws_desc})
            desc_set = True
        except SkillError:
            desc_set = False
        row_after = _src_row(new_wid)
        link = LINK_TPL % new_wid
        _record({"ts": _now(), "store": store_id, "group": group_id,
                 "groupName": group_name, "source": wid, "new": new_wid,
                 "price": a.price, "stock": a.stock, "limit": a.limit,
                 "link": link, "status": "on_sale", "wsDesc": ws_desc})
        summary.update({"new_wholesaleId": new_wid, "group": group_id,
                        "added": added, "link": link, "ws_desc": ws_desc,
                        "ws_desc_ok": desc_set,
                        "verify": {**{k: vi.get(k) for k in (
                            "unitPrice", "unitPrice1", "unitPrice2", "unitPrice7",
                            "unitPrice8", "unitPrice9", "stockAvailable",
                            "maxAmount", "maxAmountPerUser", "isRestrict",
                            "restrictGroupId", "areaGroupId", "status",
                            "prodDate", "validDate")},
                            "wsDesc": row_after.get("wsDesc")}})
    except SkillError as exc:
        summary.update({"ok": False, "error": str(exc)})
        if new_wid:
            try:
                _do_off(new_wid)
            except SkillError:
                pass
        _emit(summary)
        return 1
    _emit(summary)
    return 0


# ================================================================ SCM 修改
def act_ws_desc(a):
    if not a.confirm:
        _emit({"ok": True, "action": "ws-desc", "dry_run": True, "wholesaleId": a.id,
               "wsDesc": a.desc, "hint": "加 --confirm 才写入"})
        return 0
    _call("/scm-goods/wholesaleDrug/editWsDesc",
          {"id": int(a.id), "wsDesc": a.desc})
    row = _src_row(a.id)
    got = row.get("wsDesc")
    _emit({"ok": got == a.desc, "action": "ws-desc", "wholesaleId": a.id,
           "wsDesc": got, "expected": a.desc})
    return 0 if got == a.desc else 1


def act_ws_stock(a):
    if a.qty is not None and a.qty < 0:
        raise SkillError("PARAM_INVALID", "--qty 不能为负数", hint="库存数量需 >= 0")
    row = _src_row(a.id)
    wi, _, _, _ = _template(a.id, a.type or row.get("wholesaleType") or 1)
    drug_id = row.get("drugId") or wi.get("drugId")
    body = {"drugId": drug_id, "id": int(a.id),
            "wholesaleType": int(a.type or row.get("wholesaleType") or 1),
            "manualSyncStock": 0 if a.sync == "on" else 1}
    if a.qty is not None:
        body["drugStock"] = int(a.qty)
    if not a.confirm:
        _emit({"ok": True, "action": "ws-stock", "dry_run": True, "payload": body,
               "current": {"stockAvailable": row.get("stockAvailable"),
                           "manualSyncStock": row.get("manualSyncStock")},
               "hint": "加 --confirm 才写入"})
        return 0
    _call("/scm-goods/wholesaleDrug/editStock2", body)
    after = _src_row(a.id)
    _emit({"ok": True, "action": "ws-stock", "wholesaleId": a.id,
           "stockAvailable": after.get("stockAvailable"),
           "manualSyncStock": after.get("manualSyncStock")})
    return 0


def act_ws_ladder(a):
    """阶梯价：--get 读；--min-qty/--price 写（最多 2 档）。"""
    path_get = "/scm-promotion/admin/singleCoupon/getLadderPriceInfo"
    path_set = "/scm-promotion/admin/singleCoupon/addLadderPrice"
    if a.get:
        r = _call(path_get, {"id": int(a.id)})
        _emit({"ok": True, "action": "ws-ladder", "mode": "read",
               "wholesaleId": a.id, "data": r.get("data")})
        return 0
    if a.min_qty is None or a.price is None:
        raise SkillError("PARAM_INVALID", "写入阶梯价需 --min-qty 与 --price（删除用 --remove）")
    row = _src_row(a.id)
    begin = row.get("beginDate") or _ts(time.strftime("%Y-%m-%d 00:00:01"))
    end = row.get("endDate") or _ts(time.strftime("%Y-%m-%d 23:59:59"))
    body = {"wholesaleId": int(a.id), "disType": 1,
            "add": 0 if a.remove else 1,
            "minCnt": int(a.min_qty), "disPrice": float(a.price),
            "limitArea": 0, "areaCodes": [],
            "tagDesc": a.tag or ("满%d盒%s元" % (a.min_qty, a.price)),
            "beginDate": int(begin), "endDate": int(end),
            "tagPic": "", "tagPicAudit": ""}
    if a.min_qty2 is not None and a.price2 is not None:
        body.update({"minCnt2": int(a.min_qty2), "disPrice2": float(a.price2)})
    if not a.confirm:
        _emit({"ok": True, "action": "ws-ladder", "dry_run": True,
               "payload": {k: body[k] for k in ("wholesaleId", "add", "minCnt",
                                                "disPrice", "minCnt2", "disPrice2",
                                                "tagDesc") if k in body},
               "hint": "加 --confirm 才写入"})
        return 0
    try:
        _call("/scm-goods/drug/checkPriceAct",
              {"wholesaleId": int(a.id), "disPrice": float(a.price),
               "disPrice2": float(a.price2) if a.price2 is not None else 0,
               "from": "addWsDisTag", "ifDisWs": 1})
    except SkillError as exc:
        _emit({"ok": False, "action": "ws-ladder", "stage": "checkPriceAct",
               "error": str(exc)[:160]})
        return 1
    _call(path_set, body)
    r = _call(path_get, {"id": int(a.id)})
    _emit({"ok": True, "action": "ws-ladder", "wholesaleId": a.id,
           "verify": r.get("data")})
    return 0


def act_reprice(a):
    """改价：默认只出两个候选；--plan ladder|rebuild 才执行。"""
    row = _src_row(a.id)
    cur = {"unitPrice": row.get("unitPrice"), "unitPrice9": row.get("unitPrice9"),
           "wholesaleType": row.get("wholesaleType")}
    if not a.plan:
        _emit({
            "ok": True, "action": "reprice", "need_choice": True,
            "wholesaleId": a.id, "current": cur,
            "target": {"price": a.price, "minQty": a.min_qty},
            "options": [
                {"plan": "ladder",
                 "title": "方案一：设置单品阶梯价（原价不变，满 %s 件享 %s）" % (a.min_qty, a.price),
                 "pros": "链接/二维码不变、秒级生效、不动原活动",
                 "cons": "原价仍可单买；最多 2 档；仅自营；会显示促销标签",
                 "next": "python scm.py scene ljgl reprice --id %s --price %s --min-qty %s --plan ladder --confirm"
                         % (a.id, a.price, a.min_qty)},
                {"plan": "rebuild",
                 "title": "方案二：重建链接（下架旧的，按新价复制一条）",
                 "pros": "原价即新价、链接干净",
                 "cons": "活动ID/链接/二维码都会变；旧链接下架；约 1~2 分钟",
                 "next": "python scm.py scene ljgl reprice --id %s --price %s --plan rebuild --confirm"
                         % (a.id, a.price)},
            ],
            "hint": "选一个 plan 再加 --confirm 执行；不选则不改动任何数据",
        })
        return 0
    if a.price is None:
        raise SkillError("PARAM_INVALID", "需要 --price")
    if a.plan == "ladder":
        if a.min_qty is None:
            raise SkillError("PARAM_INVALID", "ladder 需 --min-qty")
        ns = argparse.Namespace(id=a.id, get=False, min_qty=a.min_qty,
                                price=a.price, min_qty2=None, price2=None,
                                tag=None, remove=False, confirm=a.confirm)
        return act_ws_ladder(ns)
    # rebuild：下架旧 → 以旧为源复制 → 库存/备注
    if not a.confirm:
        _emit({"ok": True, "action": "reprice", "plan": "rebuild", "dry_run": True,
               "wholesaleId": a.id, "price": a.price,
               "hint": "加 --confirm 执行（会下架旧链接并新建一条）"})
        return 0
    wi, di, pi, price_types = _template(a.id, cur["wholesaleType"] or 1)
    if not wi:
        raise SkillError("BUSINESS_ERROR", "取旧活动模板失败")
    group_id = row.get("restrictGroupId") or 0
    area_id = row.get("areaGroupId")
    begin = "%s 00:00:01" % time.strftime("%Y-%m-%d")
    end = "%s 23:59:59" % time.strftime("%Y-%m-%d")
    payload = build_payload(wi, di, pi, row, price_types, group_id=group_id,
                            area_id=area_id, price=a.price, stock=None,
                            limit=None, begin=begin, end=end)
    off_ok, via, _ = _do_off(a.id)
    r = _call("/scm-goods/wholesaleDrug/addWholesale", payload, ex="fixedPriceShelf")
    inner = r.get("data") or {}
    if isinstance(inner.get("data"), dict):
        inner = inner["data"]
    new_wid = inner.get("wholesaleId")
    if not new_wid:
        _emit({"ok": False, "action": "reprice", "plan": "rebuild",
               "off_via": via, "detail": str(r)[:200]})
        return 1
    v = _call("/scm-goods/wholesaleDrug/getWholesale",
              {"wholesaleId": int(new_wid), "wholesaleType": cur["wholesaleType"] or 1,
               "ctype": 1, "copyId": 1, "mode": "edit"})
    vi = (v.get("data") or {}).get("wholesaleInfo") or {}
    _record({"ts": _now(), "replaced": a.id, "new": new_wid,
             "price": a.price, "status": "on_sale", "link": LINK_TPL % new_wid})
    _emit({"ok": True, "action": "reprice", "plan": "rebuild",
           "replaced": a.id, "new_wholesaleId": new_wid, "off_via": via,
           "link": LINK_TPL % new_wid,
           "verify": {k: vi.get(k) for k in ("unitPrice", "unitPrice1",
                                             "unitPrice2", "unitPrice7",
                                             "unitPrice8", "unitPrice9",
                                             "status")}})
    return 0


def act_group_create(a):
    name = a.name
    if not name and a.store:
        sid, _ = _resolve_store(a.store)
        name = GROUP_NAME_TPL % sid
    if not name:
        raise SkillError("PARAM_INVALID", "需要 --name 或 --store")
    desc = a.desc or GROUP_DESC_TPL % time.strftime("%Y%m%d")
    if not a.confirm:
        _emit({"ok": True, "action": "group-create", "dry_run": True,
               "groupName": name, "groupDesc": desc, "hint": "加 --confirm 才创建"})
        return 0
    _call("/scm-setting/saleControl/editStoreGroup",
          {"storeGroupId": None, "groupName": name, "groupDesc": desc},
          ex="ControlDrugstoreGroup")
    r = _call("/scm-setting/saleControl/storeGroup",
              {"pageNo": 1, "pageSize": 10, "groupName": name},
              ex="ControlDrugstoreGroup")
    for x in (r.get("data") or {}).get("results") or []:
        if x.get("groupName") == name:
            _emit({"ok": True, "action": "group-create",
                   "group": x.get("storeGroupId"), "groupName": name})
            return 0
    _emit({"ok": False, "action": "group-create", "groupName": name,
           "hint": "创建后回查不到，检查重名/上限"})
    return 1


def act_group_update(a):
    meta = _group_meta(a.group)
    if not meta:
        _emit({"ok": False, "action": "group-update", "group": a.group,
               "hint": "组不存在或无权访问"})
        return 2
    name = a.name or meta.get("groupName")
    desc = a.desc if a.desc is not None else meta.get("groupDesc")
    if not a.confirm:
        _emit({"ok": True, "action": "group-update", "dry_run": True, "group": a.group,
               "from": {"groupName": meta.get("groupName"),
                        "groupDesc": meta.get("groupDesc")},
               "to": {"groupName": name, "groupDesc": desc},
               "hint": "加 --confirm 才修改"})
        return 0
    _call("/scm-setting/saleControl/editStoreGroup",
          {"storeGroupId": int(a.group), "groupName": name, "groupDesc": desc},
          ex="ControlDrugstoreGroup")
    _emit({"ok": True, "action": "group-update", "group": a.group,
           "groupName": name, "groupDesc": desc})
    return 0


def act_group_del(a):
    meta = _group_meta(a.group)
    if not meta:
        _emit({"ok": False, "action": "group-del", "group": a.group,
               "hint": "组不存在或无权访问（未做任何删除）"})
        return 2
    info = {"group": a.group, "groupName": meta.get("groupName"),
            "groupDesc": meta.get("groupDesc"), "storeNum": meta.get("storeNum"),
            "is_temporary_group": _is_temporary_group(meta)}
    if not info["is_temporary_group"] and not a.force:
        _emit({"ok": False, "action": "group-del", **info,
               "hint": "该组不符合「<药店id>临时控销 / agent临时控销！yyyyMMdd后可删除。」格式，"
                       "疑似非本场景创建；确认无误再加 --force"})
        return 2
    ref = _call("/scm-setting/saleControl/wsCountByRG",
                {"groupIds": [int(a.group)]}, ex="ControlDrugstoreGroup")
    used = ref.get("data")
    if used and not a.force:
        _emit({"ok": False, "action": "group-del", **info,
               "referenced_by_wholesales": used,
               "hint": "该组仍被 %s 个活动引用（含已下架）；确认活动都已下架后加 --force" % used})
        return 2
    if not a.confirm:
        _emit({"ok": True, "action": "group-del", "dry_run": True, **info,
               "referenced_by_wholesales": used, "hint": "加 --confirm 才删除（不可逆）"})
        return 0
    _call("/scm-setting/saleControl/delGroups",
          {"groupIds": [int(a.group)]}, ex="ControlDrugstoreGroup")
    _emit({"ok": True, "action": "group-del", **info,
           "referenced_by_wholesales": used, "deleted": True})
    return 0


def act_group_add(a):
    sid, row = _resolve_store(a.store)
    if not a.confirm:
        _emit({"ok": True, "action": "group-add", "dry_run": True, "group": a.group,
               "branchId": sid, "storetitle": row.get("storeTitle"),
               "hint": "加 --confirm 才执行"})
        return 0
    r = _call("/scm-setting/saleControl/addStoreBatch",
              {"batchType": 0, "storeGroupId": int(a.group),
               "branchIdList": [int(sid)]}, ex="ControlDrugstoreGroup")
    d = r.get("data") or {}
    _emit({"ok": True, "action": "group-add", "group": a.group, "branchId": sid,
           "rightCount": d.get("rightCount"), "errorCount": d.get("errorCount")})
    return 0


def act_group_remove(a):
    sid, row = _resolve_store(a.store)
    if not a.confirm:
        _emit({"ok": True, "action": "group-remove", "dry_run": True, "group": a.group,
               "branchId": sid, "storetitle": row.get("storeTitle"),
               "hint": "加 --confirm 才执行"})
        return 0
    _call("/scm-setting/saleControl/delStoreBatch",
          {"storeGroupId": int(a.group), "branchIdList": [int(sid)]},
          ex="ControlDrugstoreGroup")
    _emit({"ok": True, "action": "group-remove", "group": a.group, "branchId": sid})
    return 0


def act_group_add_nostore(a):
    r = _call("/scm-setting/saleControl/getNoOrderStore",
              {"storeGroupId": int(a.group), "fullName": a.full_name},
              ex="ControlDrugstoreGroup")
    rows = r.get("data") or []
    hit = [x for x in rows
           if str(x.get("fullName")) == a.full_name or str(x.get("drugstoreBranchId")) == str(a.store_id)]
    if not hit:
        _emit({"ok": False, "action": "group-add-nostore", "group": a.group,
               "candidates": rows[:10],
               "hint": "未匹配到未下单药店；用 --full-name 传系统完整名称"})
        return 2
    target = hit[0]
    if not a.confirm:
        _emit({"ok": True, "action": "group-add-nostore", "dry_run": True,
               "group": a.group, "target": target, "hint": "加 --confirm 才执行"})
        return 0
    _call("/scm-setting/saleControl/addNoOrderStore",
          {"storeGroupId": int(a.group), "fullName": target.get("fullName"),
           "drugstoreBranchId": target.get("drugstoreBranchId")},
          ex="ControlDrugstoreGroup")
    _emit({"ok": True, "action": "group-add-nostore", "group": a.group,
           "branchId": target.get("drugstoreBranchId"),
           "fullName": target.get("fullName")})
    return 0


# ================================================================ PMS 修改
def act_pms_limit(a):
    pid = _pms_provider_id()
    row = _src_row(a.id)
    body = {"wholesaleId": int(a.id), "providerId": pid,
            "minQty": int(a.min_qty if a.min_qty is not None else (row.get("minAmount") or 1)),
            "step": int(a.step if a.step is not None else (row.get("step") or 1)),
            "maxAmountPerStore": int(a.max_per_store if a.max_per_store is not None
                                     else (row.get("maxAmount") or 0)),
            "calculatePeriod": int(a.period if a.period is not None else 0)}
    if not a.confirm:
        _emit({"ok": True, "action": "pms-limit", "dry_run": True,
               "payload": body, "current": {"minAmount": row.get("minAmount"),
                                            "step": row.get("step"),
                                            "maxAmount": row.get("maxAmount")},
               "hint": "加 --confirm 才写入（minQty/step 必带）"})
        return 0
    r = _call(PMS + "updateGoodsSaleLimitConf/v27280", body, host="pms")
    _emit({"ok": (r.get("data") or {}).get("result") == 1, "action": "pms-limit",
           "wholesaleId": a.id, "result": r.get("data")})
    return 0


def act_pms_area(a):
    pid = _pms_provider_id()
    row = _src_row(a.id)
    wtype = getattr(a, "type", None) or row.get("wholesaleType") or 1
    area_group = a.area_group if a.area_group is not None else row.get("areaGroupId")
    storetype = a.storetype_group if a.storetype_group is not None else row.get("storetypeGpId")
    if not area_group or not storetype:
        # wsList 行可能不返回 storetypeGpId，回退 providerInfo（文档 §3.6 前置要求，不盲发）
        try:
            _wi, _di, pi, _pt = _template(a.id, wtype)
            area_group = area_group or pi.get("areaGroupId")
            storetype = storetype or pi.get("storetypeGpId")
        except SkillError:
            pass
    if a.area_group is not None or a.storetype_group is not None or a.restrict is not None:
        if not area_group or not storetype:
            raise SkillError("PARAM_INVALID",
                             "定向写入要求活动已有商圈与供货对象（缺则先补），不盲发",
                             details={"areaGroupId": area_group,
                                      "storetypeGroupId": storetype})
    body = {"wholesaleId": int(a.id), "providerId": pid,
            "areaGroupId": int(area_group or 0),
            "storetypeGroupId": int(storetype or 0)}
    if a.restrict is not None:
        body["isRestrict"] = int(a.restrict)
        body["restrictId"] = int(a.restrict_id or 0) if a.restrict else 0
    if not a.confirm:
        _emit({"ok": True, "action": "pms-area", "dry_run": True, "payload": body,
               "hint": "加 --confirm 才写入；isRestrict: 0否/1控销/2禁销"})
        return 0
    r = _call(PMS + "updateGoodsSaleAreaConf/v27280", body, host="pms")
    _emit({"ok": (r.get("data") or {}).get("result") == 1, "action": "pms-area",
           "wholesaleId": a.id, "result": r.get("data")})
    return 0


def act_pms_time(a):
    if _ts(a.end) < _ts(a.begin):
        raise SkillError("PARAM_INVALID", "endDate 不得早于 beginDate",
                         hint="检查 --begin / --end")
    wtype = int(a.type or (_src_row(a.id).get("wholesaleType") or 1))
    body = {"wholeSaleId": int(a.id), "wholeSaleType": wtype,
            "beginDate": a.begin, "endDate": a.end}
    if not a.confirm:
        _emit({"ok": True, "action": "pms-time", "dry_run": True, "payload": body,
               "hint": "加 --confirm 才写入（yyyy-MM-dd HH:mm:ss）"})
        return 0
    r = _call(PMS + "updateYkjWsActivityTime/v27280", body, host="pms")
    _emit({"ok": (r.get("data") or {}).get("result") == 1, "action": "pms-time",
           "wholesaleId": a.id, "result": r.get("data")})
    return 0


# ================================================================ 生命周期
def _do_off(wid):
    try:
        _call("/scm-goods/WholesaleDrugES2/pause",
              {"id": int(wid), "pauseNote": "agent off"})
        return True, "scm.pause", ""
    except SkillError as exc:
        err = str(exc)
    wtype = _src_row(wid).get("wholesaleType") or 1
    r = _call(PMS + "updateYkjWholeSaleStatus/v27280",
              {"wholeSaleId": int(wid), "wholeSaleType": int(wtype), "status": 1},
              host="pms")
    if (r.get("data") or {}).get("result") == 1:
        return True, "pms.w1", err
    return False, "", err


def act_off(a):
    if not a.confirm:
        _emit({"ok": True, "action": "off", "dry_run": True, "wholesaleId": a.id,
               "hint": "加 --confirm 才执行下架"})
        return 0
    ok, via, err = _do_off(a.id)
    _emit({"ok": ok, "action": "off", "via": via, "wholesaleId": a.id,
           "scm_error": (err or "")[:120]})
    if ok:
        _record({"ts": _now(), "new": a.id, "status": "off", "via": via})
    return 0 if ok else 1


def act_restart(a):
    if not a.confirm:
        _emit({"ok": True, "action": "restart", "dry_run": True,
               "wholesaleId": a.id, "hint": "加 --confirm 才执行重上架"})
        return 0
    err = ""
    try:
        _call("/scm-goods/WholesaleDrugES2/batchRestart",
              {"handleList": [int(a.id)], "start": 1}, ex="goodsOnShelves")
        _emit({"ok": True, "action": "restart", "via": "scm.batchRestart",
               "wholesaleId": a.id})
        return 0
    except SkillError as exc:
        err = str(exc)
    wtype = _src_row(a.id).get("wholesaleType") or 1
    r = _call(PMS + "updateYkjWholeSaleStatus/v27280",
              {"wholeSaleId": int(a.id), "wholeSaleType": int(wtype), "status": 2},
              host="pms")
    ok = (r.get("data") or {}).get("result") == 1
    _emit({"ok": ok, "action": "restart", "via": "pms.w1" if ok else "",
           "wholesaleId": a.id, "scm_error": err[:120]})
    return 0 if ok else 1


def act_end(a):
    if not a.confirm:
        _emit({"ok": True, "action": "end", "dry_run": True, "wholesaleId": a.id,
               "hint": "加 --confirm 才执行（内部先下架再结束）"})
        return 0
    off_ok, via, _ = _do_off(a.id)
    r = _call("/scm-goods/WholesaleDrugES2/batchEnd",
              {"handleList": [int(a.id)]}, ex="goodsOffShelves")
    d = r.get("data") or {}
    done = "已成功结束活动1个" in str(d.get("info") or "")
    _emit({"ok": done, "action": "end", "wholesaleId": a.id,
           "off_via": via if off_ok else "", "info": d.get("info"),
           "error_reason": d.get("errorReasonList"),
           "hint": "" if done else "若为自动运营/短期链接，SCM 无结束出口 → 网页端「已下架」页操作"})
    return 0 if done else 1


def act_schedule(a):
    at = a.at.strip().replace(" ", "T")
    if len(at) != 16:
        raise SkillError("PARAM_INVALID", "--at 需 'YYYY-MM-DD HH:MM'")
    cmd = "python scm.py scene ljgl off --id %s --confirm" % a.id
    prompt = ("执行下架：%s ；完成后复验该活动 status=4（已下架），"
              "并把结果追加到台账 link-records.jsonl；"
              "若 SCM pause 被拒（自动运营/短期链接），脚本会自动降级 PMS W1，无需人工干预。"
              % cmd)
    _emit({"ok": True, "action": "schedule", "wholesaleId": a.id, "at": a.at,
           "scheduledAt": at,
           "how": "由 Agent 调用 IDE automation_update（scheduleType=once），技能内不起常驻进程",
           "automation": {"mode": "suggested create",
                          "name": "下架订单链接 %s" % a.id,
                          "scheduleType": "once", "scheduledAt": at,
                          "status": "ACTIVE", "cwds": str(_ROOT),
                          "prompt": prompt},
           "note": "短期链接 PMS W2 不可切运营模式；到点若 SCM pause 被拒会降级 PMS W1。IDE 需在线。"})
    _record({"ts": _now(), "new": a.id, "status": "scheduled", "at": a.at})
    return 0


# ================================================================ 辅助
def act_qr(a):
    try:
        import qrcode
    except ImportError:
        raise SkillError("DEPENDENCY_MISSING", "缺少 qrcode 依赖", hint="pip install qrcode")
    link = LINK_TPL % a.id
    out = Path(a.out).expanduser() if a.out else \
        Path.home() / "Desktop" / ("orderlink_%s.png" % a.id)
    out.parent.mkdir(parents=True, exist_ok=True)
    qrcode.make(link).save(str(out))
    _emit({"ok": True, "action": "qr", "wholesaleId": a.id, "link": link,
           "png": str(out), "bytes": out.stat().st_size})
    return 0


# ================================================================ CLI
def build_parser():
    p = argparse.ArgumentParser(
        prog="scm.py scene ljgl",
        description="链接管理：查询 / 创建 / SCM修改 / PMS修改 / 生命周期 / 辅助")
    sub = p.add_subparsers(dest="action")

    # ---- 查询
    s = sub.add_parser("store", help="【查询】药店全部信息")
    s.add_argument("--keyword", required=True, help="药店ID/名称/编码")
    s.set_defaults(func=act_store)

    f = sub.add_parser("find", help="【查询】商品活动候选（一口价+特价）")
    f.add_argument("--store", help="药店名称/编码/ID")
    f.add_argument("--drug", help="商品名称/编码/药师帮id/国药准字")
    f.add_argument("--include-self", action="store_true",
                   help="包含本场景自建活动（默认过滤）")
    f.set_defaults(func=act_find)

    gl = sub.add_parser("group-list", help="【查询】控销组内药店")
    gl.add_argument("--group", type=int, required=True)
    gl.set_defaults(func=act_group_list)

    gn = sub.add_parser("group-nostore", help="【查询】搜索未下单药店")
    gn.add_argument("--group", type=int, required=True)
    gn.add_argument("--name", help="药店名称关键字")
    gn.set_defaults(func=act_group_nostore)

    pf = sub.add_parser("pms-find", help="【查询】PMS 按活动id搜一口价/特价")
    pf.add_argument("--id", type=int, help="活动ID")
    pf.add_argument("--code", help="商品编码")
    pf.add_argument("--type", type=int, choices=[1, 4], default=1,
                    help="1=一口价 4=特价")
    pf.set_defaults(func=act_pms_find)

    l = sub.add_parser("list", help="【查询】台账最近记录")
    l.add_argument("--limit", type=int, default=20)
    l.set_defaults(func=act_list)

    # ---- 创建
    c = sub.add_parser("create", help="【创建】建组→加店→复制→库存→备注→链接")
    c.add_argument("--store", required=True)
    c.add_argument("--drug", required=True)
    c.add_argument("--source", type=int, help="源活动ID（候选不唯一时必填）")
    c.add_argument("--price", type=float, help="目标售价；省略保持源价")
    c.add_argument("--stock", type=int, help="库存数量；省略保持源设置")
    c.add_argument("--limit", type=int, help="单店上限；省略同 stock")
    c.add_argument("--date", help="活动日期 YYYY-MM-DD，默认当天")
    c.add_argument("--desc", help="活动备注；省略默认模板，传空串清空")
    c.add_argument("--desc-date", help="组描述里的可删除日期")
    c.add_argument("--group-id", type=int, help="复用已有控销组ID")
    c.add_argument("--include-self", action="store_true",
                   help="候选包含本场景自建活动（默认过滤）")
    c.add_argument("--confirm", action="store_true")
    c.set_defaults(func=act_create)

    # ---- SCM 修改
    wd = sub.add_parser("ws-desc", help="【SCM改】活动备注")
    wd.add_argument("--id", type=int, required=True)
    wd.add_argument("--desc", required=True, help="新备注；空串清空")
    wd.add_argument("--confirm", action="store_true")
    wd.set_defaults(func=act_ws_desc)

    ws = sub.add_parser("ws-stock", help="【SCM改】库存同步开关/数量")
    ws.add_argument("--id", type=int, required=True)
    ws.add_argument("--sync", choices=["on", "off"], default="off",
                    help="on=同步库存 off=不同步（默认）")
    ws.add_argument("--qty", type=int, help="不同步时的库存数量")
    ws.add_argument("--type", type=int, choices=[1, 4], help="活动类型，缺省查源")
    ws.add_argument("--confirm", action="store_true")
    ws.set_defaults(func=act_ws_stock)

    wl = sub.add_parser("ws-ladder", help="【SCM改】单品阶梯价（最多2档）")
    wl.add_argument("--id", type=int, required=True)
    wl.add_argument("--get", action="store_true", help="只读当前阶梯价")
    wl.add_argument("--min-qty", type=int, help="第1档起量")
    wl.add_argument("--price", type=float, help="第1档价格")
    wl.add_argument("--min-qty2", type=int, help="第2档起量")
    wl.add_argument("--price2", type=float, help="第2档价格")
    wl.add_argument("--tag", help="促销标签文案")
    wl.add_argument("--remove", action="store_true", help="删除阶梯价")
    wl.add_argument("--confirm", action="store_true")
    wl.set_defaults(func=act_ws_ladder)

    rp = sub.add_parser("reprice", help="【SCM改】改价（先出 ladder/rebuild 两方案）")
    rp.add_argument("--id", type=int, required=True)
    rp.add_argument("--price", type=float)
    rp.add_argument("--min-qty", type=int, help="ladder 方案的起量")
    rp.add_argument("--plan", choices=["ladder", "rebuild"],
                    help="选择方案后才执行")
    rp.add_argument("--confirm", action="store_true")
    rp.set_defaults(func=act_reprice)

    gc = sub.add_parser("group-create", help="【SCM改】新建控销组")
    gc.add_argument("--name", help="组名；省略按 --store 生成")
    gc.add_argument("--desc", help="组描述")
    gc.add_argument("--store", help="药店名称/编码/ID")
    gc.add_argument("--confirm", action="store_true")
    gc.set_defaults(func=act_group_create)

    gu = sub.add_parser("group-update", help="【SCM改】修改控销组名称/描述")
    gu.add_argument("--group", type=int, required=True)
    gu.add_argument("--name", help="新组名")
    gu.add_argument("--desc", help="新描述（空串清空）")
    gu.add_argument("--confirm", action="store_true")
    gu.set_defaults(func=act_group_update)

    gd = sub.add_parser("group-del", help="【SCM改】删除控销组（不可逆）")
    gd.add_argument("--group", type=int, required=True)
    gd.add_argument("--force", action="store_true")
    gd.add_argument("--confirm", action="store_true")
    gd.set_defaults(func=act_group_del)

    ga = sub.add_parser("group-add", help="【SCM改】药店加入控销组")
    ga.add_argument("--group", type=int, required=True)
    ga.add_argument("--store", required=True)
    ga.add_argument("--confirm", action="store_true")
    ga.set_defaults(func=act_group_add)

    gr = sub.add_parser("group-remove", help="【SCM改】药店移出控销组")
    gr.add_argument("--group", type=int, required=True)
    gr.add_argument("--store", required=True)
    gr.add_argument("--confirm", action="store_true")
    gr.set_defaults(func=act_group_remove)

    gan = sub.add_parser("group-add-nostore", help="【SCM改】添加未下单药店")
    gan.add_argument("--group", type=int, required=True)
    gan.add_argument("--full-name", required=True, help="药店系统完整名称")
    gan.add_argument("--store-id", help="药店ID（可辅助匹配）")
    gan.add_argument("--confirm", action="store_true")
    gan.set_defaults(func=act_group_add_nostore)

    # ---- PMS 修改
    pl = sub.add_parser("pms-limit", help="【PMS改】起订量/倍数/单店上限/刷新周期")
    pl.add_argument("--id", type=int, required=True)
    pl.add_argument("--min-qty", type=int, help="起订量")
    pl.add_argument("--step", type=int, help="购买倍数")
    pl.add_argument("--max-per-store", type=int, help="单店上限，0=不限")
    pl.add_argument("--period", type=int, choices=[0, 1, 2, 3, 4],
                    help="刷新周期 0活动期内/1每笔/2每天/3每周/4每月")
    pl.add_argument("--confirm", action="store_true")
    pl.set_defaults(func=act_pms_limit)

    pa = sub.add_parser("pms-area", help="【PMS改】商圈/供货对象/控销")
    pa.add_argument("--id", type=int, required=True)
    pa.add_argument("--area-group", type=int, help="商圈ID")
    pa.add_argument("--storetype-group", type=int, help="供货对象组ID")
    pa.add_argument("--restrict", type=int, choices=[0, 1, 2],
                    help="0否/1控销/2禁销")
    pa.add_argument("--restrict-id", type=int, help="控销组ID（restrict!=0 时）")
    pa.add_argument("--confirm", action="store_true")
    pa.set_defaults(func=act_pms_area)

    pt = sub.add_parser("pms-time", help="【PMS改】活动时间")
    pt.add_argument("--id", type=int, required=True)
    pt.add_argument("--begin", required=True, help="yyyy-MM-dd HH:mm:ss")
    pt.add_argument("--end", required=True, help="yyyy-MM-dd HH:mm:ss")
    pt.add_argument("--type", type=int, choices=[1, 4])
    pt.add_argument("--confirm", action="store_true")
    pt.set_defaults(func=act_pms_time)

    # ---- 生命周期
    o = sub.add_parser("off", help="【生命周期】下架（SCM→PMS W1 降级）")
    o.add_argument("--id", type=int, required=True)
    o.add_argument("--confirm", action="store_true")
    o.set_defaults(func=act_off)

    rs = sub.add_parser("restart", help="【生命周期】重上架")
    rs.add_argument("--id", type=int, required=True)
    rs.add_argument("--confirm", action="store_true")
    rs.set_defaults(func=act_restart)

    en = sub.add_parser("end", help="【生命周期】结束活动（内部先下架）")
    en.add_argument("--id", type=int, required=True)
    en.add_argument("--confirm", action="store_true")
    en.set_defaults(func=act_end)

    sc = sub.add_parser("schedule", help="【生命周期】定时下架（输出 IDE 自动化参数）")
    sc.add_argument("--id", type=int, required=True)
    sc.add_argument("--at", required=True, help="YYYY-MM-DD HH:MM")
    sc.set_defaults(func=act_schedule)

    # ---- 辅助
    q = sub.add_parser("qr", help="【辅助】生成链接二维码 PNG")
    q.add_argument("--id", type=int, required=True)
    q.add_argument("--out", help="输出路径，默认桌面")
    q.set_defaults(func=act_qr)
    return p


def main(argv):
    global _ACCOUNT
    argv = list(argv or [])
    if "--account" in argv:
        i = argv.index("--account")
        if i + 1 < len(argv):
            _ACCOUNT = argv[i + 1]
            del argv[i:i + 2]
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    try:
        return int(args.func(args) or 0)
    except SkillError as exc:
        _emit({"ok": False, "error": getattr(exc, "code", "ERROR"),
               "message": str(exc), "hint": getattr(exc, "hint", "")})
        return 1
    except Exception as exc:  # noqa: BLE001
        _emit({"ok": False, "error": "UNEXPECTED", "message": str(exc)[:300]})
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
