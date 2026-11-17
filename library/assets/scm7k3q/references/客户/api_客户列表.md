# 客户列表（API）

> 查询药店（客户）、客群统计、客户分组、导出客户名单。控销组见 `api_控销组.md`，黑名单见 `api_黑名单.md`。
> 请求：`POST /scm-order/crm/*`，`application/json`。公共参数 `ex=OldCustomerManagement`、`version=1.0.0`、**不带 `lastBuildTime`**；鉴权见 `references/通用/api_认证与公共约定.md`。
> 接口清单见 `sy.md §3.1`；字段/值域见 `zddz.md §1`。
> **账号归属：③ 仅自营**（权威判定见 `references/sy.md §0.4`；本子板块为自营账号体系专属，摇钱树账号不调用）


## 1. 筛选项

主查询 `crm/list` 的请求体：

```json
{
  "area": [], "deliverType": "", "drugstoreBranchId": "",
  "page": 1, "pageSize": 10, "providerCode": "",
  "storePchFlag": "", "storeTagId": "", "storeTitle": "", "subType": "",
  "timeRange": [],  // 采购时间筛选；不按采购时间筛时留空数组（抓包示例曾带具体历史日期）
  "token": "<token>", "platform": "scm-admin", "version": "1.0.0",
  "ua": "<UA>", "ex": "OldCustomerManagement"
}
```

| 筛选项 | 参数 | 类型 | 取值 | 来源 / 用法 |
|---|---|---|---|---|
| 所在分组 | `storeTagId` | string | `""`=全部；分组 ID | **动态**：`crm/getStoreTagList` 返回 `{"0":"待分组","2198":"老客户组",…}`，取 key 作值 |
| 地区 | `area` | array | `[[省,市,区]]` | **动态**：`/scm-goods/areaGroup/getAreaCode`（见 1.2） |
| 药店 ID | `drugstoreBranchId` | string | 精确 ID | 直接输入 |
| 药店编码 | `providerCode` | string | 编码 | 直接输入 |
| 药店名称 | `storeTitle` | string | 名称（支持模糊） | 直接输入 |
| 客户标签 | `storePchFlag` | string | 3 位码，见 1.4 | **静态枚举** |
| 采购时间 | `timeRange` | array | `["YYYY-MM-DD","YYYY-MM-DD"]` | 见 1.5 |
| 订单活动类型 | `deliverType` | string | `""` / `"7"` | **静态**：`7`=拼团订单 |
| 药店类型 | `subType` | string | `0`–`6`、`8` | 见 1.7 |

### 1.1 所在分组

- 选项来源：`POST /scm-order/crm/getStoreTagList` → `data={"0":"待分组","2198":"老客户组","7079":"测试分组"}`（随账号配置变化，**必须运行时获取**）。
- `""`=全部；传分组 ID（如 `2198`）。
- ⚠️ 实测传 `"0"`（待分组）不生效（返回全量），按实际分组 ID 过滤。

### 1.2 地区（级联动态）

- 字典接口：`POST /scm-goods/areaGroup/getAreaCode`，body `{level, maxLevel, parentCode}`（+ 公共参数）。
  - 省：`{level:0, maxLevel:0, parentCode:0}` → `[{areaCode:11, areaName:"北京市", leaf:false}, …]`
  - 市：`{level:1, parentCode:<省 areaCode>}` → `[{areaCode:1101, areaName:"北京市"}]`
  - 区：`{level:2, parentCode:<市 areaCode>}` → `[{areaCode:110101, areaName:"东城区", leaf:true}, …]`
- 提交 `crm/list`：**`area: [[省 areaCode, 市 areaCode, 区 areaCode]]`**（可只到省/市）。
- 实测（11-10 与 11-12 两次一致）：`[[11]]`→4095、`[[11,1101]]`→4095、`[[11,1101,110101]]`→43；扁平 `[11]`→`40004`、字符串 `"11"`→`40004`。
- ⚠️ 不要用老版 `getCity`/`getNextArea` 的区域 ID（如 `36443`），那是另一套编码，传进 `area` 会返回 0 条。
- ⚠️ 归档《客户列表》曾记「`area` 四种形态全部失败」——**该结论已被两次复测推翻**，正确形态是上表的二维数组。

### 1.3 药店 ID / 编码 / 名称

`drugstoreBranchId`（精确）、`providerCode`（精确）、`storeTitle`（支持模糊子串）。三者任一可反查该药店全部字段。

### 1.4 客户标签（静态 8 码）

| 显示 | 传值 |
|---|---|
| 全部 | `""` |
| 111客户 / 110客户 / 101客户 / 100客户 | `111` / `110` / `101` / `100` |
| 011客户 / 010客户 / 001客户 / 000客户 | `011` / `010` / `001` / `000` |

- 必须传**纯 3 位数字**；传 `"000客户"` 返回 0 条。
- 实测部分码可收窄（`011`→8408、`101`→7930、`110`→8892）；`000/001/010/100/111` 返回全量。

### 1.5 采购时间（2026-11-12 复测修正）

- 参数 `timeRange`，格式 **`["YYYY-MM-DD","YYYY-MM-DD"]`**（数组、纯日期字符串）。
- 带时分秒（`"2026-11-01 00:00:00"`）或传字符串 → `40004 参数验证异常`。
- **不是结果集过滤器**：实测合法区间/极窄 1 天/跨度 4 个月，`totalRecord` 均仍为 `10000`；但**首行药店 ID 会变**（无时间 3580863 → 近 10 天 3231188 → 极窄 2328901），说明它影响**成交数据口径与排序**，不是筛选行数。
- `totalRecord` 有 **10000 硬上限**，所以不能用"total 是否变"判断 `timeRange` 生效；跨度 >3 月后端不报错（是否限 3 月疑为**前端校验**，API 未证实）。
- 顶部统计 `getFansNum` / `getVisitTimes` / `getOrderUserNum` **不吃 `timeRange` 也不吃 `area`**（带与不带返回同一数字），是全站统计值。

### 1.6 订单活动类型（2026-11-12 复测修正）

- 前台选项：`""`（全部）、`"7"`（拼团订单）。传 `deliverType: "7"`（字符串或数字 `7` 均可）。
- ⚠️ **`deliverType=7` 单独传不收窄**（`totalRecord` 仍 10000，因命中上限）；必须与**地区 `area` 组合**才体现过滤：
  - 北京 `[[11]]`：4095 → **36**；东城区 `[[11,1101,110101]]`：43 → **0**；广东 `[[44]]`：10000 → **293**；辽宁 `[[21]]`：10000 → **238**。
  - 组合 `storePchFlag=011 + deliverType=7` → **1185**（亦可收窄）。
- 后端另接受 `0`（不收窄）、`8`（实测 9141，收窄）；其余值（如 `99`）不生效。以上值除 `7` 外前台未暴露。

### 1.7 药店类型

| 值 | 类型 | 值 | 类型 |
|---|---|---|---|
| `0` | 零售单体 | `4` | 连锁总部（纯连锁） |
| `1` | 第三终端 | `5` | 商业公司 |
| `2` | 连锁总部（批零一体） | `6` | 民营医院 |
| `3` | 连锁加盟 | `8` | 医疗器械经营店 |

- 码值映射来自 `POST /scm-goods/areaGroup/getAvailableStoretype`。
- 实测（2026-11-12 复测）：`2`→1355、`4`→5472、`8`→78；`0` 返回全量 10000；`7` 未使用（0 条）。另有 `5`→3969、`6`→5406（11-10 实测，随数据微浮动）。
- 组合验证：`area三级 + subType=2` → **1**（证明筛选真实生效，非 10000 上限误判）。

> **复测证据**：脚本 `过程区/账号权限实测/crm_verify.py`、`crm_verify2.py`，结果 `crm_verify_result.json`。所有请求均为**只读查询**。归档《客户列表》记「`area` 四种形态全部失败 / 不支持日期参数」是采集期旧结论，**已被本复测推翻，以本文为准**。

## 2. 查询到的信息

### 2.1 主查询 `crm/list`

分页用 **`page` + `pageSize`**（不是 `pageNo`）。

```json
POST /scm-order/crm/list
{ "page": 1, "pageSize": 10, "area": [], "deliverType": "", "drugstoreBranchId": "",
  "providerCode": "", "storePchFlag": "", "storeTagId": "", "storeTitle": "", "subType": "",
  "token": "<token>", "platform": "scm-admin", "version": "1.0.0", "ua": "<UA>", "ex": "OldCustomerManagement" }
```

响应：`data.{pageNo,pageSize,totalRecord,totalPage,results[]}`。

### 2.2 返回字段（`data.results[]`）

| 字段 | 含义 |
|---|---|
| `drugstoreBranchId` | 药店 ID |
| `providerCode` | 药店编码 |
| `storeTitle` / `fullName` | 药店简称 / 全称 |
| `address` | 药店地址 |
| `province` / `city` | 省 / 市（城市列） |
| `areaId` | 区域 ID |
| `subType` | 药店类型码（见 1.7） |
| `storePchFlag` | 客户标签（如 `000客户`） |
| `storeTags` | 所在分组名 |
| `visitTimes` | 浏览次数（近 7 天） |
| `orderNum` | 采购订单数 |

分页外壳 `totalRecord/totalPage`。`totalRecord` 实测有 **10000 上限**（全量与多条件均返回 10000）。

### 2.3 客群统计（页面顶部 3 个数字）

| 指标 | 接口 | 返回 |
|---|---|---|
| 药房粉丝 | `POST /scm-order/crm/getFansNum` | `data`=数字 |
| 浏览 | `POST /scm-order/crm/getVisitTimes` | `data`=数字 |
| 下单客户数 | `POST /scm-order/crm/getOrderUserNum` | `data`=数字 |

### 2.4 分组列表

`POST /scm-order/crm/getProStoreGroupList`，body `page`/`pageSize` → `data.results[]{storeTagId,tagName,providerId,ctime,ctimeStr,storeNum}`。分组字典用 `crm/getStoreTagList`。

## 3. 导出

`GET /provider.php/Admin/ExcelExport/exportProStore`，浏览器直接下载文件流（`window.open`），**不走导出任务列表**。

11 个 query 参数：

```
store_tag_id, province, city, area,
drugstore_branch_id, provider_code, storetitle,
store_pch_flag, date, deliver_type, sub_type
```

- 与 `crm/list` 参数为下划线写法：`storeTagId↔store_tag_id`、`providerCode↔provider_code`、`storeTitle↔storetitle`、`storePchFlag↔store_pch_flag`、`deliverType↔deliver_type`、`subType↔sub_type`。
- 导出另有 `province/city/area/date`（`crm/list` 无 `date` 字段）。
> ⚠️ **待实测**：上述 4 个导出参数的取值域/格式，及 `timeRange`(数组)→`date`、`area`(`[[省,市,区]]`)→`province/city/area` 的换算规则**未采集**，无法保证「导出＝当前查询」。首次使用须真机比对导出列头与筛选结果，不得臆造映射。

## 4. 分页控制

- 本板块（`crm/*`，含组列表 `getProStoreGroupList`）统一用 **`page` + `pageSize`**（不是 `pageNo`）；三套分页体系见 `references/通用/api_认证与公共约定.md §9`。

| 控制项 | 参数 | 取值 |
|---|---|---|
| 每页条数 | `pageSize` | 10 / 50 / 100 / 200 |
| 页码 | `page` | 从 1 开始 |


