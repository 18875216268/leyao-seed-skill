# 客户（板块索引）

> **板块归属（板块内单独说明）**：本板块为**混合归属**——`api_客户列表.md`（客户-客户列表）＝**自营专属**；`api_控销组.md`、`api_黑名单.md`、`api_供货对象管理.md` ＝**通用**（两账号体系）。归属唯一事实源与两账号板块地图见 `references/sy.md §0`。
> 本目录覆盖 SCM「客户」菜单下的四块业务：**客户列表**、**控销组**、**黑名单**、**供货对象管理**。
> 不在本目录：IM/在线客服（`/scm-setting/customer/*`，见 `modules/customer/GUIDE.md`）；控销组设置页的「不限量药店组」「商圈黑名单」两页签属独立体系，未纳入本目录。
> 公共参数与鉴权见 `references/通用/api_认证与公共约定.md`；导出任务轮询见 `references/通用/api_导出任务.md`。
> 取数用 `python scm.py call`（`AGENT_GUIDE.md §4.1`）；客户列表注意 `ex=OldCustomerManagement`、`version=1.0.0`、**不带 `lastBuildTime`**。

## 1. 子板块地图

| 文档 | 覆盖 | 能力 |
|---|---|---|
| `api_客户列表.md` | 客户（药店）查询、客群统计、客户分组、导出 | 读取 · 导出 |
| `api_控销组.md` | 控销药店组的建/改/删、组内药店增删 | 读取 · 写入 · 导出 |
| `api_黑名单.md` | 黑名单搜索、增/删/改、导出 | 读取 · 写入 · 导出 |
| `api_供货对象管理.md` | 供货对象组列表、动态客户类型、新增/改名/设为默认 | 读取 · 写入 |

## 2. 已实现功能

| 子板块 | 读取 | 写入 | 导出 |
|---|---|---|---|
| 客户列表 | ✅ | —（分组维护不做） | ✅ 直接 GET |
| 控销组 | ✅ | ✅ | ✅ 异步任务（CSV） |
| 黑名单 | ✅ | ✅ | ✅ 直接 xlsx |
| 供货对象管理 | ✅ | ✅ | ⚪ 无导出端点（页面无导出按钮） |

## 3. 端点总表

### 3.1 客户列表（`/scm-order/crm/`，POST JSON）

| 操作 | 路径 | 说明 |
|---|---|---|
| 主查询 | `crm/list` | 分页查询客户，17 字段/行 |
| 粉丝数 | `crm/getFansNum` | 客群分析「药房粉丝」 |
| 浏览数 | `crm/getVisitTimes` | 客群分析「浏览」 |
| 下单客户数 | `crm/getOrderUserNum` | 客群分析「下单」 |
| 分组字典 | `crm/getStoreTagList` | 下拉「所在分组」选项 |
| 分组列表 | `crm/getProStoreGroupList` | 页签「组列表」 |

### 3.2 控销组（`/scm-setting/saleControl/`，POST JSON）

| 操作 | 路径 | 说明 |
|---|---|---|
| 组列表/搜索 | `saleControl/storeGroup` | `groupName`/`storeName`/`branchId` |
| 组内药店数 | `saleControl/getBranchInfoCount` | |
| 组内药店列表 | `saleControl/getBranchInfo` | |
| 未下单药店搜索 | `saleControl/getNoOrderStore` | 加店前查询 |
| 无活动组 | `saleControl/allNoWsGroups` | 返回 `storeGroupId[]` |
| 关联活动数 | `saleControl/wsCountByRG` | 使用该组的活动数（编辑前确认弹窗 N） |
| 新建/编辑组 | `saleControl/editStoreGroup` | `storeGroupId:null`=新建 |
| 删除组 | `saleControl/delGroups` | `groupIds[]` |
| 加单店 | `saleControl/addStoreSingle` | `batchType:0` |
| 批量加店 | `saleControl/addStoreBatch` | `batchType` 0/1/2 |
| 加未下单店 | `saleControl/addNoOrderStore` | |
| 删单店 | `saleControl/delStoreSingle` | |
| 批量删店 | `saleControl/delStoreBatch` | |

### 3.3 黑名单（`/scm-setting/saleControl/` + legacy `/provider.php/...`）

| 操作 | 路径 | 鉴权 |
|---|---|---|
| 搜索 | `saleControl/blackList` | SCM token |
| 维度开关 | `saleControl/inBlackListProductTypeConfig` | SCM token |
| 单删 | `saleControl/delStore` | SCM token |
| 批删（文件） | `saleControl/batchDelBackList` | SCM token |
| 改备注 | `saleControl/updateStore` | SCM token |
| 改维度 | `saleControl/updateBlackListProductType` | SCM token |
| 按 ID/编码添加 | `provider.php/SaleControl/batchAddProviderStoreWhitelist` | PHPSESSID + XHR |
| 按名称加未下单 | `provider.php/Admin/SaleControl/addnoOrderStore` → `doAddnoOrderStore` | PHPSESSID + XHR |
| 选店 | `provider.php/Admin/SaleControl/providerStoreWhitelist` | PHPSESSID + XHR |

### 3.4 导出（三份文档共用，机制不同）

| 导出 | 接口 | 机制 |
|---|---|---|
| 客户列表 | `GET /provider.php/Admin/ExcelExport/exportProStore` | 浏览器直接下载（11 个 query） |
| 控销组明细 | `POST /export-file/file/exportStoreGroupList/v100` | 异步导出任务 → 轮询 → `qiniuUrl` 下载 GBK CSV |
| 黑名单 | `POST /scm-setting/saleControl/exportBlackList` | 响应即 xlsx，直接导出 |

> **导出 token 口径（实测，闭环）**：`/export-file/` 导出服务**必须用 `credential.json` 的 `token`**，用 `cms_token` 会返回 `40003 导出数据失败,非法请求`（或误导性的「十分钟内提交多次请求」）。`/scm-order/crm/*` 与 `/scm-setting/saleControl/*` 用两种 token 都能成功，**唯独导出服务敏感**。提交参数 `templateType:26` + `storeGroupId`；建议组内至少 1 个成员再导出（空组也会报"非法请求"）。`40003` 在本板块多义（参数错 / 空组 / 真限流），以 `message` 区分，只有真限流才退避 10 分钟。依据出处见 §6 数据来源。

### 3.5 采集期登记端点（**未实测 / 未展开，调用前须实测或经授权**）

> 以下端点来自采集记录，**技能内不给可照抄的完整参数**；标「仅端点名」者连参数键名都未采集，Agent **不得猜测参数**，命中时按 `references/sy.md §0.5` 第 6 步如实告知。写端点一律按 `AGENT_GUIDE.md §10` 授权，本次全面测试均**未调用**。

| 组 | 端点 | 已采集到的信息 | 状态 |
|---|---|---|---|
| **① 客户分组写（新版 JSON）** | `/scm-order/crm/addProStoreGroup` | `tagName` → `data:1`；+ 公共参数 | 仅登记（写，未实测） |
| | `/scm-order/crm/delProStoreGroup` | `storeTagId` → `data:null` | 仅登记（写，未实测） |
| **② 老版 Drugstore 分组弹窗** | `/provider.php/Admin/Drugstore/storeList` | 14 参数（`drugstoreBranchId`/`providerCode`/`storeTitle`/`province`/`city`/`area`/`isPurchased`/`netPay*`/`orderNum*`/`drugNum*`/`tag_id`）；返回 HTML 表格 | 采集登记（读），另有 GET iframe `?usedForWeb=1` |
| | `getStoreTagList`(老版) / `getCity` / `getNextArea` | `id`+`key=1` → `<option>` HTML；**老版区域码表未采全，勿与 `areaGroup/getAreaCode` 混用** | 采集登记（读） |
| | `changeTag` / `groupDataCount` / `groupDataCharts` | `groupDataCount` 用 `tag_id`+`dateRange=YYYYMMDD-YYYYMMDD`+`store_pch_flag` → 结构化 `info{storeNum,purStoreNum,orderNum,netPay,avg}`；`groupDataCharts` 用 `checkLine[]=[0,1,2,3]`+`dataType=1` → ECharts HTML | 采集登记；`changeTag` 响应采集为 null |
| | `importGroupList` | multipart；模板 `GET /uploads/excelTemplate/drugstoreId.xlsx`；返回 `failList[]` | **仅登记（写）＋上传文件字段名未采集** |
| | `addTag` / `addStoreToTagGroup` | `tag_id`+药店 ID（`id` / `store_id[]`）→ `status:1` 文案 | 仅登记（写，未实测） |
| | `showGroupDetail` | 仅 GET iframe 路由 `?tag_id=...&usedForWeb=1` | 仅登记（页面路由），响应未采集 |
| **③ 不限量药店组** | `/scm-setting/saleControl/noLimitStoreCount` / `noLimitStore` | `keyword` `orderByNum:-1` `orderFieldNum:-1` `pageNo` `pageSize`；排序枚举未采集 | 采集登记（读） |
| | `/provider.php/SaleControl/storeCountForNoLimit` | `branch_id` `provider_code` `storetitle` `province` `city` `district` → `info:"1"` | 采集登记（老版，方法未标注） |
| | `/provider.php/Admin/SaleControl/storeListForNoLimit?usedForWeb=1` | 同上 6 参数 + `page`/`pagesize=10` → HTML | 采集登记（老版） |
| **④ 区域组 / 商圈黑名单（第三套体系）** | `scm-goods/areaGroup/getBlacklistAreaGroupListCount` | `pageNo`/`pageSize` → `totalRecord` | 仅采集样本，未实测；HTTP 方法未标注 |
| | `getBlacklistAreaGroupList` | 同上 → `[{id, providerId, groupName, mdatetimeStr, opId, storetypeStr, opIdName}]` | 同上 |
| | `getBlacklistAreaGroupForEdit` | `id` → `{storeSubtype, blackType, editOriginalAreaCodes, busiScope, busiScopeList}` | 同上 |
| | `getAllAreaCode` / `getAvailableStoretype` / `getAvailableBusiScope` | `areaType:4` → 区域码树 / 无业务参数 → 药店类型码表 / 无 → 经营范围 15 项 | 同上 |

> **④ 组定性（原文结论）**：「商圈黑名单 = 区域组（**不是控销组**）」，返回字段与 **`storeGroupId` 无关**，属**第三套体系**（另两套：控销组 `storeGroupId`、客户分组 `storeTagId`；商品上架页 `getAreaGroupDropList` 的 `allowModify`/`nationwide`/`isWarehouse` 又是另一套）。**文档与代码都不得把它并入控销组**。`ex` 为 `BizAreaSetting`（编辑）或 `ControlDrugstoreGroup`（列表）。
> 不存在独立端点 `getBlacklistAreaGroup`（无后缀）——只是 `getBlacklistAreaGroup*` 通配前缀；`checkMerpProvDrugCode` 同理只有端点名、零参数记载。

### 3.6 供货对象管理（`/scm-setting/storetypeGroup/`，POST JSON，`ex=StoretypeGroupManagement`）

| 用途 | 端点 | 已确证参数 |
|---|---|---|
| 列表 | `post /scm-setting/storetypeGroup/getStoretypeGroupListAct` | `pageNo`/`pageSize` → 行含 `id`/`groupName`/`storeSubtypes`/`storeTypes[]`/`notOverWsNum`/`overWsNum`/`isMax`/`isDefault` |
| 计数 | `post /scm-setting/storetypeGroup/getStoretypeGroupListCountAct` | 同上 → `totalRecord`（`results=null`） |
| 动态客户类型 | `post /scm-setting/storetypeGroup/getNoSelectAndSelectStoreType` | 无业务参数 → 8 种 `{storeType,storeTypeDesc,selected}` |
| 客户类型（另路） | `post /scm-setting/storetypeGroup/getSubType` | 前端 JS 存在，未触发 |
| 新增（写） | `post /scm-setting/storetypeGroup/addStoretypeGroupAct` | `groupName` + `storeSubtypes:[int]`；**按类型集合去重** |
| 改名（写） | `post /scm-setting/storetypeGroup/updateStoretypeGroupName` | `id` + **`name`**（不可重名） |
| 设为默认（写） | `post /scm-setting/storetypeGroup/setDefaultSg` | `id`；hover 行→确认弹窗→确定 |

---

## 4. 鉴权与公共参数

| 类型 | 约定 |
|---|---|
| `scm-order/crm/*`、`scm-setting/saleControl/*` | SCM token + `platform/version/ua/ex`（客户列表 `version=1.0.0`、无 `lastBuildTime`；控销/黑名单 `version=1.0.3`） |
| `provider.php/*`（legacy） | 同一登录会话的 `PHPSESSID` + 头 `X-Requested-With: XMLHttpRequest` + `provideridm: md5(str(providerId))`；表单内带 `token` |
| `/export-file/*` | 必须用 `credential.json` 的 `token`，**不能用 `cms_token`** |

> 成功码 `code="40001"`（不是 HTTP 400）。`40003` 在本板块有多种含义（参数错误/空组导出/导出限流），以 `message` 区分。

> **账号通用性（2026-11-11 实测）**：接口与参数与账号无关，已用 **自营账号** 与 **摇钱树账号** 双账号验证通过。仅 `token` / `PHPSESSID` / `provideridm` 按账号不同（`provideridm = md5(str(providerId))`）。黑名单「改维度」受账号/店铺配置限制：摇钱树账号 返回 `40003 当前店铺不可修改黑名单维度`（自营账号可改），属权限差异而非接口差异。

## 5. 阅读顺序

1. 查客户、导客户名单 → `api_客户列表.md`
2. 建控销组、往组里放药店、导组明细 → `api_控销组.md`
3. 维护黑名单 → `api_黑名单.md`
4. 供货对象组（列表/新增/改名/设默认）→ `api_供货对象管理.md`

## 6. 边界与待确认

> 已确认（原缺口关闭）：
> - 客户列表**地区筛选可用** → `area: [[省,市,区]]`，`areaCode` 来自 `POST /scm-goods/areaGroup/getAreaCode`（见 `api_客户列表.md §1.2`）。
> - 客户列表**订单活动类型** `deliverType="7"`（拼团订单）**单独传不收窄**（命中 10000 上限），须与 `area` 组合才生效：北京 4095→36、东城区 43→0、广东→293、辽宁→238（11-12 复测，见 `api_客户列表.md §1.6`）。
> - 客户列表**采购时间** `timeRange` 是成交数据口径/排序参数、**不是结果集过滤器**（total 恒 10000，但首行 ID 变）；顶部 3 个统计接口不吃 `timeRange`/`area`（11-12 复测，见 `api_客户列表.md §1.5`）。
> - `wsCountByRG` = 引用该控销组的**活动数（含已下架）**；实测 3 条全部下架后仍返回 3，**不能作为"还有没有活口"的唯一依据**（删组前人工确认后 `--force`）；二次确认弹窗的「N 个活动」即此值（见 `api_控销组.md §1.4/§2.2`）。
> - `noNoverNum`/`overNum` = **未结束/已结束活动数**（上架活动总数 = 两者之和）。
> - 组内药店搜索 `getBranchInfo` 支持 `branchId`（药店ID）、`provCode`（编码）、`storetitle`（名称）。

> **数据来源与时效**：一手采集记录在 `交付区/归档/客户/文档编写/{客户列表.md, 控销组管理.md}`（保留原件不改）。**结论以本技能 `references/客户/*` 为准**：归档《客户列表》的「`area` 四形态全失败 / 不支持日期参数」等采集期旧结论已被 2026-11-12 浏览器只读复测推翻，复测证据 `过程区/账号权限实测/crm_verify*.py` / `crm_verify_result.json`。§3.5 的登记端点属"采集有、未实测"，调用前须实测或授权。

| # | 项 | 现状与处置 |
|---|---|---|
| 1 | 商品上架保存时选择控销组的字段 | 属商品板块，见 `references/商品/zddz.md`（`restrictGroupId`） |
| 2 | **供货对象管理**、**客户编码修改** | 板块地图（自营「客户」）列有这两个子项，但**采集未覆盖、无端点、本技能无文档**。命中时按 `references/sy.md §0.5` 第 6 步如实告知，不猜测端点 |
| 3 | **商圈黑名单 = 区域组** | 第三套体系、与 `storeGroupId` 无关、**不并入控销组**；端点与结论已在 **§3.5 ④** 展开 |
| 4 | **不限量药店组** / 老版 Drugstore 分组弹窗 | 独立页签；端点与已采集参数已在 **§3.5 ②③** 登记（未实测） |
| 5 | **黑名单** | 本技能有 `api_黑名单.md`（通用），但板块地图自营「客户」子项未列；属文档覆盖面大于菜单名，路由以 `references/sy.md §0.4` 为准 |

## 7. 分页约定

三套分页体系见 `references/通用/api_认证与公共约定.md §9`。客户列表用 `page` + `pageSize`（可选 10/50/100/200）。
