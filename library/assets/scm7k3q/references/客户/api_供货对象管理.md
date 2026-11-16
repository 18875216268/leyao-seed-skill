# 供货对象管理（API）

> **账号归属：② 通用**——自营「客户 → 供货对象管理」与摇钱树同菜单；
> 2026-11-16 以摇钱树账号 `yqs22796` 实测全部 7 端点通过（归属唯一事实源 `references/sy.md §0.4`）。
> 公共参数/鉴权见 `references/通用/api_认证与公共约定.md`；本子板块统一 `ex = StoretypeGroupManagement`。
> 板块索引见 `references/客户/sy.md`；字段/枚举台账见 `references/客户/zddz.md §4`。

---

## 1. 接口总表（7 个，全部 `POST`）

| # | 端点 | 用途 | 写? |
|---|---|---|---|
| 1 | `/scm-setting/storetypeGroup/getStoretypeGroupListAct` | 供货对象组列表 | 否 |
| 2 | `/scm-setting/storetypeGroup/getStoretypeGroupListCountAct` | 列表计数 | 否 |
| 3 | `/scm-setting/storetypeGroup/getNoSelectAndSelectStoreType` | **动态客户类型**（含勾选态） | 否 |
| 4 | `/scm-setting/storetypeGroup/getSubType` | 客户类型（另一路，前端 JS 存在，未触发） | 否 |
| 5 | `/scm-setting/storetypeGroup/addStoretypeGroupAct` | 新增供货对象组 | **是** |
| 6 | `/scm-setting/storetypeGroup/updateStoretypeGroupName` | 改组名（不可重名） | **是** |
| 7 | `/scm-setting/storetypeGroup/setDefaultSg` | 设为默认 | **是** |

> 前端路由 `StoretypeGroupManagement`；权限 key `storetypeGroupManager`（`/scm-base/common/operation` 返回 1 = 有权限）。

---

## 2. 显示：列表与计数

### 2.1 R1 列表 `getStoretypeGroupListAct`

**实测请求体**（分页默认值）：

```json
{ "pageNo": 1, "pageSize": 10, "token": "...", "platform": "scm-admin",
  "version": "1.0.3", "ua": "...", "ex": "StoretypeGroupManagement",
  "lastBuildTime": "2026-11-13 17:12" }
```

**响应** `data[]` 行字段（与页面四列一一对应）：

| 页面列 | 字段 | 说明 |
|---|---|---|
| 供货对象组ID | `id` | 数字 |
| 名称 | `groupName` | 名称；默认组另有 `isDefault=1` 标签 |
| 供货对象 | `storeSubtypes` / `storeTypes[]` | 前者为**数字拼接串**（如 `01234568`），后者为对应中文数组 |
| 上架活动：未结束/已结束 | `notOverWsNum` / `overWsNum` | 页面显示 `notOver / over` |
| （标签） | `isMax` / `isDefault` | 最大供货对象 / 默认供货对象 |

### 2.2 R2 计数 `getStoretypeGroupListCountAct`

请求同 2.1；响应 `data.{pageNo, pageSize, totalRecord, totalPage, results:null}`。
**注意**：`results` 恒为 `null`，计数只取 `totalRecord`（实测 17 → 新增后 18）。

### 2.3 客户类型枚举（实测确证）

`getNoSelectAndSelectStoreType` 响应 `data[]`：

| `storeType` | `storeTypeDesc` |
|---|---|
| 0 | 零售单体 |
| 1 | 第三终端 |
| 2 | 连锁总部（批零一体） |
| 3 | 连锁加盟 |
| 4 | 连锁总部（纯连锁） |
| 5 | 商业公司 |
| 6 | 民营医院 |
| 8 | 医疗器械经营店 |

- 值为**数字**，集合写法 `storeSubtypes` 用去重后的拼接串，接口提交用数组 `[int]`；
- **没有 7**；
- 响应带 `selected` 字段（`1` = 前端勾选），新增弹层**默认全选 8 种**。

---

## 3. 写操作（须按 `AGENT_GUIDE.md §10` 授权）

### 3.1 新增 `addStoretypeGroupAct`

**实测请求体**：

```json
{ "groupName": "agent全部01", "storeSubtypes": [0,1,2,3,4,6,8],
  "token": "...", "platform": "scm-admin", "version": "1.0.3",
  "ua": "...", "ex": "StoretypeGroupManagement", "lastBuildTime": "..." }
```

| 参数 | 含义 |
|---|---|
| `groupName` | 组名，前端 `maxlength=30` |
| `storeSubtypes` | 勾选的客户类型值数组；来自 `getNoSelectAndSelectStoreType` 的 checkbox |

> ⚠️ **服务端按类型集合去重，不按名称**：全选 `[0,1,2,3,4,5,6,8]` 与 id `185039`（全部客户）重复 →
> `40003 已存在相同药店类型的供货对象组，id:185039`。新增前须先用列表查 `storeSubtypes` 占用情况，
> 选一个未用组合（实测占用 17 种，见 `zddz.md §9.3`）。
>
> 实测成功：`[0,1,2,3,4,6,8]`（去掉商业公司 5）→ `40001 添加成功`，新组 id `185042`，总数 17 → 18。

### 3.2 改名 `updateStoretypeGroupName`

**实测请求体**：

```json
{ "id": 185039, "name": "agent校验改名", "...": "公共参数", "ex": "StoretypeGroupManagement" }
```

- 字段是 **`name`**（不是 `groupName`）；
- 前端弹层标题「编辑供货对象名称」，预填当前名；点名称旁 `svg#icon-修改` 打开；
- 重名会失败（用户要求「不可和现在的重名」）；
- 回滚：查原 `groupName` 后用同一接口反向写回。

### 3.3 设为默认 `setDefaultSg`

**实测请求体**：

```json
{ "id": 122688, "...": "公共参数", "ex": "StoretypeGroupManagement" }
```

- 前端入口**只在 hover 行时出现**：行首 `div.link-btn`「设为默认」→ 确认弹窗
  「是否将该供货对象设置成默认？」→「确 定」；
- 当前默认组（如 `185039`）无此按钮；
- 本次仅拦截抓参，**未真实设默认**（会改变全局默认，属高风险写操作）。

---

## 4. 输出契约与退出码

- 成功 `code=40001`；重复类型集合 `40003`（message 给出冲突组 id）；
- 所有写操作须 `--confirm` 或显式授权；Agent 不擅自设默认；
- CLI 尚未封装本子板块，用 `scm.py call --path <端点> --body '<JSON>' --ex StoretypeGroupManagement` 直连。

---

## 5. 实测证据（2026-11-16，摇钱树 yqs22796）

| 动作 | 结果 |
|---|---|
| 列表 / 计数 | `40001`，17 组，字段与页面四列一致 |
| 动态客户类型 | `40001`，8 种、默认全选 |
| 新增全选 `[0..8]` | ❌ `40003` 与 185039 类型集合重复（未落库） |
| 新增 `[0,1,2,3,4,6,8]` | ✅ `40001 添加成功`，id `185042`，总数 18 |
| 改名 185039 | ✅ 接口生效（测试后已恢复原名「全部客户」） |
| 设为默认 | 仅 route 拦截抓参，未真实提交 |
| **双账号通用性** | 浏览器（摇钱树 `yqs22796`）实测 7 端点全部 `40001`；CLI `python scm.py call --path .../getStoretypeGroupListAct --ex StoretypeGroupManagement`（自营凭证）亦 `40001`，返回自营侧数据（如 id `5503`）→ **两账号体系均可用，数据天然隔离** |

---

## 6. 已知坑

1. `storeSubtypes` 在**列表响应是字符串**，在**新增请求是数组**，勿直接透传。
2. 计数接口 `results=null`，只取 `totalRecord`。
3. 新增按类型集合去重，不按名称；全选几乎必然撞默认组。
4. 改名用 `name`，新增用 `groupName`，两个接口字段名不同。
5. 设为默认需 hover 才出现按钮，且有二次确认；不确认不发请求。
