#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""摇钱树 · 筛选器候选值 CLI（实时获取 + 按当前登录用户缓存，TTL 24h）。

用法：
  python scripts/candidates.py --filter "业务类型"            # 取候选（缓存优先）
  python scripts/candidates.py --filter "业务类型" --refresh  # 强制重新实测
  python scripts/candidates.py --filter "客户类型" --search 重  # 条件返回（按关键字取子集）
  python scripts/candidates.py --list                         # 当前缓存概况
  python scripts/candidates.py --list-all                     # 列出全部 41 个筛选器名称

候选值随账号权限与业务数据变化，不内置；需要完整长清单时按关键字分片取（服务端 exceedLimit 非错误）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="摇钱树候选值 CLI")
    ap.add_argument("--filter", help="筛选器名称")
    ap.add_argument("--search", help="条件返回关键字")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--list", action="store_true", help="显示缓存概况")
    ap.add_argument("--list-all", action="store_true", help="列出全部筛选器名称")
    a = ap.parse_args()

    if a.list_all:
        sels = C.load_selectors()
        for s in sels:
            print(f"- {s['name']} (`{s['selectorId']}`) 驱动 {len(s.get('targetCdIds', []))} 卡")
        return

    if a.list:
        cf = C.RES / "candidate_cache.json"
        if not cf.is_file():
            print("[candidates] 暂无缓存，先用 --filter 取一次")
            return
        cache = json.loads(cf.read_text(encoding="utf-8"))
        for k, v in cache.items():
            print(f"- {k}  ({v.get('count')} 项, {'刷新' if v.get('ts') else ''})")
        return

    if not a.filter:
        print("[candidates] 需指定 --filter <名称>", file=sys.stderr)
        sys.exit(2)

    res = C.get_candidates(a.filter, search=a.search, refresh=a.refresh)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
