# 优惠券管理 API 文档

> 适用对象：Agent / 开发者。用户只需说明业务意图，Agent 按本文定位接口、字段、默认值。
> 依据：优惠券系统前端源码逆向（界面控件级），2026-11-17。
> 鉴权前提：所有业务云函数（下称 A/B/C/D/E/F 组）body 必带 `credentials`（由乐药种子技能 SCM 登录器提供）；共享券读取走数据库层（见 §4.6）。登录实现不在本文范围。

## 通用约定

| 项 | 内容 |
|---|---|
| 云函数形态 | 腾讯云 SCF HTTP 地址，`POST` + JSON body（不是 SDK 云函数） |
| 通用 body | `{credentials, action, ...业务参数}`；`credentials` 由登录器产出，本文不再展开 |
| 成功判定 | `result.success === true`；响应数据多在 `result.data` |
| 统一表头 | `Content-Type: application/json; charset=UTF-8` |
| 写操作 | 效期/作废/赠送/活动/创建均为写操作，执行前须用户明确授权；界面多数无二次确认 |
| 域名分组 | A `14tsfynz25` / B `g6mwvpruev` / C `4hivucf0ph` / D `lc0ftian1b` / E `7vayk0nz7f` / F `21j36twzqr`（均为 `*.ap-guangzhou.tencentscf.com`） |

## 0. 获取优惠券的两种方式

| 方式 | 条件 | 能力 | 接口/来源 |
|---|---|---|---|
| **A 登录后查询** | 有权限账号（凭证由种子技能 SCM 登录器提供） | 全部功能：搜索券、GMV、生成/访问二维码、活动管理、创建/作废/赠送/改效期 | A-F 组业务云函数，body 带 `credentials` |
| **B 共享库直接获取** | **无需权限/无需登录** | 读取已共享优惠券及其活动信息（名称/有效期/活动抢券时间/二维码链接） | 数据库层 `SjkModule.getWhere('coupons','provider_id','==',pid)` / `getAll('coupons')`（公共分享页）；固定 token，无用户凭证 |

> 二维码：方式A 用 `getActivity` 取活动ID生成（`dian.ysbang.cn/#/grabCoupon?id={activityId}`）；方式B 共享券节点内 `activities[].activity_url` 直接就是分享链接。

## 0.1 药店信息反查（赠送/作废的名称→ID）

用户只给药店名称/编码/ID其中任意一项时，先到**客户列表**反查全部信息，再执行赠送/作废：

| 用户给的 | 反查参数 | 接口 |
|---|---|---|
| 名称 | `storeTitle`（模糊子串） | `POST /scm-order/crm/list`（SCM 域，见 `references/客户/api_客户列表.md`） |
| 编码 | `providerCode`（精确） | 同上 |
| 药店ID | `drugstoreBranchId`（精确） | 同上 |

- 返回字段含 `drugstoreBranchId`（药店ID）、`providerCode`（编码）、`storeTitle`（简称）、`fullName`（全称）等——**三者任一可反查全部字段**（客户列表文档 L55）
- 反查后：赠送用 `parseMode=storeId`（ID）或 `storeCode`（编码）；作废 store 模式用返回的实例ID选中
- 不能用客户列表查到时，如实告知用户，不猜 ID

## 0.2 执行前确认（Agent 行为）

| 模式 | 行为 |
|---|---|
| 默认（用户未声明） | 写操作前用表格返回「操作/对象/参数/默认值/将产生什么」给用户确认，确认后执行 |
| 用户要求每次确认 | 同上，每次都确认 |
| 用户要求全自动 | 不再逐次确认，但仍按本文红线执行（关键信息缺失必须问、不擅作主张） |

> 确认表格式：`| 项 | 值 |` 列出券名/ID、字段、默认值、操作结果；用户说"直接做/不用问"才进入全自动。

## 0.3 折扣语义（务必按此，不要混淆）

| 用户说法 | 含义 | 归一值 | 前端解析 |
|---|---|---|---|
| 98折 / 98 / 0.98 / 9.8 | **降2个点**（原价100→98、10→9.8、1→0.98），即付原价98% | `9.8` | `parseDiscount`：>10除10、<=1乘10、否则原值 |
| 99折 / 99 / 0.99 / 9.9 | 降1个点（付原价99%） | `9.9` | 同上 |
| 96折 / 97折 | 降4/3个点（付原价96%/97%） | `9.6`/`9.7` | 同上 |

> ⚠️ 用户说"98折扣"指的是**付98%（降2点）**，不是中文口语"打二折=付20%"。三种写法都归一到 `9.8`，UI 显示"98折"。

---

## 1. 效期

### 1.1 返回基本信息
- 入口：券卡片按钮「效期」（`data-action="validity"`）→ 弹窗 `#yhquan-xq-modal`
- 展示（只读）：券名称、券详情、当前有效期、状态
- 无接口调用；数据来自当前卡片 coupon 对象

### 1.2 修改效期
| 项 | 内容 |
|---|---|
| 接口 | C 组 `POST https://1317825751-4hivucf0ph.ap-guangzhou.tencentscf.com` |
| action | `editEndTime` |
| 请求体 | `{credentials, action:'editEndTime', couponId, newEndDate}` |
| 界面控件 | `#yhquan-xq-date`（`type=date`），按钮 `#yhquan-xq-submit`「修改」 |
| 默认值 | 日期框默认 = 当前结束日 +1 天（`min` 同值） |
| 必填 | `couponId`（来自卡片）、`newEndDate`（用户选） |
| UI 限制 | `newEndDate` 必须**严格晚于当前结束日期**；已失效券（`couponStatus!=='1'`）按钮禁用 |
| 校验提示 | 未选：「请选择新的失效日期。」；不晚于：「新日期必须晚于当前结束日期（{当前日期}）。」 |
| 确认弹窗 | 无（点「修改」即提交） |
| 成功 | 提示「效期已修改到 {newEndDate}。」；卡片 endTime 更新为 `{newEndDate} 23:59:59`；共享池 `coupon_expire_at` 同步；1.5 秒后自动关窗 |

---

## 2. 作废

### 2.1 返回基本信息
- 入口：券卡片「作废」→ 弹窗 `#yhquan-zf-modal`
- 展示（只读）：券名称、券信息区块；下方为作废方式/创建时间筛选/药店列表

### 2.2 作废方式
| 项 | 内容 |
|---|---|
| 控件 | 下拉 `#yhquan-zf-mode` |
| 取值 | `coupon`=按优惠券（整券，默认）｜`store`=按药店ID |
| 切换行为 | 清空已选药店、重绘药店列表；两种方式下列表都显示，差异只在复选框是否可用 |
| 复选框 | `coupon` 模式下全选 `#yhquan-zf-check-all` 与每行 `.yhquan-zf-store-check` 均禁用 |

### 2.3 根据创建时间查找
| 项 | 内容 |
|---|---|
| 控件 | 两个只读文本框：开始 `#yhquan-zf-create-start`、结束 `#yhquan-zf-create-end` |
| 形式 | 时间**区间**；点击弹出日历 `#yhquan-zf-date-picker` |
| 日历操作 | 选日期格（`data-date`）自定义；快捷「今天」（`data-action=today`）→ 起止均为今天；「清除」（`data-action=clear`）→ 清空 |
| UI 限制 | 开始 > 结束时，自动把结束改为开始 |
| **实现方式** | **纯前端过滤**，不传给云函数。用 `store.ctimeStr \|\| store.createTime` 与区间比较过滤内存中的药店列表 |
| 必填 | 否（不过滤则显示全部） |

### 2.4 药店列表及药店所有信息
| 项 | 内容 |
|---|---|
| 接口 | D 组 `getStoreList`，body `{credentials, action:'getStoreList', couponId, status:99}` |
| 响应 | `result.data` → 药店数组，一次性全部返回（无分页、无排序） |
| 搜索框 | `#yhquan-zf-search`（placeholder「请输入药店ID/名称/编码/状态搜索...」），前端模糊过滤 |
| 表格列 | 复选框｜药店ID `storeId`｜药店名称 `storeName`｜状态 `statusDesc` |
| 搜索可匹配字段 | `storeId`、`storeName`、`storeCode`、`providerCode`、`ctimeStr/createTime`、`usertimeStr/useTime`、`orderSn`、`couponPay`、`statusDesc` |
| 其他字段 | `store.id`（实例ID，用于批量作废的 `instanceIds`）；`store.canCancel`（false 时复选框禁用，不显示） |
| 全选 | `#yhquan-zf-check-all`，仅选 `canCancel=true` 的药店 |

### 2.5 作废提交
| 模式 | action | 请求体 | 提示 |
|---|---|---|---|
| 按优惠券 | `revokeType` | `{credentials, action:'revokeType', couponId}` | 后端 message 或「作废成功」 |
| 按药店ID | `revokeBatch` | `{credentials, action:'revokeBatch', couponId, instanceIds:[选中的 store.id]}` | 未选药店：「请选择要作废的药店」 |
| 确认弹窗 | 无 | — | 成功后整券模式置 `couponStatus='0'`、`isSharing=false`；按店模式刷新列表 |

---

## 3. 赠送

### 3.1 返回基本信息
- 入口：券卡片「赠送」→ 弹窗 `#yhquan-zs-modal`，标题「赠送 - {券名}」
- 展示（只读）：券基本信息；已失效券按钮禁用（title「该优惠券已失效，无法赠送」）

### 3.2 赠送数量
| 项 | 内容 |
|---|---|
| 控件 | 下拉 `#yhquan-zs-quantity` |
| 选项 | `1`（默认）、`2`、`3`、`4`、`5` |
| 提交字段 | `amount`（数字） |
| 必填 | 有默认值 1，用户不改可不提供 |

### 3.3 赠送方式（解析模式）
| 项 | 内容 |
|---|---|
| 控件 | 下拉 `#yhquan-zs-parse-mode` |
| 选项 | `auto`=自动解析（默认）｜`storeId`=药店ID｜`storeCode`=客户编码｜`mobile`=手机号 |
| 提交字段 | `parseMode` |
| 规则 | 用户给的是药店ID就选 storeId、手机号选 mobile；auto 由后端判断，明确类型时建议指定 |

### 3.4 赠送目标
| 项 | 内容 |
|---|---|
| 控件 | 文本框 `#yhquan-zs-targets`（textarea） |
| 占位提示 | 「支持药店ID、客户编码以及手机号~」 |
| 输入格式 | 每行一个目标；多个目标换行分隔 |
| 提交字段 | `inputText`（原始文本） |
| 打开弹窗时 | 自动尝试读取剪贴板填入 |
| 必填 | 是（无目标时后端返回失败） |

### 3.5 提交接口与结果
| 项 | 内容 |
|---|---|
| 接口 | E 组 `giveAll`，body `{credentials, action:'giveAll', inputText, couponTypeId:String(couponId), amount, parseMode, storeMode:'batch', interval:2500, retryCount:3}` |
| 固定值 | `storeMode='batch'`、`interval=2500`、`retryCount=3`（界面无控件，代码固定） |
| 额外校验 | 无确认弹窗；提交即提示「成功发起请求...」 |
| 错误处理 | HTTP400→`COUPON_LIMIT`；`needLogin` 或含登录字样→`LOGIN_EXPIRED`（触发重新登录） |
| 结果展示 | 成功：`data.success[]` 逐条；失败：`data.failed` 按 reason 分组逐条提示 |
| 自助任务 | 后台 `zizhu.js` 监听共享券 `tasks`（status=pending），自动抢占并以 amount=1、任务自带 parse_mode 执行，完成后写回 done/failed |

---

## 4. 活动

### 4.1 返回基本信息
- 入口：券卡片「活动」→ 全屏弹窗 `#yhquan-hd-modal`，标题「活动 - {券名}」
- 展示（只读）：券名称/详情/有效期/状态；活动下拉（活动项 `.yhquan-hd-activity-item[data-id]`，无活动显示「无抢券活动！」且禁用）
- 操作入口：新增 `#yhquan-hd-create-toggle`（+）、刷新 `#yhquan-hd-activity-refresh`、删除（活动项 × `.yhquan-hd-activity-delete`）、底部保存/创建 `#yhquan-hd-save`

### 4.2 创建抢券活动（默认创建 + 自定义）
| 字段 | DOM | 必填 | 默认值 | UI 限制 / 说明 |
|---|---|---|---|---|
| 活动名称 | `#yhquan-hd-activity-name` | 否 | 券名称 | 空则用券名（券名按 §5.1.1 的 `额度/数值+后缀` 代拟，如 `2000/98+11月`）；用户单独指定活动名则以指定为准 |
| 总量上限 | `#yhquan-hd-total` | 否 | 10000 | `min=1`；提交为 `couponAmount` |
| 单店限制 | `#yhquan-hd-store` | 否 | 5 | `min=1 max=5`；输入 >5 强制改回并提示「单店限制最大为 5！」；提交 `couponNum` |
| 抢券开始 | `#yhquan-hd-begin` | 否 | 今天 | date；提交 `beginTimeDate` + `beginTimeHms:'00:00:00'` |
| 抢券结束 | `#yhquan-hd-end` | 否 | 今天+2（≤券结束日） | date；提交 `endTimeDate` + `endTimeHms:'23:59:59'`；改开始日自动调结束日 |
| 可用状态 | `#yhquan-hd-availability` | 否 | 启用 | `enabled`→`isClose:0`；`disabled`→`isClose:1` |
| 共享情况 | `#yhquan-hd-share-mode` | 否 | 私有 | `public`/`private`；禁用状态时该控件不可用 |
| 领券对象 | `.yhquan-hd-chips .chip[data-value]` | 否 | `[-1]` 不限 | 多选，见 §4.3 |
| 区域 | `#yhquan-hd-area-nolimit` / `.yhquan-hd-area-chip` | 否 | 不限（`isLimitArea:0, selectedAreaIds:[]`） | 见 §4.4 |

- 提交：F 组 `createActivity`（创建）/ `editActivity`（编辑，带 `id`）；无确认弹窗
- 接口：`POST https://1317825751-21j36twzqr.ap-guangzhou.tencentscf.com`，body `{credentials, action, ...params}`

#### 数量设置
- 总量上限 = 活动可领总张数（默认 10000）；单店限制 = 每家店最多领几张（默认 5，最大 5）。用户说"限1000张"= 总量上限 1000。

#### 抢券时间设置
- 界面只有日期（type=date），**没有时分秒控件**；保存代码固定 `00:00:00` / `23:59:59`
- 用户说"明天10点到12点" → **界面做不到**，Agent 须如实告知；若用户确认绕过界面直接调 API，`createActivity`/`editActivity` 的 payload 接受 `beginTimeHms`/`endTimeHms` 可指定时段
- `tagBeginTimeDate/Hms` 无界面控件，提交时与 beginTime 同值

#### 如何刷新抢券时间
- 齿轮按钮 `#yhquan-hd-time-setting` → 弹窗「刷新设置」，提示原文「开启后，系统会定时将抢券活动时间刷新到当前优惠券有效期内。」
- 选项：`auto`=自动刷新 / `manual`=不自动刷新（默认 manual）
- 生效条件：仅「启用 + 公共共享」时可设置；后台 `sx.js` 每 **30 分钟** 检查 `time_refresh_behavior==='auto'` 的活动，把抢券时间改为今天~今天+2（≤券结束日），调 `editActivity` 并写回共享库 `grab_time`/`time_refresh_updated_at`
- 活动弹窗内的小「刷新」按钮是重置表单默认值（`applyAllDefaultsUI`），与自动刷新不同

### 4.3 领券对象（storeSubTypes）
| 值 | 中文 | 值 | 中文 |
|---|---|---|---|
| -1 | 不限（默认） | 4 | 连锁总部（纯连锁） |
| 0 | 零售单体 | 5 | 商业公司 |
| 1 | 第三终端 | 6 | 民营医院 |
| 2 | 连锁总部（批零一体） | 8 | 医疗器械经营店 |
| 3 | 连锁加盟 | | |

- 多选 chip；若选中"不限"则最终只提交 `[-1]`；API 返回的是拼接串（如 `"0163"`→`[0,1,6,3]`，前端 `parseApiStoreSubtypes` 解析）

### 4.4 区域设置与共享券

**区域设置**：点「不限」→ `isLimitArea:0, selectedAreaIds:[]`；点省份 chip（区域数据来自 F 组 `getAreaTree`，懒加载）→ `isLimitArea:1, selectedAreaIds:[选中的 areaId]`

**共享优惠券（免鉴权，数据库直接获取）**：
- 存储：CF Worker + D1 网关 `https://yhsjk.cfdaili.top`，集合 `coupons`，docId = `{providerId}::{couponId}`
- 读取方式（**不调用业务云函数、不带用户 credentials**）：
```js
// 按供应商取共享券（最常用）
await window.SjkModule.getWhere('coupons', 'provider_id', '==', providerId);
// 取单张券的共享节点
await window.SjkModule.get('coupons', `${providerId}::${couponId}`);
// 公共分享页：拉全库
sjkCall('getAll', {collection:'coupons'});
```
- 鉴权说明：业务 SCF（A-F 组）需用户 `credentials`；数据库层用**全站固定 token**（`x-yh-token` 头，前端常量），公共分享页 `zhiliao/gongxiang.html` 无需用户登录即可读取 `coupons` 全表——即"共享券无需（用户）鉴权"
- 共享券 doc 结构（字段以源码为准）：
```
provider_id, couponId, coupon_name, provider_name, coupon_expire_at, updated_at,
tasks{taskId:{status,created_at,activity_name,result,error,...}},
activities{activityId:{activity_name,total_limit,store_limit,
  area:{is_limit,ids,names}, grab_time:{begin,end}, activity_url,
  time_refresh_behavior, updated_at, time_refresh_updated_at}}
```
- 注意：`coupon_id`/`expire_at`/`share_mode` 不是真实字段名，分别为 `couponId`/`coupon_expire_at`/无（刷新行为用 `time_refresh_behavior`）

### 4.5 可用状态设置与启停
- 控件 `#yhquan-hd-availability`：`enabled`=启用（`isClose:0`）｜`disabled`=禁用（`isClose:1`）
- 无独立启停按钮：选择后点底部「保存」→ F 组 `disableActivity`（`id`, `isClose`, `storeSubTypes`）→ 无确认弹窗
- 共享模式 `public/private`：高折扣券（满减<2000 或折扣<0.98）设「启用+公共共享」时 `jy.js` 校验拦截，提示「免邮券暂不支持共享！」「优惠较大，请设置至少1个区域！」「优惠力度过大，请设置领券对象和区域！」→ 按提示补领券对象/区域，或保持私有

### 4.6 活动其他操作
| 操作 | 接口/方式 | 确认 |
|---|---|---|
| 查看/切换活动 | 点活动项 `.yhquan-hd-activity-item` → `getActivity` 载入表单 | 无 |
| 删除活动 | 先 `disableActivity` 再 `deleteActivity`，移除共享快照 | 有：「确认要删除当前抢券活动？」 |
| 生成活动二维码 | 券卡片二维码图标 → `getActivity` 取数据 → QRCode.js 生成，URL=`https://dian.ysbang.cn/#/grabCoupon?id={activityId}` | 无活动/过期/禁用时有对应确认弹窗 |

### 4.7 高折扣校验规则（jy.js，仅启用+公共共享时）
| 条件 | 提示 |
|---|---|
| 免邮券（type25） | 免邮券暂不支持共享！ |
| 高折扣且无区域 | 优惠较大，请设置至少1个区域！ / 优惠力度过大，请设置区域！ |
| 高折扣且无领券对象 | 优惠力度过大，请设置领券对象！ / 优惠力度过大，请设置领券对象和区域！ |
| 阈值 | `minPayAreaLimitThreshold=2000`、`aggressiveDiscountThreshold=0.98`（minPay<2000 或折扣<0.98 视为高折扣） |

---

## 5. 创建

入口：悬浮「+」`#yhquan-cj-fab` → 弹窗「创建优惠券」。三种券类型页签：`data-type=13/11/25`，默认 13；切换会清空自动生成的说明并重渲染表单。

### 5.1 三种券类型字段对照

> **列说明**：`来源` = 用户提供 / 系统自动生成 / 固定值。
> **用户只需提供**：券类型（`type`）+ 使用条件（`minPay`）+ 优惠值（`discount`/`price`）；其余或自动生成、或有默认值。

| 字段（中文） | 提交字段 | 打折券 13 | 满减券 11 | 免邮券 25 | 来源 | 默认值 | 取值/说明 |
|---|---|---|---|---|---|---|---|
| 券类型 | `type` | ✓ | ✓ | ✓ | 用户提供 | 13 | 13商家打折券 / 11商家满减券 / 25商家免邮券 |
| 名称 | `name` | ✓ | ✓ | ✓ | **Agent 代拟**（前端必填，无UI自动生成） | — | 统一格式 **`额度/数值+后缀`**（详见 §5.1.1）；打折券 `2000/98+11月`、满减券 `1000/10+11月`、免邮券 `99/免邮+11月`；后缀由 Agent 从用户语义提取，用户未提后缀则省略 |
| 使用条件（元） | `minPay` | ✓ | ✓ | ✓ | 用户提供 | — | 数字 >0，满多少元可用 |
| 折扣 | `discount` | ✓ | — | — | 用户提供 | — | 98/0.98/9.8 → 归一 `9.8`（=98折=降2点）；归一化由 `parseDiscount` 自动完成，Agent 原样传用户输入即可 |
| 最高优惠金额（元） | `maxCash` | ✓ | — | — | 用户提供（可省） | 空→0 | 留空=不限制（系统自动填 0）；打折券特有 |
| 优惠金额（元） | `price` | — | ✓ | — | 用户提供 | — | 减多少元；>0；满减券特有 |
| 使用说明 | `note` | ✓ | ✓ | ✓ | **系统自动生成** | 按类型生成 | 留空自动填，见 §5.2；用户手动填过则保留 |
| 首推反哺券 | `bfrFlag` | ✓ | ✓ | ✓ | 用户提供（可省） | 0 否 | 0否 / 3自营商家首推补贴 / 4省钱卡 |
| 有效期模式 | `selectDateType` | ✓ | ✓ | ✓ | **系统派生** | 0 时间段 | 由激活的有效期页签派生，无直接控件 |
| 开始日期 | `beginTimeDate` | ✓（模式0） | ✓ | ✓ | 用户提供 / 系统补全时刻 | 今天 | 系统自动补 ` 00:00:00` |
| 结束日期 | `endTimeDate` | ✓（模式0） | ✓ | ✓ | 用户提供 / 系统补全时刻 | 本月最后一天 | 系统自动补 ` 23:59:59` |
| 有效天数/小时 | `validDays` | ✓（模式1） | ✓ | ✓ | 用户提供 / 系统补默认 | 空→1 | 数字 ≥1（系统 `Number()||1`） |
| 时长单位 | `validType` | — | — | ✓ | **系统补默认** | 0 | 0天 / 1小时；仅免邮券提交此字段 |
| 备注（内部） | `extNote` | ✓ | ✓ | ✓ | 用户提供（可省） | 空 | 不展示给用户 |
| 固定值 | `toCondition` | ✓ | ✓ | ✓ | **系统固定** | 5 | 界面无控件，代码固定 |
| 折扣率提示 | — | — | ✓ | — | **系统自动计算** | — | 满减券输入框旁实时显示「当前X折扣」=`((minPay-price)/minPay*10)`，仅提示不提交 |

### 5.1.1 券名称 / 抢券活动名称命名规则（Agent 自动代拟）

**统一格式**：`额度/数值+后缀`
- `额度` = `minPay`（使用条件，元）；`数值` 按券类型取折扣或减免额；`后缀` 从用户语义提取，用户未提则省略 `+后缀`。

| 券类型 | 数值来源 | 名称示例（无后缀） | 名称示例（带后缀） |
|---|---|---|---|
| 打折券 13 | `discount`（归一后，如 98） | `2000/98`、`3000/98` | `2000/98+11月`、`3000/98+双11` |
| 满减券 11 | `price`（减免额，如 10） | `1000/10` | `1000/10+11月` |
| 免邮券 25 | 固定 `免邮` | `99/免邮` | `99/免邮+11月` |

**后缀提取（Agent 从用户语义自动分析，不要问用户）**：
| 用户说法 | 提取的后缀 | 最终名称示例 |
|---|---|---|
| "11月的活动/11月券" | `11月` | `2000/98+11月` |
| "双11促销/双十一" | `双11` | `3000/98+双11` |
| "年货节用" | `年货节` | `2000/98+年货节` |
| "给老客户的券" | `老客户` | `2000/98+老客户` |
| "店庆活动" | `店庆` | `1000/10+店庆` |
| 用户给了自定义名称 | **直接用用户原名**，不套格式 | 原样 |

- 后缀取用户语义里的**时间/节日/人群/用途**关键词，简洁（≤6字），不编造用户未提及的信息
- 用户明确说"名称用XX"时，以用户给的为准，不套本格式
- Agent 代拟后须在确认表里显示"名称（代拟）=xxx"，让用户可见

**抢券活动名称**（`eventName`）：默认值 = 券名称（源码 `hd/yewu.js`：`this.currentCoupon?.name`），即直接用 `额度/数值+后缀` 的券名；用户单独指定活动名时以用户指定为准。

### 5.2 使用说明自动生成规则（note 留空时）
| 券类型 | 自动生成的文案 |
|---|---|
| 打折券 | 满 {minPay} 元后任意金额享 {discount} 折… |
| 满减券 | 满 {minPay} 元减 {price} 元，仅可购买当前店铺内产品 |
| 免邮券 | 仅当前店铺内商品可用，可直接抵扣邮费 |

> 用户手动改过 note 后不再被自动生成覆盖。

### 5.2.1 系统自动生成字段汇总（Agent 不要问用户、不要自己填错）

| 字段 | 触发时机 | 生成规则（源码位置） |
|---|---|---|
| `discount` | 用户输入任意写法 | `parseDiscount`：>10 除10、<=1 乘10、否则原值 → 98/0.98/9.8 都得 9.8（cj/yewu.js parseDiscount） |
| `note` | 留空时 | 按 type 生成（§5.2）；用户手填过则保留（noteManualEdited） |
| `selectDateType` | 提交时 | 时间段页签激活→0；天数页签激活→1（非手填控件） |
| `beginTimeDate` | 选了开始日期 | 自动拼 ` 00:00:00` |
| `endTimeDate` | 选了结束日期 | 自动拼 ` 23:59:59` |
| `validDays` | 空 | `Number('') || 1` → 1 |
| `validType` | 仅 type25，空 | `Number('') || 0` → 0（天） |
| `maxCash` | 空 | `Number('') || 0` → 0（不限） |
| `bfrFlag` | 未选 | `Number(undefined || 0)` → 0（否） |
| `toCondition` | 总是 | 固定 5 |
| `name` | **前端不生成** | validate 强制必填；Agent 按 §5.1 规则代拟并告知用户 |

> **Agent 原则**：表中"系统自动生成"的字段，传用户输入或留空即可，系统/前端会按规则处理；不要替用户决定业务关键值（minPay、优惠值），但可代拟 name 并明确告知。

### 5.3 校验规则（按序返回首个错误）
| 提示原文 | 触发条件 |
|---|---|
| 请输入券名称 | name 空 |
| 请输入有效的使用条件 | minPay 空或 ≤0 |
| 请输入有效的折扣 | 打折券 discount ≤0 |
| 请输入有效的优惠金额 | 满减券 price ≤0 |
| 请选择有效期时间段 | 模式0 起止日期任一空 |
| 请输入有效天数/小时 | 模式1 validDays<1 |

### 5.4 提交与结果
| 项 | 内容 |
|---|---|
| 接口 | B 组 `addCoupon`，body `{credentials, action:'addCoupon', couponData:{...上表字段}}` |
| 按钮 | `#yhquan-cj-submit`「创建」；提交中变「创建中...」并禁用；无确认弹窗 |
| 成功 | 提示后端 message 或「创建成功」→ 关弹窗 → 自动刷新券列表 |
| 失败 | 提示 message 或「创建失败」；网络异常「创建失败: {err.message}」 |

### 5.5 用户话术 → 字段示例
| 用户说 | type | name（Agent代拟，§5.1.1） | minPay | discount | maxCash | price | 有效期 | 系统自动生成 |
|---|---|---|---|---|---|---|---|---|
| 满100减20，7天 | 11 | `100/20` | 100 | — | — | 20 | 模式1，validDays=7 | note / selectDateType=1 / toCondition=5 / bfrFlag=0 |
| 满2000享98折，封顶50，11月用 | 13 | `2000/98+11月` | 2000 | 98 | 50 | — | 模式0，今天~月末 | discount归一9.8 / note / 时刻补全 / toCondition=5 |
| 免邮满99，7天，店庆 | 25 | `99/免邮+店庆` | 99 | — | — | — | 模式1，validDays=7 | note / validType=0 / selectDateType=1 / toCondition=5 |
| 3000/98，双11活动（用户给了"名称"意图但按格式代拟） | 13 | `3000/98+双11` | 3000 | 98 | — | — | 默认 | discount归一 / note / 时刻补全 |

> **必须用户提供的**：券类型、使用条件（`minPay`）、优惠值（`discount`/`price`）、有效期（若非默认）。
> **Agent 代拟并告知**：`name`（前端必填但无自动生成，按 §5.1.1 的 `额度/数值+后缀` 代拟，后缀从用户语义提取）；抢券活动 `eventName` 默认同券名。
> **系统自动生成，不要问用户**：`note`、`discount`归一、`selectDateType`、时刻补全、`validDays`/`validType`/`maxCash`/`bfrFlag`/`toCondition` 默认值（见 §5.2.1）。

---

## 6. 可合并/统一之处（优化建议）
1. **所有接口共用 body 骨架** `{credentials, action, ...}`，可统一封装一个 `callCouponApi(action, params)`，只换 URL 组与 action——避免每个功能重复拼装
2. **"返回基本信息"四功能一致**：效期/作废/赠送/活动都展示同一券信息（名称/详情/有效期/状态），可统一为一个 `couponBaseInfo(coupon)` 渲染函数，文档中也统一表述
3. **三类型券公共字段**（name/minPay/note/bfrFlag/有效期/extNote/toCondition）可复用一张公共表单，仅按 type 增减特有字段——本文 §5.1 已按此合并展示
4. **有效期模式统一**：创建券（selectDateType 0/1）与活动抢券时间（begin/end）语义不同，不建议合并；但都只支持"日期"级别（活动无时分秒），需注意提醒用户

## 7. 红线
- 用户关键信息缺失（门槛、优惠值、有效期）时**询问用户**，不猜
- "具体时段"界面做不到时**明确告知**，不静默改为按天
- 写操作执行前确认用户授权；多数界面无二次确认，点了即生效
- 共享券读取不带用户 credentials（数据库层固定 token），不要误用业务云函数
