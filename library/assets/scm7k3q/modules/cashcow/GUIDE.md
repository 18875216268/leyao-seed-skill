# 我的摇钱树（cashcow）

> 状态：🟡 **开放部分**（接口文档已交付、可按文档直接取数；CLI 暂未开放，`cashcow.query` 返回 `MODULE_TODO`）｜ 已知端点 **11** 个
> 账号归属：**摇钱树专属**（自营账号无此板块，越界不调用；归属唯一事实源 `references/sy.md §0.4`）
> 接口文档：`references/我的摇钱树/sy.md`（摇钱树销售流水 / 我的品种 / 区域划分查看）｜ 直连用 `python scm.py call`（`AGENT_GUIDE.md §4.1`）

## 1. 说明

- 摇钱树销售流水 / 我的品种 / 区域划分查看：接口、参数、字段见 `references/我的摇钱树/`（CLI 未开放；**只读查询**按文档直连）；
- **`ex` 按子板块取专属值**（实测确证，非空串）：销售流水 `MyCashcowSaleLog`、我的品种 `MyVariety`、区域划分 `RegionDivision`；`call` 时 `--ex <值>` 覆盖默认；
- **导出有服务端接口**：`exportSaleLogsAct`（流水）、`myVariety/export`（品种），均为 xlsx 文件流，`call --out` 落盘；
- **写接口（须 `AGENT_GUIDE.md §10` 授权）**：`myVariety/update`（单品价维护）、`myVariety/batchEditBottomPrice`（批量导入，multipart）；
- 端点明细与字段/枚举台账见 `references/我的摇钱树/zddz.md`。

## 2. 已知端点（11）

| # | 路径 |
|---|---|
| 1 | `/scm-setting/cashcoworder/saleLogsAct` |
| 2 | `/scm-setting/cashcoworder/saleLogsCountAct` |
| 3 | `/scm-setting/cashcoworder/exportSaleLogsAct` |
| 4 | `/scm-goods/areaGroup/getAreaCodeWithoutLimit` |
| 5 | `/scm-setting/myVariety/myDrugsAct` |
| 6 | `/scm-setting/myVariety/init` |
| 7 | `/scm-setting/myVariety/export` |
| 8 | `/scm-setting/myVariety/update` |
| 9 | `/scm-setting/myVariety/batchEditBottomPrice` |
| 10 | `/scm-base/provider/getProviderDelivers` |
| 11 | `/scm-base/provider/getAreaPriceList` |

> 「拼团最低供乐药价维护」候选端点 `/scm-goods/cashcow/editMinLeyoPrice`（静态分析·未实测）已登记在 `modules/marketing/__init__.py`，本板块以交叉引用说明，详见 `references/我的摇钱树/api_我的品种.md §3.3`。

## 3. 参考

- `references/我的摇钱树/sy.md`（板块索引与使用约定）
- `references/我的摇钱树/zddz.md`（页面口径 ↔ 代码字段 ↔ 枚举字典）
- `references/附录/接口总表.md`（全量端点索引，#539~#549）
