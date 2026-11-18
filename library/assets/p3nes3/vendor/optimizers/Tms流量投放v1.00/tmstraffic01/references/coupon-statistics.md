> **框架内自包含副本** ｜ token 由调用方通过 `--token`/`PMS_TOKEN`/`--state-file` 传入；本包不登录、不读父凭证仓库。
> `buildTime` 通过 `--build-time` 可选传入（默认 `2026-11-17 18:42:50`）；凭证/构建异常只报错，不自行登录。
> 原始归档已剥离（实测身份与过程路径不随包，以本副本为准）。

# 优惠券统计 API 文档（完全独立版 · 可照此开发）

> 页面：`https://pms.ysbang.cn/#/tms/coupon-statistics`
> 生成：2026-11-17 ｜ 方法：webpack 源码 100% 逆向（chunk `43595` 三Tab组件、`1846` API、`app.js` 公共枚举）+ 真实 HTTP 请求实测（凭证 token 直调。**凭证 token 对两个域名均有效**）
> **自包含**：鉴权/公共参数/错误码/全部枚举/字段名（前端界面名=源码字段名=API参数名三者一致）/参数模板/真实响应/调用顺序/公式说明全在此文。
> 三个 Tab：优惠券使用统计(usage) / 子公司地区汇总(summary) / 优惠券查看(view)。

---

## 0. 快速开始（Agent 照抄）

1. token：由调用方通过 `--token`/`PMS_TOKEN`/`--state-file` 传入
2. **两个域名**（凭证 token 均已实测可用）：
   - 统计类（Tab1/Tab2/导出）：`https://pms.leyopharm.com`
   - 券台账类（Tab3/couponInfo）：`https://pms.ysbang.cn`
3. 默认时间窗只有**1天**（T-1），查历史须改 `beginTime/endTime`。
4. Tab1 一次搜索并发调 2 个接口（汇总卡+明细），明细拿到 couponId 后调券详情补 tooltip。

---

## 0.5 推荐默认值（本板块说明）

本板块为**只读查询/导出**，无新增表单，因此**无新增默认值配置**。
- 查询时间窗默认 T-1（昨天）单日，查历史须显式改 `beginTime/endTime`。
- 促销费用/活动的新增默认值见各自文档 §0.5（用户 2026-11-18 确认）。

---

## 1. 鉴权与公共参数

- **token**：调用方通过 `--token`/`PMS_TOKEN`/`--state-file` 传入；凭证失效只报错、不自行登录
- **请求头**：`Content-Type: application/json`、`token:<TOKEN>`、`Authorization: Bearer <TOKEN>`、`origin/referer: https://pms.ysbang.cn`。
- **成功码** `code="40001"`（券详情 message 为"成功"）。Tab1 汇总 `data[]`（无分页）；Tab1 明细/Tab2/Tab3 `data:{total,records/couponList}`。
- 错误码见 §10。

---

## 2. 枚举字典（源码常量，全部实测确认）

| 枚举 | 前端标签→值 | 用途 |
|---|---|---|
| `timeType` | 支付时间 `2` / 出库时间 `1`（默认2） | 三Tab时间口径 |
| `bizTypes` | 首推1 / 集采5 / 控销4 / YQS3 / 普品0 | 业务类型多选 |
| `deliverTypesV1070` | 一口价1 / 特价2 / 拼团3 / 限量秒杀4 / 批购包邮5 / 连锁优选6 / 其他0 | 活动类型多选 |
| `clientTypes` | 零售单体0 / 第三终端1 / 批零一体2 / 连锁加盟3 / 连锁总部4 / 商业公司5 / 其他8 | 客户类型多选 |
| `isInProvince` | 全部0 / 省内1 / 省外2 | 省内外单选 |
| `dimension`（Tab2） | 子公司1 / 地区(省)2 / 城市3 | 汇总/导出维度 |
| `status`（Tab3） | 有效1 / 已失效0 | 优惠券状态单选 |
| `couponType`（Tab3） | 商家满减券1 / 商家打折券2 / 商家免邮券3 | 优惠券类型单选 |
| `expiredType`（Tab3） | 时间段1 / 天数2 / 小时3 | 有效期类型单选（选"时间段"才用有效时间筛选） |

---

## 3. Tab1 优惠券使用统计

### 3.1 筛选控件（界面=源码=API 字段）
| 界面标签 | 控件类型 | API 字段 | 默认 | 数据源/接口 |
|---|---|---|---|---|
| 子公司 | 静态下拉单选 | `providerId` | 第一个公司id | vuex providerList |
| 时间 | 下拉(支付2/出库1)+日期区间 | `timeType`+`beginTime`/`endTime` | 2 / T-1~T-1 | — |
| 业务类型 | 静态下拉多选 | `bizTypes[]` | `[]` | 枚举§2 |
| 活动类型 | 静态下拉多选 | `deliverTypesV1070[]` | `[]` | 枚举§2 |
| 省内外 | 静态下拉单选 | `isInProvince` | 0 | 枚举§2 |
| 折扣力度 | 两个数字输入(0~100,2位) | `beginDiscount`/`endDiscount` | 空 | 校验：单个空报错；左>右报错 |
| 客户负责人 | 远程搜索下拉(filterable,remote) | `customerName` | `""` | `/datacenter_pms/web/search/customerOptions/pv583` body `{providerId,customerName}` → `[{userId,userName}]`，option value=**userName** |
| 客户区域 | 省市级联(el-cascader lazy) | `canons[]`/`citys[]` | `[]` | `/datacenter_pms/web/search/sysAreasOptions/v438` body `{areaCodes:[code]}`→`[{areaCode,areaName,areaType}]` |
| 客户类型 | 静态下拉多选 | `clientTypes[]` | `[]` | 枚举§2 |
| 优惠券名称 | 输入框 | `couponName` | `""` | — |
| 优惠券ID | 输入框(仅数字) | `couponId` | `""` | `replace(/[^\d]/g,"")` |
| 按钮 | 重置/搜索/导出 | — | — | 导出下拉：多公司账号有"当前公司数据"/"所有公司数据" |

### 3.2 汇总卡接口
`POST https://pms.leyopharm.com/pms_operation/web/coupon/couponStatisticsTotal/pv1070`
body = 筛选 + `{ascs:"discount",descs:"",current:1,size:10,token,buildTime}`。
响应 `data[]` 三行（`typeName`=优惠订单汇总/无优惠订单汇总/所有订单汇总），每行 9 字段：
| 界面列 | 字段 | 实测示例 |
|---|---|---|
| (汇总类型) | `typeName` | 优惠订单汇总 |
| 优惠总额 | `couponTaxAmount` | 31178.89 |
| 销售额 | `taxAmount` | 1746466.16 |
| 折扣力度 | `discount` | 98.25折 |
| 订单数量 | `orderNum` | 2404 |
| 订单客户数 | `customerNum` | 919 |
| P1毛利率 | `p1Rate` | 3.44% |
| P4毛利率 | `p4Rate` | 4.66% |
| 营销费用率 | `marketRate` | - / 0.65% |
> 源码 tooltip：折扣力度=优惠订单销售额/(优惠订单销售额+优惠总额)；营销费用率=优惠总额/所有订单销售额。字段均为**字符串**，比率带%。

### 3.3 明细表接口
`POST https://pms.leyopharm.com/pms_operation/web/coupon/couponStatisticsTable/pv1070`
body 同汇总卡。响应 `data:{total,records:[]}`，records 字段 14 个（界面10列+4扩展）：
`providerId`、`providerName`、`couponName`(优惠券名称)、`couponId`(优惠券ID)、`couponPayTaxAmount`(优惠总额)、`taxAmount`(销售额)、`discount`(折扣力度)、`orderNum`(订单数量)、`customerNum`(订单客户数)、`p1Rate`(P1毛利率)、`p4Rate`(P4毛利率)、`p1CostTaxAmount`(P1成本额)、`p4CostTaxAmount`(P4成本额)、`marketRate`(营销费用率)。
- 排序：`ascs`/`descs` 二选一（默认 `ascs:"discount"`）；可排序字段：couponPayTaxAmount/taxAmount/discount/p1Rate/p4Rate/marketRate。
- 券详情 tooltip：明细拿到 couponId 列表后调 `POST https://pms.ysbang.cn/pms-main/coupon/couponInfo/v740` body `{ids:["2073210",...]}` → `[{id,couponName,couponType,couponAmt,useCond,expired,getNum,status}]`（悬浮"优惠券名称"列显示）。

### 3.4 导出
`POST https://pms.leyopharm.com/pms_operation/web/coupon/couponStatisticsExport/pv1070`
- body = 筛选 + `{isExportAll:0}`（0=当前筛选，1=全量；源码 `"all"===e?1:0`），**去掉** beginDiscount/endDiscount/ascs/descs/current/size。
- 同步返回文件流：`application/octet-stream` xlsx（PK头），filename"优惠券使用统计导出.xlsx"。

---

## 4. Tab2 子公司地区汇总

### 4.1 筛选控件
| 界面标签 | 控件类型 | API 字段 | 默认 |
|---|---|---|---|
| 时间 | 下拉(timeType)+日期区间(clearable=false) | `timeType`+`beginTime`/`endTime` | 2 / T-1~T-1 |
| 子公司 | 静态下拉多选 | `providerIds[]` | `[]` |
| 业务类型 | 静态下拉多选 | `bizTypes[]` | `[]` |
| 活动类型 | 静态下拉多选 | `deliverTypesV1070[]` | `[]` |
| 客户区域 | 省市级联 | `canons[]`/`citys[]` | `[]` |
| 客户类型 | 静态下拉多选 | `clientTypes[]` | `[]` |
| 省内外 | 静态下拉单选（子公司汇总视图显示） | `isInProvince` | 0 |

### 4.2 查询接口（三种维度）
`POST https://pms.leyopharm.com/pms_operation/web/coupon/couponCompony/pv1070`
| 维度 | body 关键差异 | 实测 |
|---|---|---|
| 子公司汇总 | `dimension:1`, `{current,size,ascs,descs}` | total=1（重庆央拓） |
| 地区汇总 | `dimension:2`, `isInProvince:null` | total=31（省） |
| 城市下钻 | `dimension:3`, `canons:["<省名>"]`, `isInProvince:null` | 新疆→15城市 |
响应 `data:{total,records:[]}`，每行 21 字段，`dimensionName`=地区/子公司名。每行界面显示**两行**（优惠订单汇总 / 所有订单汇总），字段成对：
- 优惠订单汇总行：`couponTaxAmount`(优惠总额) / `taxAmount`(销售额) / `discount`(折扣力度) / `p1Rate` / `p4Rate` / `couponOrder`(优惠订单销售额占比)
- 所有订单汇总行：`allCouponTaxAmount` / `allTaxAmount` / `allDiscount` / `allP1Rate` / `allP4Rate` / `allMarketRate`(营销费用率) / `allCouponOrder`
- 其它：`providerIds[]`、`providerId`、`providerName`、`cancon`、`city`、`dimension`(字符串"1"/"2"/"3")
> 源码 tooltip：折扣力度=优惠订单销售额/(优惠订单销售额+优惠总额)；营销费用率=优惠总额/所有订单销售额；优惠订单销售额占比=优惠订单销售额/所有订单销售额。
- 交互：点击"子公司/地区"名 → 切换到该公司地区视图（`handleSwitchTab`：tabName=ListTableByArea, providerIds=[providerId]）。

### 4.3 导出（三种维度）
`POST https://pms.leyopharm.com/pms_operation/web/coupon/couponComponyExport/pv1070`
body = 筛选 + `{dimension:1|2|3}`（1子公司/2省份/3城市）→ 同步 xlsx：
- dimension=1 → filename"子公司地区汇总导出-子公司维度.xlsx"
- dimension=2 → "...-省份维度.xlsx"
- dimension=3 → "...-城市维度.xlsx"
实测均返回 PK 头 xlsx。

---

## 5. Tab3 优惠券查看

### 5.1 筛选控件
| 界面标签 | 控件类型 | API 字段 | 默认 | 说明 |
|---|---|---|---|---|
| 子公司 | 静态下拉单选 | `providerId` | 第一个公司id | — |
| 状态 | 静态下拉单选 | `status` | `""` | 有效1/已失效0 |
| 优惠券类型 | 静态下拉单选 | `couponType` | `""` | 满减1/打折2/免邮3 |
| 有效期类型 | 静态下拉单选 | `expiredType` | `""` | 时间段1/天数2/小时3 |
| 有效时间 | 日期区间 | `payTime:["start","end"]`→`beginDate`/`endDate` | `["",""]` | 仅"时间段"类型生效 |
| 优惠券名称 | 输入框 | `couponName` | `""` | — |
| 优惠券ID | 输入框(仅数字) | `id` | `""` | oninput 过滤非数字 |
| 按钮 | 重置/搜索/导出 | — | — | 导出走 ExportExcelButton |

### 5.2 券列表接口
`POST https://pms.ysbang.cn/pms-main/coupon/couponList/v740`
- body（源码 handleSearch 构造）：`{...formData, beginDate:payTime[0], endDate:payTime[1], pageNum, pageSize, payTime:undefined, token, buildTime}`。
- 响应 `data:{total:28591, couponList:[]}`，每行 14 字段（界面13列+providerId）：
  `provider`(子公司)、`providerId`、`id`(优惠券ID)、`couponName`(优惠券名称)、`couponType`(类型)、`frReg`(首推反哺)、`couponAmt`(面额)、`useCond`(使用条件满N元)、`instr`(使用说明)、`expired`(有效期)、`getNum`(被领取数量)、`usedNum`(已使用数量)、`status`(状态)、`ctime`(创建时间)。
- 筛选实测：状态有效391/已失效28200；类型商家打折券12081；有效期类型时间段28056；ID精确匹配；名称"500"→6086。

### 5.3 导出
`POST https://pms.ysbang.cn/pms-main/coupon/exportCouponList/v740`
- body = 筛选 + `{beginDate,endDate}`（payTime 去掉）→ 同步 xlsx（实测 2MB），filename"优惠券查看.xlsx"。

### 5.4 其它券接口（非本页调用，标注）
| 接口 | 用途 | 说明 |
|---|---|---|
| `POST /pms-main/coupon/couponInfo/v740` | 券详情（批量ids） | Tab1 tooltip 用，见 §3.3 |
| `POST /pms-main/coupon/availableGoodsCount/v31130` | 券可用商品数 | 模块1846定义但本页未调用；参数需"领券活动ID"（非 `id`），本页不传，**待其它业务确认，不臆测** |
| `POST /pms-main/coupon/availableWholesaleIds/v31130` | 券可用活动ID | 同上 |

---

## 6. 调用顺序（Agent 标准流程）

- **Tab1**：确认调用方 token 已传入
- **Tab2**：确认调用方 token 已传入
- **Tab3**：确认调用方 token 已传入

---

## 7. 错误码

| code | 含义/处理 |
|---|---|
| 40001 | 成功 |
| 40005/40006/40007 | 未登录/无权限/token过期 → 报错并请调用方提供新凭证 |
| 40050 | 功能鉴权拒绝 |
| 40003/42054/45600 | 参数错/自定义错误/业务停止 |
| 52080 | 告警 |

---

## 8. 证据与注意事项

- ⚠️ 字段名一致性：本文档字段名严格取前端源码变量名（如 `couponTaxAmount`/`couponPayTaxAmount`/`deliverTypesV1070`/`dimensionName`/`allCouponTaxAmount`），与界面标签一一映射。
- ⚠️ 所有金额/比率字段是**字符串**（金额"1069.96"、比率"8.67%"、"-"表示无），Agent 解析时按字符串处理。
- ⚠️ buildTime 随会话变化不写死；token 经登录器取，两个域名同一 token 可用。
- ⚠️ 默认时间窗1天；Tab2 城市下钻需先用地区维度的 dimensionName 作 canons。
