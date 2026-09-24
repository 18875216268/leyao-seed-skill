# -*- coding: utf-8 -*-
"""摇钱树业务线板块 · 权限自检 CLI（选板必验用）。
用当前凭证对一张代表卡做 limit=1 轻量探测，输出 JSON：
  {"board": "摇钱树业务线", "permission": "ACCESSIBLE|NO_PERMISSION|AUTH_EXPIRED|NETWORK|UNKNOWN"}
AI 在路由到本板前应先跑本命令：ACCESSIBLE 才继续；NO_PERMISSION 则本板不可用，
需切到账号有权限的板块或换对应部门账号重登（切勿拿运营 token 跑本板、反之亦然）。
"""
import sys
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common  # noqa: E402


def main():
    status = common.verify_board_permission()
    out = {
        "board": "摇钱树业务线",
        "permission": status,
        "ok_to_use": status == "ACCESSIBLE",
    }
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
