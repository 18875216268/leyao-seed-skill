# 订单（板块索引）

> **板块归属（板块内单独说明）**：本板块 **自营专属**（对应菜单「订单 - 订单列表」）；归属唯一事实源与两账号板块地图见 `references/sy.md §0`。
> 状态（**接口文档层**）：**查询 + 导出 + 详情只读均已交付**。其中**查询有 CLI 命令**；导出/详情按本文 §1 的 `api_*.md` 直连（`scm.py export` 未封装订单，只会返回 `MODULE_TODO`）。写操作（改单/退款/备注等）不在本板块范围内。
> 本文是订单板块入口：子板块地图、已实现功能、端点边界、阅读顺序。
> 依据采集 + 2026-11-12 浏览器逐字段复测：`zddz.md §1.3` 的 35 个筛选参数**已全部实测锁定 ✅**；其余未覆盖项见各 `api_*.md` 的「待实测」标注。

## 1. 子板块地图

| 子板块 | 文档 | 内容 |
|---|---|---|
| 订单查询 | `api_订单查询.md` | 列表 `wholesaleOrder/list`、页签计数 `tabCount`、共用列表 `listCommon`、实时概览 `realTimeOrderInfo`、融合状态 `fusedStatusInfo` |
| 订单导出 | `api_订单导出.md` | 直接 CSV（`batchExportOrder`/`exportProviderOrder`）+ 自定义导出（`exportOrderData` + 字段组/模板/任务轮询） |
| 订单详情 | `api_订单详情.md` | 药店证件 `getCertificateData`、业务员 `getSalesmenUserInfo`、开票 `getDrugstoreInvoiceInfo`、质检报告 `getApplyDrugCheckData` |

> 字段/值域统一在 `zddz.md`（筛选参数↔界面、返回字段、证件/开票/业务员/导出字段、异常标签映射）。

## 2. 已实现功能

| 能力 | 状态 | 说明 |
|---|---|---|
| 订单列表 | ✅ 只读 | 标签筛选 / 状态筛选 / 基础查询 / 展开更多搜索（`order_time` 数组、分页 `page`/`pagesize`） |
| 页签计数 | ✅ 只读 | `tabCount` 返回 `tab1`~`tab9`（状态页签计数） |
| 实时概览 | ✅ 只读 | `realTimeOrderInfo`（新单/待审退款/未发货等计数） |
| 药店证件 | ✅ 只读 | `getCertificateData`（营业执照/身份证/委托书/执业许可证） |
| 业务员 | ✅ 只读 | `getSalesmenUserInfo`（名称/手机/二维码） |
| 开票信息 | ✅ 已实机验证 | `getDrugstoreInvoiceInfo`，见 `api_订单详情.md §3` |
| 质检报告 | ✅ 只读 | `getApplyDrugCheckData`（申请报告数据；参数待补，见 `api_订单详情.md §5`） |
| 直接导出 CSV | ✅ 接口文档已交付 | `provider.php/Admin/ApiRouter/batchExportOrder`（GET） |
| 自定义导出 | ✅ 接口文档已交付（部分参数待实测） | `exportOrderData/v100`（异步通用导出中心 → `getExportTaskRecord` 轮询下载） |

## 3. 端点边界

- 查询/详情接口文档已交付（查询另有 CLI）：`list`/`tabCount`/`listCommon`/`realTimeOrderInfo`/`fusedStatusInfo`/`getCertificateData`/`getSalesmenUserInfo`/`getApplyDrugCheckData`。
- 导出接口文档已交付（CLI 未封装）：`batchExportOrder`/`exportProviderOrder`/`exportOrderData`/`getSelectFields`/`getAllCustomizeTemplate`/`getExportTaskRecord`。
- 模块的 `ENDPOINTS` 清单共 **85** 个端点；导出/详情端点另见 `references/附录/接口总表.md`，未实现部分仅登记。
- CLI 用法与参数映射见 `modules/order/GUIDE.md`；**订单导出/详情 CLI 未封装**，用 `scm.py call`（`AGENT_GUIDE.md §4.1`）按 §1 的 `api_*.md` 构造请求，调用 `scm.py export` 只会得到 `MODULE_TODO`。
- 分页：列表请求用 `page` + `pagesize`（小写 s）；响应外壳 `data.{pageNo, pageSize, totalRecord, totalPage, results[]}`。
- **覆盖度说明**：`zddz.md §1.3` 的 35 个「展开更多搜索」参数已全部浏览器实测锁定 ✅；异常标签计数接口见 `api_订单详情.md §6`（部分标注待复验）。

## 4. 阅读顺序

1. 先看 `zddz.md` 了解「界面字段 ↔ API key」总表（含覆盖度标注）；
2. 列表/计数调 `api_订单查询.md`；
3. 导出调 `api_订单导出.md`；
4. 点开某订单看证件/业务员/开票/报告调 `api_订单详情.md`；
5. 其余订单端点先查 `references/附录/接口总表.md`，未实现前不要臆造参数。
