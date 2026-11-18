---
name: Tms流量投放v1.00
description: PMS TMS 三板块（促销费用管理 / 促销活动管理 / 优惠券统计）的查询、导出与写操作指引。当用户问 TMS 促销费用池、投流活动、用券统计、子公司地区汇总、券台账时使用；与 Pms-商品活动管理(pmsact01)、促销毛利(psol5x) 区分。
---

# Tms 流量投放 v1.00

> 框架生态提示：本资产位于 p3nes3 包的 `library/assets/` 下 → 使用前先回主框架读 `library/ROUTES.md` 与父 `p3nes3/app.md`〈登录（唯一入口）〉；独立安装态不受此限。
> 版本：v1.00 ｜ 知识基线 ｜ 归属：p3nes3 子 skill ｜ **自包含**：4 文档 + 1 发送器全在本目录，零外部依赖。

## §1 凭证（由调用方传入，本包不登录）
本包**不实现登录**：不获取、不生成、不存储凭证，也不读父凭证仓库。调用方拿到 PMS token 后按任一入口传入：
1. `--token <token>`（单次）；2. 环境变量 `PMS_TOKEN`（多次推荐）；3. `--state-file PATH` / `PMS_STATE_FILE`（调用方自备文件，仅读 token 字段）。
公司口径 providerId 由调用方指定（`--payload-file` 内 `providerIds`）；凭证缺失或 40005/40006/40007/40050 → **报错并请调用方提供新凭证**，本包不自行重登、不换源拼接 ✗。

## §2 何时用 / 不适用
**何时用**：TMS 促销费用池（建档/查询/明细/导出）；TMS 促销活动投流（按商品或平台活动 ID 建活动/复制/提前结束/补贴订单）；优惠券用券统计（Tab1 用券效果 / Tab2 子公司地区汇总 / Tab3 券台账）。
**不适用**：PMS 商品活动管理（一口价/特价上下架/限购/调价审批）→ `pmsact01`；促销毛利（当天实时/历史）→ `psol5x`；SCM 优惠券创建/抢券 → `scm7k3q`；SCM 商品/订单/客户 → `scm7k3q`。如实告知，不混用 ✗。

## §3 核心流程
1. 调用方传 token → 2. 选板块与接口（§4）→ 3. 组装 payload（§5；本包发送器自动注入 token+buildTime）→ 4. 查询/导出走 §6 命令 → 5. 写操作（新增/编辑/结束/导入）**只输出方案，须用户授权 + 留回滚信息 + 写后复验** → 6. 结果按口径呈现，数字带来源。

## §4 接口速查（三板块）
### 促销费用（domain=ley）
- 查询 R1：`POST /operation-service/promotion-expense/page/v100`（近30天、`providerIds[]`、page/pageSize）
- 详情 R2：`POST /operation-service/promotion-expense/detail/v100`（`{"id":<ID>}`）
- 导出 E1：`POST /pms_operation/web/pms/promotion-expense/export/v100`（异步，fileType=206）→ `/operation-service/promotion-activity-export-task/list` 轮询 `fileStatus`
- 写 W1-W4：add / update / finish / 导入（⚠️需授权）

### 促销活动（domain=ley）
- 查询 R3：`POST /operation-service/promotion-activity/page/v100`（`expenseId`/活动名/近30天）
- 详情 R4：`POST /operation-service/promotion-activity/detail/v100`；补贴明细 `subsidy-order-page/v100`
- 导出 E2：`POST /pms_operation/web/pms/promotion-activity/export/pv29230`（异步，fileType=207）+ 轮询；部分结束 `partial-finish/v100`
- 写 W5-W8：add / copy / finish / partial-finish / 导入（⚠️需授权）

### 优惠券统计（domain=ley；券台账可能 ysb）
- Tab1 R5：`/pms_operation/web/coupon/couponStatisticsTotal/pv1070`（汇总卡）+ `couponStatisticsTable/pv1070`（明细）
- Tab2 R6：`/pms_operation/web/coupon/couponCompony/pv1070`（dimension=1 子公司 / 2 地区 / 3 下钻）
- Tab3 R7：`/pms-main/.../couponList/v740` 或文档标注域（ysb）
- 导出 E3：`couponStatisticsExport`/`couponComponyExport`/`exportCouponList`（同步下载）

## §5 常用 payload 模板
查询（费用/活动）：`{"providerIds":[<公司ID>],"createTimeStart":"YYYY-MM-DD 00:00:00","createTimeEnd":"YYYY-MM-DD 23:59:59","page":1,"pageSize":10}`（token/buildTime 由发送器注入）
统计（券）：`{"beginDate":"YYYY-MM-DD","endDate":"YYYY-MM-DD","timeType":2,"pageNum":1,"pageSize":10,...}`（token/buildTime 自动注入）
> 写操作模板见 `references/promotion-expense.md` §5 / `promotion-activity.md` §5——**须授权后才可组装执行**。

## §6 命令（自带自包含发送器；不调用父 pms_call.py）
工作目录＝本子包目录（`.../tmstraffic01/`）：
```bash
python scripts/tms_call.py --domain ley \
  --path /operation-service/promotion-expense/page/v100 \
  --payload-file query.json --token <token> --out-file result.json
# 多次调用推荐：export PMS_TOKEN=<token>；--build-time 可覆盖默认构建时刻
```
- `--domain ley|ysb` 内置双域常量，不读 `sync_config.json`；`/operation-service/` 自动带 Bearer
- `--build-time`：默认 `2026-11-17 18:42:50`；若 token 有效却 40006/40007，请调用方提供其页面当前 buildTime
- 参数以 `python scripts/tms_call.py --help` 为准

## §7 按需读取（全在本目录，无外部指针）
- `references/overview.md`：三板块总览、鉴权、错误码、导出机制
- `references/promotion-expense.md`：促销费用全字段/筛选项/写操作/导出
- `references/promotion-activity.md`：促销活动全字段/写操作/导入/导出
- `references/coupon-statistics.md`：用券统计三 Tab + 地区汇总 + 台账

## §8 强制规则
1. 零外部依赖：不 import 父模块、不读 `sync_config.json`、不调父发送器、不用 requests、不读任务区 ✗
2. 凭证只由调用方传入；本包无凭证获取逻辑、不读父凭证仓库；401 类错误只报错并请调用方提供新凭证 ✗
3. 写操作须用户授权 + 回滚信息 + 写后复验；只描述不擅执行 ✗
4. 导出假成功：`lineUpNumber` 只是排队，须轮询 `fileStatus` 确认
5. 空筛选导出：促销两板块默认带公司/时间范围，全量须显式清空
6. 数字带口径（时间/主体/含税与否）；code=40001 是成功不是错误
7. 品种/商品编码等 ID 完整不截断；表格优先、结论先行
8. 输出契约：stdout 只给摘要（code/shape/输出路径），不得输出 token/凭证/密码；详细响应写 `--out-file`
