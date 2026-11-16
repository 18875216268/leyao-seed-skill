"""PMS 凭证"消费者"层（非登录器 · 与主技能零代码耦合）。

职责边界：
- 只读消费"用户级固定凭证文件"里由主技能 pms_login.py 产出的 PMS 凭证；
- 复用与 pms_login.py 同值的请求常量（PMS_BASE/APP_VERSION/PMS_HEADERS/_build_time）；
- pms-login 动作通过**子进程委托主技能 pms_login.py --reuse**（不 import 其代码、不复制登录逻辑），
  保持"弹窗登录"功能完全不变，且 PMS 登录器唯一真源在主技能。

本模块不实现任何登录流程、不含二维码/鉴权代码（框架子资产消费父凭证的标准姿态）。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .errors import SkillError

# ---- 与主技能 pms_login.py 同值的固定常量（只读，无登录逻辑） -----------------
PMS_BASE = "https://pms.ysbang.cn"
APP_VERSION = "14.30.1"
MODULE = "promo_profit_monitor"
USER_AGENT = "pms-cxml/1.08"
ORIGIN = PMS_BASE
PMS_HEADERS: dict[str, str] = {
    "accept": "application/json, text/plain, */*",
    "appversion": APP_VERSION,
    "platform": "web",
    "module": MODULE,
    "origin": ORIGIN,
    "referer": f"{ORIGIN}/",
    "user-agent": USER_AGENT,
}
CHINA_TZ = timezone(timedelta(hours=8))


def _build_time() -> str:
    return datetime.now(CHINA_TZ).strftime("%Y-%m-%d %H:%M:%S")


# ---- 凭证仓库定位（用户级固定路径，与主技能同一处；不读父仓库内部代码） -------
def _data_home() -> Path:
    override = os.environ.get("PMS_OPERATIONS_HOME", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "pms-operations-query"
    xdg = os.environ.get("XDG_DATA_HOME", "").strip()
    return (Path(xdg).expanduser() if xdg else Path.home() / ".local" / "share") / "pms-operations-query"


def load_credential() -> dict[str, Any]:
    """读取 PMS 凭证（只读、绝不弹窗）；损坏/缺失返回 {}。"""
    path = _data_home() / "credential.json"
    try:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def verify_credential(*, validate_remote: bool = True, raise_on_invalid: bool = False) -> dict[str, Any]:
    """本地只读校验（绝不弹窗）。远端校验委托主技能 pms_login.py --status --no-remote 之外的方式：
    这里仅做本地字段检查；需要远端强校验时由框架引导调用主技能 pms_login.py --status。
    返回结构对齐主技能：authenticated / reason / credentialPath。
    """
    cred_path = _data_home() / "credential.json"
    cred = load_credential()
    result: dict[str, Any] = {
        "ok": False,
        "authenticated": False,
        "source": "local",
        "reused": True,
        "credentialPath": str(cred_path),
    }
    if not cred or not cred.get("token"):
        result["reason"] = "missing"
        if raise_on_invalid:
            raise SkillError("AUTH_REQUIRED", "尚未登录 PMS，请先在主技能执行 pms_login.py --reuse")
        return result
    result.update({"ok": True, "authenticated": True, **cred})
    result["credentialPath"] = str(cred_path)  # 对齐主技能：凭证文件内的空值不覆盖真实路径
    return result


def _locate_main_login() -> str | None:
    """定位主技能 pms_login.py：环境变量 > 框架内相对路径 > 宿主 skills 常规位置。"""
    env = os.environ.get("PMS_LOGIN_SCRIPT", "").strip()
    if env and Path(env).is_file():
        return env
    here = Path(__file__).resolve()  # .../library/assets/scm7k3q/core/pms_client.py
    candidates = [
        here.parent.parent.parent / "p3nes3" / "scripts" / "pms_login.py",  # 框架内同级资产
        Path.home() / ".codebuddy" / "skills" / "leyao-seed-skill" / "library" / "assets" / "p3nes3" / "scripts" / "pms_login.py",
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    return None


def get_credential(
    *,
    force_relogin: bool = True,
    validate_remote: bool = True,
    interactive: bool = True,
    parent: Any = None,
) -> dict[str, Any]:
    """PMS 登录：子进程委托主技能 pms_login.py --reuse（弹窗登录，功能不变）。

    不 import 主技能代码、不复制登录逻辑；登录器唯一真源在主技能。
    成功后从用户级凭证文件读回完整凭证并补 credentialPath。
    """
    script = _locate_main_login()
    if not script:
        raise SkillError(
            "AUTH_REQUIRED",
            "找不到主技能 PMS 登录器 pms_login.py（用于委托弹窗登录）。",
            hint="设置环境变量 PMS_LOGIN_SCRIPT 指向 p3nes3/scripts/pms_login.py，"
                 "或在 leyao-seed-skill 框架内使用本资产",
        )
    if not interactive:
        raise SkillError(
            "AUTH_REQUIRED",
            "PMS 凭证不可用（非交互模式，绝不弹窗）。",
            hint=f"python \"{script}\" --reuse",
        )
    cmd = [sys.executable, script, "--reuse"]
    if not validate_remote:
        cmd.append("--no-remote")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SkillError("AUTH_FAILED", f"委托主技能 PMS 登录失败：{exc}") from exc
    if proc.returncode != 0:
        raise SkillError(
            "AUTH_FAILED",
            f"主技能 PMS 登录未完成（exit={proc.returncode}）：{(proc.stderr or proc.stdout or '').strip()[:200]}",
        )
    cred = load_credential()
    if not cred or not cred.get("token"):
        raise SkillError("AUTH_TOKEN_MISSING", "PMS 登录已返回，但未读到凭证文件。")
    cred.setdefault("credentialPath", str(_data_home() / "credential.json"))
    return cred
