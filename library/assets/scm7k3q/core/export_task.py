"""导出任务：轮询与下载（所有板块共用）。

提交任务由各板块负责（返回 recordId），本模块只做：
- `wait_url()`：轮询导出列表，命中 recordId 且 status=3 时返回 qiniuUrl；
- `download()`：下载 CSV（GBK）。
"""

from __future__ import annotations

import time
from pathlib import Path

from .errors import SkillError
from .http import post

RECORD_PATH = "/export-file/file/getExportTaskRecord/v100"
STATUS_LABEL = {1: "进行中", 2: "等待中", 3: "已完成", 4: "异常", 5: "已过期"}

# status=4 是生成中可能出现的短暂异常态：自营实测 5 个任务先显示 4，
# 约 10 分钟后全部转为 3 并产出文件，因此不能立即判失败。
DEFAULT_TIMEOUT = 900           # 15 分钟，覆盖上述约 10 分钟延迟
DEFAULT_INTERVAL = 5            # 轮询间隔（秒）
DEFAULT_ABNORMAL_GRACE = 600    # status=4 连续宽限 10 分钟；超过则判服务端持续异常


def _status_code(task: dict) -> int | None:
    """状态归一化：接口可能返回数字或数字字符串。"""
    try:
        return int(task.get("status"))
    except (TypeError, ValueError):
        return None


def wait_url(session, token: str, record_id: int, *,
             timeout: int = DEFAULT_TIMEOUT,
             interval: int = DEFAULT_INTERVAL,
             abnormal_grace: int = DEFAULT_ABNORMAL_GRACE) -> str:
    """轮询导出任务直到完成；超时/持续异常/已过期抛 SkillError。

    状态机（见《references/通用/api_导出任务.md》§4）：
      1/2 进行中·等待中 → 继续轮询并重置异常宽限；
      3 已完成 → 取 qiniuUrl 返回；
      4 异常 → 短暂态，继续轮询；连续超过 abnormal_grace 才判持续异常；
      5 已过期 → 立即失败（终态，等待无意义）。

    任何失败都提示「勿重复提交」，避免触发 40003 限流。
    """
    if timeout <= 0 or interval <= 0:
        raise SkillError("PARAM_INVALID", "timeout / interval 必须为正数")
    grace = min(abnormal_grace, timeout)
    deadline = time.monotonic() + timeout
    abnormal_since: float | None = None
    last_status: int | None = None
    polls = 0

    while time.monotonic() < deadline:
        polls += 1
        data = post(session, token, RECORD_PATH, {"pageNo": 1, "pageSize": 20})
        page = (data or {}).get("exportTaskRecordPageResult") or {}
        matched = next(
            (t for t in (page.get("results") or [])
             if str(t.get("recordId")) == str(record_id)),
            None,
        )
        if matched is None:
            time.sleep(interval)
            continue

        status = _status_code(matched)
        last_status = status

        if status == 3:
            url = matched.get("qiniuUrl")
            if not url:
                raise SkillError(
                    "EXPORT_NO_URL", "任务已完成但暂无下载地址",
                    hint="稍后在导出列表复查该 recordId；勿重复提交（会触发 40003 限流）",
                    details={"recordId": record_id, "polls": polls},
                )
            return url

        if status == 5:
            raise SkillError(
                "EXPORT_EXPIRED", "导出任务已过期，文件已被清理",
                hint="重新提交导出任务；若连续失败先确认导出服务状态",
                details={"recordId": record_id, "polls": polls},
            )

        now = time.monotonic()
        if status == 4:
            if abnormal_since is None:
                abnormal_since = now
            elif now - abnormal_since >= grace:
                raise SkillError(
                    "EXPORT_FAILED",
                    f"导出任务连续 {grace}s 处于 status=4，未产出文件",
                    hint="服务端导出可能持续异常；勿重复提交（会触发 40003 限流），"
                         "稍后在导出列表复查 recordId 或联系运营确认导出服务",
                    details={"recordId": record_id, "lastStatus": 4, "polls": polls,
                             "abnormalSeconds": round(now - abnormal_since)},
                )
        else:
            abnormal_since = None  # 状态回到 1/2 说明任务仍在推进，重置宽限

        time.sleep(interval)

    raise SkillError(
        "EXPORT_TIMEOUT", f"导出任务 {timeout}s 未完成",
        hint="稍后在导出列表查看该 recordId，或减少筛选范围；勿重复提交（会触发 40003 限流）",
        details={"recordId": record_id, "lastStatus": last_status,
                 "lastStatusText": STATUS_LABEL.get(last_status, "未命中任务"),
                 "polls": polls, "timeout": timeout},
    )


def download(session, url: str, out: str | Path) -> Path:
    """下载导出文件；自动创建目录。"""
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    response = session.get(url, headers={"Referer": "https://scm.ysbang.cn/"}, stream=True, timeout=120)
    if response.status_code != 200:
        raise SkillError("DOWNLOAD_FAILED", f"下载失败 HTTP {response.status_code}")
    with open(path, "wb") as handle:
        for chunk in response.iter_content(8192):
            handle.write(chunk)
    return path
