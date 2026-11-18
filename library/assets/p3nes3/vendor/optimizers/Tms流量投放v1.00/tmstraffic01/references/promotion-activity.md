> **框架内自包含副本** ｜ token 由调用方通过 `--token`/`PMS_TOKEN`/`--state-file` 传入；本包不登录、不读父凭证仓库。
> `buildTime` 通过 `--build-time` 可选传入（默认 `2026-11-17 18:42:50`）；凭证/构建异常只报错，不自行登录。
> 原始归档已剥离（实测身份与过程路径不随包，以本副本为准）。

# 促销活动管理 API 文档（完全独立版 · 可照此开发）

> 页面：`https://pms.ysbang.cn/#/tms/promotion-activity-management`
> 生成：2026-11-17 ｜ 方法：webpack 源码 100% 逆向（chunk `3610` 页面/表单、`81793` module `63585` API、`app.js` 公共）+ 真实 HTTP 请求实测（凭证 token 直调，全部接口已验证）
> **自包含**：鉴权/公共参数/错误码/全部枚举/字段名（前端界面名=源码字段名=API参数名，三者一致）/参数模板/真实响应/调用顺序/导入模板全在此文。

---

## 0. 快速开始（Agent 照抄即可创建一条活动）

1. 前置：需一条**可用的关联促销费用**（先选费用才启用公司/业务类型/商品配置）；费用名称≤20字符。
2. 所有请求 POST 到 `https://pms.leyopharm.com`，body 必带 `token`+`buildTime`（见 §1）。
3. 按商品建活动：上传商品 Excel → `add/v100`，body 的 `goodUrl`=上传返回的 `fileUrl`、`totalPromotionAmount`=上传返回的合计。

按商品建活动实测成功 body（活动10372）：
```json
{
  "businessType":3,"campaignItems":[],"userType":3,"customerLabelIds":[],
  "customerFileUrl":"","customerIds":"","inputMode":null,
  "startTime":"2026-11-17 00:00:00","endTime":"2026-11-30 23:59:59",
  "expenseId":1640,"goodUrl":"<上传fileUrl>","goodsItems":[],"joinActivityTypes":[],
  "providerId":3364,"remark":"按商品测试","wholesaleUrl":"",
  "totalPromotionAmount":100,"availableAmount":10000,"customerTypes":[-1],"areaCodes":[],
  "token":"<TOKEN>","buildTime": "<BT>"
}
```

---

## 0.5 推荐默认值（用户 2026-11-18 确认，Agent 创建时自动填充）

> **优先级**：用户本次明确要求 > 本默认值 > 前端系统默认 > 留空。

| 前端显示名称 | 推荐默认值 | 说明 |
|---|---|---|
| 促销活动名称 | `Agent自动补贴` | 固定值，无后缀，≤20字 |
| 关联促销费用 | 自动规则 | 用户无额外要求 → 选本次会话最新创建的费用；无则自动新建费用并选；用户有要求 → 严格按用户 |
| 公司 / 业务类型 | 跟随关联费用 | 前端联动带出 |
| 促销活动类型 | 未填 → **询问用户** | 必填且无系统默认（按商品 / 按活动ID） |
| 商品输入框 / 活动输入框 | 留空 | 动态项，由用户提供 |
| 单盒补贴金额 | 未填 → **询问用户** | 用户未设默认（历史实测常用 0.01，但不作默认） |
| 促销数量上限 | 200 | 导入默认（用户指定） |
| 单客补贴数量上限 | 20 | 导入默认（用户指定） |
| 导入（Excel） | 按用户要求自动生成模板并上传 | 按活动ID表头：活动ID/公司ID/单盒补贴金额/单客补贴数量上限/促销数量上限 |
| 客户圈选 | 未填 → 系统默认 | 全部客户 |
| 自定义标签 / 自定义名单 / 可使用区域 | 留空 | 按客户圈选联动 |
| 客户类型 | 未填 → 系统默认 | 不限 |
| 活动时间（开始） | 处理日期当天 `00:01:00` | 相对规则，按当天动态计算 |
| 活动时间（结束） | 处理日期当天 `23:59:59` | 秒补59（前端提交规则） |
| 备注 | `agent自动投流！` | ≤200字 |

**同批创建费用时**：费用有效时间与活动时间一致（见费用文档 §0.5）。

---

## 1. 鉴权与公共参数（所有接口必带）

- **token 来源：调用方传入（--token/PMS_TOKEN/--state-file）
  
  - **实测**：凭证 token 可直接调用本文档所有接口（page/detail/add/finish/partial-finish/上传/导出等全部已用 `requests` 直调验证），**无需浏览器/CDP（直连）**。
  - ⚠️ 凭证缺失或 40006/40007 → 报错并请调用方提供新凭证
- **buildTime**：前端构建时刻字符串，源码 `79851.D()` 写入 `params.buildTime`；由 `--build-time` 可选传入，默认 `2026-11-17 18:42:50`；异常时请调用方提供其页面当前值。
- **请求头**：`Content-Type: application/json`、`token:<TOKEN>`、`Authorization: Bearer <TOKEN>`、`origin/referer: https://pms.ysbang.cn`。
- **成功码** `code="40001"`；分页 `data.list[] + data.count`；导出任务列表前端改写为 records/total。
- 完整错误码见 §11。

---

## 2. 字段命名约定（前端=源码=API，三者一致）

本文档所有字段名直接采用**前端源码变量名 = API 参数名**，与界面中文标签一一映射。例：界面"促销活动名称" → 源码 `formData.activityName` → API `activityName`；界面"单盒补贴金额" → 源码 `subsidyPerBox` → API `subsidyPerBox`。这样 Agent 从界面看到什么，就能在 API 里找到对应字段。

关键映射表（新增/编辑表单提交体）：
| 界面标签 | 前端源码字段 | API 参数 | 类型/说明 |
|---|---|---|---|
| 促销活动名称 | `formData.activityName` | `activityName` | string，≤20字，trim |
| 关联促销费用 | `formData.expenseId` | `expenseId` | number |
| 公司 | `formData.providerId` | `providerId` | number |
| 业务类型 | `formData.businessType` | `businessType` | number：1普品/2集采/3普品+集采 |
| 促销活动类型 | `formData.activityScopeType` | `activityScopeType` | number：1按商品/2按活动ID |
| 客户圈选 | `formData.userType` | `userType` | number：3全部/0店铺新客/1品种新客/2自定义标签/5自定义名单 |
| 自定义标签 | `formData.customerLabelIds` | `customerLabelIds[]` | number[]（userType=2） |
| 自定义名单-文件 | `formData.customerFileUrl` | `customerFileUrl` | string（userType=5） |
| 自定义名单-粘贴 | `formData.customerIds` | `customerIds` | string，逗号分隔 |
| 名单输入方式 | `formData.customerListInputMode` | `inputMode` | 1文件/2粘贴/null |
| 客户类型 | `formData.customerTypes` | `customerTypes[]` | number[]，默认[-1]不限 |
| 可使用区域 | `formData.areaCodes` | `areaCodes[]` | number[] 市区编码 |
| 活动时间-开始 | `formData.startTime` | `startTime` | string `YYYY-MM-DD HH:mm:ss`，秒=0 |
| 活动时间-结束 | `formData.endTime` | `endTime` | string `YYYY-MM-DD HH:mm:ss`，秒=59 |
| 备注 | `formData.remark` | `remark` | string，≤200字，trim |
| 商品文件 | `formData.goodsImportFileUrl` | `goodUrl` | string，上传返回的 fileUrl（按商品） |
| 活动文件 | `formData.goodsImportFileUrl` | `wholesaleUrl` | string，上传返回的 fileUrl（按活动） |
| 黑名单文件 | `formData.blacklistFileUrl` | `blackWholesaleUrl` | string |
| 商品明细 | `formData.goodsItems` | `goodsItems[]` | 见 §5.3 |
| 活动明细 | `campaignRows`→`campaignItems` | `campaignItems[]` | 见 §5.3 |
| 参与活动类型 | `formData.joinActivityTypes` | `joinActivityTypes[]` | number[] |
| 总促销金额 | `totalAmount` | `totalPromotionAmount` | number，须=Σ(单盒补贴×数量上限) |

> 注意：`goodUrl`（按商品）与 `wholesaleUrl`（按活动）在源码里同源于 `formData.goodsImportFileUrl`，但提交时按 `activityScopeType` 分别落到不同字段。大文件(>50条)以文件为准时，`goodsItems`/`campaignItems` 可为空数组，但 `goodUrl`/`wholesaleUrl` 必须=上传 fileUrl。

---

## 3. 筛选项详解（控件类型 100% 源码确认 + 实测）

| 筛选项（界面） | 控件类型 | API 字段 | 默认值 | 数据源/接口 |
|---|---|---|---|---|
| 促销活动ID | 输入框（仅字母数字，回车即搜） | `id` | `""` | 手输 |
| 促销活动名称 | 输入框（maxlength50，回车即搜） | `activityName` | `""` | 手输 |
| 公司 | 静态下拉多选 | `providerIds[]` | `[]` | vuex newProviderList |
| 关联促销费用 | **远程搜索下拉·单选**（输入关键字弹候选） | `expenseId` | `""` | `list-selectable-expenses/v100` body `{queryContent}` → `[{expenseId,expenseName,providerIds,businessType}]`，候选显示"id - name" |
| 商品 | **两级**：左侧静态下拉选"按商品/按活动ID" + 右侧远程搜索输入框 | `goodsKeywordScope` + `goodsKeyword` | 1 / `""` | 下拉未选时右侧禁用；右侧 placeholder"商品编码、名称" |
| 活动ID | 输入框（maxlength64） | `campaignId` | `""` | 手输，平台活动ID |
| 创建人 | 远程搜索下拉多选 | `creatorIds[]` | `[]` | `BudgetUserSelector`→`userOption/pv28280`，取 userId |
| 活动状态 | 静态下拉单选 | `status` | `""` | 待开始/进行中/已结束 |
| 活动时间 | 日期区间 | `activityTimeStart` / `activityTimeEnd` | 近30天 | datetimerange |

---

## 4. 查询接口

### 4.1 列表分页
`POST /operation-service/promotion-activity/page/v100`
实测 body：
```json
{"id":"","activityName":"","expenseId":"","goodsKeywordScope":1,"goodsKeyword":"","campaignId":"",
 "providerIds":[],"creatorIds":[],"status":"","activityTimeStart":"2026-10-18 00:00:00",
 "activityTimeEnd":"2026-11-17 23:59:59","page":1,"pageSize":10,"token":"<TOKEN>","buildTime": "<BT>"}
```
响应 `data.list[] + data.count`，行字段（界面列=字段）：
| 界面列 | 字段 | 实测示例 |
|---|---|---|
| 促销活动ID | `activityCode` | SUB20261117036 |
| 促销活动名称 | `activityName` | 泰尔丝加投 |
| 已补贴金额 | `subsidizedAmount` | 16.8（点击→补贴明细） |
| 关联促销费用 | `expenseName`/`expenseCode` | 泰尔丝加投/FY… |
| 公司 | `providers[].name` | 重庆央拓 |
| 业务类型 | `businessTypeText` | 普品+集采 |
| 促销活动类型 | `activityScopeTypeText` | 按商品/按活动ID |
| 活动时间 | `startTime`/`endTime` | … |
| 平台校验状态 | `checkStatus`（码→文本见 §10.3） | 4=平台创建成功 |
| 错误明细 | `failUrl`（有值时显示"下载"） | "" |
| 状态 | `status` | 进行中/已结束 |
| 创建时间 | `cdatetime` | … |
| 操作 | — | 查看/复制/结束 |

### 4.2 详情（查看活动）
`POST /operation-service/promotion-activity/detail/v100`，body `{"id":<主键>}`。
响应字段（与提交体同源）：`id,activityCode,activityName,expenseId,expenseName,providers[],businessType(Text),activityScopeType(Text),startTime,endTime,subsidizedAmount,status,canEnd,editable,creatorName,cdatetime,subsidyPlanId,expenseCode,checkStatus,failUrl,remark,userType,customerFileUrl,customerIds,customerLabels[],customerTypes[],areaCodes[],areaItems[],goodsRows[],campaignRows[],blacklistCampaignIds[],joinActivityTypes[]`。

### 4.3 字典/远程搜索
| 用途 | 接口 | body | 响应 |
|---|---|---|---|
| 关联促销费用下拉 | `POST /operation-service/promotion-activity/list-selectable-expenses/v100` | `{queryContent}` | `[{expenseId,expenseName,providerIds,businessType}]` |
| 按费用预填 | `POST /operation-service/promotion-activity/prepare-expense/v100` | `{expenseId,providerId}` | `{businessType,expenseHasGoodsRows,expenseGoodsRows[],promotionRequestWholesaleDtos[],availableAmount,expenseActivityTypes[],userType,customerTypes[],areaCodes[],...}` |
| 活动搜索 | `POST /operation-service/promotion-activity/search-campaigns/v100` | `{queryContent}` | 活动候选 |
| 公司下拉 | `POST /datacenter_pms/web/pms/user/companyOptions/v100` | `{}` | `[{providerId,providerName,shortName}]` |
| 用户搜索（创建人/预算使用人） | `POST /datacenter_pms/web/search/userOption/pv28280` | `{size:200,name,providerId:"",userIsvalId:"1"}` | `[{userId,userName,account}]` |

---

## 5. 新增 / 复制活动（写操作）

### 5.1 提交体完整模板
见 §0 快速开始（按商品）与下例（按活动ID）：
```json
 "businessType":3,"campaignItems":[],"userType":3,"customerLabelIds":[],
 "customerFileUrl":"","customerIds":"","inputMode":null,
 "startTime":"2026-11-17 00:00:00","endTime":"2026-11-30 23:59:59",
 "expenseId":1639,"goodUrl":"","goodsItems":[],"joinActivityTypes":[],
 "providerId":3364,"remark":"...","wholesaleUrl":"<上传fileUrl>",
 "totalPromotionAmount":7960,"availableAmount":999999,"customerTypes":[-1],"areaCodes":[]}
```
- 新增：`POST /operation-service/promotion-activity/add/v100` → `data=<新活动ID>`

### 5.2 校验规则（源码 `formError` + 实测报错）
| 字段 | 校验 | 报错 |
|---|---|---|
| activityName | 必填、≤20字 | "请填写" / `40004 size must be between 0 and 20` |
| expenseId | 必填 | "请选择" |
| providerId / businessType / activityScopeType | 必填 | "请选择" |
| goodsItems/campaignItems | 按模式不可空（大文件除外靠 fileUrl） | `41007 按活动配置时活动行不能为空` / `按商品配置时商品行不能为空` |
| totalPromotionAmount | 须=Σ补贴×数量 | `41007 总促销金额与实际活动行/商品行总促销金额不一致！` |
| startTime/endTime | 必填、在费用有效期内、跨度≤366天 | "请选择"/"结束时间与开始时间间隔不能超过366天" |
| customerTypes | 必填 | "请选择" |
| customerLabelIds | userType=2 时必选 | "请选择客户标签" |
| 名单 | userType=5 时须校验过 | "请先校验自定义名单" |
| areaCodes | 选了区域须在费用可用区域内 | "选择的区域不在可使用区域范围内" |

### 5.3 商品/活动明细字段（界面=源码=API）
**商品行 `goodsItems[]`**（界面"商品配置"表格）：`erpCode`（商品编码）、`providerId`（公司ID）、`subsidyPerBox`（单盒补贴金额）、`qtyLimit`（品种数量上限，费用侧）、`actualQtyLimit`（促销数量上限，界面可填）、`perCustomerQtyLimit`（单客补贴数量上限）、`goodsName/goodsSpec/providerName/goodsBusinessType`（展示）。
**活动行 `campaignItems[]`**（界面"活动ID明细"）：`campaignId`（活动ID）、`wholesaleType`（活动类型码）、`subsidyPerBox`（单盒补贴金额）、`qtyLimit`（促销数量上限）、`perCustomerQtyLimit`（单客补贴数量上限）、`providerId`。

### 5.4 上传导入接口（4 类模板）
| 类型 | 上传接口 | type | 模板表头（实测） |
|---|---|---|---|
| 按商品 | `POST /operation-service/promotion-activity/validate-import-file/v100` | `1` | `ERP编码｜公司ID｜单盒补贴金额｜单客补贴数量上限｜促销数量上限` |
| 按活动ID | 同上 | `2` | `活动ID｜公司ID｜单盒补贴金额｜单客补贴数量上限｜促销数量上限` |
| 活动黑名单 | 同上 | `3` | `活动id` |
| 多公司 | `POST /operation-service/promotion-activity/multi-company-import/v100` | — | 15列（公司ID/促销活动名称/关联促销费用ID/业务类型/促销活动类型/参与活动类型/客户圈选/客户类型/可使用区域/活动时间/备注/商品编码或活动ID/单盒补贴金额/促销数量上限/单客补贴数量上限）；**仅集团账号** |
- 上传 multipart 字段：`excelFile`（文件）+ `type` + `businessType` + `providerId` + token/buildTime。
- 响应：`{success,message,fileUrl,totalPromotionAmount,campaignRows[],goodsRows[],platformExcelResult:{rightCount,errorCount,data:[[ID,金额,单客上限,促销上限,失败原因]],header,filename}}`。
- **报错接口**：失败时从 `platformExcelResult.data` 取逐行失败原因（如"活动id重复""活动起购门槛大于单客户减免上限""阶梯价活动不能参与单品立减"），按原因处理后重新上传。实测：`data.fileUrl` 是可下载的错误数据 xlsx。
- **模板下载**（返回 xlsx 文件流）：`/operation-service/promotion-activity/import-goods-template/v100`（按商品）、`import-campaigns-template/v100`（按活动）、`import-blacklist-template/v100`（黑名单）、`multi-company-import-template/v100`（多公司）。
- 实测补贴参数（用户指定）：**单盒补贴金额 0.01、单客补贴数量上限 1、促销数量上限 1000**；BI 选品条件：业务类型"普通"(BI)=普品、广东省有销售、ERP编码不含"-"。

---

## 6. 查看 / 明细 / 提前结束

### 6.1 查看促销活动（详情弹窗，只读）
- 接口：detail/v100（§4.2）。弹窗含：基础信息 / 商品配置（按钮"添加活动ID""下载报错结果" + 表格列 公司/活动ID/促销状态/单盒补贴金额/促销数量上限(实际促销数量)/单客补贴数量上限）/ 客户配置 / 活动时间 / 备注。

### 6.2 活动ID明细（提前结束弹窗）
- 按活动查明细：`POST /operation-service/promotion-activity/campaign-detail-page-by-activity/v100`，body `{activityId,page,pageSize}` → `data.list[]`，字段：
  `campaignId`(活动ID)、`wholesaleType`(活动类型码)、`wholesaleTypeDesc`(活动类型文本)、`activityStatus`(活动状态码，5=进行中)、`activityStatusDesc`、`promotionStatus`(促销状态码，1=进行中/3=已结束)、`promotionStatusDesc`、`providerId`、`subsidyPerBox`(单盒补贴金额)、`qtyLimit`(促销数量上限)、`perCustomerQtyLimit`(单客补贴数量上限)、`selectable`（是否可提前结束=活动状态且促销状态均进行中）。
- 按商品查明细：`POST .../campaign-detail-page-by-goods/v100`，需 `{providerId,erpCode,activityId}`（缺则 `40004 公司ID不能为空,ERP编码不能为空`）。
- 弹窗列=活动ID/活动类型/活动状态/促销状态/单盒补贴金额/促销数量上限/单客补贴数量上限；带分页。

### 6.3 提前结束部分活动
`POST /operation-service/promotion-activity/partial-finish/v100`
- body（按活动）：`{activityId, activityScopeType:2, campaignIds:[<活动ID>...]}`；按商品附 `erpCode`。
- 参数错误提示："促销活动ID不能为空/活动类型不能为空/请选择要结束的平台活动"。
- 业务校验：`41007 仅活动状态与促销状态均为进行中的平台活动可提前结束：<campaignId>`（只能结束 `selectable=true` 的行）。
- 实测：活动10371（99条双进行中可选行）勾选2条 → `40001 操作成功`。

### 6.4 结束整单（行内"结束"）
`POST /operation-service/promotion-activity/finish/v100`，body `{"id":<主键>}`，confirm"确认结束该促销活动吗？"→ 状态变"已结束"、canEnd=false、editable=false。

---

## 7. 补贴明细（双击"已补贴金额"进入）

- 触发：列表"已补贴金额"点击 → 路由 `PromotionActivitySubsidyDetail?activityId=<ID>`（面包屑"促销活动管理 > 补贴明细"）。
- 列表接口：`POST /operation-service/promotion-activity/subsidy-order-page/v100`，body `{activityId,page,pageSize}` → `data.list[]+count`。字段（界面列=字段）：
  `orderId`(订单ID)、`wholesaleId`(活动ID)、`promotionActivityCode`(促销活动ID=SUB编码)、`activityName`(促销活动名称)、`orderTime`(下单时间)、`pharmacyId`(药店ID)、`pharmacyName`(药店名称)、`activityTypeText`(活动类型)、`subsidyAmount`(补贴金额)、`orderStatusText`(订单状态)、`activityId`(促销活动主键)、`ysbCustomerId`、`pharmacyInfo`。
- **已补贴金额导出**：`POST /operation-service/promotion-activity/subsidy-order-export/v100`，body `{"activityId":<主键>}`（必须 activityId，用 id 报 40004）→ 返回 xlsx 文件流（`application/vnd.ms-excel`，filename"促销活动已补贴金额导出"，PK 头）。必须 POST（GET 报 40012）。

---

## 8. 导出 / 批量任务列表（与费用板块共用组件）

- 导出：`POST /pms_operation/web/pms/promotion-activity/export/pv29230`，body=列表筛选参数去page/pageSize + `fileName`（前端生成"促销活动管理<YYYYMMDDHHmmss>"）→ `{lineUpNumber,estimateTime,exportInfoId,exportInfoType}`。
- 批量任务列表：`POST /operation-service/promotion-activity-export-task/list`，body `{current:1,size:10,total:0,type:9999,fileType:207}`（207=促销活动，206=促销费用）→ `data.list[]`：`id`(=exportInfoId)、`fileType`("促销活动管理-导出")、`fileTypeCode:207`、`fileName`、`ctime`、`fileStatus`/`fileStatusText`、`estimateTime`、`url`、`beEncrypt`。
- 进度枚举：0进行中/1已完成/2已过期/3已删除/4导出失败。
- 下载：`window.open(url)`；实测 URL 为 zip（内含 xlsx），`beEncrypt=1` 但 password 空、未加密；查密码 `POST /datacenter_pms/web/exportinfo/selectExportPassword/pv583` body `{id}`；记录查看 `POST /datacenter_pms/web/exportinfo/updatePasswordNum/pv4860` body `{id}`。

---

## 9. 写操作实测清单（全部基于自建/复制活动，测完清理）

| 操作 | 接口 | 实测 |
|---|---|---|
| 新增（按活动ID） | add/v100 | add/v100 |
| 新增（按商品） | add/v100 | 10372（BI选10商品，0.01/1/1000，校验成功） |
| 部分结束 | partial-finish/v100 | 10371 双进行中行提前结束成功 |

---

## 10. 枚举字典（源码+实测）

### 10.1 活动状态（`68155.c`）
创建中 `0` / 待开始 `1` / 进行中 `2` / 已结束 `3` / 创建失败 `4`（列表筛选 1/2/3）。

### 10.2 平台校验状态（`68155.o`）
校验中 `0` / 商品校验失败 `1` / 活动校验失败 `2` / 平台创建失败 `3` / 平台创建成功 `4`。

### 10.3 业务类型 / 活动类型 / 客户
- 业务类型：普品 `1`/集采 `2`/普品+集采 `3`。
- 促销活动类型 `activityScopeType`：按商品 `1`/按活动ID `2`。
- 活动子类型 `wholesaleType`：一口价1/特价4/限时特价(不可用券)5/限时特价(可用券)6/普通拼团7/批购包邮8/诊所拼团71/连锁包邮11。
- 客户圈选 `userType`：全部3/店铺新客0/品种新客1/自定义标签2/自定义名单5。
- 客户类型 `customerTypes`：不限-1/零售单体0/第三终端1/连锁总部(批零一体)2/连锁加盟3/连锁总部(纯连锁)4/商业公司5/民营医院6/医疗器械经营店8。
- 活动状态（明细 `activityStatus`）：5=进行中；促销状态 `promotionStatus`：1=进行中/3=已结束。

---

## 11. 错误码

| code | 含义/示例 |
|---|---|
| 40001 | 成功 |
| 40004 | 参数校验：`size must be between 0 and 20`（名称超长）/ `公司ID不能为空,ERP编码不能为空`（按商品明细缺参）/ `促销活动ID不能为空` |
| 40005/40006/40007 | 未登录/无权限/token过期 |
| 40012 | 一般错误（如导出用GET） |
| 40050 | 功能鉴权拒绝 |
| **41007** | 业务校验：活动行不能为空 / 总促销金额不一致 / 活动id重复 / 仅双进行中可提前结束 / 仅集团账号可多公司导入 |
| 42053 | 文件导出中（查密码时未完成） |
| 52080 | 告警 |

> 上传校验失败的业务错误在 `data.message` 里以 `ErrCode:[41007], ErrMsg:[...]` 形式返回，逐行原因在 `platformExcelResult.data`。

---

## 12. 调用顺序（Agent 标准流程）

**按商品新增**：token → selectable-expenses 选费用 → prepare-expense 取业务类型 → 上传商品Excel(type=1) → add/v100(goodUrl=fileUrl,totalPromotionAmount=合计) → 得新ID。
**按活动新增**：同上但上传 type=2 → add/v100(wholesaleUrl=fileUrl)。
**查看/明细**：detail → campaign-detail-page-by-activity（活动ID明细）或 by-goods（商品明细，需providerId+erpCode）。
**补贴明细**：列表已补贴金额点击 → subsidy-order-page → 导出 subsidy-order-export。
**提前结束**：明细选 selectable=true 行 → partial-finish(activityId,activityScopeType,campaignIds)。
**复制**：detail 源 → add/v100 去id沿用字段。
**导出**：export/pv29230 → 轮询批量任务(fileType=207) → 下载。

---

## 13. 证据与注意事项

- 证据已并入本文。
- ⚠️ 字段名一致性：本文档字段名严格取前端源码变量名（如 `subsidyPerBox`/`qtyLimit`/`perCustomerQtyLimit`/`campaignId`/`wholesaleUrl`），与界面标签一一映射（§2），Agent 可直接按此构造请求。
- ⚠️ 测试产生的活动/费用均已结束清理；所有写操作测试必须在自建对象上进行。
- ⚠️ buildTime 默认 `2026-11-17 18:42:50`，可由 `--build-time` 覆盖；token 由调用方传入，本包不抓包/不自行获取凭证。
