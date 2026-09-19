# login_leyou_cloud · 乐药云智库独立登录器

> 模块文件：`login_leyou_cloud.py`（**单文件自包含；依赖 `requests`，弹窗用标准库 tkinter，零额外依赖**）
> 一句话：**给它一个 token 文件路径（或默认用户区），它还你一份可直接发请求的完整凭证。**
> 既能 `python login_leyou_cloud.py` 独立运行，也能被任何 Python 程序 `import login_leyou_cloud` 直接调用——与 `login_bi.py` / `pms_login.py` 同构。

```
leyou/
├── login_leyou_cloud.py     登录器本体（单文件自包含，站点常量硬编码于文件内）
├── login_leyou_cloud.md     本文档
├── leyou_cloud.py           业务客户端（登录实现已迁移至本登录器，status/login 转发调用）
```

**运行只需 2 个文件**（`login_leyou_cloud.py` + 本 md），拷到任何 Windows / Linux 机器即可使用。

---

## 目录

1. [能做什么](#1-能做什么)
2. [环境要求](#2-环境要求)
3. [方式一：命令行直接运行](#3-方式一命令行直接运行)
4. [方式二：Python 调用（推荐）](#4-方式二python-调用推荐)
5. [内部组件 LoginFlow（不对外）](#5-内部组件-loginflow不对外)
6. [凭证（唯一落盘形态）](#6-凭证唯一落盘形态)
7. [返回值：完整凭证字段表](#7-返回值完整凭证字段表)
8. [错误处理](#8-错误处理)
9. [UI 弹窗状态机](#9-ui-弹窗状态机)
10. [登录链路（实测协议）](#10-登录链路实测协议)
11. [配置与文件位置](#11-配置与文件位置)
12. [完整可复制示例](#12-完整可复制示例)
13. [注意事项 / 常见坑](#13-注意事项--常见坑)

---

## 1. 能做什么

| 能力 | 说明 |
|---|---|
| **扫码登录** | 弹出企微二维码窗口，用户扫码确认后返回全新凭证 |
| **凭证复用** | 本地凭证仍有效时直接复用，不弹窗、不打扰 |
| **凭证校验** | 只检查现有凭证是否可用，**绝不弹窗** |
| **仅弹窗登录** | 登录只有原生二维码窗口一种形态（**无出码 / 无界面模式**） |
| **凭证持久化** | 自动以明文 JSON 存盘，下次仍可用（文件受用户目录写权限保护） |
| **弹窗零依赖** | tkinter 为标准库；二维码与绿色大√由 Canvas 原生绘制，**不需要 PIL / PyQt5** |
| **零落盘** | 二维码全程内存渲染（不写任何文件），流程结束即释放，不留运行产物 |

---

## 2. 环境要求

| 依赖 | 版本 | 是否必需 | 说明 |
|---|---|---|---|
| Python | ≥ 3.10 | 必需 | 代码用了 `str \| None` 等新语法 |
| `requests` | `>=2.31,<3` | **必需** | 所有模式都需要 |
| `tkinter` | 标准库 | 弹窗需要 | Windows/macOS 官方 Python 自带；Linux 装 `python3-tk` |

```bash
python -m pip install "requests>=2.31,<3"
```

---

## 3. 方式一：命令行直接运行

```bash
python login_leyou_cloud.py                 # 默认：弹窗扫码重新登录，输出全新凭证
python login_leyou_cloud.py --status        # 只验证已有凭证是否有效（绝不弹窗）
python login_leyou_cloud.py --reuse         # 有效则复用，失效才弹窗
python login_leyou_cloud.py --check         # 环境自检（依赖 tkinter；异常给修复指引）
python login_leyou_cloud.py --no-remote     # 跳过远端校验（只做本地检查）
python login_leyou_cloud.py --status --compact   # 只验证 + 单行 JSON（机器解析友好）
```

### 参数表

| 参数 | 默认 | 作用 |
|---|---|---|
| *(无)* | — | 弹窗扫码，返回全新凭证 |
| `--status` | 关 | 只做校验，绝不弹窗 |
| `--reuse` | 关 | 优先复用本地有效凭证，失效才弹窗 |
| `--check` | 关 | 环境自检：检查 tkinter 与登录器可调用性，异常给出修复指引 |
| `--no-remote` | 关 | 跳过远端校验，只做本地检查（不发网络请求） |
| `--wait` | 300 | 扫码等待秒数 |
| `--token-file` | 用户区 | 凭证文件路径（见[第 6 节](#6-凭证唯一落盘形态)） |
| `--quiet` | 关 | 静默（不输出人类提示到 stderr） |
| `--compact` | 关 | 单行 JSON 输出（机器解析友好） |

### 输出与退出码

- **stdout**：一份 JSON（成功为完整凭证，失败为 `{"ok": false, "error": {...}}`），可直接被上游程序解析（`--compact` 单行）。
- **stderr**：人类可读的中文提示（如 `二维码已生成：…`）。
- **退出码**：

| 退出码 | 含义 |
|---|---|
| `0` | 成功（拿到可用凭证，或 `--status` 判定有效） |
| `1` | 业务错误（网络失败、二维码失效等） |
| `2` | 参数错误 / 未分类错误 |
| `3` | 需要登录（`AUTH_REQUIRED` / `LOGIN_CANCELLED`） |

---

## 4. 方式二：Python 调用（推荐）

```python
from login_leyou_cloud import (
    relogin,             # 弹窗扫码重登，返回全新凭证（并按 token-file 落盘）
    verify_credential,   # 验证凭证（绝不弹窗）
    get_credential,      # 组合：强制重登 / 复用（非交互调用只复用）
    is_authenticated,    # 快捷：现在能不能用
    build_credential,    # 手工打包凭证
    LeyouLoginError,     # 统一错误
)
```

### 4.1 `verify_credential()` —— 只验证，绝不弹窗

```python
verify_credential(
    *,
    token=None,              # 显式指定 token（默认读 token_file）
    uuid=None,               # 显式指定 uuid（默认读文件 / 兜底默认值）
    token_file=None,         # 凭证文件路径（默认用户区）
    validate_remote=True,    # 是否额外发一次远端校验请求
    raise_on_invalid=False,  # True → 无效时抛 LeyouLoginError
    session=None,            # 可复用已有 requests.Session（业务预检场景）
) -> dict
```

- 有效 → [完整凭证](#7-返回值完整凭证字段表)（`authenticated=True`，`source="local"`，`reused=True`）；
- 无效 → `{"ok": False, "authenticated": False, "reason": ..., "error": {...}, "credentialPath": "..."}`。

| `reason` | 含义 | 建议动作 |
|---|---|---|
| `missing` | 本地没有任何凭证 | 调用 `relogin()` 扫码 |
| `expired` | 本地凭证超过 `expires_at` 参考值 | 调用 `relogin()` 扫码 |
| `invalid` | 远端判定失效（507 / 栏目为空） | 调用 `relogin()` 扫码 |
| `not_validated` | 远端校验未通过（网络不通 / 限流） | 可先重试；仍失败再 `relogin()` |

### 4.2 `is_authenticated()` —— 只要一个布尔值

```python
is_authenticated(validate_remote=True, session=None, token_file=None) -> bool
```

**绝不弹窗、绝不抛异常**。

### 4.3 `relogin()` —— 弹窗扫码，拿全新凭证

```python
relogin(*, token_file=None, max_wait=300, quiet=False) -> dict
```

- **返回**：完整凭证（`source="qr"`，`reused=False`）；
- **落盘**：登录成功后自动写入 token 文件（原子写）；
- **抛出**：`LeyouLoginError` —— `LOGIN_CANCELLED`（用户取消）/ `QR_EXPIRED`（过期/超时）/ `QR_CREATE_FAILED` / `NETWORK_ERROR`；
- **阻塞**直到用户完成扫码或取消；弹窗轮询在后台线程，**窗口不会卡死**。

### 4.4 `get_credential()` —— 组合入口（最灵活）

```python
get_credential(*, force_relogin=True, validate_remote=True, interactive=True,
               token_file=None, max_wait=300, quiet=True) -> dict
```

| 参数组合 | 效果 |
|---|---|
| `force_relogin=True`（默认） | 总是弹窗扫码（等价 `relogin()`） |
| `force_relogin=False` | 先验证：有效复用；失效且 `interactive=True` 才弹窗 |
| `force_relogin=False, interactive=False` | 非交互调用：只复用，不可用直接抛 `AUTH_REQUIRED` |

> **弹窗策略**：只有「凭证本身不可用」（missing / expired / invalid）才允许弹窗；网络、限流类错误一律直接抛出，不会莫名其妙弹窗。
> `interactive=False` 与 `force_relogin=True` **互斥**：非交互调用不支持扫码重登（抛 `AUTH_REQUIRED`）；非交互下要拿凭证请用 `force_relogin=False`（只复用）。

### 4.5 拿到凭证之后怎么发请求

本模块只负责「登录并给你完整凭证」，**不发任何业务请求**。凭证里已包含可直接使用的 `token` / `cookies` / `endpoints`：

```python
import requests

cred = get_credential(force_relogin=False, interactive=False)   # 优先复用，不弹窗
resp = requests.get(
    f"{cred['endpoints']['get']}/foreground/tannant/search-tannant",
    headers={"x-auth-token": cred["token"]},
    params={"tannant_id": "8980", "keyword": "毛利", "page": 1, "pagesize": 10,
            "uuid": cred["uuid"], "search_item": "all"},
)
resp.raise_for_status()
```

业务侧完整封装见 `leyou_cloud.py`（`status` / `search` / `detail` …全部子命令）。

---

## 5. 内部组件 `LoginFlow`（**不对外**）

`LoginFlow` 是二维码窗口的内部驱动内核（取码 / 轮询 / 失效重载 / 换 token），
**不是对外的"无界面登录方式"**——本登录器只提供**原生弹窗登录**一种形态。

- 外部 / Agent 取凭证只用门面：`relogin` / `verify_credential` / `get_credential` / `is_authenticated`；
- **禁止**组装 `LoginFlow` 自建流程（历史教训：自拼登录会绕过落库与身份校验）；
- 阶段常量 `STAGE_LOADING` / `STAGE_QR_READY` / `STAGE_SCANNED` / `STAGE_AUTHENTICATING` /
  `STAGE_FAILED` 与文案常量 `STATUS_LOADING` / `STATUS_SCAN` / `STATUS_CONFIRM` /
  `STATUS_LOGGING_IN` / `STATUS_RETRY`，仅用于说明窗口各阶段（见[第 9 节](#9-二维码窗口状态机)）。

---

## 6. 凭证（唯一落盘形态）

- **存储位置**（按优先级）：
  1. `--token-file` 显式指定；
  2. 资产在包内运行（存在 `scripts/common.py`）→ 数据区权威解析 `common.LEYOU_TOKEN_F`（与桥接**同一落点**，含框架挂载与 `LEYAO_KB_HOME` 判定）；
  3. 独立单文件运行 → `$LEYAO_KB_HOME/leyou_token.json` → `~/.leyao-kb/leyou_token.json`（用户数据区，**绝不写包内**）。
- **存什么**：`{token, uuid, watermark, login_at, expires_at}`——与业务客户端 `leyou_cloud.py` 完全兼容（同一文件、同一字段；桥接无需改动）。
- **怎么存**：明文 JSON + **原子写**（临时文件 + `os.replace`），尽力 `chmod 600`；
- **`expires_at` 说明**：为登录时写入的 **30 天参考值**（服务端不下发过期时间）——实际有效性以远端校验 `get-list` 为准。

---

## 7. 返回值：完整凭证字段表

```python
{
    "ok": True,
    "authenticated": True,
    "source": "qr",                 # "qr" = 本次新扫码；"local" = 复用本地
    "reused": False,                # 本次是否为复用
    "token": "…",                   # 请求凭证明文
    "uuid": "…",                    # 搜索需要的 hl_uuid（登录 cookie，取不到用兜底值）
    "watermark": "…",               # 品牌水印文字（登录后自动带出）
    "login_at": "2026-09-18T10:00:00+0800",
    "expires_at": "2026-10-18",     # 30 天参考值
    "cookies": {                    # 可直接塞进任何 HTTP 客户端
        "hlsdk_token_cp7nb9": "…",
        "hl_siteid_8980": "…",
        "hl_uuid": "…"
    },
    "endpoints": {"get": "https://api-get.helplook.net",
                  "site": "https://leyohrai.helplook.net"},
    "credentialPath": "C:\\Users\\…\\leyou_token.json"   # 资产内 = 数据区路径；独立拷贝 = ~/.leyao-kb
}
```

`verify_credential()`（远端校验时）额外含业务预检字段：`categories`（栏目数）、`first_category`（第一个栏目名）。

**最常用的三个字段**：`token`（或 `cookies`）、`uuid`、`endpoints`。

---

## 8. 错误处理

所有失败统一为 `LeyouLoginError`（`from login_leyou_cloud import LeyouLoginError`）：

```python
try:
    cred = relogin()
except LeyouLoginError as exc:
    print(exc.code)        # 机器可读错误码
    print(exc.message)     # 中文说明
    print(exc.retryable)   # 是否可重试
    print(exc.to_dict())   # {"code":…, "message":…, "retryable":…}
```

### 错误码表

| code | 含义 | 处理建议 |
|---|---|---|
| `AUTH_REQUIRED` | 本地无凭证（或非交互调用时不可用） | 人工跑一次 `python login_leyou_cloud.py --reuse` 扫码 |
| `AUTH_EXPIRED` | 本地凭证超过 `expires_at` 参考值 | 调用 `relogin()` 扫码 |
| `CREDENTIALS_INVALID` | 远端判定失效 / 凭证文件损坏 | 调用 `relogin()` 扫码 |
| `NOT_VALIDATED` | 远端校验未通过（网络 / 限流） | 稍后重试（**不触发弹窗**） |
| `LOGIN_CANCELLED` | 用户取消 / 关闭窗口 | 正常业务分支 |
| `QR_EXPIRED` | 二维码失效 / 等待扫码超时 | 重新调用登录 |
| `QR_CREATE_FAILED` | 拉取登录页 / 二维码失败 | 检查网络后重试 |
| `NETWORK_ERROR` | 网络不可达 / 超时 | 检查网络后重试 |
| `INTERNAL_ERROR` | 未分类异常 | 看日志 |

---

## 9. 二维码窗口状态机

内置弹窗（tkinter，零额外依赖）的实际表现：

| 阶段 | 二维码区显示 | 底部状态文字 |
|---|---|---|
| 打开前 | ——（窗口未创建，正在拉取登录页与二维码） | —— |
| `qr_ready` | 二维码 | `请使用企微扫码【剩余 Ns】……`（实时倒计时） |
| `scanned` | 二维码 + 黑色蒙版 + 绿色勾 | `扫码成功！请确认~` |
| 登录成功 | 保持绿勾，约 0.9s 后窗口自动关闭 | —— |
| 二维码失效 | 窗口内自动重载新码（≤3 次） | `二维码已失效，正在重新加载……` |
| 取消 | 窗口立即关闭 | —— |

- 结果：成功 → 返回凭证；超时 → 抛 `QR_EXPIRED`；点右上角关闭 → 抛 `LOGIN_CANCELLED`；重新执行登录即可。
- 窗口标题：`乐药云智库 · 扫码登录`；无图标（零依赖，二维码与绿勾均由 Canvas 原生绘制）。
- `LoginFlow` 是内部组件、**禁止外部组装**（见[第 5 节](#5-内部组件-loginflow不对外)）；上表为内置窗口的实际表现。

---

## 10. 登录链路（实测协议）

本模块是**整个云智库的登录**，只做两件事：拿凭证、存凭证。链路与 BI / PMS 同为企微扫码底座：

| 环节 | 接口 | 说明 |
|---|---|---|
| 取登录地址 | `GET {BASE_GET}/foreground/tannant/get-auth-url`（`tannant_id` / `redirect_uri`） | 拿到企微登录页 URL |
| 取二维码 | 解析登录页 HTML 中的 `qrcode?key=<16hex>` 与 `sessionSignature` → `GET …/wwlogin/sso/qrcode?key=…` | 二维码图片 |
| 轮询状态 | `POST …/wwlogin/monoApi/sso/login/getWebQrCodeStatus`（JSON: `webKey/lastStatus/openDataSid`） | `QRCODE_SCAN_SUCC` 时返回 `auth_code` |
| **换凭证** | `GET {CALLBACK}?code=<auth_code>&state=…`（跟随重定向） | 从落地 URL 提取 `token` |
| 取身份附属 | `GET {BASE_GET}/foreground/tannant/get-watermark` | 水印文字；uuid 取自登录 cookie `hl_uuid` |
| 校验凭证 | `GET {BASE_GET}/foreground/content/get-list`（`x-auth-token` 头） | 带 token 200 / 无 token 507（实测确认） |

要点：
- **账户附属信息（uuid / 水印）都是登录鉴权之后实时获取的**，登录本身不依赖它们（模块配置里没有任何账号信息）；
- 轮询间隔 0.8s（避免错过短暂的"已扫码待确认"状态）；轮询偶发超时（企微限流）忽略继续；
- 登录全程只访问固定官方主机，不引入任何本地服务、代理或第三方端点。

---

## 11. 配置与文件位置

| 项目 | 位置 |
|---|---|
| **连接配置** | 硬编码为 `login_leyou_cloud.py` 顶部的模块常量（`TENANT_ID` / `SITE` / `BASE_GET` / `CALLBACK` / `POLL_URL` / `QR_IMG_URL` / `UA`）；**不读取任何外部文件、不含任何账号信息**，换环境改常量即可 |
| **凭证** | 默认与数据区对齐（资产内运行时 = `common.LEYOU_TOKEN_F`；独立拷贝时 `~/.leyao-kb/leyou_token.json`）；`--token-file` 覆盖 |
| **存储方式** | 明文 JSON + 原子写；不做加解密（拿到文件即可用该凭证，**请勿外传**） |

环境变量：

| 变量 | 作用 |
|---|---|
| `LEYAO_KB_HOME` | 覆盖凭证存储目录（默认 `~/.leyao-kb`） |

---

## 12. 完整可复制示例

### 12.1 最简：拿凭证发请求

```python
from login_leyou_cloud import get_credential

cred = get_credential(force_relogin=False, interactive=False)  # 优先复用，不弹窗
print(cred["token"], cred["uuid"])
```

### 12.2 推荐：复用优先，失效才扫码

```python
from login_leyou_cloud import is_authenticated, verify_credential, relogin

if is_authenticated():
    cred = verify_credential()          # 复用，不弹窗
else:
    cred = relogin()                    # 弹窗扫码
```

### 12.3 后台 / AI 调用（先人工扫码一次，之后自动复用）

```python
from login_leyou_cloud import get_credential, LeyouLoginError

try:
    # interactive=True 才允许弹窗；后台一般先让人工在桌面跑一次 --reuse 扫码（会落盘），之后复用
    cred = get_credential(force_relogin=False, interactive=False, validate_remote=False)
except LeyouLoginError as exc:
    # 拿不到凭证 → 人工跑一次 `python login_leyou_cloud.py --reuse` 扫码
    raise SystemExit(f"凭证不可用：{exc.code} - {exc.message}")
```

### 12.4 命令行（供外部程序调用）

```bash
python login_leyou_cloud.py --reuse --no-remote --compact > cred.json
# 退出码 0 表示成功；cred.json 里就是完整凭证
```

### 12.5 不接受「自定义界面 / 出码」

本登录器**只有原生二维码窗口**一种形态：没有出码模式，也没有"回调自建界面"的用法。
`LoginFlow` 属内部组件（见第 5 节），外部请只用门面：

```python
from login_leyou_cloud import relogin, get_credential

if not get_credential(force_relogin=False, interactive=False).get("authenticated"):
    relogin()          # 弹二维码窗口，用户扫码后自动关闭并落盘
```

---

## 13. 注意事项 / 常见坑

1. **弹窗零依赖是刻意的**：tkinter 为标准库，Linux 若无 `python3-tk` 会导入失败——先 `--check` 并按其 `fix` 提示安装 tkinter 后重试（**本登录器不提供出码 / 无界面模式**）。
2. **`validate_remote=True` 依赖网络**：会真的请求一次云智库 `get-list`。网络抖动或限流时，即使本地凭证其实有效，也可能返回 `reason="not_validated"`——**不会弹窗**，重试即可；或 `--no-remote` 只做本地检查。
3. **明文凭证请勿外传**：凭证为明文 JSON，复制即用；换电脑、换用户后可直接搬运，但不要同步到网盘 / 提交到 Git / 放进整机备份。
4. **`relogin()` 会阻塞**：弹窗内部 `mainloop()` 等待用户操作；轮询在后台线程，窗口不会卡死。若在 AI / 服务里调用，请放在工作线程（本登录器不提供无界面模式）。
5. **只有「凭证本身不可用」才会弹窗**：网络、限流错误一律直接抛 `LeyouLoginError`，不会莫名其妙弹出登录窗——这是刻意的安全设计。
6. **二维码有效期**：默认 300 秒（`--wait` 可调）——失效时窗口内自动重载新码（≤3 次），仍失败才抛 `QR_EXPIRED`；二维码以**弹窗**展示（全程内存渲染，不落盘）。
7. **`expires_at` 是本地 30 天参考值**：服务端不下发过期时间；判断"现在算不算登录"请用 `verify_credential()`（远端为准）或业务客户端的 `status`。
8. **与业务客户端的关系**：`leyou_cloud.py` 的 `status` / `login` 子命令已转发本登录器（行为、输出、凭证文件不变）。
9. **包内零写入**：默认凭证路径即数据区（资产内运行时与桥接同一落点）；`leyou_bridge.py` 另经 `--token-file` 显式指向数据区——不要把凭证提交进包。
10. **独立单文件可整体拷走**：拷 `login_leyou_cloud.py` 到任何机器即可运行（`--status` 判定已有凭证、或扫码重登）；不依赖包内任何其它文件。
