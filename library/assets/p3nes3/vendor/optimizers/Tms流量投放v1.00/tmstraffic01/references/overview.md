> **框架内自包含副本** ｜ token 由调用方通过 `--token`/`PMS_TOKEN`/`--state-file` 传入；本包不登录、不读父凭证仓库。
> `buildTime` 通过 `--build-time` 可选传入（默认 `2026-11-17 18:42:50`）；凭证/构建异常只报错，不自行登录。
> 原始归档已剥离（实测身份与过程路径不随包，以本副本为准）。

# PMS TMS 三板块 API 总览与调用指南（面向 Agent）

> 生成：2026-11-17 ｜ 方法：webpack 源码静态逆向 + 真实 HTTP 请求实测（抓取请求/响应模板）
> 适用：让不懂代码的人通过 Agent 完成数据查询与导出；写操作须用户授权 + 留回滚信息 + 写后复验（框架红线）

## 一、通用约定（三板块一致）

### 1. 真实服务域名与路径
- 页面入口：`https://pms.ysbang.cn/#/tms/...`（前端 SPA，hash 路由）
- **API 实际域名**：`https://pms.leyopharm.com`（部分老接口仍在 `https://pms.ysbang.cn`，如 `/pms-main/coupon/...`）
- 接口前缀两类：
  - `/operation-service/...`（业务服务，v100 版本）
  - `/pms_operation/web/...`（PMS 操作服务，导出/统计，pv1070 / pv29230 版本）

### 2. 鉴权与公共参数（所有接口必带）
实测每个请求 body 都自动注入：
```json
{"token": "<登录态 token>", "buildTime": "<BT>"}
```
- `token`：由调用方通过 `--token`/`PMS_TOKEN`/`--state-file` 传入（子包不登录、不读父凭证仓库）
- `buildTime`：前端构建时刻字符串（源码 `79851.D()` 注入）；由 `--build-time` 可选传入，默认 `2026-11-17 18:42:50`；若 token 有效却 40006/40007，请调用方提供其页面当前 buildTime
- **源码已确认的注入逻辑**（app.js module 79851，此前 ⚠️ 现已攻克）：
  - `token` 来源 `T()` = `vuex getters.token || sessionStorage.getItem("token")`
  - `D()` 同时把 token 写入 **body 和 header**；body 每个 string 参数做 `.trim()`
  - `/operation-service/` 前缀额外注入 header `Authorization: Bearer <token>`（三板块促销接口均属此类）
  - 层公共头 `N()`：`__module__`/`module`（路由 meta.module）、`appVersion:"14.30.1"`、`platform:"web"`、`timestamp`（秒级）——前端增强，服务端非强制
  - **Agent 直连最小必需**：body 带 `token`+`buildTime`，header 带 `token`（实测即成功）
- **调用方式**：用本包 `scripts/tms_call.py`（urllib 标准库）发送 POST 到 API 域名，body 带 `token`+`buildTime`、header 带token；token 由调用方传入（--token/PMS_TOKEN/--state-file）

### 3. 统一响应格式
```json
{"code": "40001", "message": "操作成功/请求成功", "data": {...}}
```
- `code=40001`：PMS 的成功码（**不是错误**，与 SCM 一致）
- 列表分页字段：促销两板块用 `data.list` + `data.count`；优惠券统计用 `data.records` + `data.total`；导出任务列表用 `data.list` + `data.count`，返回前前端改写为 records/total

### 4. 导出机制（重要）
促销费用/促销活动的导出是**异步任务**，不是直接返回文件：
1. 调导出接口 → 返回 `exportInfoId` / `lineUpNumber`（排队号）/ `estimateTime`
2. 到「批量任务列表」查任务：`/operation-service/promotion-activity-export-task/list`，带 `fileType`（206=促销费用，207=促销活动）
3. 任务 `fileStatus=0` 导出中，完成后 `url` 出现下载链接
优惠券统计的导出是**同步下载**（`Ay.download`，直接返回文件流）

### 5. 时间/格式约定
- 促销两板块：时间 `YYYY-MM-DD HH:mm:ss`；默认最近 30 天（活动）/ 最近 30 天（费用）
- 优惠券统计：日期 `YYYY-MM-DD`；`timeType` 时间类型（支付时间/出库时间，实测默认 2）

## 二、三板块速查

| 板块 | 页面 | 核心查询接口 | 核心导出接口 | 详细文档 |
|---|---|---|---|---|
| 促销费用管理 | `#/tms/promotion-cost-management` | `POST /operation-service/promotion-expense/page/v100` | `POST /pms_operation/web/pms/promotion-expense/export/v100`（异步） | [01-促销费用管理-API.md](01-促销费用管理-API.md) |
| 促销活动管理 | `#/tms/promotion-activity-management` | `POST /operation-service/promotion-activity/page/v100` | `POST /pms_operation/web/pms/promotion-activity/export/pv29230`（异步） | [02-促销活动管理-API.md](02-促销活动管理-API.md) |
| 优惠券统计 | `#/tms/coupon-statistics` | `POST /pms_operation/web/coupon/couponStatisticsTable/pv1070`（Tab1）+ 2 个 Tab 接口 | `POST /pms_operation/web/coupon/couponStatisticsExport/pv1070`（同步） | [03-优惠券统计-API.md](03-优惠券统计-API.md) |

## 三、典型场景（Agent 操作指南）

### 场景 1：查促销费用列表
1. 确认调用方 token 已传入
2. POST `/operation-service/promotion-expense/page/v100`，body = 默认模板（见 01 文档 §3.1）+ token/buildTime
3. 读 `data.list[]`，字段如 `expenseCode`（费用ID）、`expenseName`、`amount`、`availableAmount`

### 场景 2：导出促销活动数据
1. POST `/pms_operation/web/pms/promotion-activity/export/pv29230`，body = 查询参数去掉 page/pageSize + `fileName`
2. 记下 `exportInfoId`
3. POST `/operation-service/promotion-activity-export-task/list`，body 带 `fileType:207`，找到该任务，`fileStatus` 完成后取 `url` 下载

### 场景 3：查优惠券使用统计
1. POST `/pms_operation/web/coupon/couponStatisticsTable/pv1070`（明细表）和 `couponStatisticsTotal/pv1070`（汇总卡），body = 统计模板（见 03 文档）
2. 表字段 `couponName`/`taxAmount`/`orderNum`/`discount` 等

### 6. 统一错误码表（源码 module 79851 `S`，已确认）
| code | 含义 | Agent 处理 |
|---|---|---|
| 40001 | 成功 | 正常读 data（不是错误） |
| 40005 | 未登录 | 凭证失效，报错并请调用方提供新凭证 |
| 40006 / 40007 | 无权限 / token过期 | 凭证失效，报错并请调用方提供新凭证 |
| 40050 | 功能鉴权拒绝 | 账号无该接口权限，停止 |
| 40000 | 版本升级 | 前端 reload，稍后重试 |
| 40003 / 42054 / 45600 | 参数错 / 自定义错误 / 业务停止推进 | 读 message |
| 52080 | 告警（含禁采名单弹窗） | 读 message/data |
| HTTP≠200 | 网关/网络层错误 | 重试或检查网络 |

## 四、红线与注意事项
- **写操作（新增/编辑/结束/导入）只描述接口，不实际执行**；本文档写操作章节供了解，Agent 执行前必须取得用户授权并说明影响
- 费用/活动的"新增"是复杂表单（含商品明细、客户圈选、金额校验），见各板块文档写操作章节
- 导出假成功：`lineUpNumber` 只是排队成功，需到批量任务列表确认 `fileStatus`
- 空筛选导出：促销两板块默认带了公司/时间范围，要全量导出须显式清空这些字段
- token 注入逻辑已从 app.js module 79851 完整提取（见 §2），首轮此项 ⚠️ 已消除

## 五、证据与局限性
- 所有接口路径来自 webpack chunk 源码（module ID 见各文档），请求/响应模板来自真实 HTTP 请求实测（2026-11-17）
- 未实测：写操作（红线）、token 刷新逻辑（源码见 79851 `FedLogOut` 分支，未实际触发）
- 仍存不确定性（已尽力，非臆测）：`dimension` 子公司值源码=1 但未抓到该维度实测响应；部分深层字典接口完整响应未逐一实测
