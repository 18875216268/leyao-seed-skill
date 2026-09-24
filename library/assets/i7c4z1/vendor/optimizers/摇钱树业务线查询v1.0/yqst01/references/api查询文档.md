# 摇钱树业务线 · API 查询文档（接口事实源）

> 配套引擎：`scripts/common.py`（凭证/会话/筛选构造/取数/候选/导出）。
> 端点域：`https://bi.leyopharm.com`。凭证：Cookie `uIdToken`/`uIdToken.sig`（见 `app.md` 凭证窗口）。

---

## 1. 端点总览

| 用途 | 方法 | 路径 | 说明 |
|---|---|---|---|
| 目录树 | GET | `/api/page-v3` | 定位「摇钱树业务线」(folderId `q4e929703ce5247db98af47a`)，拿 6 个 pageId |
| 页面组件 | GET | `/api/page/{pageId}` | 拿该看板全部组件（cards[]），含 cdId/cdType/chartType/filters/维度/指标 |
| 单卡声明 | GET | `/api/card/{cdId}` | 补 chartType / 维度指标补充 |
| **取数** | POST | `/api/card/{cdId}/data` | 主取数端点（请求体见 §2） |
| 候选值 | POST | `/api/selector/{selectorId}/data` | 页面筛选器实时候选值（`{"search":"关键字"}` 条件返回） |
| 导出提交 | POST | `/api/write/file/{cdId}?typeOp=EXCEL` | 提交导出任务，返回 taskId |
| 导出轮询 | GET | `/api/task/{taskId}` | 轮询 status，直到 `FINISHED` |
| 导出下载 | POST | `/api/export/file/common/{taskId}` | 下载 xlsx（响应体前 2 字节 `PK` 即为文件） |

---

## 2. 取数请求体模板

```json
{
  "filters": [
    {"name":"出库日期","fdId":"j837cb1313e434000bb42295","dsId":"ufef96cebcac14ff38494bb2",
     "cdId":"<目标cardId>","fdType":"DATE","filterType":"BT","filterLevel":"DETAIL",
     "filterValue":["2026-09-01","2026-09-22"]}
  ],
  "treeFilters":[],"dynamicParams":[],"dynamicFieldFilters":[],"combinationFilters":[],"layerTreeFilters":[],
  "view":"GRAPH","isUniversalStructure":false,"offset":0,"limit":50
}
```

- **`filters[]` 必须是完整键组**：`name/fdId/dsId/cdId/fdType/filterType/filterValue`（建议附 `originFilterType/sourceCdId`，与页面下发一致），缺键 → `5001`。
- **每页卡片必须带页面默认筛选等价项**（`recommended_filters` 自动注入，矩阵见 `parameters.md` §二）：销售进度出库明细集=j837 EQ 昨日宏；负利润卡（r6cd9b22f 数据集）=sc5733bd；货主利润=BT 本月到昨天；经营分析/考核=FIRST_PICK 最新月；库存=EQ 今日；补货=FIRST_PICK 最新快照日；配送/人工=EQ 昨日。不带 → 服务端回退**全表累计**错数（实测亿级）。
- **`NOT_NULL` 声明不可传参**（传则 `1012`）→ 跳过。
- 筛选值须为合法域值（用候选值）；库存快照日（STRING 域值）写死"今天"会 1012，取候选最新。
- **`dynamicParams[]`**：PARAMETER 筛选器传参，元素含 `dpId/name/valueType/defaultValue(=所选值)/optionValue/sourceCdId/inheritParent/multiple`。经营分析「分析维度」（`dpId=h24cff5ad…`）不传则回退「省内外」；补货页有「开始日期」「分析维度（动销金额区间）」。
- **`dynamicFieldFilters[]`**：动态字段注入 `{dzId, key, sourceCdId}`。配送/人工成本拆分卡必须带全 5 个（否则只回总计 1 行）；销售曲线「日/周/月」粒度 dz 不带则按月聚合（`CARD_DZ_DEFAULTS` 已内置）。
- 响应：`chartMain.{row,column,data,count,hasMoreData,offset,limit}`。`data[i][j].v` 为单元格值（指标），维度值在 `row.values[i]`。

## 3. 取数响应结构（两种，解析都要兼容）

**A. 透视/表格类**（PIVOT_TABLE / DATA_GRID / GROUPED_TABLE）：
```
chartMain:
  row:    { meta:[{name,fdType,...}], values:[[维度值 per row]] }
  column: { values:[[{title/name}]], metricFieldFormat:{ numberFormat:[{specifier:".2%"}] } }
  data:   [ [ {v,display}, ... ], ... ]   # 每行 = 一个维度组合；内层按 metric 对齐
  count, hasMoreData, offset, limit
```
- 取值用 `v`；百分比列看 `metricFieldFormat.numberFormat[i].specifier == ".2%"`。
- DATA_GRID 特例：可能出现 count>0 而 data 空（月目标及达成 2 卡实测），需人工核对。

**B. 图表类**（BASIC_BAR / MULTI_LINE / PIE / BUTTERFLY / 面积图等）：
```
chartMain:
  meta.categories: [{name:"分析维度", fdId:...}, ...]   # 维度字段声明
  categories:      ["1、零售单体", ...]                  # 行标签（维度值）
  series:          [ {name:"含税金额", data:[{y:...},...]}, ... ]  # 每系列一列
```
- 行数=len(categories)，列=series；同名系列加序号去重（实测存在"含税金额"+"含税金额#2"占比列）。
- `_extract` 已自动兼容两种结构。

**包装差异**：`/api/card/*/data` 与 `/api/selector/*/data` 返回**裸结构**（chartMain / count+result 直接在顶层）；`/api/page*` 类接口为 `{result:"ok", response:{…}}` 包装。

- **`hasMoreData=true` 必须翻页**：固定 `filters`、只递增 `offset`，直到 `false`，再合并 `data`（实测 count=6258 卡 offset 0/50/100 各回 50 行）。

## 4. 导出三步链（⚠ 禁带 j837）

```
① POST /api/write/file/{cdId}?typeOp=EXCEL   body={filters:[...]}  → taskId
② GET  /api/task/{taskId}                     → 轮询至 status=FINISHED（数秒~数十秒）
③ POST /api/export/file/common/{taskId}       body={"downloadFileName":"..."} → xlsx 字节流
```

- **导出请求体的 `filters` 不得含页面级出库日期 `j837`**（否则任务 `1012 FAILED`）。`scripts/export.py` 已自动剥离。
- 候选值很大（如商品名称 1000+）时，带 `{"search":"关键字"}` 分片取；服务端 `exceedLimit` 非错误。

## 5. 错误码

| 码 | 含义 | 处置 |
|---|---|---|
| `5001` | 请求体键名/方法错 | 用完整键组；树筛选键名是 `fields`+`values` |
| `1012` | 非法过滤参数 | 跳过 NOT_NULL、用合法域值（快照日取候选最新，勿写死今天）、导出剥离 j837；⚠ 库存快照集在新快照导入窗口会**整组 1012（正确请求也报）**，等就绪重试 |
| `1004` | 无权访问 | 换有权账号 |
| `401`/`1017` | 凭证过期/被顶 | 重扫 `login_bi.py` |
| `40002` | 查询超时 | 收窄日期/降 limit/减维度 |
| `14001` | 数据量 >120MB | 加日期过滤 |
