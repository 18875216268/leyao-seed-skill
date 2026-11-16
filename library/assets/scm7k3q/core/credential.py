"""凭证读取与校验（薄封装）。

凭证文件默认 `%LOCALAPPDATA%\\scm-operations-query\\credential.json`，
可用环境变量 `SCM_OPERATIONS_HOME` 或 CLI `--cred-dir` 覆盖。

校验分两级：
- 本地：过期时间；
- 远端：token（getProviderLoginInfo）+ cmsToken（业务只读接口探针）。
"""

from __future__ import annotations

from pathlib import Path

import scm_login as login
from .errors import SkillError


def cred_dir() -> Path:
    """当前凭证目录（受 SCM_OPERATIONS_HOME 控制）。"""
    return login.data_home()


def load(account: str | None = None) -> dict:
    """读取凭证；account 为空读当前生效，指定则读归档。"""
    return login.load_credential(account) or {}


def check(credential: dict, *, remote: bool = True) -> tuple[str | None, object]:
    """校验凭证；返回 (reason, error)，reason 为空表示有效。"""
    if not credential:
        return "missing", None
    return login.check_credential(credential, validate_remote=remote)


def ensure(account: str | None = None, *, remote: bool = True) -> dict:
    """取一份可用凭证；不可用则抛 SkillError（带可执行提示）。"""
    credential = load(account)
    if not credential:
        target = f"账号 {account} 的" if account else ""
        raise SkillError(
            "AUTH_REQUIRED",
            f"没有可用的{target} SCM 凭证",
            hint="python scm.py login --account <账号>（弹出登录窗，人工输入验证码）",
        )
    reason, error = check(credential, remote=remote)
    if reason:
        message = getattr(error, "message", "") or "凭证不可用"
        raise SkillError(
            "AUTH_EXPIRED" if reason == "expired" else "CREDENTIALS_INVALID",
            f"SCM 凭证不可用：{message}",
            hint="python scm.py login --account <账号> 重新登录",
            details={"reason": reason},
        )
    return credential
