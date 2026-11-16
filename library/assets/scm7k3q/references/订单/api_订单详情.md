# 订单详情（API）

> 订单行内「查看证件 / 药师帮业务员 / 查看开票信息」按钮，以及质检报告，对应的只读接口。
> 公共参数/鉴权见 `references/通用/api_认证与公共约定.md`；字段映射见 `zddz.md §3~§5`。
> **账号归属：③ 仅自营**（权威判定见 `references/sy.md §0.4`；本子板块为自营账号体系专属，摇钱树账号不调用）


## 1. 接口总表

| # | 接口 | 用途 | 请求 | 返回 |
|---|---|---|---|---|
| 1 | `POST /scm-order/drugstore/getCertificateData` | 查看药店证件 | `orderId`+`storeId`+`receiverinfo` | `data.{storeInfo,storeInfoExt,storePapersInfo,allPapers,errorReason,base}` |
| 2 | `POST /scm-base/index/getSalesmenUserInfo` | 查看业务员 | 仅公共参数 | `data.{name,phone,qrcodeUrl,techContact}` |
| 3 | `POST /scm-order/wholesaleOrder/getDrugstoreInvoiceInfo` | 查看开票信息 | `drugstoreBranchId`+`storeInvoiceType` | `data.{taxNo,bankName,bankcardNo,picName,picAddress,invoicePhone,invoicePic}` ✅实测 |
| 4 | `POST /scm-base/index/getInvoiceAgreementInfo` | 发票协议/可选类型 | 仅公共参数 | 该药店可选发票类型列表 |
| 5 | `POST /scm-order/DrugCheckReport/getApplyDrugCheckData` | 申请质检报告数据 | 订单相关 | 报告数据（"申请报告未处理数"标签源） |
| 6 | `POST /scm-order/wholesaleOrder/getOrderInvApplyNotDoneCount` | 申请开票未开票数 | 仅公共参数 | `data.{count,per,isNonDrug}` |
| 7 | `POST /scm-order/wholesaleOrder/getOrderInvApplyPer` | 开票率 | 仅公共参数 | `data.{per,perLast,isNonDrug}` |
| 8 | `POST /scm-order/wholesaleOrder/providerAbnormalOrderCount` | 异常标签总计数 | 仅公共参数 | `data`（int 0 或 各标签 dict） |

---

## 2. 查看药店证件（`getCertificateData`）

请求体：

```json
{ "orderId": 715214322, "storeId": 3322351,
  "receiverinfo": "重庆市重庆市重庆市九龙坡区杨家坪街道西郊路19号4幢附6号",
  "token": "…", "platform": "scm-admin", "version": "1.0.3" }
```

响应 `data`：

| 子结构 | 关键字段 | 界面字段 |
|---|---|---|
| `storeInfo` | `storetitle`、`fullName`(**营业执照名称**)、`invoiceType`、`taxFlag`、`subType`/`realSubType`/`childSubType`、`certStatus` | 药店名称/营业执照名称/药店类型 |
| `storeInfoExt` | `bePapersSyn`、`systemCheckId`、`manCheck` | ERP客户信息待确认判定 |
| `storePapersInfo[]` | `picTitleId`/`picName`/`no`/`name`/`beginDate`/`endDate`/`isLongEnd`/`longEndDate`/`proxyOpername`/`principal`/`qualityManager`/`picAddress`/`phone`/`certifiUnit`/`areaPrefix`/`picUrl` | 证件明细 |
| `allPapers` | 字典（键=证件类型 ID：4/6/7/16/2/3/31/32…50+） | 门店照片/其它证件 |
| `errorReason[]` | `codeValue`/`codeName` | 证件异常原因 |
| `base` | `providerId`/`providerName`/`tabNum`/`orderInfo` | 供应商/订单基础 |

`storePapersInfo` 实测 4 类（picTitleId → 名称 → 界面映射）：

| picTitleId | 名称 | 采集字段 → 界面 |
|---|---|---|
| 4 | 营业执照 | `no`=社统编号；`fullName`=营业执照名称 |
| 6 | 采购人员身份证扫描件 | `name`=姓名、`no`=身份证号、`beginDate`=发证日期、`endDate`/`isLongEnd`=有效期至(长期)、`longEndDate` |
| 7 | 采购委托书扫描件 | `name`=姓名、`no`=身份证号、`phone`=电话、`beginDate`=起始日期、`endDate`/`isLongEnd`=有效期至(长期) |
| 16 | 医疗机构执业许可证/诊所备案证 | `name`=许可证店名、`no`=证书编号、`principal`=法定代表人、`qualityManager`=主要负责人、`beginDate`=发证日期、`endDate`=有效期至、`certifiUnit`=发证机关、`areaPrefix`=省市区、`picAddress`=证件地址 |

> 「长期」以 `isLongEnd=1` + `longEndDate` 表示。

---

## 3. 查看开票信息（按钮）✅ 已实机验证

**接口**：`POST /scm-order/wholesaleOrder/getDrugstoreInvoiceInfo`（已实机调用，返回真实开票资料）

请求体：

```json
{ "drugstoreBranchId": 2534281, "storeInvoiceType": 1,
  "token": "…", "platform": "scm-admin", "version": "1.0.3" }
```

| 参数 | 说明 |
|---|---|
| `drugstoreBranchId` | 药店分支 ID（取列表行 `drugstoreBranchId`） |
| `storeInvoiceType` | 发票类型（1=采集样本；可选类型来自 `getInvoiceAgreementInfo`） |

响应 `data`（与界面 7 字段逐项对应，实机样本）：

| 界面字段 | 响应 key | 实机样本值 |
|---|---|---|
| 税号 | `taxNo` | 91520329MAAJW1P25H |
| 开户银行 | `bankName` | （部分药店空） |
| 开户账号 | `bankcardNo` | （部分药店空） |
| 公司名称 | `picName` | 余庆县吕生举药房 |
| 公司地址 | `picAddress` | 余庆县松烟镇江北路70号 |
| 联系电话 | `invoicePhone` | `<联系电话，已脱敏>` |
| 发票图片 | `invoicePic` | 图片 URL（样本 None） |

> 发票类型候选值由 `getInvoiceAgreementInfo` 提供；列表行另有 `invoiceSign`/`invoiceTypeName` 标记是否开票/类型。

---

## 4. 查看业务员（`getSalesmenUserInfo`）

请求：仅公共参数。响应 `data`：

| 字段 | 界面 |
|---|---|
| `name` | 业务员名称 |
| `phone` | 业务员手机号 |
| `qrcodeUrl` | 二维码 |
| `techContact` | 技术联系人 |

> 点击列表行「药师帮业务员」按钮即调用；返回当前订单对应业务员信息。

---

## 5. 质检报告（`getApplyDrugCheckData`）

`POST /scm-order/DrugCheckReport/getApplyDrugCheckData`（采集 11 次）。用于「申请报告未处理数」标签与查看报告。请求/响应结构采集未展开，调用前以真机实测为准；本接口登记为"详情-报告"已可用，参数待补。

---

## 6. 异常标签计数端点

顶部「标签筛选0/1」共 9 个标签的数据源：

| 标签 | 端点 | 状态 |
|---|---|---|
| 申请开票未开票数 | `getOrderInvApplyNotDoneCount` → `data.{count,per,isNonDrug}` | ✅实测响应 |
| 申请报告未处理数 | `getApplyDrugCheckData`（见 §5） | ✅端点定位 |
| 其余 7 个（超72h/超24h未揽收、ERP待确认、发货超5天未签收、部分未开单、电汇待审核、物流异常） | `providerAbnormalOrderCount` | ⚠️端点定位，`data` 变体（int 0 / 各标签 dict）待带数据账号复验 |

> 详细字段映射见 `zddz.md §7`。

---

## 7. 限制

- 全部只读；写操作（改备注/改单/退款）不在本板块。
- `getCertificateData` 必须带 `orderId`+`storeId`+`receiverinfo`（从列表行取）。
- 开票信息（`getDrugstoreInvoiceInfo`）、申请开票未开票数（`getOrderInvApplyNotDoneCount`）已实机验证；质检报告/异常标签聚合的细项待带数据账号复验。
