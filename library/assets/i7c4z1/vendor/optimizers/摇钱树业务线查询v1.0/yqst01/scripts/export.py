#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""摇钱树 · 导出 CLI（三步链：提交→轮询→下载）。

⚠ 导出任务**拒绝页面级「出库日期」过滤 j837**（带→任务 1012 FAILED）。本脚本自动剥离 j837，
只用卡片自身筛选（+ 用户指定筛选）。结果即「筛选后定制视图」的小表。

用法：
  python scripts/export.py --card "商务考核数据" --out 导出.xlsx
  python scripts/export.py --card <cardId> --payload-file body.json --out 导出.xlsx
        # body.json 至少含 {"filters":[...]}（完整键组）；j837 会被自动剥离
  python scripts/export.py --task <taskId> --out 续传.xlsx     # 超时/中断后续传

输出 JSON：{ "ok": true, "taskId": ..., "out": ..., "bytes": ... }
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="摇钱树导出 CLI")
    ap.add_argument("--card", help="卡片名称或 cardId")
    ap.add_argument("--payload-file", help="请求体 JSON（含 filters）")
    ap.add_argument("--out", help="输出 xlsx 路径（默认 ./<卡名>_<时间戳>.xlsx）")
    ap.add_argument("--task", help="续传：直接按 taskId 下载")
    a = ap.parse_args()

    s = C.resolve_session()

    if a.task:
        from datetime import datetime
        out = a.out or f"./导出_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
        r2 = s.get(f"{C.BASE}/api/task/{a.task}", headers=C.UA, timeout=60)
        j2 = r2.json().get("response", r2.json())
        if j2.get("status") != "FINISHED":
            print(json.dumps({"ok": False, "status": j2.get("status")}, ensure_ascii=False))
            return
        r3 = s.post(f"{C.BASE}/api/export/file/common/{a.task}", headers=C.J,
                    json={"downloadFileName": "续传"}, timeout=600)
        Path(out).write_bytes(r3.content)
        print(json.dumps({"ok": True, "taskId": a.task, "out": out, "bytes": len(r3.content)},
                         ensure_ascii=False))
        return

    if not a.card:
        print("[export] 需指定 --card", file=sys.stderr)
        sys.exit(2)
    card = C.find_card(a.card)
    if not card:
        print(json.dumps({"ok": False, "detail": f"未找到卡片「{a.card}」"}, ensure_ascii=False))
        return

    filters = []
    if a.payload_file:
        body = json.loads(Path(a.payload_file).read_text(encoding="utf-8"))
        filters = body.get("filters", []) or []
    else:
        # 默认用推荐筛选（销售进度页带 j837，但 export_card 会自动剥离）
        filters = C.recommended_filters(card, C.load_selectors())

    from datetime import datetime
    out = a.out or f"./{card.get('name') or card['cardId']}_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    res = C.export_card(card, filters, out, session=s)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
