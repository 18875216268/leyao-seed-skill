# 我的品种（API）

> 子板块：我的摇钱树 → **我的品种**（页面 `#/my-cashcow-management/my-variety`，菜单 menuId 970）。
> **账号归属：② 仅摇钱树**（自营账号无此子板块，越界不调用；归属唯一事实源 `references/sy.md §0.4`）。
> 请求约定见 `sy.md §3`：`POST` + JSON；**`ex` = `MyVariety`**（实测 2026-11-16 抓包确证，非空串）。
> 参数与字段来自真实抓包：采集 2026-11-16（登录摇钱树账号，只读导航 + 写/导出触发，零业务影响）；列表/配置/导出/更新/批量导入业务码均 `40001` 可达。

## 1. 总览

| 界面 | 后端 | 类型 | 说明 |
|**实测请求体（2026-11-16 浏览器实测，两种类型均确证）**：

```json
// A. 底价维护（实测 updateType=2，bottomPrice 6 → 88）
{ "id": 1268244, "updateType": 2, "bottomPrice": 88, ...公共参数 }
// B. 拼团最低供乐药价维护（点列表「未维护」旁编辑图标 → 选「维护拼团最低供乐药价」→ 勾同意 → 提交）
{ "id": 983160, "updateType": 1, "useMinLeyoPrice": 1, "minLeyoPrice": 99, ...公共参数 }
```

| 参数 | 含义 | 实测取值 |
|---|---|---|
| `id` | 品种行 id | 取列表 `results[].id` |
| `updateType` | **1 = 拼团最低供乐药价；2 = 底价** | ✅ 两种均实测，响应 `40001 成功` |
| `useMinLeyoPrice` | 启用拼团最低供乐药价 | `1`（仅 `updateType=1`） |
| `minLeyoPrice` | 拼团最低供乐药价（数字） | 实测 `99`；列表 `0.0` = 未维护 |
| `bottomPrice` | 底价（数字） | 实测 `6` → `88`；列表 `-1.0` = 未维护 |

> 拼团最低供乐药价弹层须勾选「我已充分了解此功能，同意系统在此设定价格基础上做自动调价」，否则提交不生效。|---|---|---|
| 我的品种列表（分页） | `myDrugsAct` | 只读 | 主列表；10 个业务筛选参数 |
| 筛选配置初始化 | `init` | 只读 | 下拉候选与默认值（枚举全集见 §4） |
| 导出 xlsx | **`export`** | 只读 | 服务端文件流（✅ 实测捕获） |
| 拼团最低供乐药价维护 / 底价维护 | **`update`** | **写** | ✅ 实测捕获（`updateType` 语义待补，§3.1） |
| 导入维护价格 | **`batchEditBottomPrice`** | **写** | ✅ 实测捕获（multipart 上传，§3.2） |

> 全部在 `/scm-setting/myVariety/` 前缀。

---

## 2. 读取

### 2.1 读取接口总表

| # | 接口 | 用途 | 业务参数 |
|---|---|---|---|
| R1 | `POST /scm-setting/myVariety/myDrugsAct` | 品种列表 | 10 个（§2.2） |
| R2 | `POST /scm-setting/myVariety/init` | 筛选配置初始化 | 无 |

### 2.2 R1 品种列表 `myDrugsAct`

**实测请求体**：

```json
{
  "pageNo": 1, "pageSize": 10,
  "lyErpDrugCode": "", "erpDrugName": "", "erpStock": -1, "fixedPrice": -1,
  "storeCode": "", "maintainPrice": -1, "maintainLyPrice": -1,
  "adjustPriceStatus": -1, "erpStockSort": -1, "onlyNeedApply": 0,
  "ex": "MyVariety"
}
```

**业务参数**（10 个，默认 `-1`/`0` = 全部/不筛）：

| 界面筛选项 | 参数 | 默认 | 取值 |
|---|---|---|---|
| 乐药ERP商品编码 | `lyErpDrugCode` | `""` | 字符串 |
| ERP商品名称 | `erpDrugName` | `""` | 字符串 |
| ERP库存 | `erpStock` | `-1` | `-1` 全部 / `1` 大于0 / `2` 小于等于0 |
| 一口价 | `fixedPrice` | `-1` | `-1` 全部 / `1` 无进行中 |
| 本公司编码 | `storeCode` | `""` | 字符串 |
| 维护底价 | `maintainPrice` | `-1` | `-1` 全部 / `1` 未维护 / `2` 已维护 |
| 维护最低供乐药价 | `maintainLyPrice` | `-1` | `-1` 全部 / `1` 未维护 / `2` 已维护 |
| 调价状态 | `adjustPriceStatus` | `-1` | `-1` 全部 / `1` 未调价 / `2` 已调价 |
| ERP库存排序 | `erpStockSort` | `-1` | `-1` 无排序 / `1` 正序 / `2` 倒序 |
| 仅查看需要申请新增商品的品种 | `onlyNeedApply` | `0` | `0` 否 / `1` 是 |

> 页面筛选项另有「商品ID」（匹配平台商品ID）→ 对应 `drugId`：**列表接口实测 body 未发送**，**导出接口（§2.4）实含**；同流水子板块处理，推荐用导出接口形态。

分页：`pageNo` / `pageSize`。

### 2.3 R1 响应字段

分页容器：`data.pageNo` / `pageSize` / `totalRecord` / `totalPage` / `results[]`（实测 `totalRecord=471`、`totalPage=48`）。

行字段（实测 ~44 字段）：

| 界面结果项 | 字段 | 实测样例/说明 |
|---|---|---|
| 乐药ERP商品编码 | `provDrugCode` | 如 `YP16049-52` |
| ERP商品名称 | `drugName` | — |
| ERP规格 / 厂家 / 国药准字 | `pack` / `factory` / `approval` | — |
| 匹配平台商品ID | `drugId` | 数字 |
| 平台商品名称 / 规格 / 厂家 / 国药准字 | `pdrugName` / `ppack` / `pfactory` / `papproval` | `p` 前缀 = 平台侧 |
| 配送商 | `providerName` | 如「央拓医药旗舰店(重庆央拓医药有限公司)」；另有 `deliverProviderId` |
| 最新供货价（动态价格） | `latestPurchasePrice` | 可为 `null` |
| 一口价、特价费率(%) | `commisionPercent1~11` | **动态档位列**（实测出现 1/2/3/4/7/8/9/10/11），按实际键遍历，勿写死 |
| ERP库存 | `stockBalance` | 可为 `null` / `"-"`，解析按数值兜底 |
| 一口价 / 拼团 / 批购包邮 状态 | `wholeSaleType1/15/13/16/1789/75/73/76/7789/7/8/85/83/86` | 14 个键，值 **0/1**；映射**未定谳**（§5） |
| 本公司编码 | `compCode` | 如 `Y0012309` |
| 拼团最低供乐药价 | `minLeyoPrice` | 数字（`0.0` = 未维护） |
| 维护计数 / 标记 | `minLeyoPriceModifiedCount` / `isMinLeyoPriceModified` | 计数可为 `null`；标记 `0`/`1` |
| 底价 | `bottomPrice` | 数字；**`-1.0` = 未维护** |
| 需申请新增标记 | `showApply` | `0`/`1` |
| 行 id | `id` | 维护写接口的主键（§3.1） |

### 2.4 R2 筛选配置 `init`

```json
{}   // 仅公共参数
```

响应 `data` 为各筛选项的下拉候选（`[{code, value}]`），即 §2.2 表右列的**权威取值来源**：`erpStock` / `fixedPrice` / `maintainPrice` / `maintainLyPrice` / `adjustPriceStatus` / `erpStockSort`。

---

## 3. 写操作（**须按 `AGENT_GUIDE.md §10` 授权**）

> ⚠️ 本节均为**写操作**：默认只读，执行前须取得授权（场景/单次/提前），执行前留回滚值（旧 `bottomPrice`/旧价），执行后核验并写审计日志（`write-audit.jsonl`）；**只改需求范围内的字段**，不顺带改一口价/库存/状态。
> 页面「业务功能」两个写入口的对应关系：**导入维护价格** = §3.2（实测）；**拼团最低供乐药价维护 / 底价维护** = §3.1（实测，字段由 `updateType` 选择）+ §3.3 候选专用端点（静态分析·未实测）。

### 3.1 `update` — 单品价格维护（底价 / 拼团最低供乐药价）

| 项 | 值 |
|---|---|
| 端点 | `POST /scm-setting/myVariety/update` |
| `ex` | `MyVariety` |

**实测请求体**：

```json
{ "id": 1268244, "updateType": 2, "bottomPrice": 6 }
```

| 参数 | 含义 | 备注 |
|---|---|---|
| `id` | 品种行 id | 取列表 `results[].id` |
| `updateType` | 维护类型选择器 | 实测样本 `2` → 写入 `bottomPrice`（底价）；**推断 `1` = 拼团最低供乐药价**（依据：列表含 `minLeyoPrice` 且页面有该维护入口、另有专用端点 §3.3）。⚠️ 现有采集与逆向资料**均无该枚举完整定义**，需补 1 次「维护拼团最低供乐药价」抓包方可定谳（见 §5.4） |
| `bottomPrice` | 底价（数字） | 实测写入值 `6`；列表里 `-1.0` = 未维护 |

响应：`{"code":"40001","message":"成功","data":null}`。

> **回滚要点**：执行前先 `myDrugsAct` 查该 `id` 行的旧 `bottomPrice`（或 `minLeyoPrice`）留档；失败或误改按旧值反向 `update` 还原。

### 3.2 `batchEditBottomPrice` — 导入维护价格（批量）

| 项 | 值 |
|---|---|
| 端点 | `POST /scm-setting/myVariety/batchEditBottomPrice` |
| `ex` | `MyVariety` |
| Content-Type | **`multipart/form-data`**（文件上传，非 JSON） |

**响应**（实测，JSON；返回**失败明细**）：

```json
{"code":"40001","message":"success","data":{
  "rightCount": 0, "errorCount": 1,
  "data": [["SP0273304-57","央拓医药","编码+配送商无匹配数据"]],
  "header": ["本公司编码","配送商","失败原因"],
  "filename": "失败数据.xlsx"}}
```

| 响应字段 | 含义 |
|---|---|
| `rightCount` / `errorCount` | 成功行数 / 失败行数 |
| `data` | 失败行明细（二维数组，按 `header` 列） |
| `header` | 失败表头（见下方模板列） |
| `filename` | 失败数据文件名（如 `失败数据.xlsx`） |

**导入模板列（2026-11-16 补采实测：5 次真实导入，4 次 `rightCount=1`）**：

响应 `data.header` 是**失败数据.xlsx 的表头**，实测出现 4 种成功组合 + 1 种失败：

| # | 响应 header（失败明细列） | 实测结果 |
|---|---|---|
| 1 | `乐药erp商品编码` + `配送商` + `失败原因` | ✅ `rightCount=1, errorCount=0` |
| 2 | `本公司编码` + `配送商` + `失败原因` | ✅ `rightCount=1, errorCount=0` |
| 3 | `乐药erp商品编码` + `底价` + `失败原因` | ✅ `rightCount=1, errorCount=0` |
| 4 | `本公司编码` + `底价` + `失败原因` | ✅ `rightCount=1, errorCount=0` |
| 5 | `本公司编码` + `配送商` + `失败原因` | ⚠️ `errorCount=1`，原因「编码+配送商无匹配数据」 |

> 注意：原表写的「`本公司编码`+`配送商`+`底价`」属**上传模板列**；响应 header 是**失败明细列**（不含底价列），两者不是一回事，勿混。

**失败原因样例**（实测）：`编码+配送商无匹配数据`、`底价数据不规范`。

**multipart 字段（2026-11-16 浏览器实测确证，route 拦截抓包，未真实提交）**：

| 字段 | 含义 | 实测取值 |
|---|---|---|
| `priceType` | 导入类型 | **`0` = 拼团最低供乐药价；`1` = 底价** |
| `type` | 导入方式 | **`0` = 按乐药erp商品编码；`1` = 按本公司编码** |
| `file` | xlsx 文件 | `filename="本公司编码_底价.xlsx"` 等 |
| `token` / `platform` / `version` / `ua` / `ex` / `lastBuildTime` | 公共参数六件套 | 放在 **multipart 表单**，非 JSON body；`ex=MyVariety` |

模板对应：`ERP编码_底价.xlsx`→(1,0)；`本公司编码_底价.xlsx`→(1,1)；
`按乐药erp_导入维护拼团最低供乐药价.xlsx`→(0,0)；`本公司编码_导入维护拼团最低供乐药价*.xlsx`→(0,1)。
拼团最低供乐药价导入须勾选「我已充分了解…」。`scm.py call` 当前只支持 JSON body/get，
multipart 需按 `AGENT_GUIDE.md §10.5` 复用凭证自行实现（不得自建登录）。

### 3.3 `cashcow/editMinLeyoPrice` — 拼团最低供乐药价维护（**已否定：非实际入口，实操走 §3.1 `update`**）

| 项 | 值 |
|---|---|
| 端点 | `POST /scm-goods/cashcow/editMinLeyoPrice` |
| 来源 | 逆向分析**源码静态分析**（`cashcow` 模块，`main.js`），**未实测可达**（红线：变更类未实时提交） |
| 可行性置信 | 低 |

> 端点名 `editMinLeyoPrice` 直译即「编辑拼团最低供乐药价」，与页面「拼团最低供乐药价维护」**名称吻合**，是本功能的**候选专用端点**。
> ⚠️ **三点存疑，勿直接调用**：①逆向工作簿给出的字段（`afterName`/`bankName`/`reason` 等）与「价格维护」明显不符，疑为源码静态分析的**字段误配**；②该端点与 §3.1 `update` 谁真正承担「拼团最低供乐药价维护」**未定谳**；③该端点已登记在 `modules/marketing/__init__.py` 的静态端点清单（故本板块不重复登记），路径可能在 `/scm-goods/cashcow/` 下由 goods 服务承载。**需补 1 次真实维护抓包**确证端点与字段后方可用。**参数未确证前不得臆造、不得调用。**

---

## 4. 导出 `export`（✅ 实测捕获，服务端文件流）

| 项 | 值 |
|---|---|
| 端点 | `POST /scm-setting/myVariety/export` |
| `ex` | `MyVariety` |
| 响应 | **二进制文件流（xlsx）**，`scm.py call --out <文件>` 落盘 |

**实测请求体**（含列表接口未发送的 `drugId`）：

```json
{ "pageNo": 1, "pageSize": 10, "lyErpDrugCode": "", "erpDrugName": "",
  "drugId": "", "erpStock": -1, "fixedPrice": -1, "storeCode": "",
  "onlyNeedApply": 0, "ex": "MyVariety" }
```

> 与列表体差异：导出含 `drugId`（商品ID筛选）；不含 `maintainPrice`/`maintainLyPrice`/`adjustPriceStatus`/`erpStockSort`。以各接口实测 body 构造，勿混。

---

## 5. 已知坑与待确认

1. **`ex` 必须传 `MyVariety`**（非空串、非默认 `goodsOnShelves`）。
2. **默认值语义**：`erpStock`/`fixedPrice`/`maintainPrice`/`maintainLyPrice`/`adjustPriceStatus`/`erpStockSort` 默认 `-1`=全部；`onlyNeedApply` 默认 `0`。取值以 `init` 返回为准。
3. **`wholeSaleType*` 映射未定谳**：14 个键值为 **0/1** 标志位，对应「一口价/拼团/批购包邮 × 进行中/已暂停」的具体映射**未确证**（键值形如 `1789`/`7789` 为组合键）；首次使用调列表打印首行、对照页面三组状态列确证后再解析。
4. **`updateType` 语义** ✅ **2026-11-16 已确证**：`1`=拼团最低供乐药价（+`useMinLeyoPrice=1`+`minLeyoPrice`）；`2`=底价（+`bottomPrice`）
5. **批量导入文件字段名待确证**：multipart 已确证，但采集器未记录请求体（`raw_data=None`），文件表单字段名**在所有资料中均缺失**；模板列已知（见 §3.2 三种组合）。补 1 次导入抓包（含 form 字段）即可。
6. **费率档位动态**：`commisionPercent*` 键按返回实际键遍历；与 `priceTypes` 字典的关系待确证。
7. **`stockBalance` 可为 `null`/`"-"`**：解析按数值兜底。
8. **`storeCode`（筛选）vs `compCode`（返回）**：同一口径（本公司编码）两个命名，勿混用。
9. **`bottomPrice` 哨兵值**：`-1.0` 表示未维护（非真实价格 -1）。
10. **仅摇钱树账号可达**：先确认账号归属，无信息先问、不猜。
