> **框架内自包含副本** ｜ token 由调用方通过 `--token`/`PMS_TOKEN`/`--state-file` 传入；本包不登录、不读父凭证仓库。
> `buildTime` 通过 `--build-time` 可选传入（默认 `2026-11-17 18:42:50`）；凭证/构建异常只报错，不自行登录。
> 原始归档已剥离（实测身份与过程路径不随包，以本副本为准）。

# 促销费用管理 API 文档（完全独立版 · 可照此开发）

> 页面：`https://pms.ysbang.cn/#/tms/promotion-cost-management`
> 生成：2026-11-17 ｜ 方法：webpack 源码 100% 逆向（`83250`/`81793:41225`/`app.js:76937,79851`）+ 真实 HTTP 请求实测
> **自包含**：本文档含鉴权、公共参数、错误码、全部枚举、字段类型、参数模板、真实响应、调用顺序。开发者/Agent 无需参考其它文档即可完成查询与创建。

---

## 0. 快速开始（Agent 照抄即可创建一条费用）

1. 拿到登录态 token（见 §1）；所有请求 POST 到 `https://pms.leyopharm.com`。
2. 组装 body（见 §5.1 新增模板），**必带** `token` + `buildTime`。
3. `POST /operation-service/promotion-expense/add/v100` → `code="40001"`、`data=<新费用ID>` 即成功。

```json
{
  "brandInfo": "", "amount": 10000,
  "goodsItems": [{"erpCode":"SP0010681","providerId":3364,"maxSubsidyPerBox":0.7,"qtyLimit":100,"perCustomerQtyLimit":10}],
  "userType": 3, "customerLabelIds": [], "customerFileUrl": "", "customerIds": "", "inputMode": null,
  "effectiveStart": "2026-11-17 00:00:00", "effectiveEnd": "2026-11-24 23:59:59",
  "activityTypes": [1], "budgetUserIds": [], "customerTypes": [-1], "areaCodes": [], "fundSource": 3,
  "token": "<TOKEN>", "buildTime": "<BT>"
}
```

---

## 0.5 推荐默认值（用户 2026-11-18 确认，Agent 创建时自动填充）

> **优先级**：用户本次明确要求 > 本默认值 > 前端系统默认 > 留空。

| 前端显示名称 | 推荐默认值 | 说明 |
|---|---|---|
| 促销费用名称 | `Agent自动补贴费用_<递增序号>` | 序号1,2,3…递增（取已存在同前缀最大序号+1），≤20字 |
| 指定公司 | 未填 → 系统默认第一个公司 | 如 3364 重庆央拓 |
| 业务类型 | 未填 → 系统默认 | 普品+集采 |
| 厂牌信息 | 留空 | — |
| 费用资金来源 | 子公司-店铺费用 | 字典 code=5 |
| 费用 | 1000000 | — |
| 商品输入框 / 最高补贴金额 / 品种数量上限 / 单客补贴数量上限 | 留空 | 动态项，由用户提供 |
| 客户圈选 | 未填 → 系统默认 | 全部客户 |
| 自定义标签 / 自定义名单 / 可使用区域 | 留空 | 按客户圈选联动 |
| 客户类型 | 未填 → 系统默认 | 不限 |
| 费用有效时间（开始/结束） | **与活动时间一致** | 参见下条；默认当天 `00:01:00~23:59:59` |
| 活动类型 | 全部 | 选"全部"会清空其它勾选 |
| 预算使用人 | 留空 | 空=所有人 |

**费用有效时间规则（用户确认）**：与活动时间一致——若用户指定了活动时间则完全取活动开始/结束；否则取处理日期当天 `00:01:00~23:59:59`（与活动默认相同）。不再单独询问。

---

## 1. 鉴权与公共参数（所有接口必带）

- **token**：由调用方通过 `--token`/`PMS_TOKEN`/`--state-file` 传入（本包无凭证获取逻辑）：
  
  - **实测**：凭证 token 可直接调用本文档所有接口（已验证 page/v100、add/v100 等），**无需浏览器/CDP（直连）**。
  - ⚠️ 凭证缺失或 40006/40007 → 报错并请调用方提供新凭证
- **buildTime**：前端构建时刻字符串，源码 `79851.D()` 强制写入 `params.buildTime`。由 `--build-time` 可选传入，默认 `2026-11-17 18:42:50`；若 token 有效却 40006/40007，请调用方提供其页面当前 buildTime（本包不抓包）。
- **请求头**（源码 `79851` 注入，直连建议带上）：
  - `Content-Type: application/json`
  - `token: <TOKEN>`
  - `Authorization: Bearer <TOKEN>`（`/operation-service/` 前缀接口必带）
  - `origin: https://pms.ysbang.cn`、`referer: https://pms.ysbang.cn/`
- **成功码**：`code="40001"`（不是错误）；失败码见 §9。
- **响应分页**：`data.list[]` + `data.count`。

---

## 2. 页面结构总览

| 区域 | 内容 |
|---|---|
| 筛选项（9） | 促销费用ID / 促销费用名称 / 公司 / 商品 / 状态 / 预算使用人 / 费用创建人 / 费用有效时间 / 创建时间 |
| 按钮 | 重置 / 搜索 / 新增 / 导出 / 批量任务列表 |
| 列表（13列+操作） | 见 §4 |
| 新增抽屉（1480px，7 分组） | 基础信息 / 费用总金额 / 商品补贴配置 / 客户选择 / 费用有效时间 / 活动类型 / 预算使用人 |

---

## 3. 筛选项详解（控件类型 100% 源码确认 + 前端实测）

数据源 `U()` 默认值 + `MultiOrSingleSelector`/`SearchGoods`/`SearchUser`/`DatePicker` 组件（chunk 83250）。

| 筛选项 | 控件类型 | 传参字段 | 默认值 | 数据源/接口 | 交互 |
|---|---|---|---|---|---|
| 促销费用ID | **输入框** el-input | `expenseCode` | `""` | 手输 | 输入即过滤非字母数字；**回车直接搜索** |
| 促销费用名称 | **输入框** el-input | `expenseName` | `""` | 手输 (maxlength50) | 回车直接搜索 |
| 公司 | **静态下拉·多选** MultiOrSingleSelector | `providerIds[]` | 默认取公司列表第一个 (3364) | vuex `newProviderList` | 实测候选：重庆央拓(3364) |
| 商品 | **远程搜索候选** SearchGoods | `goodsKeyword` | `""` | `goodsOption/pv7240`（`76937.Zv`），valueProp=goodsCode | placeholder"商品编码、名称"；allow-create；选中后自动搜索 |
| 状态 | **静态下拉·单选** MultiOrSingleSelector | `status` | `""` | 枚举 §7.1 | 实测候选：待开始/进行中/已结束 |
| 预算使用人 | **远程搜索候选·多选** SearchUser | `budgetUserIds[]` | `[]` | `userOption/pv28280` | placeholder"请输入姓名搜索"，取 userId |
| 费用创建人 | **远程搜索候选·多选** SearchUser | `creatorIds[]` | `[]` | `userOption/pv28280` | 同上 |
| 费用有效时间 | **日期区间** DatePicker(datetimerange) | `effectiveStart`/`effectiveEnd` | `""` | — | format yyyy-MM-dd HH:mm；提交 start 补`:00`/end 补`:59` |
| 创建时间 | **日期区间** DatePicker | `createTimeStart`/`createTimeEnd` | 近30天 (T-29~T) | — | 提交 start 补`00:00:00`/end 补`23:59:59` |

**筛选→查询参数格式化**（源码 `R()`）：空串/空数组字段直接删除（不过滤＝不带该字段）；时间字段按上表补秒；附加 `page/pageSize`。

---

## 4. 查询列表接口

### 4.1 列表分页
`POST /operation-service/promotion-expense/page/v100`

实测请求体（默认，公司3364 + 创建时间近30天）：
```json
{"expenseCode":"","expenseName":"","effectiveStart":"","effectiveEnd":"",
 "providerIds":[3364],"goodsKeyword":"","status":"","budgetUserIds":[],"creatorIds":[],
 "createTimeStart":"2026-10-19","createTimeEnd":"2026-11-17",
 "page":1,"pageSize":10,"token":"<TOKEN>","buildTime": "<BT>"}
```

实测响应 `code=40001, data:{list,count}`，`list[]` 行字段：
| 字段 | 含义 | 实测示例 |
|---|---|---|
| `id` | 主键 | <ID> |
| `expenseCode` | 促销费用ID | FY20261116204 |
| `expenseName` | 名称 | 莎普爱思特价补贴（省内） |
| `providers[]` | 公司 `{id,name}` | 3364/重庆央拓 |
| `businessTypeText` | 业务类型文本 | 普品+集采 |
| `fundSource` / `fundSourceText` | 资金来源码/文本 | 3 / 子公司-厂牌费用 |
| `amount` / `availableAmount` | 费用总额 / 可使用金额 | 99999.0 / 92999.7 |
| `effectiveStart`/`effectiveEnd` | 有效期 | 2026-11-16 00:00:00 / … |
| `activityTypes[]` | 活动类型 `[{id,name}]` | [{id:4,name:"特价（不可用券）"}] |
| `budgetUsers[]` | 预算使用人 `[{id,name}]` | [] |
| `creatorName`/`cdatetime` | 创建人/创建时间 | 曾文雅 / 2026-11-16 19:30:42 |
| `status` | 状态文本（直接显示） | 进行中 |
| `editable`/`canEnd` | 可编辑/可结束 | false / true |

### 4.2 列表 13 列与行字段映射
| 列 | 行字段 | 显示 |
|---|---|---|
| 促销费用ID | `expenseCode`（可点击→详情） | 原样 |
| 促销费用名称 | `expenseName` | 折叠文本 |
| 公司 | `providers[].name` join | 空"--" |
| 业务类型 | `businessTypeText` | 空"--" |
| 费用资金来源 | `fundSourceText` | 空"--" |
| 费用 | `amount` | 空"--" |
| 可使用金额 | `availableAmount` | 空"--" |
| 费用有效时间 | `effectiveStart`/`effectiveEnd` | 去秒后 `start - end` |
| 活动类型 | `activityTypes[].name` join | 空"--" |
| 预算使用人 | `budgetUsers[].name` join | 空"所有人" |
| 创建人 | `creatorName` | 空"--" |
| 创建时间 | `cdatetime` | 原样 |
| 状态 | `status` | Tag：待开始success/进行中warning/已结束disabled |

### 4.3 详情
`POST /operation-service/promotion-expense/detail/v100`，body `{"id":<主键>}`，返回 §5.1 表单同结构（含 `goodsRows[]`/`customerLabels[]`/`areaCodes`/`customerTypes`/`fundSource`/`businessType`/`userType` 等）。

### 4.4 字典/远程搜索接口（筛选与表单共用）
| 接口 | 方法 | 请求体 | 实测响应 |
|---|---|---|---|
| `/operation-service/promotion-expense/fund-source-options/v100` | POST | `{}`（无参） | `data:[{"code":3,"label":"子公司-厂牌费用"},{"code":4,"label":"子公司品种毛利"},{"code":5,"label":"子公司-店铺费用"}]` ⚠️字段是 **code** 不是 value |
| `/datacenter_pms/web/pms/user/companyOptions/v100` | POST | `{}` | `data:[{"providerId":3364,"providerName":"重庆央拓医药有限公司","shortName":"重庆央拓","providerType":1}]` |
| `/datacenter_pms/web/search/userOption/pv28280` | POST | `{"size":200,"name":"刘","providerId":"","userIsvalId":"1"}` | `data:[{"userId":1844,"userName":"刘丽娟","account":"LY010357"},…]`（预算使用人/创建人取 userId） |
| `/datacenter_pms/web/search/goodsOption/pv7240`（`76937.Zv`） | POST | 搜索词参数 | 商品远程搜索（筛选用，valueProp=goodsCode） |
| `/operation-service/customerLabel/labelList/v100` | POST | `{"providerId":3364,"labelName":"","page":1,"pageSize":50,"updateStatusList":[1]}` | `data.list[]`（id/name/provider/customerNum 等），自定义标签候选取 id/name |

---

## 5. 新增 / 编辑费用（核心写操作）

```json
{
  "providerIds": [3364],
  "businessType": 3,
  "brandInfo": "",
  "amount": 10000,
  "goodsItems": [
    {"erpCode":"SP0010681","providerId":3364,"maxSubsidyPerBox":0.7,"qtyLimit":100,"perCustomerQtyLimit":10}
  ],
  "userType": 3,
  "customerLabelIds": [],
  "customerFileUrl": "",
  "customerIds": "",
  "inputMode": null,
  "effectiveStart": "2026-11-17 00:00:00",
  "effectiveEnd": "2026-11-24 23:59:59",
  "activityTypes": [1],
  "budgetUserIds": [],
  "customerTypes": [-1],
  "areaCodes": [],
  "fundSource": 3,
  "token": "<TOKEN>", "buildTime": "<BT>"
}
```
- 新增：`POST /operation-service/promotion-expense/add/v100` → `data=<新ID>`
- 编辑：`POST /operation-service/promotion-expense/update/v100`，body 同上 **+ `id`**，goodsItems 行带 `id`（编辑场景：id + goodsItems 行 id）
- 校验通过后前端弹"保存成功"并刷新列表

### 5.2 每个字段的来源/控件/必填（100% 源码确认）
| 分组 | 字段 | 控件类型 | 传参字段 | 必填 | 来源与约束 |
|---|---|---|---|---|---|
| 基础信息 | 促销费用名称 | 输入框(max20) | `expenseName` | ✓ | 手输 trim |
| 基础信息 | 指定公司 | 静态多选下拉 | `providerIds[]` | ✓ | companyOptions；变更时过滤掉不在选中公司的商品 |
| 基础信息 | 业务类型 | 静态单选下拉 | `businessType` | ✓ | 1普品/2集采/3普品+集采；变更时按映射过滤商品 |
| 基础信息 | 厂牌信息 | 输入框(max20) | `brandInfo` | — | trim |
| 费用总金额 | 费用资金来源 | 静态单选下拉 | `fundSource` | ✓ | fund-source-options 的 **code** |
| 费用总金额 | 费用 | 输入框(仅数字) | `amount` | ✓ >0 | 输入时 `replace(/[^\d]/g,"")`；校验商品补贴合计≤费用 |
| 商品补贴配置 | 商品输入 | 远程搜索多选 el-select | → goodsItems | — | 见 §5.3 |
| 商品补贴配置 | 最高补贴金额（元/盒） | 数字输入(min 1e-6) | `goodsItems[].maxSubsidyPerBox` | ✓ | 合计不能超 amount |
| 商品补贴配置 | 品种数量上限 | 数字输入(min1,整数) | `goodsItems[].qtyLimit` | — | |
| 商品补贴配置 | 单客补贴数量上限 | 数字输入(min1,整数) | `goodsItems[].perCustomerQtyLimit` | — | |
| 商品补贴配置 | 参考信息 | 只读 | `estimatedP4`/`stockAvailable` | — | 预估P4/可用库存，空"--" |
| 客户选择 | 客户圈选 | 单选 radio | `userType` | ✓ | 5 项见 §7.4 |
| 客户选择 | 自定义标签 | 远程搜索多选 | `customerLabelIds[]` | 当 userType=2 | labelList 接口 |
| 客户选择 | 自定义名单 | 粘贴/上传组件 | `customerFileUrl`/`customerIds`/`inputMode` | 当 userType=5 | 见 §5.4 |
| 客户选择 | 客户类型 | 多选 checkbox | `customerTypes[]` | ✓ | 见 §7.5，默认[-1]不限 |
| 客户选择 | 可使用区域 | 省市级联(depth2) | `areaCodes[]` | — | 省+市编码 |
| 费用有效时间 | 起止 | 日期区间(datetimerange) | `effectiveStart`/`effectiveEnd` | ✓ | 提交 start秒=0/end秒=59 |
| 活动类型 | 多选 checkbox | `activityTypes[]` | ✓ | 见 §7.3；选"全部"清空其它 |
| 预算使用人 | 远程搜索多选 | `budgetUserIds[]` | — | userOption 接口，取 userId；空显示"所有人" |

**必填校验**（源码 `K`）：expenseName / providerIds / businessType / amount>0 / customerLabelIds(userType=2) / 客户名单已校验(userType=5) / effectiveStart+End / activityTypes / customerTypes / fundSource。另有商品行校验（重复、maxSubsidyPerBox 必填）与补贴合计≤amount。

### 5.3 商品补贴配置（输入候选 + 导入）

**（A）远程搜索输入框**
- placeholder（实测）：`可输入drugid、SPU编码、乐药编码、商品编码、商品名称、厂牌营销方`
- 控件：`el-select(filterable, remote, multiple, value-key=erpCode)`，选中后可继续输入选择，点"添加"批量加入表格，可单行删除。
- 接口：`POST /operation-service/promotion-expense/goods-options/v100`
- 请求体：`{"goods":"<关键词>","providerIds":[3364],"businessType":[0,5],...}`
  - `businessType` 传**数组**：普品→`[0]`、集采→`[5]`、普品+集采→`[0,5]`（源码 `y.Q0` 映射）
  - 实测用 `[0,5]` 搜"阿莫西林"成功。
- 响应 `data[]` 每项字段（实测）：
  `providerId, providerName, erpCode, goodsId, productCode, drugId, spuCode, goodsName, goodsSpec, manufacturer, pmsStaffName, goodsBusinessType, estimatedP4, stockAvailable`
  - 这就是"可输入 spuid（goodsId）/SPU编码（spuCode）/乐药编码/商品编码（erpCode）/商品名称（goodsName）/厂牌营销方（pmsStaffName）"的匹配来源。
  - **交叉验证**（`fee_crosscheck.py`）：关键词 `SPU0009092`（SPU编码）、`375788`（drugId）、`阿西诺`（商品名称/厂牌）均命中同一条商品 `SP0010681` —— 多种输入方式实测有效。
- 加入 goodsItems 时仅提交 `{erpCode,providerId,maxSubsidyPerBox,qtyLimit,perCustomerQtyLimit}`（estimatedP4/stockAvailable 仅展示，不提交）。

**（B）Excel 导入**（`导入`按钮，先选公司才可用）
- 模板下载：`DOWNLOAD /operation-service/promotion-expense/import-goods-template/v100`（无参，返回 xlsx，content-type `application/vnd.ms-excel;charset=utf-8`）
- 模板表头（实测）：`商品编码 | 公司ID | 最高补贴金额（元/盒） | 数量上限 | 单客补贴上限`
- 上传：`UPLOAD /operation-service/promotion-expense/import-goods/v100?providerIds=3364&businessType=3`
  - multipart 字段：`excelFile`（xlsx 文件）+ token/buildTime
  - 字段名映射（源码常量 S）：`商品编码→erpCode, 公司ID→providerId, 最高补贴金额（元/盒）→maxSubsidyPerBox, 数量上限→qtyLimit, 单客补贴上限→perCustomerQtyLimit, 失败原因→errorMessage`
- 实测响应（上传 2 行成功）：
```json
{"code":"40001","message":"操作成功","data":{"successCount":2,"message":"已成功导入2条数据",
 "goodsRows":[
  {"importSuccess":true,"errorMessage":"","providerId":3364,"providerName":"重庆央拓","erpCode":"SP0010681","goodsName":"阿西诺 威奇达 阿莫西林克拉维酸钾片","goodsSpec":"0.375g*6片","maxSubsidyPerBox":0.5,"qtyLimit":100,"perCustomerQtyLimit":10,"goodsBusinessType":1},
  {"importSuccess":true,"errorMessage":"","erpCode":"SP0010740",...}
 ]}}
```
  - 前端按 `importSuccess` 过滤成功行回填 goodsItems；失败行走"下载失败数据" `download-invalid-list`（`82430.gR`，失败数据 xlsx 列名含"失败原因"）。

### 5.4 客户选择 · 自定义名单（userType=5）

两种输入方式（互斥，通过 `inputMode` 区分：1=文件 / 2=粘贴）：

**（A）粘贴文本**（实测）
- 接口：`UPLOAD /operation-service/promotion-expense/validate-customer-list/v100`
- ⚠️ **调用形态**：走 `Ay.upload`（FormData），`pasteText` 必须是 **multipart 表单字段**（不是 JSON body）——用 JSON/form-urlencoded 会返回 `41007 请上传Excel或粘贴名单`。
- 内容格式：一行一个药店，支持三种填法（前端提示原文）：
  1. **纯药店ID**（如 `2799279`）
  2. **药店名称**（按名称反查，需名称可唯一识别）
  3. **药店ID + 药店名称**（如 `2799279 重庆XX药店`）——**两者都填时以药店ID为准校验**
  - 单次≤50行（源码前端限制 >50 行提示改用 Excel）。
- 实测（交叉验证，三种填法均 `passed:true`，见 `fee_crosscheck*.json`）：
```json
// 纯ID '2799279\n1335719'
{"code":"40001","data":{"passed":true,"customerCount":2,"customerIds":"2799279,1335719","inputMode":2,"errorMessage":"","errorRows":[]}}
// ID+名称 '2799279 重庆'  → customerIds="2799279"
// ID正确+名称错误 '2799279 错误名称测试' → 仍 passed:true, customerIds="2799279"（证明以ID为准）
```
  - 校验通过后取 `data.customerIds` → 提交体 `customerIds`，`data.inputMode` → `inputMode`，`data.customerFileUrl` → `customerFileUrl`。
- 失败示例（ID 不存在）：`passed:false, errorMessage:"输入的药店ID 1001 未识别", errorRows:[]`。
- 数据字段返回：`passed, customerCount, customerFileUrl, customerIds, inputMode, errorMessage, errorRows`。

**（B）Excel 上传**：同接口 multipart 传 `file`（excel 字段：药店ID、药店名称），返回同结构，`inputMode=1`。

> 药店 ID 来源：可走 BI 出库统计 Ultra 查「药店id」维度（实例：2799279/1335719/2817110，注：并非所有 BI 药店 ID 都被促销系统识别，以本校验接口结果为准）；商品来源：§5.3(A) 商品搜索接口。

---

## 6. 导出 / 批量任务列表 / 列表操作（全部实测）

### 6.1 导出（异步任务）
`POST /pms_operation/web/pms/promotion-expense/export/v100`
- body = 筛选参数去掉 page/pageSize + `fileName`（前端自动生成，格式"促销管理费用<YYYYMMDDHHmmss>"，可自定义）
- 实测响应：`{"code":"40001","data":{"lineUpNumber":122,"estimateTime":"2026-11-20 10:51:31","exportInfoId":217681,"exportInfoType":1}}`
- 前端提示："已经生成导出任务，请到【批量任务列表】查看！"（`lineUpNumber` 只是排队成功，**不代表文件已生成**）

### 6.2 批量任务列表
`POST /operation-service/promotion-activity-export-task/list`
- body：`{"current":1,"size":10,"total":0,"type":9999,"fileType":206,"token":..,"buildTime":..}`（`fileType=206`=促销费用；207=促销活动）
- 实测响应 `data.list[]` 行字段：
  | 字段 | 含义 | 实测示例 |
  |---|---|---|
  | `id` | 任务ID（=exportInfoId） | 217680 |
  | `fileType`/`fileTypeCode` | 任务名称/编码 | 促销管理费用-导出 / 206 |
  | `fileName` | 文件名 | 促销管理费用202611172110 |
  | `ctime` | 申请时间 | 2026-11-17 21:10:27 |
  | `fileStatus` / `fileStatusText` | 进度码/文本 | 0导出中 / 1已导出 / 4导出失败 |
  | `estimateTime` | 预计完成时间 | 2026-11-20 10:40:27 |
  | `url` | 下载链接（fileStatus=1 出现） | `https://image.leyopharm.com/pms/import/.../促销管理费用202611172110.zip` |
  | `beEncrypt` | 是否加密标志 | 1 |
- **进度枚举**（源码 module 58814）：`0`进行中 / `1`已完成 / `2`已过期 / `3`已删除 / `4`导出失败。进度文本带"预计结束: <estimateTime>"。
- 列表列（4 列）：任务名称(fileType) / 文件名称(fileName) / 申请时间(ctime) / 任务进度(fileStatus)；**密码列**仅在 `beEncrypt===1` 且任务已完成时显示。
- 下载：`window.open(url)`；`fileStatus=4` 时按钮文案变"下载失败数据"。

### 6.3 下载文件形态与密码（实测）
- **文件形态**：实测下载 URL 是 `.zip`（`content-type: application/zip`），内含 1 个 `.xlsx`（如 `促销管理费用202611172110.xlsx`）。⚠️ 下载结果**可能是 xlsx，也可能是 zip 压缩包**（视导出量/配置），Agent 需按实际 content-type/扩展名处理。
- **加密与密码**：
  - `beEncrypt=1` 表示"可能加密"，但是否真加密要看文件内容——实测本次 zip 内 xlsx 的 `flag_bits=0x808`（`0x1` 位为 0，**未实际加密**），密码查询返回空串，与用户"目前测试不需要密码"一致。
  - 查询密码：`POST /datacenter_pms/web/exportinfo/selectExportPassword/pv583`，body `{"id":<任务ID>}` → `data:{id,fileName,password,estimateTime,fileStatus}`；导出未完成时返回 `code=42053 文件导出中！！！`。
  - 记录查看次数：`POST /datacenter_pms/web/exportinfo/updatePasswordNum/pv4860`，body `{"id":<任务ID>}` → `data.num`。
  - 若 `beEncrypt=1` 且 `password` 非空：下载文件为加密包，需该密码解压/打开（前端"密码"列展示，显示 30 秒后自动打码）。Agent 拿到密码后按 zip/xlsx 加密流程处理。
  - 默认批量任务查询接口（非本页自定义时）：`POST /datacenter_pms/web/exportinfo/listExportInfoByType/pv583`，body `{current,size,type}`。

### 6.4 列表操作（编辑 / 复制 / 结束，全部基于我们创建的费用实测）

| 操作 | 触发条件 | 接口 | 实测结论 |
|---|---|---|---|
| **编辑** | `status≠已结束` 且 `editable=true` | `POST /operation-service/promotion-expense/update/v100`（body=§5.1 + `id`，goodsItems 行带 `id`） | 修改 id 对应费用（body=§5.1 + id） |
| **复制** | 任何行 | 前端：以 copy 模式打开抽屉（detail 回填）→ 走 **add/v100**（body 去顶层 `id`、goodsItems 去行 `id`）→ 可改任意字段 | 复制 add/v100（去 id） |
| **结束** | `canEnd=true` | `POST /operation-service/promotion-expense/finish/v100`，body `{"id":<主键>}` | 结束 finish/v100，返回 status=已结束 |

- ⚠️ `editable` 字段含义 = "是否有活动在使用"（false 时禁止编辑），与 `status` 无关；但列表"编辑"按钮按 `status≠'已结束'` 控制显示——已结束后即使 `editable=true` 也不显示编辑按钮。
- 复制是"新建"而非"引用"：复制件是独立新费用（新 ID、新费用编码），源费用不受影响。

---

## 7. 完整枚举字典（源码常量，全部确认）

### 7.1 状态（`99382.xq`）
待开始 `1` / 进行中 `2` / 已结束 `3`（列表 status 显示文本，不传码）

### 7.2 业务类型（`99382.u/UL`）
普品 `1` / 集采 `2` / 普品+集采 `3`（默认3）；业务类型→商品 businessType 映射：普品→`[0]`、集采→`[5]`、普品+集采→`[0,5]`

### 7.3 活动类型（`99382.v/$1`）
全部 `-1` / 一口价 `1` / 特价（不可用券）`4` / 限时特价（不可用商家券）`5` / 限时特价（可用商家券）`6` / 普通拼团 `7` / 批购包邮 `8` / 诊所拼团 `71` / 连锁包邮 `11`（注意：UI 显示顺序为 批购包邮 在 普通拼团 前，码值以本表为准）

### 7.4 客户圈选（`1687.o/ov`）
全部客户 `3` / 店铺新客户 `0`（从不在店铺采购） / 品种新客户 `1`（近一年未采购该品种） / 自定义标签 `2` / 自定义名单 `5`

### 7.5 客户类型（`56627`）
不限 `-1` / 零售单体 `0` / 第三终端 `1` / 连锁总部（批零一体）`2` / 连锁加盟 `3` / 连锁总部（纯连锁）`4` / 商业公司 `5` / 民营医院 `6` / 医疗器械经营店 `8`

### 7.6 资金来源（动态字典 §4.4）
`3`子公司-厂牌费用 / `4`子公司品种毛利 / `5`子公司-店铺费用（以接口返回为准）

### 7.7 商品业务类型 `goodsBusinessType`
`1`普品 / `2`集采（商品搜索返回，用于按业务类型过滤商品）

---

## 8. 调用顺序（Agent 标准流程）

**查询**：确认 token → （可选）取公司/资金来源字典 → `page/v100` 带筛选 → 读 `data.list`。
**创建**：确认 token → `companyOptions` 取 providerIds → `fund-source-options` 取 fundSource → `goods-options` 搜商品（businessType 数组）→ `labelList`(userType=2)/`validate-customer-list`(userType=5) → 组装 §5.1 body → `add/v100` → 读 `data` 新 ID。
**编辑**：`detail/v100` 回填 → 改字段 → `update/v100`（+id，goodsItems 行+id）。
**复制**：`detail/v100` 回填 → 去掉 id/行id → `add/v100` 新建（可改字段）→ 得新 ID。
**结束**：`finish/v100` body `{"id"}` → 该费用 status 变"已结束"、canEnd=false，不可再用。
**导出**：`export/v100` 记 exportInfoId → 轮询 `promotion-activity-export-task/list`(fileType=206) 至 fileStatus=1 → 取 url 下载（xlsx 或 zip）→ 若 beEncrypt=1 且需密码，调 `selectExportPassword/pv583` 取密码。

---

## 9. 错误码

| code | 含义 | Agent 处理 |
|---|---|---|
| 40001 | 成功 | 读 data |
| 40005 / 40006 / 40007 | 未登录 / 无权限 / token过期 | 报错并请调用方提供新凭证 |
| 40050 | 功能鉴权拒绝 | 账号无权限，停止 |
| 40000 | 版本升级 | 稍后重试 |
| 40003 / 42054 / 45600 | 参数错 / 自定义错误 / 业务停止 | 读 message |
| **41007** | 请上传Excel或粘贴名单 | 客户名单校验用错调用形态（须 multipart）或内容为空 |
| **42053** | 文件导出中 | 查导出密码时任务未完成，等 fileStatus=1 再查 |
| 52080 | 告警 | 读 message/data |
| HTTP≠200 | 网关/网络错误 | 重试或检查网络 |

---

## 10. 实测证据与注意事项

- buildTime 默认 `2026-11-17 18:42:50`，可由 `--build-time` 覆盖；异常时由调用方提供其页面当前值，本包不抓包。
- 易错点（源码+实测双重确认）：① 资金来源字典字段是 `code`（非 value）；② 商品搜索 businessType 传数组（普品[0]/集采[5]/两者[0,5]）；③ 客户名单校验必须 multipart（pasteText/file）；④ 客户名单"ID+名称"以 ID 为准；⑤ 导出下载可能是 zip 内含 xlsx；⑥ beEncrypt=1 不一定真加密（以 password 是否非空为准）。
- 时间字段提交格式 `YYYY-MM-DD HH:mm:ss`（start 秒0、end 秒59）；筛选创建时间默认近30天。
