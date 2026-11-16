# 订单字段对照（zddz）

> 只管「界面字段 ↔ API key ↔ 值域」。接口/参数见 `api_订单查询.md` / `api_订单导出.md` / `api_订单详情.md`。
> **覆盖度标记**：✅=采集请求体/表单模型实锤参数名；⚠️推断=按「`<响应字段名>List`」约定推导（表单模型已实锤此约定，证据强），待真机带数据账号复验筛选效果；❓=未找到。
> **展开搜索参数约定（实锤）**：页面 Vue `data()` 表单模型显示，多选筛选字段以 **`<响应字段名>List`** 数组提交（如 `orderTypeList`/`subTypeList`），单值字段裸名提交（如 `tbBundled`/`area`/`warehouseCode`）。据此推断其余字段。

---

## 1. 筛选参数 ↔ 界面

### 1.1 状态筛选（8 项 → `tabProcessStatus` 1~9）

列表 `tabCount` 实测返回 `tab1`~`tab9`（=页签计数）。用户「状态筛选」8 项对应其中值；`8`=配送完成已验证（量最大）。

| 界面状态 | `tabProcessStatus` | 备注 |
|---|---|---|
| 待处理 | 1 | 采集样本默认 |
| 资质审核 | 2 | |
| 正在开单 | 3 | |
| 分拣中 | 4 | |
| 待配送 | 5 | |
| 配送中 | 6 | |
| 配送完成 | 8 | ✅验证 |
| 整单退款 | 9 | |
| （全部/其他） | 7 / 另 | tab7 量小 |

> 另有 `processStatus`（导出用，数组，见 `api_订单导出.md §2`）。

### 1.2 基础查询（4 项，✅实测）

| 界面 | 参数 | 备注 |
|---|---|---|
| 订单id | `orderId` | 精确 |
| 药店名称 | `storeTitle`(返回) / 检索 `drugStore` | `drugStore`=药店编码 |
| 药店编码 | `drugStore` | 编码精确 |
| 营业执照名称 | `storeInfo.fullName`(详情) | 列表行无直字段，详情见 `getCertificateData` |
| 手机号 | `phone` | 收货电话 |
| 下单时间 | `order_time` | **数组** `[起ISO, 止ISO]` |

### 1.3 展开更多搜索（全部字段 + 覆盖度）

> **覆盖度标记**：✅=**浏览器实测**（Playwright 驱动系统 Edge，逐筛选字段隔离设值+抓包，确定 label↔param）。全部 35 个字段均已实测锁定。
> **重要更正**：此前按"`<响应字段名>List`"约定做的推断**大量错误**（如收款方式误为 `thirdPayIdList`、发票类型误为 `invoiceTypeList`、开单组合误为 `openCombList`、处理时间误为 `lastBuildTime` 等）。以下全部以**浏览器实测**为准。

| 界面字段 | 请求参数 | 状态 | 依据 |
|---|---|---|---|
| 订单id | `orderId` | ✅ | 浏览器隔离实测 |
| 药店 | `drugStore` | ✅ | 浏览器隔离实测 |
| 手机号 | `phone` | ✅ | 浏览器隔离实测 |
| 下单时间 | `order_time` | ✅ | 浏览器隔离实测 + bulk HAR 值变化双证 |
| 快递单号 | `logisticsNo` | ✅ | 浏览器隔离实测 |
| 商品名称 | `drugname` | ✅ | 浏览器隔离实测 |
| 订单类型 | `orderTypeList` | ✅ | 浏览器隔离实测(数组) |
| 开单组合 | `deliver_alone` | ✅ | 浏览器隔离实测 |
| 订单活动类型 | `wholesale_type` | ✅ | 浏览器隔离实测 |
| 开单后需退款 | `delivery_lack` | ✅ | 浏览器隔离实测 |
| 收款方式 | `pay_on_cash` | ✅ | 浏览器隔离实测 |
| 结算状态 | `is_close` | ✅ | 浏览器隔离实测 |
| 药店类型 | `subTypeList` | ✅ | 浏览器隔离实测(数组；表单模型亦实锤) |
| 药店ID | `drugstore_id` | ✅ | 浏览器隔离实测 |
| 揽收情况 | `latestCollectTime` | ✅ | 浏览器隔离实测 + bulk HAR 值变化双证(`receive_status` 仅 None→'' 非筛选项) |
| 医械城拼团换购 | `insBundleDeputyFlag` | ✅ | 浏览器隔离实测 |
| 医械城订单 | `order_source` | ✅ | 浏览器隔离实测 |
| 随心购订单 | `tbBundled` | ✅ | 浏览器隔离实测(表单模型亦实锤) |
| 活动ID | `wholesale_id` | ✅ | 浏览器隔离实测 |
| 地区 | `area` | ✅ | 浏览器隔离实测(表单模型亦实锤) |
| 处理时间 | `acc_end_time` | ✅ | 浏览器隔离实测(日期区间数组) |
| 申请结算时间 | `clear_time` | ✅ | 浏览器隔离实测(日期区间数组；clear_time=结算时间) |
| 运费 | `deliverFeeFlag` | ✅ | 浏览器隔离实测 |
| 特殊药品 | `containHempFlag` | ✅ | 浏览器隔离实测 |
| 签收回执 | `autograpFlag` | ✅ | 浏览器隔离实测 |
| 购销合同 | `autograpFlag2` | ✅ | 浏览器隔离实测 |
| 发票类型 | `storeInvoiceType` | ✅ | 浏览器隔离实测 |
| 分仓筛选 | `warehouseCode` | ✅ | 浏览器隔离实测(表单模型亦实锤) |
| 随货同行单 | `orderShipping` | ✅ | 浏览器隔离实测 |
| 运营标签 | `operationFlag` | ✅ | 浏览器隔离实测 |
| 区域标签 | `bindType` | ✅ | 浏览器隔离实测 |
| 是否有追溯码 | `isTraceCode` | ✅ | 浏览器隔离实测 |
| 托管 | `isHostedDrug` | ✅ | 浏览器隔离实测 |
| 维价类型 | `maintainPriceType` | ✅ | 浏览器隔离实测(表单模型亦实锤) |
| 多品凑单订单 | `tcmStoreGroupOrderFlag` | ✅ | 浏览器隔离实测 |

> 列表公共参数：`page`+`pagesize`、`cert_status`、`tabProcessStatus`、`order_str`、`is_logist`、`invoiceCount`、三个日期区间参数 `order_time[]`/`acc_end_time[]`/`clear_time[]`、token/platform/version/ex/ua 等鉴权与公共参。
> 实测方法：Playwright 驱动系统 Edge，加载已登录凭据态，进入订单列表→展开更多搜索，对 35 个 `search-item` **逐字段单独设值并触发搜索请求**，用请求体相对基线的「值变化」差集锁定每个界面字段对应的真实参数名（脚本见 `过程区/账号权限实测/isolate_params.py`、`single_iso.py`、`clean_iso.py`、`recover.py`、`date_test*.py`）。下拉类用键盘导航选值；只读日期选择器(`readonly input`)用 JS 派发 `mousedown` 事件绕过可见性检查开面板、再点日期格设区间。

---

## 2. 结果返回字段（按界面 8 组，节选）

| 界面分组 | 返回字段（key） |
|---|---|
| 订单id | `orderId`(订单id)、`orderSn`、`logisticsNo`(快递单号)、`orderTypeName`/`className`(商家标签：商家直供/YQS等) |
| 下单/最新处理时间 | `orderTime`(下单)、`providerMtime`/`pmtimeStr`(最新处理)、`payTime`(支付)、`warehouseName`/`warehouseCode`(配送仓库) |
| 药店名称 | `storeTitle`/`storeFullName`(名称)、`drugstoreBranchId`/`providerId`(药店id)、`providerCode`/`secProviderCode`(药店编码) |
| 总金额 | `totalCost`(含运费口径)、`orderPay`(应收)、`actualCost`(用户实付)、`deliverFee`/`orginDeliverFee`(运费)、`processStatus`/`processStatusName`(处理状态/标签) |
| 处理情况 | `processStatus`/`processStatusName`(状态)、`processNote`/`ysbNote`/`message`/`checkMsg`(备注)、`providerMtime`(日期时间)、`orderProcesses`(历史备注)、状态标签字段 |
| 收货信息 | `receiverName`/`receiverPhone`(收件人)、`receiverAddress`/`address`/`provinceName`/`cityName`(收货地址) |
| 订单下载次数 | `exportTimes`(次数) |
| 商品详情（下拉 `orderDetails[]`） | `orderDetailId`(序号)、`provDrugCode`(商品编码)、`wholesaleId`(活动id)、`drugname`/`drugName`(商品信息)、`specification`(规格/包装)、`factory`(厂家)、`amount`(数量)、`unitPrice`(单价)、`payPrice`(实付单价)、`realAmount`(金额)、`refundAmount`(退款金额)、`refundCost`(退款成本)；回溯码 `isTraceCode`/托管 `isHostedDrug`/维价 `maintainPriceType` |

> 返回行共 170+ 字段，全量键名以实际响应为准（详见 `api_订单查询.md §4`）。

---

## 3. 药店证件字段（`getCertificateData`，请求 `orderId`+`storeId`+`receiverinfo`）

响应 `data`：

| 子结构 | 关键字段 | 界面映射 |
|---|---|---|
| `storeInfo` | `storetitle`(药店名)、`fullName`(**营业执照名称**)、`invoiceType`、`taxFlag`、`subType`/`realSubType`/`childSubType`(药店类型)、`certStatus` | 营业执照名称= `fullName` |
| `storeInfoExt` | `bePapersSyn`、`systemCheckId`、`manCheck` | ERP客户信息待确认相关 |
| `storePapersInfo[]` | `picTitleId`/`picName`(证件名)、`no`(证书编号)、`name`(姓名)、`beginDate`(发证/起始日期)、`endDate`/`isLongEnd`/`longEndDate`(**有效期至/长期**)、`proxyOpername`(委托代理)、`principal`(法定代表人)、`qualityManager`(主要负责人)、`picAddress`(证件地址)、`phone`(电话)、`certifiUnit`(发证机关)、`areaPrefix`(省市区)、`picUrl` | 见下表 |
| `allPapers` | 字典，键=证件类型 ID（41/4/2/3/31/32/7/6/16/25/8/9/10/11/12/14/17/13/131/15…共 50+） | 门店照片/其它 |
| `errorReason[]` | `codeValue`/`codeName` | 证件异常原因 |
| `base` | `providerId`/`providerName`/`tabNum`/`orderInfo` | 供应商/订单基础 |

`storePapersInfo` 实测 4 类（picTitleId → 名称）：

| picTitleId | 名称 | 对应界面 |
|---|---|---|
| 4 | 营业执照 | 营业执照名称/编号 |
| 6 | 采购人员身份证扫描件 | 姓名/身份证号/有效期至/发证日期 |
| 7 | 采购委托书扫描件 | 姓名/身份证号/电话/起始日期/有效期至 |
| 16 | 医疗机构执业许可证/诊所备案证 | 店名/法定代表人/主要负责人/证书编号/有效期至/发证日期/发证机关/省市区/证件地址 |

> 「长期」以 `isLongEnd=1` + `longEndDate` 表示；`beginDate`/`endDate` 为 ISO 日期。

---

## 4. 开票信息字段（查看开票信息按钮）✅ 已实机验证

界面展示：发票类型 / 税号 / 开户银行 / 开户账号 / 公司名称 / 公司地址 / 联系电话。

**接口（已实机验证返回真实数据）**：`POST /scm-order/wholesaleOrder/getDrugstoreInvoiceInfo`
- 请求：`drugstoreBranchId`(药店分支ID) + `storeInvoiceType`(开票类型, 采集样本=1) + 公共参数
- 响应 `data` 字段（与界面逐项对应）：

| 界面字段 | 响应 key | 采集样本值 |
|---|---|---|
| 发票类型 | （由 `storeInvoiceType` 入参决定；`storeInfo.invoiceType` 也含类型） | 1 |
| 税号 | `taxNo` | 91520329MAAJW1P25H |
| 开户银行 | `bankName` | （样本空，部分药店未填） |
| 开户账号 | `bankcardNo` | （样本空） |
| 公司名称 | `picName` | 余庆县吕生举药房 |
| 公司地址 | `picAddress` | 余庆县松烟镇江北路70号 |
| 联系电话 | `invoicePhone` | `<联系电话，已脱敏>` |
| 发票图片 | `invoicePic` | 图片 URL（样本 None） |

> 发票类型候选值来源：`getInvoiceAgreementInfo`（采集有该端点，返回该药店可选发票类型列表）；`storeInfo.invoiceType` 为当前类型。
> 列表行内另有 `invoiceSign`/`invoiceTypeName`（是否开票/类型标记）。完整 7 字段以 `getDrugstoreInvoiceInfo` 为准，已实测可达。

---

## 5. 业务员字段（`getSalesmenUserInfo`）

响应 `data`：`name`(业务员名称)、`phone`(业务员手机号)、`qrcodeUrl`(二维码)、`techContact`(技术联系人)。点击列表行「药师帮业务员」按钮即调用。

---

## 6. 导出字段组（`getSelectFields/v100`）

| 组 | 字段数 | 字段（节选） |
|---|---|---|
| `orderList` | 17 | `orderId`(订单ID)、`statusStr`(订单状态)、`provCouponTitle`(优惠券)… |
| `drugList` | 13 | `factory`(生产厂家)、`amount`(采购数量)、`code`(商品编码)… |
| `receiptList` | 6 | `address`(收货地址)、`cityName`(市)、`districtName`(区/县)… |
| `storeList` | 2 | `providerCode`(药店编码)、`storeFullName`(药店名称) |
| `logisticsList` | 0 | （本次采集为空） |

已有自定义模板（`getAllCustomizeTemplate/v100`）：`86088` 订单ID+客户信息、`204496` 药店金额、`204534` 分拣、`455168` KA连锁总部订单明细、`455169` KA商业公司订单明细。

---

## 7. 异常标签（顶部「标签筛选0/1」）

用户所述两行异常标签：

- 标签筛选0：超72小时未揽收 / 申请开票未开票数 / 申请报告未处理数
- 标签筛选1：超24小时未揽收 / ERP客户信息待确认 / 发货后超5天未签收 / 部分未开单 / 电汇待审核 / 物流异常

**覆盖度**：这 9 个标签字符串在采集 JSON 中 0 命中（疑前端计算或未捕获 XHR）。但已**定位到计数/数据端点**：

| 异常标签 | 计数/数据端点 | 状态 | 依据 |
|---|---|---|---|
| 申请开票未开票数 | `POST /scm-order/wholesaleOrder/getOrderInvApplyNotDoneCount` | ✅实测响应 | 响应 `data:{count,per,isNonDrug}`（采集 sample: 0/'--'/0） |
| 申请报告未处理数 | `POST /scm-order/DrugCheckReport/getApplyDrugCheckData` | ✅端点已定位 | 采集该端点出现 11 次（质检报告） |
| 超72小时未揽收 / 超24小时未揽收 / ERP客户信息待确认 / 发货后超5天未签收 / 部分未开单 / 电汇待审核 / 物流异常（共 7 个） | `POST /scm-order/wholesaleOrder/providerAbnormalOrderCount` | ⚠️端点已定位 | 该端点即"异常订单计数"聚合口；采集样本 `data`=int:0（账号无异常），**各标签子字段名待带数据账号复验**（预期为有 key 的 dict 变体） |

> `providerAbnormalOrderCount` 是异常标签的总聚合端点；`getOrderInvApplyNotDoneCount` 专管"申请开票未开票数"；`getApplyDrugCheckData` 专管"申请报告未处理数"。
> 文档与代码一致原则：除已 ✅ 实测的 3 个外，其余 7 个标签的**精确子字段名待真机复验**，上表仅作排查线索，不得臆造固定参数写入调用代码。

---

## 8. 动态下拉字典源（候选选项来源）

> 用户强调"候选下拉选项是动态的"。下列端点为采集内可定位的**动态选项源**（非前端硬编码）：

| 下拉字段 | 字典端点 | 响应结构 | 样本 |
|---|---|---|---|
| 药店类型 | `GET /scm-goods/wholesaleDrug/getStoreTypeGroup` | `data[]`: `{id, groupName, storeSubtypes}`（67 组） | `storeSubtypes` 取值如 `0`(零售单体)/`01`/`0123`/`0123456` |
| 价格类型 | `GET /scm-goods/wholesaleDrug/getPriceTypes` | `data[]`: `{priceType, priceTypeName, haveInvoice}`（5 档） | `1`偏远省份价/`2`省内价/`7`周边省份价/`8`KA价/`9`含税成本价 |
| 批发标签 | `GET /scm-promotion/admin/label/listWholesaleTag` | `data.results[]` | 标签列表（分页） |
| 表格标签 | `GET /scm-base/providerTask/gettableTagList` | `data[]` | 表格标签 |
| 运营标签 | `GET /scm-base/common/operation` | 待确认响应结构 | 运营相关（采集有该端点） |

> **未捕获的字典源**：订单类型(`orderType` 值 1/3…)、收款方式(`thirdPayId`)、发票类型(`invoiceType`)、维价类型(`maintainPriceType`)、区域标签(`areaTag`)、运营标签(`opTag`)等下拉的**选项枚举接口未在本次采集捕获**（疑前端硬编码枚举或通用字典未触发）。这类字段的候选值以列表响应中的实际枚举出现为准（如 `orderType`:1/3）。

> **2026-11-12 浏览器实测更正（见 §9）**：上表字典端点是「商品」等板块的字典源，**并非订单列表 35 个筛选项的选项来源**。对订单列表逐字段打开下拉监听接口，实测结论：**仅「订单类型」开下拉时触发 `gettableTagList`（动态），其余 24 个下拉全部 `dynOpen=False`（选项为前端静态硬编码/页面加载时已就位，开下拉不再请求）**。故订单列表筛选选项以 §9 的实测枚举为准，上表仅作跨板块字典端点索引保留。

---

## 9. 筛选下拉选项全枚举 + 选项值（浏览器实测 2026-11-12）

> 方法：Playwright 驱动系统 Edge，对 35 个 `search-item` 逐个打开下拉读取全部选项标签（只取当前浮层，规避 Ant 虚拟列表残留），并**逐选项选中→点搜索→抓 `wholesaleOrder/list` 请求体**读该字段 param 的实际值。脚本 `过程区/账号权限实测/enum_options2.py`、`enum_values.py`、`fix_special2.py`；结果 `enum_options.json`、`enum_values.json`、`enum_values_special.json`。
> **动态/静态判定**：开下拉期间监听新请求。结果 **25 个下拉仅「订单类型」= 动态**（`gettableTagList`），其余 24 个 = 静态（硬编码）。值类型以请求体原样为准（区分字符串 `"1"` 与数字 `1`）。

### 9.1 文本框 / 日期（无枚举选项）

| 界面字段 | 控件 | 参数 | 说明 |
|---|---|---|---|
| 订单id | 文本框 | `orderId` | 订单号 |
| 药店 | 文本框 | `drugStore` | 药店名/编码模糊 |
| 手机号 | 文本框 | `phone` | 收货电话 |
| 快递单号 | 文本框 | `logisticsNo` | — |
| 商品名称 | 文本框 | `drugname` | 模糊 |
| 药店ID | 文本框 | `drugstore_id` | — |
| 活动ID | 文本框 | `wholesale_id` | — |
| 下单时间 | 日期区间 | `order_time` | 数组 `[起ISO, 止ISO]`，页面带默认区间 |
| 处理时间 | 日期区间 | `acc_end_time` | 数组 `[起ISO, 止ISO]` |
| 申请结算时间 | 日期区间 | `clear_time` | 数组 `[起ISO, 止ISO]` |

### 9.2 下拉：选项 → 提交值（静态，除标注外）

| 界面字段(参数) | 选项 → 值 |
|---|---|
| 订单类型(`orderTypeList`) **动态** | 商家直供=`[1]`、委托配送=`[3]`（多选数组；选项来自 `gettableTagList`） |
| 开单组合(`deliver_alone`) | 正常开单=`0`、单品独立开单=`1`、中药=`2`、计生用品=`3`、医疗器械=`4`、食品=`5`、非药品=`6`、计生药品=`7`、冷藏药品=`8`、处方药需凭处方=`13` |
| 订单活动类型(`wholesale_type`) | 特价商品订单=`4`、秒杀订单=`2`、普通拼团订单=`996`、诊所拼团订单=`997`、批购包邮订单=`8`、连锁包邮订单=`11`、其他订单=`100`、药师帮补贴订单=`999` |
| 开单后需退款(`delivery_lack`) | 筛选=`"1"`（单选项开关） |
| 收款方式(`pay_on_cash`) | 在线付款=`"0"`、月结=`"2"`、支付宝先采后付=`"155"` |
| 结算状态(`is_close`) | 未结算=`"0"`、结算中=`"2"`、已结算=`"1"` |
| 药店类型(`subTypeList`) | 多选数组；8 项精确值：零售单体=`[1]`、民营医院=`[2]`、连锁总部（批零一体）=`[3]`、连锁加盟=`[4]`、连锁总部（纯连锁）=`[5]`、第三终端=`[6]`、商业公司=`[8]`、医疗器械经营店=`[0]` |
| 揽收情况(`latestCollectTime`) | 已揽收=`"1"`、未揽收=`"0"` |
| 医械城拼团换购(`insBundleDeputyFlag`) | 是=`"1"`、否=`"0"` |
| 医械城订单(`order_source`) | 是=`"1"`、否=`"0"` |
| 随心购订单(`tbBundled`) | 随心拼多单订单=`[]`、拼团一盒随心拼订单=`[7]`、批购包邮一盒随心拼订单=`[8]`（多选数组） |
| 地区(`area`) **级联省多选** | 34 个省级选项；值=`[[国标省码前2位]]` 二维数组（实测：北京市=`[["11"]]`、天津市=`[["12"]]`、河北省=`[["13"]]`、山西省=`[["14"]]`、内蒙古=`[["15"]]`、辽宁省=`[["21"]]`…），多选可同时含多个省 |
| 运费(`deliverFeeFlag`) | 有运费=`1`、无运费=`0` |
| 特殊药品(`containHempFlag`) | 含麻药品=`1`、冷链（仅预约）=`2`、冷链（不含预约）=`3`、非冷链（仅预约）=`4`、其他=`0` |
| 签收回执(`autograpFlag`) | 有=`1`、无=`0` |
| 购销合同(`autograpFlag2`) | 有=`1`、无=`0` |
| 发票类型(`storeInvoiceType`) | 普票=`"1"`、专票=`"2"`、无要求=`"3"` |
| 分仓筛选(`warehouseCode`) | 重庆仓=`11501`（本账号仅 1 个可见仓，随账号权限/公司变化） |
| 随货同行单(`orderShipping`) | 是=`1`、否=`0` |
| 运营标签(`operationFlag`) | 自动运营=`1`、手动运营=`2`、随心购=`7`、自动调价=`9`、自动跟价=`10`、手动调价=`11`（浮层另有重复标签「自动调价/自动跟价」，属渲染重复） |
| 区域标签(`bindType`) | 省内=`12`、省外=`13` |
| 是否有追溯码(`isTraceCode`) | 是=`1`、否=`0` |
| 托管(`isHostedDrug`) | 是=`1`、否=`0` |
| 维价类型(`maintainPriceType`) | 集团维价=`1`、集采维价=`2`、采购维价=`5` |
| 多品凑单订单(`tcmStoreGroupOrderFlag`) | 是=`1`、否=`0` |

> 结论：常见「是否」类筛选统一 `是=1/否=0`；三状态类（结算/收款/发票）用字符串枚举；仅 `orderTypeList`/`subTypeList`/`tbBundled`/`area` 与三个日期区间为数组。

---

## 10. 列表返回字段全量（浏览器实测 2026-11-12）

> 抓一次真实 `wholesaleOrder/list` 响应（`过程区/账号权限实测/response_dump.json`）：`code/message/data`，`data={pageNo,pageSize,totalRecord,totalPage,results[]}`，本次 `totalRecord=12`、`pageSize=10`。**返回行 177 个顶层字段 + `orderDetails[]` 内 53 个字段**（全量键名 `过程区/账号权限实测/returned_fields.json` / `row_fields.txt`）。表头实测 8 列：`''`(展开) / 订单ID / 下单·最新处理时间 / 药店名称 / 总金额 / 处理情况 / 收货信息 / 订单下载次数。
> 界面分组映射见 §2；此处补全量键名清单，供取数脚本核对（按响应原顺序，非按界面分组）。

**顶层 177 字段（分组归并，全量）**：

- 订单/物流标识：`wsTypeStr` `orderId` `orderSn` `logisticsId` `logisticsNo` `logisticsName` `logisticsNoedit` `logisticsStr` `isCar` `orderType` `orderTypeNamePrefix` `orderTypeName` `orderTypeNameSuffix` `orderTypeNameExport` `thirdDelivery` `thirdPayId` `orderTime` `orderTimeStr` `payTime` `payTimeStr`(无) `providerMtime` `providerMtimeStr` `deliverTime` `pmtimeStr` `originOrderSn` `orderName`
- 状态/处理：`processStatus` `processStatusName` `preSaleStr` `status` `isClose` `isCloseDesc` `realSubType` `invoiceSign` `reportSign` `orderProcesses` `processNote` `ysbNote` `message` `checkMsg` `display` `className` `isAbnormal` `isLogistReject` `urged` `hasAllAfterSale` `hasAfterSale` `isShowRefundTip` `delayCntSignal` `delayCnt` `exportTimes` `callbackStr`
- 供应商/药店：`providerId` `deliverProviderName` `providerCode` `secProviderCode` `subType` `subTypeDesc` `certStatus` `storeInfoIsChange` `leyaoFrozen` `leyaoFrozenRemark` `leyaoFrozenSyncTime` `hasTmpScope` `drugstoreBranchId` `drugProviderId` `salesPhoneM` `salesPhone` `salesName` `userName` `userId` `leyoPartnerPhone` `leyoPartnerName` `storeTitle` `storeFullName` `storeTel` `storeAddress` `storeIsEInvoice` `contactDesc` `priceTypeName` `phoneM` `orderPhone` `orderPhoneMask`
- 金额/结算：`realCouponPayP` `realCouponPayProv` `refundCoupPayP` `realSubPay` `subPay` `subsidyPay` `refundSubsidyPay` `realSubsidyPay` `realSubsidyPayO` `realIntelPurchaseSubsidyPay` `realIntelPurchaseProvSubsidyPay` `refundSubPay` `realCashBackPay` `cashBackPay` `refundCashBack` `monthPay` `deliverFee` `orginDeliverFee` `couponPayProv` `couponPayProvName` `leyoBeans` `leyoBeansPay` `localPay` `couponPay` `refundCouponPay` `couponPaySpe` `couponPayPay` `refundCouponPayPay` `thirdPartyPay` `actualCost` `totalCost` `orderPay` `orderPayDetail` `platformDiscount` `platformSubsidy` `allDeliveryAmount` `inputTotalPriceT` `refundCost` `totalPurchaseCost` `status0TotalCost` `status2TotalCost` `status3TotalCost` `status4TotalCost` `noSendTotalCost` `compensationAmt` `compensationNote` `userExtraPaidAmt` `refundUserExtraPaidAmt` `actualCostFlag`
- 发票/票据：`invoiceTypeName` `storeInvoiceType` `autographUrl` `autograph2Url` `orderShippingList` `drugBookAgreement` `orderTaxData`
- 收货人：`receiverinfo` `receiverName` `receiverPhone` `receiverProvince` `receiverAddress` `receiverinfo2` `provinceName` `cityName` `address` `areaCode` `expressLog`
- 退款/售后：`latestRefundId` `latestRefundType` `latestRefundStatus` `refundType` `latestCollectTime`
- 活动/标签/标志：`firstOrder` `gift` `isVip1` `requirement` `channel` `drugMsg` `provCouponInfo` `userIdentityM` `userIdentity` `subsidyFlag` `groupOrderSpecialFlag` `proxyFlag` `identityFlag` `warehouseCode` `warehouseName` `specialFlag6` `coldChainFlag` `specialFlag` `smApplyStatus` `smApplyStatusStr` `bulkPurchaseFlag` `orderDetails`

**`orderDetails[]` 内 53 字段（全量）**：`realAmount` `amount` `orderDetailId` `refundAmount` `unitPrice` `inputTotalPrice` `purchasePrice` `calcPriceOri` `subPay` `couponPaySpe` `deliveryAmount` `refundCost` `wsParentId` `factory` `busiScope` `drugId` `orderId` `wholesaleId` `disType` `priceType` `wsParentidTag` `drugname` `provDrugCode` `provDrugCodeScript` `drugName` `drugNameScript` `wholesaleType` `hasGift` `dis_type` `tagTitle` `tagDesc` `gift` `allDeliveryAmount` `inputTotalPriceT` `totalPurchaseCost` `specification` `containSubscribeFlag` `recType` `payPrice` `providerSubsidy` `taxRate` `taxClsCode` `warnType` `bulkPurchaseFlag` `operationFlag` `bindType` `isDrugTraceCode` `isProviderSetTraceCode` `isTraceCode` `specialFlagEs` `isHostedDrug` `maintainPriceType` `agreeRiskyFlag`

> 注：多个筛选参数名与返回字段同名（`storeInvoiceType` `latestCollectTime` `warehouseCode` `isHostedDrug` `maintainPriceType` `bindType`/`operationFlag` `isTraceCode` `proxyFlag` `bulkPurchaseFlag` 等），可作为筛选值域与返回口径对照。
