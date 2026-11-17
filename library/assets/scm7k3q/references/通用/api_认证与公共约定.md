# 认证与公共约定（API）

> 本文件是**所有接口的前置约定**，仅此一处定义，其他文档引用不再复制。
> 适用：全部 SCM 商家后台接口。
>
> ⚠️ **公共参数示例值勿照抄**：各接口文档 JSON 示例里的 `token`/`lastBuildTime`/`version`/`ua`/`ex` 是**抓包快照**，取值不一（`lastBuildTime` 有 `2026-11-09 20:28`、`2026-11-13 17:12` 等，`version` 有 `1.0.0`/`1.0.3`）。经 `scm.py call` 发请求时这些由请求层**按公共约定自动注入**（部分板块 `version=1.0.0` 且不带 `lastBuildTime` 的特例见各接口文档），Agent 只需填业务字段；手写脚本时按本文件生成，勿复制示例里的历史值。

## 1. 基础信息

| 项 | 值 |
|---|---|
| 协议 | HTTPS |
| 基础地址 | `https://scm.ysbang.cn` |
| 请求格式 | `POST` + `Content-Type: application/json;charset=UTF-8` |
| 响应 | 恒为 HTTP 200，业务状态看 `code` |
| 成功码 | `code == "40001"` |

## 2. 认证三要素

| 要素 | 来源 | 用法 |
|---|---|---|
| `token` | 登录成功后取得（32 位） | 放在**请求体**每个接口的公共参数里 |
| Cookie（含 `cmsToken`） | 登录 Cookie + `GET /provider.php/Admin/Index/indexJava` 响应 `data.cmsToken` | 随请求发送；**缺 `cmsToken` 调 Java 服务会返回 `40020`** |
| `provideridm` | `md5(providerId)`，如 `md5(<当前 providerId>)` | 放在**请求头**，部分接口必需 |

> `providerId` 取自登录信息或 `POST /scm-goods/wholesaleDrug/getProviderInfo4List2` 的 `data.providerId`。

### 2.1 【实测坑】凭证里 `token` 与 `cms_token` 的取舍（2026-11-08）

归档凭证 JSON（如 `%LOCALAPPDATA%/scm-operations-query/accounts/credential_<account>.json`）含多个 32 位 token 字段：`token`、`token_sy`、`token_hp`、`cms_token`，**它们不是同一个身份**：

| 字段 | 实测（2026-11-08） | 说明 |
|---|---|---|
| `token` | `40020 该操作需要登录` | 会先失效（登录态过期 / 网页端重登挤掉会话） |
| `token_sy` / `token_hp` | `40020 该操作需要登录` | 同样失效 |
| **`cms_token`** | **`40001 success`** ✅ | 仍有效；等同于 §2 表格里 `indexJava` 返回的 `data.cmsToken` |

**正确取值**（agent 照抄）：
```python
tok = str(cred.get("cms_token") or cred.get("token"))
body = {**public_params(tok), ...业务参数}
```
- 不要直接用 `cred["token"]`；`40020` 的含义见 `core/http.py::_CODE_HINT`（「会话缺少 cmsToken 或 token 无效」），**优先换 `cms_token` 重试，而不是立刻重新登录**。
- 严禁脚本内调 `scm.py login`（弹 GUI 挂死，且需人工验证码/企微扫码）。
- **已封装**：`python scm.py call` 自动按上述口径取 `cms_token or token` 并注入公共参数六件套，Agent 不必手工取字段（用法见 `AGENT_GUIDE.md §4.1`）。
- **可见范围差异**：`cms_token` 会话下 `getExportTaskRecord/v100` 仅见本账号自己的任务（实测 2 条），`token` 有效时曾见全系统 1946 条 → 排查导出任务时务必确认用的是哪个 token。

## 3. 公共参数（请求体，几乎所有接口必带）

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `token` | string | 是 | 登录业务 token |
| `platform` | string | 是 | 固定 `scm-admin` |
| `version` | string | 是 | 固定 `1.0.3` |
| `ua` | string | 是 | 浏览器 UA，如 `Mozilla/5.0 Chrome 120` |
| `ex` | string | 是 | 页面来源标识，商品列表为 `goodsOnShelves` |
| `lastBuildTime` | string | 是 | 当前时间 `YYYY-MM-DD HH:MM` |

## 4. 请求头

| 头 | 值 |
|---|---|
| `Content-Type` | `application/json;charset=UTF-8` |
| `Referer` | `https://scm.ysbang.cn/web-scm-admin/web/index.html` |
| `Origin` | `https://scm.ysbang.cn` |
| `provideridm` | `md5(providerId)` |

## 5. 状态码与错误

| `code` | 含义 | 处理 |
|---|---|---|
| `40001` | 成功 | — |
| `40000` | 登录失效 / 会话过期 | 重新登录 |
| `40020` | token 无效或 Cookie 缺 `cmsToken` | 检查 token 与 cmsToken |
| `40003` | 提交过于频繁（1 分钟 / 10 分钟窗口） | 退避后重试（导出提交尤其常见） |
| `40004` | 参数异常 | 检查参数名与类型（如 `storeType` 传数组会报此错） |

## 6. 编码与数据格式

| 项 | 说明 |
|---|---|
| 请求体 | UTF-8 JSON |
| 导出文件 | CSV，**GBK** 编码 |
| 时间格式 | 一般 `YYYY-MM-DD HH:mm:ss`；日期筛选必须**成对**且带时分秒 |
| 数组参数 | 部分接口要求数组（如 `wholesaleType`），部分要求 JSON 字符串（如导出提交），逐接口注明 |

## 7. 登录流程（简述）

```
GET  /provider.php/admin/public/login                 建立会话（PHPSESSID）
GET  /provider.php/Admin/Public/captcha?{ts}          取图形验证码（人工识别）
POST /provider.php/Admin/Public/postLogin             account + md5(password) + captcha + remember
     ├─ info="登录成功"  → Cookie 含 ysbang_adminToken，直接可用
     └─ info="请扫码登录" → 走企微扫码：loginWx → 二维码 → 轮询 → postLoginWx
GET  /provider.php/Admin/Index/indexJava              取 cmsToken（并入 Cookie）
POST /scm-base/provider/getProviderLoginInfo          取 providerId 等
```

> 登录工具：`scripts/scm_login.py`（独立单文件；验证码需人工输入）。

## 8. 快速自检

1. 用公共参数调 `POST /scm-goods/wholesaleDrug/getProviderInfo4List2`，返回 `40001` 即鉴权正常；
2. 若返回 `40020`，检查 Cookie 是否含 `cmsToken`；
3. 若返回 `40000`，token 已失效，需重新登录。

## 9. 分页约定（五套，勿混用）

| 体系 | 分页参数 | 适用接口 |
|---|---|---|
| 新版 CRM | `page` + `pageSize` | `crm/list`、`crm/getProStoreGroupList` |
| 控销 / 黑名单 / 导出任务 | `pageNo` + `pageSize` | `saleControl/*`、`getExportTaskRecord` |
| 订单列表 | `page` + `pagesize`（全小写 s） | `scm-order/wholesaleOrder/*`（响应外壳仍是 `pageNo/pageSize`） |
| 老版 PHP 弹窗 | `page` + `pagesize`（全小写 s） | `provider.php/Admin/Drugstore/storeList`、`changeTag` 等 |
| **PMS 域** | **`page` + `pageSize`** | `pms-main/*`（多数还需 `providerId`，见 `商品/api_pms活动管理.md §2.3`） |

- 页码从 1 开始；**接口默认 `pagesize=10`（订单/老版 PHP 全小写 s），本技能 CLI 的 `--limit` 默认 20**——两者不同，勿混。
- 客户列表每页可选 10 / 50 / 100 / 200。
- 响应分页外壳：`data.{pageNo, pageSize, totalRecord, totalPage, results[]}`（`crm/*` 请求用 `page`，响应里叫 `pageNo`）。
- 写错参数名会被忽略（返回第 1 页）。
- 商品 `wsList` 的分页以其 `references/商品/api_商品读取.md §1.2` 为准。
