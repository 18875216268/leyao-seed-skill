"""商品导出：三段式（生成 sqlParams → 提交任务 → 轮询下载）。

导出入口三种：
- 指定状态：status=0~8，tabCode 对应；
- 全部状态：status=-1，tabCode="all"（不含已结束）；
- 组单中心：独立接口，无业务参数（需 isGroupCenterOrder=1）。
"""

from __future__ import annotations

import json
from pathlib import Path

from core.errors import SkillError
from core.export_task import download, wait_url
from core.http import post

from . import TABCODE_MAP, normalize_status
from .query import build_body

ES_QUERY_PATH = "/scm-goods/excelExport/getWsListEsQuery"
EXPORT_PATH = "/export-file/file/exportWholesaleDrug/v100"
GROUP_CENTER_PATH = "/export-file/file/exportGroupOrderCenterWholesale/v100"


def _wait(session, token: str, record_id: int, poll_timeout: int | None) -> str:
    """按可选超时轮询；None 用 core 默认值（900s，含 status=4 宽限）。"""
    if poll_timeout is None:
        return wait_url(session, token, record_id)
    return wait_url(session, token, record_id, timeout=poll_timeout)


def submit(session, token: str, *, status=None, types=None, keyword: str = "",
           condition=None, extra: dict | None = None) -> int:
    """提交导出任务，返回 recordId。"""
    state = normalize_status(status)
    body = build_body(status=state, types=types, keyword=keyword, condition=condition, extra=extra)
    body.update({"pageNo": 1, "pageSize": 10})

    sql_data = post(session, token, ES_QUERY_PATH, body) or {}
    sql = sql_data.get("sqlParams")
    if not sql:
        raise SkillError("EXPORT_NO_SQL", "未取得 sqlParams", hint="检查筛选条件是否合法")
    wholesale_types = sql_data.get("wholesaleType") or body.get("wholesaleType") or []

    payload = {
        "sqlParams": sql,
        "wholesaleType": json.dumps(wholesale_types, ensure_ascii=False),
        "tabCode": TABCODE_MAP[state],
        "templateType": 10,
    }
    data = post(session, token, EXPORT_PATH, payload) or {}
    record_id = data.get("recordId")
    if not record_id:
        raise SkillError("EXPORT_NO_RECORD", "提交导出未返回 recordId")
    return int(record_id)


def export(session, token: str, out: str | Path, *, status=None, types=None,
           keyword: str = "", condition=None, extra: dict | None = None,
           poll_timeout: int | None = None) -> dict:
    """导出并下载，返回 {path, rows, recordId}。"""
    record_id = submit(session, token, status=status, types=types, keyword=keyword,
                       condition=condition, extra=extra)
    url = _wait(session, token, record_id, poll_timeout)
    path = download(session, url, out)
    return {"path": str(path), "rows": count_rows(path), "recordId": record_id}


def export_group_center(session, token: str, out: str | Path,
                        poll_timeout: int | None = None) -> dict:
    """导出组单中心活动（无筛选）。"""
    data = post(session, token, GROUP_CENTER_PATH, {}) or {}
    record_id = data.get("recordId")
    if not record_id:
        raise SkillError("EXPORT_NO_RECORD", "组单中心导出未返回 recordId",
                         hint="该账号可能未开通组单中心（isGroupCenterOrder≠1）")
    url = _wait(session, token, int(record_id), poll_timeout)
    path = download(session, url, out)
    return {"path": str(path), "rows": count_rows(path), "recordId": int(record_id)}


def count_rows(path: str | Path) -> int:
    """统计 CSV 数据行（GBK，含表头）。"""
    try:
        with open(path, "rb") as handle:
            content = handle.read().decode("gbk", "ignore")
        return max(0, len(content.splitlines()) - 1)
    except OSError:
        return -1
