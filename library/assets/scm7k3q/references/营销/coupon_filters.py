# -*- coding: utf-8 -*-
"""优惠券系统前端过滤规则 · 可执行版（从源码1:1转写，供Agent直接调用）

用法：
  from coupon_filters import *
  coupon_status(coupon) / filter_stores(stores, keyword, start, end, mode, selected_ids)
  is_id_search(keyword) / parse_store_subtypes(raw) / is_high_discount(coupon)
  is_share_time_expired(text, now=None) / grab_range(coupon, now=None) / sort_coupons(list)
  make_coupon_name(type, min_pay, discount/price, suffix=None) / extract_suffix(user_text) / make_activity_name(coupon_name, user_name)
"""
from __future__ import annotations
import re
from datetime import datetime, timedelta, date

# ---------- 通用状态 ----------
def coupon_status(coupon: dict, now: datetime | None = None) -> dict:
    """返回 {'text': '有效|已过期|已作废', 'valid': bool, 'color', 'icon'}。源码 gongju.js:146-182。"""
    now = now or datetime.now()
    if str(coupon.get("couponStatus")) != "1":
        return {"text": "已作废", "valid": False, "color": "#ef4444", "icon": "🔴"}
    end = coupon.get("endTime")
    if end:
        try:
            e = datetime.fromisoformat(str(end).replace(" ", "T"))
            if now > e:
                return {"text": "已过期", "valid": False, "color": "#f59e0b", "icon": "🕚"}
        except (ValueError, TypeError):
            pass
    sharing = bool(coupon.get("isSharing"))
    return {"text": "有效", "valid": True, "color": "#10b981",
            "icon": "🌎️" if sharing else "💡"}

def sort_coupons(coupons: list[dict], now: datetime | None = None) -> list[dict]:
    """状态升序(有效0/过期1/作废2/未知9) + 同状态 ctime 降序。源码 app.js:100-106。"""
    order = {"有效": 0, "已过期": 1, "已作废": 2}
    def key(c):
        s = order.get(coupon_status(c, now)["text"], 9)
        try: t = datetime.fromisoformat(str(c.get("ctime") or 0).replace(" ", "T"))
        except Exception: t = datetime.min
        return (s, -t.timestamp())
    return sorted(coupons, key=key)

# ---------- 搜索 ----------
def is_id_search(keyword: str) -> bool:
    """恰好7位数字→ID搜索，否则名称。源码 gongju.js:38-39。"""
    return bool(re.fullmatch(r"\d{7}", (keyword or "").strip()))

def search_payload(keyword: str, credentials: dict, page_no: int = 1, page_size: int = 9999) -> dict:
    """构造 list 查询体。源码 gongju.js:41-53。"""
    kw = (keyword or "").strip()
    by_id = is_id_search(kw)
    return {"credentials": credentials, "action": "list", "pageNo": page_no, "pageSize": page_size,
            "name": "" if by_id else kw, "id": kw if by_id else "",
            "type": "", "is_valid": "", "valid_type": "", "ctime": "", "chooseDay": ""}

# ---------- 作废药店过滤 ----------
def _dt(value: str | None, is_end: bool) -> datetime | None:
    """输入框日期→时间戳：开始补T00:00:00，结束补T23:59:59。源码 zf/yewu.js:312-318。"""
    if not value:
        return None
    try:
        return datetime.fromisoformat(f"{value}{'T23:59:59' if is_end else 'T00:00:00'}")
    except ValueError:
        return None

def _store_ctime(store: dict) -> datetime | None:
    """ctimeStr || createTime，空格替换T。源码 zf/yewu.js:320-325。"""
    v = store.get("ctimeStr") or store.get("createTime") or ""
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v).replace(" ", "T", 1))
    except ValueError:
        return None

def normalize_create_range(start: str | None, end: str | None) -> tuple[str | None, str | None]:
    """开始>结束→结束=开始。源码 zf/yewu.js:303-310。"""
    if start and end and start > end:
        end = start
    return start, end

def filter_stores(stores: list[dict], keyword: str = "", start: str | None = None,
                  end: str | None = None, mode: str = "coupon", selected_ids=None) -> list[dict]:
    """药店列表过滤。源码 zf/yewu.js:273-301。keyword 子串匹配9字段(小写)，时间闭区间。"""
    start, end = normalize_create_range(start, end)
    st, et = _dt(start, False), _dt(end, True)
    kw = (keyword or "").strip().lower()
    out = []
    for s in stores:
        ct = _store_ctime(s)
        if st and (ct is None or ct < st):
            continue
        if et and (ct is None or ct > et):
            continue
        if not kw:
            out.append(s); continue
        fields = [str(s.get("storeId") or ""),
                  (s.get("storeName") or "").lower(), (s.get("storeCode") or "").lower(),
                  (s.get("providerCode") or "").lower(),
                  (s.get("ctimeStr") or s.get("createTime") or "").lower(),
                  (s.get("usertimeStr") or s.get("useTime") or "").lower(),
                  (s.get("orderSn") or "").lower(), str(s.get("couponPay") or "").lower(),
                  (s.get("statusDesc") or "").lower()]
        if any(kw in f for f in fields):
            out.append(s)
    return out

def selectable_store_ids(stores: list[dict], mode: str) -> set:
    """可勾选的 store.id 集合：coupon模式=空；store模式=canCancel为真。源码 zf/yewu.js:204-266。"""
    if mode == "coupon":
        return set()
    return {s["id"] for s in stores if s.get("canCancel")}

# ---------- 领券对象/区域 ----------
def parse_store_subtypes(raw) -> list[int]:
    """拼接串→数组："0163"→[0,1,6,3]；"-1"→[-1]；含-1则整体[-1]。源码 hd/yewu.js:713-748。"""
    valid = {-1, 0, 1, 2, 3, 4, 5, 6, 8}
    def norm(vals):
        seen, out = set(), []
        for v in vals:
            try: n = int(v)
            except (ValueError, TypeError): continue
            if n < -1 or n not in valid or n in seen: continue
            seen.add(n); out.append(n)
        return out
    if isinstance(raw, list): vals = norm([x for x in raw])
    else:
        s = str(raw or "").strip()
        if not s or s == "-1": vals = [-1]
        elif "," in s: vals = norm(s.split(","))
        elif re.fullmatch(r"-?\d+", s):
            vals = [-1] if s.startswith("-") else norm(list(s))
        else: vals = [-1]
    return [-1] if -1 in vals else vals

def area_ids_from_tree(nodes: list[dict], fallback: list[int] | None = None) -> list[int]:
    """区域树节点→选中ID：selected或undetermined 且 assured=true；全未选中时用fallback。源码 hd/yewu.js:404-430。"""
    picked = []
    for n in nodes or []:
        s = n.get("state")
        ok = False
        if isinstance(s, list):
            ok = any(isinstance(x, dict) and x.get("status") in ("selected", "undetermined")
                     and x.get("assured") is True for x in s)
        elif isinstance(s, dict):
            ok = bool(s.get("selected") or s.get("checked") or s.get("undetermined"))
        if ok:
            try: picked.append(int(str(n.get("id", "")).replace("node_", "")))
            except ValueError: pass
    if not picked and fallback:
        picked = [int(x) for x in fallback if str(x).isdigit() and int(x) > 0]
    return picked

# ---------- 高折扣/共享过期/抢券时间 ----------
def _parse_discount_rate(raw) -> float | None:
    """折扣→0-1比率：9.8折→0.98、98→0.98、0.98→0.98、85%→0.85。源码 jy.js parseDiscountRate。"""
    if raw in (None, ""): return None
    s = str(raw)
    m = re.search(r"(\d+(?:\.\d+)?)\s*折", s)
    if m:
        n = float(m.group(1)); return n / 10 if n > 1 else n
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", s)
    if m: return float(m.group(1)) / 100
    try: n = float(raw)
    except (ValueError, TypeError): return None
    if n <= 0: return None
    if n <= 1: return n
    if n <= 10: return n / 10
    if n <= 100: return n / 100
    return None

def infer_coupon_type(coupon: dict) -> int | None:
    """推断券类型。源码 jy.js inferCouponType。"""
    known = {11, 13, 25}
    for k in ("type", "couponType", "couponTypeId", "typeId", "coupon_type", "coupon_type_id"):
        try:
            n = int(coupon.get(k))
            if n in known: return n
        except (ValueError, TypeError): pass
    if coupon.get("discount") is not None: return 13
    if coupon.get("price") is not None and coupon.get("minPay") is not None: return 11
    return None

def is_high_discount(coupon: dict) -> bool:
    """高折扣判定。源码 hd/qq/jy.js:6-9,115-180。"""
    try: min_pay = float(coupon.get("minPay"))
    except (ValueError, TypeError): min_pay = float("nan")
    min_pay_low = min_pay > 0 and min_pay < 2000
    ctype = infer_coupon_type(coupon)
    if ctype == 11:
        try: price = float(coupon.get("price"))
        except (ValueError, TypeError): price = float("nan")
        rate = (min_pay - price) / min_pay if (min_pay > 0 and 0 < price < min_pay) else None
        return min_pay_low or (rate is not None and rate < 0.98)
    if ctype == 13:
        rate = _parse_discount_rate(coupon.get("discount"))
        return min_pay_low or (rate is not None and rate < 0.98)
    return False

def parse_share_time(text: str | None, now: datetime | None = None) -> datetime | None:
    """共享时间解析：YYYY-MM-DD→当天23:59:59。源码 app.js:145-162。"""
    if not text: return None
    s = str(text).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s): s += "T23:59:59"
    elif "T" not in s: s = s.replace(" ", "T", 1)
    try: return datetime.fromisoformat(s)
    except ValueError:
        head = s.split("T")[0]
        try: return datetime.fromisoformat(head + "T23:59:59")
        except ValueError: return None

def is_share_time_expired(text: str | None, now: datetime | None = None) -> bool:
    """到期即清理，无宽限。源码 app.js:164-167。"""
    now = now or datetime.now()
    t = parse_share_time(text)
    return bool(t and t < now)

def grab_range(coupon: dict, now: datetime | None = None) -> tuple[str, str]:
    """抢券时间范围：今天~今天+2，不超过券结束日。源码 ewm.js:798-809。"""
    now = now or datetime.now()
    b = now.date(); e = now.date() + timedelta(days=2)
    cend = str(coupon.get("endTime") or "").split(" ")[0]
    if cend:
        try:
            cd = date.fromisoformat(cend)
            if cd < e: e = cd
        except ValueError: pass
    if e < b: e = b
    return b.isoformat(), e.isoformat()

# ---------- 券名称/活动名称生成（§5.1.1：额度/数值+后缀）----------
_SUFFIX_PATTERNS = [
    r"(\d{1,2}\s*月)",                      # 11月 / 12 月
    r"(双\s*11|双十一|618|双12|双十二)",
    r"(年货节|店庆|周年庆|开学季|会员日|周末)",
    r"(老客户|新客户|新客|老客|会员|VIP" + r")",
]
def extract_suffix(user_text: str) -> str:
    """从用户语义提取名称后缀（时间/节日/人群/用途），无则空串。按出现顺序取首个，≤6字。"""
    if not user_text: return ""
    for pat in _SUFFIX_PATTERNS:
        m = re.search(pat, user_text, re.I)
        if m:
            s = re.sub(r"\s+", "", m.group(1))
            return s[:6]
    return ""

def make_coupon_name(ctype: int, min_pay, value=None, suffix: str | None = None) -> str:
    """按 §5.1.1 生成券名：额度/数值+后缀。
    ctype: 13打折(value=discount如98) / 11满减(value=price如10) / 25免邮(value忽略)。
    suffix=None 时自动从 value 无法提取（调用方先 extract_suffix(user_text) 传入）。
    """
    amt = str(int(float(min_pay))) if min_pay not in (None, "") else "0"
    if int(ctype) == 13:
        num = str(int(float(value))) if value not in (None, "") else "0"
    elif int(ctype) == 11:
        num = str(int(float(value))) if value not in (None, "") else "0"
    else:
        num = "免邮"
    base = f"{amt}/{num}"
    return base + ("+" + suffix[:6] if suffix else "")

def make_activity_name(coupon_name: str, user_activity_name: str | None = None) -> str:
    """抢券活动名：用户指定优先，否则同券名（源码 hd/yewu.js currentCoupon.name）。"""
    return (user_activity_name or "").strip() or coupon_name
