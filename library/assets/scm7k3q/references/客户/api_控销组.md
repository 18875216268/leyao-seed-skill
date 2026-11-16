# 控销组管理（API）

> 控销组 = 一批药店的集合。商品侧用 `isRestrict`（0 非控非禁 / 1 控销 / 2 禁销）+ `restrictGroupId` 引用控销组，实现「只让组内客户采购」或「不让组内客户采购」。
> 请求：`POST /scm-setting/saleControl/*`，`application/json`。公共参数 `ex=ControlDrugstoreGroup`（组 CRUD）/ `ControlDrugstoreGroupEdit`（组内药店）、`version=1.0.3`；鉴权见 `references/通用/api_认证与公共约定.md`。
> 接口清单见 `sy.md §3.2`；字段见 `zddz.md §2`。

## 1. 读取

> 分页统一用 `pageNo` + `pageSize`（三套分页体系见 `references/通用/api_认证与公共约定.md §9`）。

### 1.1 控销组列表（搜索）

`POST /scm-setting/saleControl/storeGroup`

| 参数 | 说明 |
|---|---|
| `pageNo` / `pageSize` | 分页 |
| `groupName` | 组名关键字（模糊） |
| `storeName` | 包含药店名称（模糊） |
| `branchId` | 包含药店 ID |
| `groupIds` | int 数组，精确组 ID（可选） |

返回：`data.results[]`，每行 `{storeGroupId, groupName, groupDesc, storeNum, noNoverNum, overNum}`。

```json
POST /scm-setting/saleControl/storeGroup
{ "pageNo": 1, "pageSize": 10, "groupName": "", "storeName": "", "branchId": "",
  "groupIds": [], "token": "<token>", "platform": "scm-admin", "version": "1.0.3",
  "ua": "<UA>", "ex": "ControlDrugstoreGroup", "lastBuildTime": "2026-11-09 20:28" }
```

### 1.2 组内药店列表

`POST /scm-setting/saleControl/getBranchInfoCount`（数量）与 `getBranchInfo`（列表）

| 参数 | 说明 |
|---|---|
| `storeGroupId` | 组 ID（必填） |
| `pageNo` / `pageSize` | 分页 |
| `branchId` | 药店 ID 筛选 |
| `provCode` | 药店编码筛选 |
| `storetitle` | 药店名称筛选 |

返回：`[{branchId, storetitle, provCode, addAccount, addTime}]`。

> ⚠️ 实测（摇钱树账号）：`getBranchInfoCount` 可能返回 `0` 而 `getBranchInfo` 已有数据（计数接口缓存/延迟）；以列表为准，或稍后重试。

### 1.3 未下单药店搜索

`POST /scm-setting/saleControl/getNoOrderStore`，body `storeGroupId` + `fullName` → `data:[{drugstoreBranchId, storetitle, provCode, fullName}]`（可空数组）。

### 1.4 其它查询

| 接口 | 参数 | 返回 |
|---|---|---|
| `allNoWsGroups` | 同 1.1 | `data` = `storeGroupId` 整数数组（无上架活动/活动全结束的组） |
| `wsCountByRG` | `groupIds:[…]` | `data` = 数字，**引用该控销组的活动数（含已下架，不只是上架）**。实测：同一组的 3 条活动全部下架后仍返回 `3` → **删组前不能只凭它判断"是否还有活口"**，需人工确认后 `--force`。页面二次确认弹窗的「N 个活动」即此值 |

## 2. 写入

> 默认只读；写操作须按 `AGENT_GUIDE.md §10` 授权，且只对授权范围内的组执行。

### 2.1 新建控销组

`POST /scm-setting/saleControl/editStoreGroup`，`storeGroupId: null`

```json
{ "storeGroupId": null, "groupName": "<控销组名称>", "groupDesc": "<说明描述>",
  "token": "<token>", "platform": "scm-admin", "version": "1.0.3", "ua": "<UA>",
  "ex": "ControlDrugstoreGroup", "lastBuildTime": "2026-11-09 20:28" }
```
→ `{"code":"40001","message":"添加成功","data":null}`，随后 `storeGroup` 可查到新组。

### 2.2 编辑组名/描述

同一接口，`storeGroupId` 传非空组 ID → `修改成功`。字段与新建相同（`groupName`、`groupDesc`）。

> 若该组正被上架活动引用，页面会先弹确认框：「您当前有 N 个活动在使用该控销组，确定对该控销组进行调整吗？」。**N = `wsCountByRG({groupIds:[storeGroupId]})` 的返回值**。

### 2.3 删除控销组

`POST /scm-setting/saleControl/delGroups`，`{"groupIds": [167794]}` → `操作成功！`（不可逆）。

### 2.4 批量删除控销组

同 `delGroups`，`groupIds` 传多个组 ID。

### 2.5 添加药店到控销组

三种添加方式：

**① 单个（按药店 ID）** — `POST /scm-setting/saleControl/addStoreSingle`
```json
{ "batchType": 0, "branchId": 2311210, "storeGroupId": 92369, ...公共参数 }
```
→ `添加成功`；ID 非法 → `40003 请输入正确的药店ID`。

**② 批量** — `POST /scm-setting/saleControl/addStoreBatch`，`batchType` 选维度：

| 维度 | `batchType` | 值字段 | 示例 | 失败明细表头 |
|---|---|---|---|---|
| 按药店 ID | `0` | `branchIdList` | `[2311210]` | `["药店ID","失败原因"]` |
| 按药店编码 | `1` | `provCodeList` | `["K0560956"]` | `["药店编码","失败原因"]` |
| 按药店全称 | `2` | `storetitleList` | `["天津宝坻天宝福苑诊所"]` | `["药店名称","失败原因"]` |

```json
{ "batchType": 0, "storeGroupId": 92369, "branchIdList": [2311210], ...公共参数 }
```
→ `data:{rightCount, errorCount, data:[[值,原因]], header, filename}`。

- 全称必须是系统里的**完整名称**；错误字段名 → `40003 请输入至少一个药店编码/名称`；值传字符串而非数组 → `40004 参数异常`。
- **判据必须读 `rightCount`/`errorCount`**，不能只看 `code=40001`。

**③ 单个添加未下单药店** — 先 `getNoOrderStore` 搜名称，再 `POST /scm-setting/saleControl/addNoOrderStore`
```json
{ "storeGroupId": 92369, "fullName": "河南省", "drugstoreBranchId": 3503288, ...公共参数 }
```
> 注意键名是 `drugstoreBranchId`（不是 `branchId`）。

### 2.6 删除组内药店

| 方式 | 接口 | 参数 |
|---|---|---|
| 单个 | `POST /scm-setting/saleControl/delStoreSingle` | `branchId`、`storeGroupId` |
| 批量 | `POST /scm-setting/saleControl/delStoreBatch` | `branchIdList:[…]`、`storeGroupId` |

→ `删除成功`。

## 3. 导出

控销组明细走**异步导出任务**（通用导出中心），不是直接下载。

```text
# 1) 提交导出（token 必须用 credential.json 的 token，不能用 cms_token）
POST /export-file/file/exportStoreGroupList/v100
{ "templateType": 26, "storeGroupId": 92369, ...公共参数 }
→ {"code":"40001","message":"提交导出任务成功…","data":{"recordId":<任务ID>,"providerId":<当前providerId>}}

# 2) 轮询任务
POST /export-file/file/getExportTaskRecord/v100
{ "pageNo": 1, "pageSize": 10, ...公共参数 }
→ data.exportTaskRecordPageResult.results[] 中 status=3（已完成）取 qiniuUrl

# 3) 下载
GET <qiniuUrl>（带 Referer 头）→ GBK CSV
```

- CSV 表头：`药店ID, 药店编码, 药店名称, 添加人, 添加时间`。
- 空组建议先加至少 1 个成员再导出。
- 提交限流：`40003 导出数据失败,您在十分钟内提交多次请求` → 退避 10 分钟。
- 轮询/下载细则见 `references/通用/api_导出任务.md`。

## 4. 关键字段

| 键名 | 类型 | 说明 |
|---|---|---|
| `storeGroupId` | int / null | 控销组 ID；`null`=新建 |
| `groupIds` | int[] | 删除组、`wsCountByRG` 用 |
| `groupName` / `groupDesc` | string | 组名 / 描述（描述可含换行） |
| `branchId` | int | 组内药店 ID（单加/单删） |
| `branchIdList` / `provCodeList` / `storetitleList` | int[] / string[] | 批量加（按 `batchType` 选一个） |
| `drugstoreBranchId` | int | 仅 `addNoOrderStore` 用 |
| `fullName` | string | 药店全称（未下单搜索） |
| `provCode` / `storetitle` | string | 组内药店筛选 |
| `batchType` | `0/1/2` | ID / 编码 / 全称 |
| `storeNum` / `noNoverNum` / `overNum` | int | 组内药店数 / 未结束活动数 / 已结束活动数（上架活动总数 = `noNoverNum + overNum`） |
| `templateType` | `26` | 控销组明细导出模板 |

## 5. 错误码与安全

| 码 | 含义 |
|---|---|
| `40001` | 成功（批量以 `rightCount/errorCount` 为准） |
| `40003` | 本板块多义：`请输入正确的药店ID`、`请输入至少一个药店编码/名称`、导出非法请求/限流 |
| `40004` | `包含重复数据，请去重后提交！` / 参数异常 |

- 写操作只能作用于**授权范围内的组**；改动既有组前保留回滚信息（组名/描述/成员）与审计。
- 组被活动引用时，编辑前有二次确认提示，不可跳过。
