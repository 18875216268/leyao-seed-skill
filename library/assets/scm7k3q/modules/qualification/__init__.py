"""资质板块（待开发）。

状态：todo —— 仅采集到端点清单，参数未实现。
实现方式见 modules/goods/__init__.py 的结构。
"""

NAME = "资质"
STATUS = "todo"
GUIDE = "modules/qualification/GUIDE.md"

ENDPOINTS = [
    "/provider.php/Admin/CAAudit/qualitySeal",
    "/provider.php/Admin/ProviderAccount/quailtySeal",
    "/provider.php/Admin/ServiceQuality/index/menuid",
    "/provider.php/Admin/ServiceQuality/index/menuid/947",

]
