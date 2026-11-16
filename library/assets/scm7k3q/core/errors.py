"""统一错误类型与退出码。

退出码约定（供 Agent 判断）：
  0 成功 ｜ 1 业务错误 ｜ 2 参数错误 ｜ 3 凭证失效
"""

EXIT_OK = 0
EXIT_BUSINESS = 1
EXIT_PARAM = 2
EXIT_AUTH = 3

# 业务码 → 退出码
_AUTH_CODES = {"AUTH_REQUIRED", "AUTH_EXPIRED", "CREDENTIALS_INVALID", "CREDENTIAL_BUSY"}
_PARAM_CODES = {"PARAM_INVALID", "MODULE_TODO", "MODULE_UNKNOWN", "NOT_SUPPORTED"}


class SkillError(Exception):
    """技能内统一异常。code 为大写标识，message 面向使用者。"""

    def __init__(self, code: str, message: str, *, hint: str = "", details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint
        self.details = details or {}

    @property
    def exit_code(self) -> int:
        if self.code in _AUTH_CODES:
            return EXIT_AUTH
        if self.code in _PARAM_CODES:
            return EXIT_PARAM
        return EXIT_BUSINESS

    def to_dict(self) -> dict:
        out = {"ok": False, "error": self.code, "message": self.message}
        if self.hint:
            out["hint"] = self.hint
        if self.details:
            out["details"] = self.details
        return out
