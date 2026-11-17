# 我的摇钱树（板块索引）

> **板块归属（板块内单独说明 · 摇钱树专属）**：对应摇钱树账号「我的摇钱树」板块（3 个子板块）；**自营账号无此板块**，越界不调用、不试探（`references/sy.md §0`）。
> 状态：**接口文档已交付（经摇钱树账号实时导航 + 导出/写动作抓包验证 2026-11-16，零业务影响），CLI 暂未开放**（`python scm.py query --module cashcow` 返回 `MODULE_TODO`）。取数用 `python scm.py call`（`AGENT_GUIDE.md §4.1`）按本文档构造请求。
> 本文是我的摇钱树板块入口：子板块地图、端点清单、账号与请求约定、阅读顺序、边界。
> 路径基准：`references/…` 相对技能包根（本资产根）。

## 1. 子板块地图

| 子板块 | 文档 | 覆盖内容 | 端点 |
|---|---|---|---|
| 摇钱树销售流水 | `api_摇钱树销售流水.md` | 流水列表、计数、省市区级联、**导出 xlsx** | 4 |
| 我的品种 | `api_我的品种.md` | 品种列表、筛选配置、**导出 xlsx**、价格维护（写）、导入维护价格（写）+ 拼团最低供乐药价维护候选（交叉引用） | 5 |
| 区域划分查看 | `api_区域划分查看.md` | 配送商下拉数据源、区域价格列表 | 2 |

> 三个子板块均为 **② 仅摇钱树**（归属唯一事实源 `references/sy.md §0.4`）。

## 2. 端点清单（11 个，全部 `POST`）

| # | 端点 | 用途 | 分类 |
|---|---|---|---|
| 1 | `/scm-setting/cashcoworder/saleLogsAct` | 销售流水列表（9 态页签） | 读取 |
| 2 | `/scm-setting/cashcoworder/saleLogsCountAct` | 销售流水计数/统计 | 读取 |
| 3 | `/scm-setting/cashcoworder/exportSaleLogsAct` | 销售流水导出 xlsx | 导出 |
| 4 | `/scm-goods/areaGroup/getAreaCodeWithoutLimit` | 省市区级联字典（区域筛选数据源） | 读取·字典 |
| 5 | `/scm-setting/myVariety/myDrugsAct` | 我的品种列表（分页） | 读取 |
| 6 | `/scm-setting/myVariety/init` | 我的品种筛选配置初始化 | 读取·字典 |
| 7 | `/scm-setting/myVariety/export` | 我的品种导出 xlsx | 导出 |
| 8 | `/scm-setting/myVariety/update` | 单品价格维护（`updateType` 选目标：底价等） | **写** |
| 9 | `/scm-setting/myVariety/batchEditBottomPrice` | 导入维护价格（批量，multipart） | **写·上传** |
| 10 | `/scm-base/provider/getProviderDelivers` | 配送商列表（区域划分筛选项数据源） | 读取·字典 |
| 11 | `/scm-base/provider/getAreaPriceList` | 区域价格列表（按配送商） | 读取 |

> **只读 7 / 导出 2 / 写 2**。写接口执行前须按 `AGENT_GUIDE.md §10` 授权，留回滚值 + 审计日志，只改需求范围内字段。
> **附（不重复登记）**：「拼团最低供乐药价维护」候选端点 `/scm-goods/cashcow/editMinLeyoPrice`（静态分析·未实测）已登记在 `modules/marketing/__init__.py` 静态清单；参数未确证前不得调用，详见 `api_我的品种.md §3.3`。

## 3. 使用约定

1. **请求形态**：`POST`，`Content-Type: application/json;charset=UTF-8`（批量导入例外，为 `multipart/form-data`）。
2. **公共参数**（每个请求都带）：`token`/`platform`/`version`/`ua`/`ex`/`lastBuildTime` + 分页 `pageNo`/`pageSize`。
3. **⚠️ `ex` 按子板块取专属值**（2026-11-16 实测确证，**非空串**）：

   | 子板块 | `ex` |
   |---|---|
   | 摇钱树销售流水 | `MyCashcowSaleLog` |
   | 我的品种 | `MyVariety` |
   | 区域划分查看 | `RegionDivision` |

   `call` 时用 `--ex <值>` 显式覆盖默认 `goodsOnShelves`。
4. **鉴权**：会话 cookie（`ysbang_adminToken`）+ body `token`；复用 `core.credential` 凭证，见 `references/通用/api_认证与公共约定.md`。**必须登录摇钱树账号**（自营凭证调用会因账号体系隔离失败或越界）。
5. **成功码**：`40001`；HTTP 恒 200。
6. **分页**：流水/品种列表 `data.results[]` + `totalRecord`/`totalPage`（`pageNo` 从 1 开始）；区域划分两个接口无分页。
7. **数组参数**：`deliveryProvider`/`province`/`city`/`district` 均为数组；区域传数字 `areaCode`（级联接口 #4 取值）。

## 4. 阅读顺序

1. 本文 §1 选子板块 → 进对应 `api_*.md`；
2. 字段名/枚举不确定 → `zddz.md`（页面口径 ↔ 代码字段 ↔ 字典）；
3. 鉴权与公共参数 → `references/通用/api_认证与公共约定.md`；
4. 写操作 → 先 `AGENT_GUIDE.md §10`，再进 `api_我的品种.md §3`；
5. 端点在附录的位置 → `references/附录/接口总表.md`（#539~#549）。

## 5. 边界与待确认

| # | 项 | 现状 |
|---|---|---|
| 1 | 导出 xlsx | **已有服务端接口**（`exportSaleLogsAct` / `myVariety/export`，文件流）；`call --out` 落盘 |
| 2 | 我的品种写接口 | **已捕获**：`update`（单品价维护，`updateType` 选目标）、`batchEditBottomPrice`（批量导入，multipart）；另 `cashcow/editMinLeyoPrice` 为静态候选（未实测）；写需授权 + 审计 |
| 3 | 页面筛选项与接口参数差异 | 销售流水：列表带时间不带 id，导出带 id 不带时间（页筛项为并集，见流水 `§2.4`）；我的品种：`drugId` 仅导出接口实测 |
| 4 | `updateType` 语义 | 实测仅 `2`（→`bottomPrice`）；`1` 推断为「拼团最低供乐药价」但**采集与逆向资料均无枚举定义**，待补抓包确证 |
| 5 | 批量导入文件字段名 | multipart 已确证，**文件表单字段名在采集/逆向资料中均缺失**（采集器未记录请求体）；模板列 3 种组合已知（见 `api_我的品种.md §3.2`） |
| 6 | `wholeSaleType*` 映射 | 我的品种 14 个键值为 0/1 标志位，与「一口价/拼团/批购包邮 × 进行中/已暂停」的映射**未定谳** |
| 7 | 字典缺口 | 销售流水 `orderStatus` 筛选入参码值、`op` 完整枚举、`wholesaleType` 全码、结算状态全码待积累；已实测项见各 `api_*.md §4` |
