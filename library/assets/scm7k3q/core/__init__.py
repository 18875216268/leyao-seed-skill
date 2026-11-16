"""SCM 技能核心层：错误、HTTP、凭证、PMS 凭证消费者（pms_client）、导出任务。

登录器实体在 scripts/scm_login.py（SCM）；PMS 登录委托主技能 p3nes3/scripts/pms_login.py。
"""

import warnings

# 第三方依赖版本告警会污染 stdout（Agent 解析 JSON 失败），统一静默
warnings.filterwarnings("ignore", message=".*doesn't match a supported version.*")
