# 客户字段对照（zddz）

> 只管**字段、值域、界面映射**；接口与参数见 `api_客户列表.md` / `api_控销组.md` / `api_黑名单.md`。
> 分页三套体系见 `references/通用/api_认证与公共约定.md §9`。

## 1. 客户列表

### 1.1 筛选项 ↔ 参数 ↔ 值域

| 界面 | 参数 | 值域 / 取法 |
|---|---|---|
| 所在分组 | `storeTagId` | `""`=全部；分组 ID（`crm/getStoreTagList` 运行时取） |
| 地区 | `area` | `[[省 areaCode, 市 areaCode, 区 areaCode]]`（`/scm-goods/areaGroup/getAreaCode`） |
| 药店 ID | `drugstoreBranchId` | 精确 |
| 药店编码 | `providerCode` | 精确 |
| 药店名称 | `storeTitle` | 支持模糊 |
| 客户标签 | `storePchFlag` | 8 码：`000/001/010/011/100/101/110/111` |
| 采购时间 | `timeRange` | `["YYYY-MM-DD","YYYY-MM-DD"]`；**非结果集过滤器**（改成交口径/排序，不改 `totalRecord`），详见 `api_客户列表.md §1.5` |
| 订单活动类型 | `deliverType` | `""`=全部；`"7"`=拼团订单（**须与 `area` 组合才收窄**）、`8` 亦生效；详见 `api_客户列表.md §1.6` |
| 药店类型 | `subType` | `0`–`6`、`8`（见 1.3） |

> `area` 用二维数组 `[[省,市,区]]`，扁平 `[11]`/字符串会 `40004`；归档旧记「四种形态全失败」已被 11-12 复测推翻。`totalRecord` 有 10000 硬上限，判定筛选是否生效须看**组合收窄**而非 total 与基线相同。

### 1.2 返回字段 ↔ 界面列

| 界面列 | 字段 |
|---|---|
| 药店 ID | `drugstoreBranchId` |
| 药店编码 | `providerCode` |
| 药店名称 | `storeTitle` / `fullName` |
| 药店地址 | `address` |
| 客户标签 | `storePchFlag` |
| 城市 | `city`（省 `province`） |
| 浏览次数（7 天） | `visitTimes` |
| 采购订单数 | `orderNum` |
| 所在分组 | `storeTags` |

> 辅助字段：`areaId`（区域 ID）、`subType`（类型码）、`platform`/`version`/`token`/`userId`（响应占位）。

### 1.3 值域

**客户标签**（`storePchFlag`）：传 3 位纯数字码，显示为「码 + 客户」
`111` / `110` / `101` / `100` / `011` / `010` / `001` / `000`

**药店类型**（`subType`）：
`0` 零售单体 · `1` 第三终端 · `2` 连锁总部（批零一体） · `3` 连锁加盟 · `4` 连锁总部（纯连锁） · `5` 商业公司 · `6` 民营医院 · `8` 医疗器械经营店

## 2. 控销组

### 2.1 组字段（`storeGroup` 行）

| 字段 | 含义 |
|---|---|
| `storeGroupId` | 控销组 ID（`null`=新建） |
| `groupName` / `groupDesc` | 组名 / 描述 |
| `storeNum` | 组内药店数 |
| `noNoverNum` / `overNum` | 未结束 / 已结束**上架活动**数（总数 = 两者之和） |

### 2.2 组内药店字段（`getBranchInfo` 行）

| 字段 | 含义 |
|---|---|
| `branchId` | 药店 ID |
| `storetitle` | 药店名称 |
| `provCode` | 药店编码 |
| `addAccount` / `addTime` | 添加人 / 添加时间 |

### 2.3 添加方式 ↔ 参数

| 方式 | `batchType` | 值字段 |
|---|---|---|
| 按药店 ID | `0` | `branchId`（单个）/ `branchIdList`（批量） |
| 按药店编码 | `1` | `provCodeList` |
| 按药店全称 | `2` | `storetitleList` |
| 未下单药店 | — | 搜 `fullName` → 加 `drugstoreBranchId` + `fullName` |

### 2.4 其它值域

- `templateType=26`：控销组明细导出模板。
- `wsCountByRG`：使用该控销组的上架活动数（编辑前确认弹窗 N）。

## 3. 黑名单

### 3.1 行字段（`blackList` 行）

| 字段 | 含义 |
|---|---|
| `drugstoreBranchId` | 药店 ID |
| `provCode` | 药店编码 |
| `fullName` | 药店名称 |
| `address` | 药店地址 |
| `mtimeTimestamp` | 添加/更新时间 |
| `blacklistProductType` / `blacklistProductTypeName` | 维度码 / 名称 |
| `note` | 备注 |

### 3.2 维度值域（`blacklistProductType`）

`0` 全部 · `1` 自采 · `2` 非自采

### 3.3 添加方式 ↔ 参数

| 方式 | 接口 | 关键字段 |
|---|---|---|
| 按 ID / 编码（可多行） | `batchAddProviderStoreWhitelist` | `idtype=0`、`sotre_code`（`\n` 分隔） |
| 按名称（未下单） | `addnoOrderStore` → `doAddnoOrderStore` | `storeName` / `id`、`type=1`、`storeGroupId=0` |
| 选店 | `providerStoreWhitelist` | `branch_id`、`provider_code`、`storeName`、`province`、`city`、`district`、`branchType` |

### 3.4 删除方式

| 方式 | 接口 | 关键字段 |
|---|---|---|
| 单个 | `delStore` | `storeId`（整数，非 `branchId`） |
| 批量 | `batchDelBackList` | `multipart` 文件字段 `file`（xlsx，`药店ID` 列，≤3000 条） |

---

## 4. 供货对象管理

> 接口与参数见 `api_供货对象管理.md`；`ex=StoretypeGroupManagement`；归属 **② 通用**（两账号体系）。
> 2026-11-16 以摇钱树账号 `yqs22796` 实测全部 7 端点。

### 4.1 页面列 ↔ 返回字段

| 页面列 | API 字段 | 说明 |
|---|---|---|
| 供货对象组ID | `id` | 数字 |
| 名称 | `groupName` | 编辑弹层提交字段名为 **`name`** |
| 供货对象 | `storeTypes[]` / `storeSubtypes` | 前者中文数组（页面显示），后者数字拼接串（如 `01234568`） |
| 上架活动：未结束/已结束 | `notOverWsNum` / `overWsNum` | 页面 `notOver / over` |
| 标签 | `isMax` / `isDefault` | 最大供货对象 / 默认供货对象 |

### 4.2 客户类型枚举（`getNoSelectAndSelectStoreType`）

| 值 | 名称 | 值 | 名称 |
|---|---|---|---|
| 0 | 零售单体 | 4 | 连锁总部（纯连锁） |
| 1 | 第三终端 | 5 | 商业公司 |
| 2 | 连锁总部（批零一体） | 6 | 民营医院 |
| 3 | 连锁加盟 | 8 | 医疗器械经营店 |

> 无 `7`；响应带 `selected`（1=勾选），新增弹层默认全选 8 种。

### 4.3 已占用类型组合（17 组，2026-11-16 实测）

| id | 组名 | `storeSubtypes` |
|---|---|---|
| 122688 | 全部 | `0123456` |
| 122689 | 全部（除商业） | `012346` |
| 122690 | 零售单体 | `0` |
| 122691 | 第三终端 | `16` |
| 122692 | 零售单体+第三终端 | `016` |
| 122693 | 连锁总部（批零一体）+连锁加盟+连锁总部（纯连锁） | `234` |
| 128510 | 整件购 | `12456` |
| 129369 | 纯终端 | `0136` |
| 137573 | 不卖民营医院 | `012345` |
| 164882 | 除商业批发、批零一体（可去纯连锁） | `013468` |
| 164883 | 屏蔽商业 可去纯连锁 | `01346` |
| 165807 | 民营医院 | `6` |
| 166645 | 商业 | `245` |
| 169426 | 零售单体,第三终端,连锁加盟 | `013` |
| 169509 | 第三终端 | `1` |
| 184957 | 除民营医院 | `0123458` |
| 185039 | 全部客户 | `01234568` |
| **185042** | **agent全部01**（本次新增） | `0123468` |

> **新增按类型集合去重**：全选 `01234568` 撞 185039 → `40003 已存在相同药店类型的供货对象组，id:185039`。
> 新增前先查本表，选未占用组合。

### 4.4 写入参数对照

| 动作 | 端点 | 关键字段 |
|---|---|---|
| 新增 | `addStoretypeGroupAct` | `groupName` + `storeSubtypes:[int]` |
| 改名 | `updateStoretypeGroupName` | `id` + **`name`**（不可重名） |
| 设为默认 | `setDefaultSg` | `id`（hover 行 → 确认弹窗） |
