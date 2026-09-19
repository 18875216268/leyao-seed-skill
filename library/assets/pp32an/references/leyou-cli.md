# 乐药云智库 CLI 速查（兜底源）

> 客户端：`scripts/sources/leyou/leyou_cloud.py`（业务：搜索/详情/采集；原生集成）+
> 独立登录器 `scripts/sources/leyou/login_leyou_cloud.py`（登录：单文件自包含，详见同目录 `login_leyou_cloud.md`）；
> **登录态只落用户数据区** `leyou_token.json`（默认与数据区对齐：资产内运行时 = `common.LEYOU_TOKEN_F`；独立拷贝时 `~/.leyao-kb/leyou_token.json`；
> 客户端/登录器均可用 `--token-file` 指定；包内零写入）。
> **本 skill 只查不弹窗**：`status` 预检（scan=False 语义）→ 失效即返回 `LOGIN_REQUIRED` + 手动指引；
> 桥接调用统一带 `--no-auto-login`（机制保证：**绝不会触发扫码弹窗**）。
> **位置 / 执行口径**：本文件所有 `scripts/…` 命令均相对**包根**（资产根 `library/assets/pp32an/`）——**在资产根执行**；异 cwd 时脚本路径写全即可（**参数与 cwd 无关** ✓）。

## 常用子命令

> 直接手调客户端无需带 `--token-file`（默认落用户数据区）；桥接（`leyou_bridge.py`）与

```text
python scripts/sources/leyou/leyou_cloud.py status           # 登录态预检（只复用本地/库凭证）
python scripts/sources/leyou/leyou_cloud.py search <关键词>   # 搜索（本 skill 兜底调用）
python scripts/sources/leyou/leyou_cloud.py summary <slug>    # 摘要
python scripts/sources/leyou/leyou_cloud.py detail <slug>     # 详情
python scripts/sources/leyou/leyou_cloud.py collect <关键词>   # 全库采集（批量）
```

## 登录（调起独立登录器；用户仅需扫码）

凭证失效时**调起独立登录器**（黑盒、一条命令；窗口直达用户桌面，用户完成扫码即可）：**禁止读源码后自写 / 自组装登录流程** ✗；**用户已指定或提供凭证 / 登录方式 → 按其走** ✓。
**独立登录器**（推荐）：`scripts/sources/leyou/login_leyou_cloud.py`
（单文件自包含；完整手册见同目录 `login_leyou_cloud.md`）——**在资产根 `library/assets/pp32an/` 执行**：

```text
python scripts/sources/leyou/login_leyou_cloud.py                        # 弹窗扫码重登（需桌面）
python scripts/sources/leyou/login_leyou_cloud.py --reuse                # 独立登录器完整功能.真正全自动.用户体验优先首选！（零额外依赖：tkinter 标准库）
python scripts/sources/leyou/login_leyou_cloud.py --check                       # 环境自检：依赖 tkinter；异常时给出修复指引
python scripts/sources/leyou/login_leyou_cloud.py --status               # 只验证（绝不弹窗）
```

**凭证失效 → 用 `--reuse`（独立登录器弹窗）**。
兼容入口（转发同一登录器，输出/凭证文件不变）：`leyou_cloud.py login` / `leyou_cloud.py status`。
成功后凭证写入用户数据区 `leyou_token.json`，之后本 skill 常态复用、无感。
> 本 skill 不实现登录、不代扫、不保存额外凭证。
> ⚠️ `leyou_token.json` 与数据区 `config.local.json` 都是**真实运行凭证**：切勿入包/入仓；发布或提交前确认包内不存在。

## 桥接行为（`scripts/sources/leyou_bridge.py`）

- `status()`：子进程调用 `status`；输出含登录失效关键词 → `{ok:false, reason:"LOGIN_REQUIRED", next:<指引>}`；
- `search(problem)`：先 `status()` 预检，未登录**直接返回**（不浪费 12s 超时）；调用统一带 `--no-auto-login`（即使执行中 token 失效也绝不触发扫码弹窗，直接如实返回）；
- 输出容错：JSON → 结构化 items；纯文本 → 折成 1 条（`evidence: leyou#cli`），**不臆造字段**。

