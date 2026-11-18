#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TMS 流量投放 · 自包含 HTTP 发送器（零外部依赖）。

零依赖承诺：仅用 Python 标准库；不 import 父 skill 模块；不读任何父级配置或
凭证文件；不发起登录；token 只由调用方 --token/PMS_TOKEN/--state-file 传入。
双域地址内置于 DOMAINS 常量，不依赖外部配置。
"""
from __future__ import annotations
import argparse, json, os, sys, urllib.request, urllib.error

# 内置双域常量——TMS 三板块只用这两个域，不依赖任何外部配置
DOMAINS = {
    "ley": "https://pms.leyopharm.com",   # /operation-service/ 与多数 /pms_operation/web/ 统计导出
    "ysb": "https://pms.ysbang.cn",       # 老接口 /pms-main/coupon/...
}
DEFAULT_BUILD_TIME = "2026-11-17 18:42:50"  # 前端构建时刻实测值（可被 --build-time 覆盖）
SUCCESS_CODES = {"40001"}


def _token_from(args) -> str:
    """凭证三入口（优先级 --token > PMS_TOKEN > --state-file），不读父凭证仓库。"""
    if args.token:
        return args.token
    env = os.environ.get("PMS_TOKEN")
    if env:
        return env
    state_path = args.state_file or os.environ.get("PMS_STATE_FILE")
    if state_path:
        try:
            d = json.load(open(state_path, encoding="utf-8"))
            t = d.get("token") or (d.get("headers") or {}).get("token")
            if t:
                return t
        except Exception as e:
            raise SystemExit(f"[TMS] --state-file 读取失败：{e}")
    raise SystemExit("[TMS] 缺少 token：请用 --token / PMS_TOKEN / --state-file 传入（本包不登录）")


def build_payload(base: dict, token: str, build_time: str) -> dict:
    """复制 base 并注入 token + buildTime，不改调用方原对象。"""
    p = dict(base or {})
    p["token"] = token
    p["buildTime"] = build_time
    return p


def call(args) -> dict:
    token = _token_from(args)
    bt = args.build_time or DEFAULT_BUILD_TIME
    base = json.load(open(args.payload_file, encoding="utf-8")) if args.payload_file else {}
    payload = build_payload(base, token, bt)
    url = DOMAINS[args.domain].rstrip("/") + "/" + args.path.lstrip("/")
    headers = {
        "Content-Type": "application/json",
        "token": token,
        "Authorization": f"Bearer {token}",
        "Origin": DOMAINS["ysb"],
        "Referer": DOMAINS["ysb"] + "/",
    }
    data = json.dumps(payload, ensure_ascii=False, encoding="utf-8").encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as r:
            body = r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"[TMS] HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:400]}")
    except Exception as e:
        raise SystemExit(f"[TMS] 请求失败：{e}")
    try:
        out = json.loads(body)
    except Exception:
        out = {"_raw": body[:2000]}
    if args.out_file:
        with open(args.out_file, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
    code = str(out.get("code", ""))
    if code not in SUCCESS_CODES:
        msg = str(out.get("message", ""))[:200]
        hint = "（凭证失效类错误：请调用方提供新 token / 当前页面 buildTime，本包不自行登录）" \
               if code in {"40005", "40006", "40007", "40050"} else ""
        print(f"[TMS] code={code} message={msg} {hint}", file=sys.stderr)
    else:
        d = out.get("data")
        shape = f"list={len(d.get('list', []))}" if isinstance(d, dict) and "list" in d else \
                f"records={len(d.get('records', []))}" if isinstance(d, dict) and "records" in d else "data=..."
        print(f"[TMS] OK code={code} {shape}" + (f" -> {args.out_file}" if args.out_file else ""))
    return out


def main():
    ap = argparse.ArgumentParser(description="TMS 流量投放自包含发送器（标准库，无外部依赖）")
    ap.add_argument("--domain", choices=sorted(DOMAINS), required=True, help="ley=pms.leyopharm.com / ysb=pms.ysbang.cn")
    ap.add_argument("--path", required=True, help="接口路径，如 /operation-service/promotion-expense/page/v100")
    ap.add_argument("--payload-file", help="请求 body JSON 文件（token/buildTime 自动注入）")
    ap.add_argument("--token", help="PMS token（优先级最高）")
    ap.add_argument("--state-file", help="调用方提供的凭证文件（仅读 token 字段，不读父凭证仓库）")
    ap.add_argument("--build-time", default=None, help=f"前端构建时刻（默认 {DEFAULT_BUILD_TIME}）")
    ap.add_argument("--out-file", help="响应写入文件（JSON）")
    ap.add_argument("--timeout", type=int, default=60)
    call(ap.parse_args())


if __name__ == "__main__":
    main()
