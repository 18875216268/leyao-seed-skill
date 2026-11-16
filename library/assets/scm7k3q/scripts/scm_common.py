"""SCM 凭证取用与 key 注入（对齐框架 PMS/BI 的凭证消费范式）。

发送 key 优先级（任何子技能可复用）：
  --token / SCM_TOKEN 环境变量 / SCM_CREDENTIAL_FILE 凭证文件 / 登录器本地凭证仓

本模块只做"取用"，登录动作一律由 scm_login.py 本体完成（--reuse 原生窗）；
--no-ui 时不弹窗、报错指路（与 pms_call.py resolve_token 同构）。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

LOGIN_HINT = (
    "python scripts/scm_login.py --status to verify (no popup), "
    "or --reuse to reuse a valid credential; a bare run forces a re-login."
)


class ScmCredentialError(RuntimeError):
    """A user-actionable SCM credential error."""


def _load_external_file(path: str) -> dict[str, Any]:
    """读取外部注入的凭证 JSON（--credential-file / SCM_CREDENTIAL_FILE）。"""
    try:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def resolve_credential(
    token: str | None = None,
    credential_file: str | None = None,
) -> dict[str, Any]:
    """解析可用于发包的**完整凭证字典**（SCM 接口需 token + cookies + provider_id_m）。

    - `--credential-file` / SCM_CREDENTIAL_FILE：外部完整凭证 JSON，可直接用；若同时给 token 则覆盖其 token/cms_token。
    - 仅注入 token（--token / SCM_TOKEN）：以本资产登录器本地凭证仓为基座补齐
      cookies / provider_id_m / cms_token，再覆盖 token —— 因 SCM 协议除 token 外还需 provideridm 头与 cookies，
      单独 token 无法发包（与 PMS/BI 不同）。无本地基座时返回 {"token": token}，由 build_session 给出缺字段提示。
    - 无外部 key：返回 {}，由调用方走原本地凭证/登录逻辑。
    """
    cred_file = credential_file or os.getenv("SCM_CREDENTIAL_FILE", "").strip()
    data: dict[str, Any] = {}
    if cred_file:
        data = _load_external_file(cred_file)
    token = token or os.getenv("SCM_TOKEN", "").strip()
    if token:
        data = dict(data)
        data["token"] = str(token)
        data["cms_token"] = str(token)
    if not data:
        return {}
    if not data.get("cookies") or not data.get("provider_id_m"):
        # 用本地凭证仓补齐 SCM 必需的 cookies / provider_id_m
        import scm_login
        base = scm_login.load_credential()
        for k in ("cookies", "provider_id_m", "provider_id", "headers"):
            if not data.get(k) and base.get(k):
                data[k] = base[k]
    return data


def resolve_token(
    explicit_token: str | None = None,
    credential_file: str | None = None,
    *,
    no_ui: bool = False,
    validate_remote: bool = True,
) -> str:
    """解析可用的 SCM token（供只需 token 的下游复用；发 SCM 业务接口请用 resolve_credential）。

    优先级：显式 token > SCM_TOKEN > 凭证文件(SCM_CREDENTIAL_FILE) > 登录器本地凭证仓。
    """
    token = explicit_token or os.getenv("SCM_TOKEN", "").strip()
    if token:
        return str(token)

    cred_file = credential_file or os.getenv("SCM_CREDENTIAL_FILE", "").strip()
    if cred_file:
        data = _load_external_file(cred_file)
        external = str(data.get("token") or data.get("cms_token") or "").strip()
        if external:
            return external

    import scm_login  # 惰性导入自有登录器（同脚本目录）

    result = scm_login.verify_credential(validate_remote=validate_remote)
    if result.get("authenticated") and result.get("token"):
        return str(result["token"])

    if no_ui:
        raise ScmCredentialError(f"{LOGIN_HINT} (AUTH_REQUIRED)")
    credential = scm_login.get_credential(force_relogin=False, interactive=True)
    value = str(credential.get("token") or "")
    if not value:
        raise ScmCredentialError(f"{LOGIN_HINT} (AUTH_TOKEN_MISSING)")
    return value


def stored_token() -> str:
    """只取 token（本地只读、绝不弹窗），供 Agent 取用后作为 key 传给子技能。"""
    import scm_login

    result = scm_login.verify_credential(validate_remote=False)
    if result.get("authenticated") and result.get("token"):
        return str(result["token"])
    raise ScmCredentialError(LOGIN_HINT)
