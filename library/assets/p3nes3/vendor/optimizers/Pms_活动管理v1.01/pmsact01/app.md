---
name: Pms_活动管理v1.01
description: PMS 商品活动管理（自营专属）的查询、导出与写操作引导：一口价/特价/批购包邮/整件购/随心购的活动列表、统计卡、筛选字典、上下架、运营策略、限购/定向、调价审批。用户问"PMS 活动/商品活动/一口价活动/改限购/调价审批/活动导出"时优先使用；与 SCM 商品主列表、促销毛利、TMS 促销费用/活动区分。
---

# Pms_活动管理v1.01

> 框架生态提示：本资产位于某包的 `library/assets/` 下 → 使用前先回主框架：上溯到含 `library/engine.py` 的包根，读其 `SKILL.md` 的〈最高准则〉→ `library/ROUTES.md` → 按 `processor/` 五步执行；独立安装态不受此限。

版本：v1.01 ｜ 知识基线：2026-11-17 ｜ 归属：p3nes3 子 skill（优化板）

## 1. 凭证（由调用方传入）
本包**不实现登录**：不获取、不生成、不存储凭证。调用方（父 skill / 宿主 / 用户）拿到 PMS token 后按任一入口传入：
1. `--token <token>`；2. 环境变量 `PMS_TOKEN`（多次调用推荐）；3. `--state-file PATH` / `PMS_STATE_FILE`（凭证文件）。
- 公司口径：`providerId` 用凭证里的 `provider_id`（本账号 3364），多公司时由用户指定。
- 凭证缺失或 401：向**调用方**索取新凭证重试；**本包禁止自写登录、禁止读父凭证仓库** ✗。
- 本包只接收凭证，不感知凭证来源，也不指路任何登录流程。

## 2. 何时用 / 不适用
- **何时用**：PMS 商品活动管理页的活动查询/导出；自营活动在 SCM 侧被自动运营拦截、限购/控销/价格"返回成功不落库"时的转 PMS 出口；上下架、运营策略切换、活动期间、限购/定向、调价审批。
- **不适用**：SCM 商品主列表/通用导出/订单/客户 → `scm7k3q`；促销销售/毛利 → `psol5x`；TMS 促销费用管理/促销活动管理/优惠券统计（不同页面）→ 如实告知，不混用。

## 3. 核心流程
1. 取凭证（父 skill 或用户传 `--token`/`PMS_TOKEN`/`--state-file`）
2. 按"活动类型 tab"选查询接口：一口价→R1、特价→R2、批购包邮/整件购/随心购→R3
3. 默认筛选：店铺=当前、状态=进行中(5)、考核品种=是(checkFlag=1)、活动类型默认一口价且二级选项全空
4. 写操作：先按 §4 定位现值 → 留回滚 → 授权 → 调写接口 → 复查询核验
5. 导出：同步 xlsx 二进制流（非异步任务），筛选带全

## 4. 接口速查（详见 references/interfaces.md）

### 读取（查询）
| # | 接口（POST，域名 pms.ysbang.cn） | 用途 |
|---|---|---|
| R1 | `/pms-main/ykjWholesaleOperation/pageOneFixedWsList/v27280` | 一口价列表 |
| R2 | `/pms-main/ykjWholesaleOperation/getSpecialProductWholeSaleList/v27280` | 特价列表 |
| R3 | `/pms-main/wholesaleOperation/pageWholeSaleByType/v24100` | 批购包邮/整件购/随心购（tabType 2/3/4） |
| R4 | `/pms-main/ykjWholesaleOperation/getProductWholeSaleCount/v27280` | 5 tab 统计卡 |
| R10 | `/pms-main/ykjWholesaleOperation/getYKJEnumConf/v27280` | 商圈/供货对象/控销组下拉 |
| R11 | `/pms-main/ykjWholesaleOperation/listReviewSceneOptions/v28110` | 定价异常类型 |

### 写入（⚠️ 需用户授权）
| # | 接口 | 用途 |
|---|---|---|
| W1 | `/pms-main/ykjWholesaleOperation/updateYkjWholeSaleStatus/v27280` | 下架(1)/重上架(2) |
| W2 | `checkUpdateOneFixedWsOpFlag` → `updateOneFixedWsOpFlag` | 运营策略（自动↔手动，两步） |
| W3/W4/W5 | `updateYkjWsActivityTime` / `updateGoodsSaleLimitConf` / `updateGoodsSaleAreaConf` | 期间/限购/定向 |
| W6 | `/pms-main/channel/fastAdjustPriceBatch/v1540` | 快速调价（审批流） |

### 导出（同步 xlsx）
| # | 接口 | 用途 |
|---|---|---|
| E1 | `/pms-main/ykjWholesaleOperation/exportOneFixedWsList/v27280` | 一口价 |
| E2 | `/pms-main/ykjWholesaleOperation/downloadSpecialProductWholeSaleList/v27280` | 特价 |
| E3 | `/pms-main/wholesaleOperation/exportWholeSaleByType/v24100` | 批购包邮/整件购/随心购 |

## 5. 常用 payload 模板（照抄前先按需改）

**一口价列表/导出**（导出去掉 page/pageSize）：
```json
{"providerId":"<凭证providerId>","wholesaleId":"","wholesaleStatus":5,
 "provDrugCode":"","drugKeyword":"","approval":"","factory":"","enterprise":"",
 "contactor":"","operator":"","bpManager":"","busiFlag":"","checkFlag":1,
 "leyoTagIdList":[],"provTagIdList":[],"pricingStatusList":[],"abnPricingTypeList":[],
 "specialFlag":"","saleStatDataType":1,"beClickAbnWaitCheck":"","beClickMyAbnWaitCheck":"",
 "page":1,"pageSize":10}
```
> ⚠️ `checkFlag=1` 是页面默认（只看考核品种）；要全部品种置 `""`。`beClickMyAbnWaitCheck=1` 是"我的异常待确认"卡，常规导出必须留空（实测置 1 曾导空）。

**批购包邮/整件购列表/导出**（R3/E3）：
```json
{"providerId":"<凭证providerId>","wholesaleStatus":5,"checkFlag":1,
 "tabType":2,"operationFlag":"","linkFlag":"","negMarginProfitRate":"",
 "leyoTagIdList":[],"provTagIdList":[],"specialFlag":"","saleStatDataType":1,
 "pageNum":1,"pageSize":10}
```
> `tabType`：2批购包邮/3整件购/4随心购；`operationFlag` 1自动调价/2自动跟价（单值）；`linkFlag` 1省内/2省外（单值，**不是** linkFlagList）。

## 6. 命令（走父 skill 通用发送器）
```bash
# 查询（从本包目录执行；示例路径按实际调整）
python ../../../../scripts/pms_call.py --host-key pmsHost \
  --path /pms-main/ykjWholesaleOperation/pageOneFixedWsList/v27280 \
  --payload-file query.json --token <token>
# 导出（同步 xlsx）
python ../../../../scripts/pms_call.py --host-key pmsHost \
  --path /pms-main/ykjWholesaleOperation/exportOneFixedWsList/v27280 \
  --payload-file export.json --out-file one_fixed.xlsx --token <token>
```
> `../../../../scripts/pms_call.py` 相对本包指向 `p3nes3/scripts/`；`--host-key pmsHost` 对应 `p3nes3/sync_config.json` 的 host_endpoints 键；独立安装态用实际路径。参数以 `pms_call.py --help` 为准。

## 7. 按需读取
- 接口全清单/参数/响应/枚举/调用前置：[interfaces.md](references/interfaces.md)
- 详细事实源（字段表/踩坑/完整枚举/源码依据）：`library/assets/scm7k3q/references/商品/api_pms活动管理.md`——见 [pointer.md](references/pointer.md) 的权威声明与同步约定。

## 8. 强制规则
1. 无自有登录、不读父凭证仓库；凭证只由调用方传入。
2. 写操作（上下架/运营策略/限购/定向/调价）**必须先问用户授权**，写前查现值、留回滚、写后复验。
3. 导出是同步 xlsx 流，禁止套异步三步链；筛选必须带全。
4. `checkFlag`/`beClickXxx` 是窄化标记，常规查询留空或理解其默认语义。
5. 动态下拉传 ID 数字（userId/tagId/店铺ID），不传显示名。
6. 状态只有 5上架/3下架（无终态码）；PMS 与 SCM 状态编码勿混。
7. 多候选（SCM/PMS 都能接）交用户决定，不自行裁决。
