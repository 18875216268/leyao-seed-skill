# 商品下载（API）

> 账号判定见 `sy.md §3.2`；任务轮询/下载见 `references/通用/api_导出任务.md`。下载=读取，无需写授权。

## 1. 下载

> 下载 = 获取数据，**不属于写入**，无需写授权。**筛选参数与 `api_商品读取.md §1.2` 的 `wsList` 完全一致**——任意查询条件（综合查询/多条件筛选/状态页签/类型/标签）都能原样导出。
> **职责边界**：本文负责"商品专属的查询条件生成、任务提交、导出列"；**任务轮询 / 下载 / 中断 / 任务状态 5 值**统一见 `references/通用/api_导出任务.md`，本文不重复。

### 1.1 商品专属导出接口

| # | 功能 | 方法 | 路径 | 必需参数 | 返回 |
|---|---|---|---|---|---|
| 3.1 | 生成查询条件 | POST | `/scm-goods/excelExport/getWsListEsQuery` | 与 `wsList` 同参（`pageNo=1`/`pageSize=10` 即可） | `{data:{sqlParams:"<ES query JSON 字符串>",wholesaleType:[]}}` |
| 3.2 | 提交商品导出任务 | POST | `/export-file/file/exportWholesaleDrug/v100` | `sqlParams`（①原始字符串）、`wholesaleType`（**JSON 字符串**如 `"[\"1\",\"4\"]"`）、`tabCode`、`templateType=10` | `{data:{recordId}}` |
| 3.3 | 提交组单中心导出 | POST | `/export-file/file/exportGroupOrderCenterWholesale/v100` | **仅公共参数** | `{data:{recordId}}`；需账号能力开关 `isGroupCenterOrder=1` |
| 3.4 | 导出入门价 | POST | `/scm-goods/wholesaleDrug/exportAccessPrice` | **仅公共参数** | **直接 XLSX 文件流**（非 JSON） |
| 3.5 | 导出未同意高风险品种 | POST | `/scm-goods/wholesaleDrug/exportNoAgreeHighRiskDrug` | **仅公共参数** | **直接 XLSX 文件流** |

**关键**：必须先调 ① 拿 `sqlParams` 再提交 ②，否则错配到订单/消息等无关模板。`sqlParams` 随查询条件变化（综合关键词→`multi_match` 6 字段、`drugName`→`match_phrase`、`status`→`range`/`term`、`condition=14`→`must_not terms`），任意查询结果均可精确导出。

> ① 返回的 `wholesaleType` 是**映射后的枚举名**（传 `["1","4","5","6","7","8","10","11","71"]` 返回 `["1","4","time_limit",null,"normal_group","8","10","11","clinic_group"]`）；② 提交时回传原数字数组/`[]` 均可成功。

**直接下载型（3.4/3.5）**：响应用 `r.content` 接；`openpyxl` 须**非 `read_only` 模式**（只读模式会因 `<dimension ref="A1"/>` 误判为 1 行 1 列）。实测：

| 接口 | 自营 | 摇钱树 |
|---|---|---|
| `exportAccessPrice` | 7,508 行 × 8 列（活动ID/商品ID/商品名称/规格/厂家/拼团主题/当前成团价/准入价） | 158 行 × 8 列 |
| `exportNoAgreeHighRiskDrug` | 246 行 × 4 列（活动ID/商品ID/商品名称/规格包装） | 1 行（仅表头）× 4 列 |

### 1.2 三个导出入口与 tabCode 映射

| 入口 | `status` | `tabCode` | 说明 |
|---|---|---|---|
| 导出指定状态数据 | 当前页签 `0~8` | 下表对应值 | 只导当前页签 |
| 导出所有状态数据 | `-1` | `all` | **不含已结束** |
| 导出组单中心活动 | — | — | 独立接口 §1.1 #3.3，无筛选 |

| status | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|---|
| tabCode | `on_sale` | `not_start` | `auto_off` | `price_audit_fail` | `off_sale` | `wait_audit` | `not_through` | `already_over` | `"8"`（字符串） |

> 9 个映射两账号全部实测：各 `status` 调 `getWsListEsQuery` 均 `40001`、`sqlParams` 各异且都含状态条件。

### 1.3 导出列

`exportWholesaleDrug/v100` 生成 CSV（**GBK**）= **64 基础列**（全账号一致）+ **动态列**。

**64 基础列**：

```
活动ID / 活动类型 / 是否托管活动 / 活动状态 / 主题名称 / 药品ID / 商品编码 / 商品名称
/ 批准文号 / 规格 / 厂家 / 单位 / app显示名称 / 活动备注 / 是否同步价格 / 建议价
/ 补贴 / 补贴前价格 / 返佣比例 / 返点比例 / 导单系数 / 购买倍数 / 采购起订量
/ 促销起始数量1 / 阶梯价1 / 促销起始数量2 / 阶梯价2 / 促销起始数量3 / 阶梯价3
/ 上限刷新周期 / 单店采购上限 / 是否同步库存 / 可用库存 / 库存可售天数 / 有效期至
/ 生产日期 / 业务商圈 / 供货对象 / 配送商 / 开单组合 / 是否控销 / 控销组 / 优惠标签
/ 经营范围 / 采购大类 / 采购亚类 / 采购小类 / 产地区域 / 详细产地 / 列表排序
/ 商品活动说明 / 活动时间 / 上架时间 / 建议零售价 / 中包装数 / 整件数量 / 采购店数
/ 采购总量 / 采购金额 / 运营标签 / 区域标签 / 追溯码 / 建议起拼低于 / 备注
```

**动态列**：`getPriceTypes` 每档一列（列名即 `priceTypeName`，数量随账号）、本公司编码、发货仓/推广字段（随账号配置出现）。

> **列数随账号与查询条件变化**，解析一律以实际表头为准：自营实测 **68 列 / 105 行**（关键词）与 **73 列 / 73,313 行**（全量）；摇钱树因 6 档价格列数不同。组单中心导出固定 23 列。

### 1.4 任务轮询与下载

> **见 `references/通用/api_导出任务.md`**：`getExportTaskRecord/v100` 轮询、`GET {qiniuUrl}` 下载（`Referer: https://scm.ysbang.cn/`，CSV GBK）、`interruptTask/v100` 中断、任务状态 `1`进行中/`2`等待中/`3`已完成/`4`异常/`5`已过期。同一导出列表汇总全系统所有板块任务。

**账号行为差异（实测）**：

| 项 | 自营 | 摇钱树 |
|---|---|---|
| 三段式 CSV | ✅ 全链路闭环（提交→延迟约 10 分钟转 `status=3`→产出 CSV→列核对） | 任务 `（示例任务号）` 持续 `status=4` 未产出（该账号历史任务曾成功）→ 需运营侧确认；可用 §1.1 直接下载型接口替代，详见 `sy.md §4.1 #1` |
| 短时 `status=4` | 不代表失败，勿立即重提（会触发限流），持续轮询 | 不能假定一定延迟转 3 |
| 导出任务记录 | 实测 5 条 | 新提交 1 条 |
| 动态价格列 | 5 档 | 6 档 |

> 任务可见范围随 token 不同（`cms_token` 会话仅见本账号新提交的任务）。
> **CLI 轮询实现（与本文一致）**：
> - `core/export_task.py` 的 `wait_url()` 把 `status=4` 当**短暂异常态继续轮询**，默认超时 **900 秒**（覆盖自营约 10 分钟转 3）。
> - 连续 `status=4` 超 600 秒才报 `EXPORT_FAILED`（提示勿重复提交）；`status=5` 立即报 `EXPORT_EXPIRED`。
> - 可用 `python scm.py export --poll-timeout <秒>` 按账号调整；失败提示均含「勿重复提交」，避免 `40003` 限流。

### 1.5 错误与限流

| 现象 | 原因 / 处置 |
|---|---|
| `40003 导出数据失败,您在一分钟内提交多次请求` | 提交过快；间隔 ≥75 秒，或退避 10 分钟 |
| `模板类型不能为空` | 缺 `templateType=10` |
| 任务名变成「订单明细」 | 缺 `sqlParams` 或 `templateType` 错 |
| 参数异常 | `wholesaleType` 混入非数字 |
| 列数不符预期 | 动态列随账号/条件变化，以实际表头为准 |

### 1.6 最小可用示例

```python
import json, time, requests

# ① 把任意 wsList 查询条件原样交给 getWsListEsQuery（只读）
# 全量导出：searchInfo 务必留空；仅按需填具体药品关键词（示例曾因填"999感冒灵"只导出单一药品）
q = {"pageNo":1, "pageSize":10, "status":-1, "searchInfo":"",
     "wholesaleType":[], "notThroughStatus":0, "saleStatType":1}
sql = post("/scm-goods/excelExport/getWsListEsQuery", q)["data"]["sqlParams"]

# ② 提交任务（下载=读取数据，无需写授权）
e = {"sqlParams": sql, "wholesaleType": json.dumps([]),
     "tabCode": "all", "templateType": 10}
rid = post("/export-file/file/exportWholesaleDrug/v100", e)["data"]["recordId"]

# ③ 轮询 → ④ 下载：见 `references/通用/api_导出任务.md §3/§5`
for _ in range(60):
    rec = post("/export-file/file/getExportTaskRecord/v100",
               {"pageNo":1,"pageSize":20,"totalRecord":0})["data"]["exportTaskRecordPageResult"]
    t = next((r for r in rec["results"] if r["recordId"] == rid), None)
    if t and t["status"] == 3 and t["qiniuUrl"]:
        url = t["qiniuUrl"]; break
    time.sleep(5)
raw = requests.get(url, headers={"Referer":"https://scm.ysbang.cn/"}, timeout=120).content
text = raw.decode("gbk", errors="replace")
```

> `post(path, body)` = `核心层 build_session` + 公共参数（见 `sy.md §3.3`）。CLI 等价写法见 `modules/goods/GUIDE.md`。
