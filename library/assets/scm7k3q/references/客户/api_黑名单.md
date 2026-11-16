# 黑名单管理（API）

> 黑名单是**独立全局表**，不属于任何控销组（`blackList` 不带 `storeGroupId`）。
> 两类鉴权：① `scm-setting`（JSON）用 **SCM token**；② `provider.php`（legacy 表单）用同一登录会话的 **`PHPSESSID` + `X-Requested-With`**。见 `references/通用/api_认证与公共约定.md`。
> 接口清单见 `sy.md §3.3`；字段/值域见 `zddz.md §3`。

## 1. 读取

> 分页统一用 `pageNo` + `pageSize`（三套分页体系见 `references/通用/api_认证与公共约定.md §9`）。

### 1.1 搜索黑名单

`POST /scm-setting/saleControl/blackList`

| 参数 | 说明 |
|---|---|
| `keyword` | 关键字（药店名/ID 等） |
| `orderByNum` / `orderFieldNum` | 固定 `-1`（默认不排序） |
| `pageNo` / `pageSize` | 分页 |

```json
{ "keyword": "", "orderByNum": -1, "orderFieldNum": -1, "pageNo": 1, "pageSize": 20,
  "token": "<token>", "platform": "scm-admin", "version": "1.0.3", "ua": "<UA>",
  "ex": "ControlDrugstoreGroup", "lastBuildTime": "2026-11-09 20:28" }
```

返回 `data.results[]`；字段含义见 `zddz.md §3.1`（药店 ID / 编码 / 名称 / 地址 / 时间 / 维度 / 备注）。

### 1.2 维度配置开关

`POST /scm-setting/saleControl/inBlackListProductTypeConfig`（无业务参数）→ `data:true`。

## 2. 写入

> 默认只读；写操作须按 `AGENT_GUIDE.md §10` 授权，并遵守文末红线。

### 2.1 添加

**① 按药店 ID / 编码（legacy）**

```text
POST /provider.php/SaleControl/batchAddProviderStoreWhitelist
Headers: X-Requested-With: XMLHttpRequest
         provideridm: <md5(<当前 providerId>)>
         Cookie: PHPSESSID=<有效会话>
Body(form): idtype=0&sotre_code=<药店ID或编码>   # 多行用 \n 分隔；真实样本不带 token
# → {"info":"操作成功","status":1}
```

- `sotre_code` 为服务端原拼写（**含错字，须原样**）；支持多个药店，用**换行 `\n`** 分隔（如 `1314213\n1317577\n1320169`）。
- 实测（摇钱树账号）：`idtype=0&sotre_code=<药店ID>`（**不带 token**）→ 成功入榜（1478→1479），确认无需 token。
- 缺 `X-Requested-With` 会返回整页 HTML。
- 若返回「存在空行」：**先去掉多余字段（尤其 `token`）**重试（真实样本只有 `idtype` + `sotre_code`）；仍失败再 `GET` 一次选店页建立会话上下文后重试，或改走「选店 → 添加」链路。

**② 按名称添加未下单药店（legacy）**

```text
# 1) 搜候选
POST /provider.php/Admin/SaleControl/addnoOrderStore
Body(form): storeName=<药店全称>&type=1&storeGroupId=0&token=<token>
# 返回候选（含 add_store('<id>', ...)）

# 2) 确认添加
POST /provider.php/Admin/SaleControl/doAddnoOrderStore
Body(form): id=<候选药店ID>&type=1&storeGroupId=0&token=<token>
# → {"info":"操作成功", ...}
```

**③ 选店（添加前浏览候选）**

选店页表单字段（实测）：

| 字段 | 含义 |
|---|---|
| `branch_id` | 药店 ID |
| `provider_code` | 药店编码 |
| `storeName` | 药店名称 |
| `province` / `city` / `district` | 省 / 市 / 区（区域 ID，级联同 `getCity`/`getNextArea`） |
| `branchType` | 药店状态 |
| `provider_id` | 供应商 ID（由当前凭证的 `providerId` 取得，勿硬编码） |
| `pagesize` | 每页条数 |
| `is_add` / `del_sids` / `tmp_ids` / `store_group_id` | 内部字段，一般留空 |

```text
POST /provider.php/Admin/SaleControl/providerStoreWhitelist
Body(form): branch_id=&provider_code=&storeName=
            &province=36443&city=38724&district=38828
            &branchType=&is_add=2&provider_id=<当前providerId>&pagesize=10
# → HTML 候选行（checkbox name=<id>、code、title）；选定后按 ① 添加
```

### 2.2 删除

**① 单个删除**

```text
POST /scm-setting/saleControl/delStore
{ "storeId": 3105569, ...公共参数 }
# → {"code":"40001","message":"删除成功"}
```
> 键名是 `storeId`（整数），**不是 `branchId`**。

**② 批量删除（Excel 文件）**

弹出「批量删除」弹窗，上传 xlsx：**A 列表头 `药店ID`**，下方一行一个药店 ID；**每次不超过 3000 条**。

```text
POST /scm-setting/saleControl/batchDelBackList
Content-Type: multipart/form-data
fields:
  file = <黑名单删除.xlsx>   # 含表头「药店ID」+ ID 行
  token / platform / version / ua / ex / lastBuildTime = 公共参数
# → {"code":"40001","message":"success",
#     "data":{"rightCount":1,"errorCount":0,
#             "header":["药店ID","失败原因"],
#             "filename":"批量导入黑名单删除失败数据.xlsx"}}
```

> ⚠️ multipart 的 `file` 部分**不可显式设置 `Content-Type`**（设了会 `40002 服务器开小差`）；文件必须是 `.xlsx`（CSV 不被接受）。判据读 `rightCount/errorCount`。

### 2.3 修改

| 内容 | 接口 | 参数 |
|---|---|---|
| 备注 | `POST /scm-setting/saleControl/updateStore` | `drugstoreBranchId`、`note` |
| 黑名单维度 | `POST /scm-setting/saleControl/updateBlackListProductType` | `drugstoreBranchId`、`blacklistProductType`（`0` 全部 / `1` 自采 / `2` 非自采） |

→ `{"code":"40001","message":"修改成功"}`。对非黑名单药店改维度 → `40003 修改失败`。
> ⚠️ 实测（摇钱树账号）：改维度返回 `40003 当前店铺不可修改黑名单维度`（账号/店铺配置限制，非参数错误）；改备注不受影响。

## 3. 导出

`POST /scm-setting/saleControl/exportBlackList`，参数同 `blackList`（`keyword`、`orderByNum`、`orderFieldNum`、`pageNo`、`pageSize`）。

- **直接导出**：响应体即 xlsx，`Content-Type: application/octet-stream`，`Content-Disposition: attachment; filename=黑名单药店导出列表.xlsx`；**不走导出任务列表**。
- 导出列：`药店ID, 药店编码, 药店名称, 添加时间, 备注, 黑名单维度`。

## 4. 错误码与红线

| 码 | 含义 |
|---|---|
| `40001` | 成功（批量以 `rightCount/errorCount` 为准） |
| `40002` | 服务器开小差（常见于 multipart 文件被显式设 content-type / 非 xlsx） |
| `40003` | 删除失败 / 修改失败 / `当前店铺不可修改黑名单维度`（改维度受限，账号或店铺配置） |
| `40004` | 包含重复数据，请去重后提交 |

**写操作红线**：
1. 写前快照 `blackList.totalRecord` 与现有 ID 集合；
2. 仅对「基线之外、明确已知」的药店执行增/删/改；
3. 写后复验 `totalRecord` 回到基线，且除目标 ID 外无现有项被改动。

> legacy `PHPSESSID` 会过期（表现为 302 跳登录页），重新 `python scm.py login` 刷新即可；一次登录同时覆盖 `scm-setting` 与 legacy。
