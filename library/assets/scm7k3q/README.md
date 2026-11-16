# 药师帮商家助手（ScmAgent）

面向药师帮 SCM 商家后台的技能：登录/凭证、商品活动查询导出、订单只读查询、客户/数据（混合板块，按子板块归属）/ 我的摇钱树（摇钱树专属）板块直连；
并提供通用调用器 `call` 与链接管理场景 `ljgl`（25 个动作：创建/上下架/控销组/限购/备注/阶梯价）。

## 依赖

```bash
pip install -r requirements.txt     # 仅 requests 必需
pip install "qrcode[pil]"           # 可选：生成链接二维码 PNG
```

> 未安装 `requests` 时仍可查看帮助与板块清单（`python scm.py` / `python scm.py modules`），
> 只有真正发请求的命令才会提示 `DEPENDENCY_MISSING`。

## 快速开始

```bash
python scm.py                  # 帮助（无需凭证、无需网络）
python scm.py modules          # 列出 11 个板块与能力
python scm.py status           # 校验凭证（需先登录）
python scm.py login --account <账号>    # 弹窗登录（验证码或企微扫码）
python scm.py query --help     # 板块查询
python scm.py scene            # 列出已封装的高频场景
```

## 目录

| 路径 | 说明 |
|---|---|
| `SKILL.md` | 技能入口：元数据 + 决策树 |
| `AGENT_GUIDE.md` | 授权、红线、调用规范 |
| `USER_GUIDE.md` | 面向使用者的命令手册 |
| `scm.py` | 主 CLI（12 个子命令） |
| `core/` | 凭证、HTTP、错误映射、登录器 |
| `modules/` | 板块能力（商品/订单已就绪，其余 9 个为端点清单；客户/数据/摇钱树另有接口文档） |
| `references/` | 接口文档（`api_*.md` / 字典 / 附录） |
| `assets/` | 可选资产：`ljgl`（链接管理场景）、`tpcl`（图片处理） |
| `tests/selftest.py` | 自检（236 项，含离线断言） |

## 环境

Python 3.10+；Windows / macOS / Linux。
凭证落 `%LOCALAPPDATA%\scm-operations-query`（Windows）或 `~/.config/scm-operations-query`。
