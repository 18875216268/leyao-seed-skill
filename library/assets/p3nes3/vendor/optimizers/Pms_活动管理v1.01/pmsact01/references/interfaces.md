# PMS 商品活动管理 · 接口全清单与参数模板

> 本文件是 Pms_活动管理v1.01 的接口速查源（提炼自权威事实源，见 [pointer.md](pointer.md)）。
> 所有接口 POST + JSON，域名 `pms.ysbang.cn`（部分 `pms.leyopharm.com`），公共参数 `token`+`buildTime` 自动注入，成功码 `code=="40001"`。

## 目录
- 一、读取接口 R1-R17
- 二、写入接口 W1-W7
- 三、导出接口 E1-E3
- 四、下拉数据源 R18-R24
- 五、枚举字典
- 六、响应字段与错误码

---

## 一、读取接口（查询）

| # | 路径 | 用途 | 关键入参 | 返回 |
|---|---|---|---|---|
| R1 | `/pms-main/ykjWholesaleOperation/pageOneFixedWsList/v27280` | 一口价列表 | providerId + §筛选 + page/pageSize | `data.total` + `data.results[]` |
| R2 | `/pms-main/ykjWholesaleOperation/getSpecialProductWholeSaleList/v27280` | 特价列表 | 同R1（无pricingStatusList/abnPricingTypeList，多operationFlagList/linkFlagList） | 同R1 |
| R3 | `/pms-main/wholesaleOperation/pageWholeSaleByType/v24100` | 批购包邮/整件购/随心购 | providerId + tabType(2/3/4) + pageNum/pageSize + negMarginProfitRate | `data.total` + `data.list[]` |
| R4 | `/pms-main/ykjWholesaleOperation/getProductWholeSaleCount/v27280` | 5 tab 统计卡 | providerId | data |
| R5 | `/pms-main/ykjWholesaleOperation/getManualOpNumByProviderId/v27280` | 手动运营品种数额度 | providerId | data |
| R6 | `/pms-main/ykjWholesaleOperation/getMyAbnWaitCheckWsNum/v27280` | 我的异常待确认角标 | providerId | data |
| R7 | `/pms-main/channel/getDayAdjustPriceCount/v1540` | 待审批调价角标 | {} | {submitProductCount,...} |
| R8 | `/pms-main/wholesaleOperation/wholeSaleCountStat/v24100` | 批购包邮4计数 | providerId + tabType | {autoAdjustPriceCount,...} |
| R9 | `/pms-main/wholesaleOperation/getFollowNumByPid/v22240` | 跟价数 | providerId | data |
| R10 | `/pms-main/ykjWholesaleOperation/getYKJEnumConf/v27280` | 商圈/供货对象/控销组下拉 | providerId(必填) + type(1/2/3) | `data.list[{id,name}]` |
| R11 | `/pms-main/ykjWholesaleOperation/listReviewSceneOptions/v28110` | 定价异常类型枚举 | providerId | `[{type:0~10,desc}]` |
| R12 | `/pms-main/ykjWholesaleOperation/listWsPriceInfoBeforeEdit/v27280` | 调价弹窗现价+费率 | tabType + wholesaleId | {estOutboundCost,...} |
| R13 | `/pms-main/channel/checkWholesaleAudit/v351` | 调价审批单 | page/pageSize/wholesaleId | {wsdlId,status,...} |
| R14 | `/pms-main/priceAdjustConfig/listWsOpRecord/v100` | 操作记录 | wholesaleType/wholesaleId/contentType/时间/page | {contentTypeStr,...} |
| R15 | `/pms-main/wholesaleOperation/pageWholesalePurchaseDetail/v29320` | 采购明细 | providerId/wholesaleId/orderId/时间/page | {orderId,storeName,...} |
| R16 | `/pms-main/channel/getDrugInfoByWholesaleId/v7150` | 活动商品详情 | wholesaleId | 商品对象 |
| R17 | `/pms-main/drugInfo/getMedicareNetPriceByDrugId/v483` | 医保支付价 | providerId + drugId | data |

> **写操作前必先按 R1/R2/R3 定位现值。**

### 筛选参数（R1/R2 通用；R3 同构 + tabType/pageNum/negMarginProfitRate）
| 字段 | UI | 类型/说明 |
|---|---|---|
| providerId | 平台店铺 | string 必填（凭证动态） |
| wholesaleId | 活动ID | 精确，带它时 wholesaleStatus 被忽略 |
| wholesaleStatus | 活动状态 | 5进行中/0待开始/3已下架/4缺货下架/6未销售 |
| provDrugCode | 药师帮ID | 编码（精确筛选有效） |
| drugKeyword | 商品/药师帮ID输入框 | 关键词；与 provDrugCode 并存 |
| approval/factory/enterprise | 批准文号/厂家/厂牌营销方 | 文本 |
| contactor/operator/bpManager | 负责人 | **userId 数字**（动态下拉取 ID） |
| busiFlag | 业务类型 | 5普品/3集采 |
| checkFlag | 考核品种 | 默认1（只看考核）；全部置"" |
| leyoTagIdList/provTagIdList | 标签筛选 | tagId 数组（R22） |
| pricingStatusList/abnPricingTypeList | 定价状态/异常 | 数组（R1有，特价E2无） |
| specialFlag | 维价类型 | 0无/2集团/3集采/6采购 |
| operationFlagList/linkFlagList | 运营/链接策略(一口价) | 数组 1/2/8 与 1/2 |
| beClickAbnWaitCheck / beClickMyAbnWaitCheck | 异常卡 | 常规留空""，点卡置1 |
| negMarginProfitRate | 负毛利 | string（仅R3/E3） |

## 二、写入接口（⚠️ 全部需用户授权）
| # | 路径 | 用途 | 关键参数 |
|---|---|---|---|
| W1 | `/pms-main/ykjWholesaleOperation/updateYkjWholeSaleStatus/v27280` | 下架(1)/重上架(2) | wholeSaleId + wholeSaleType + status |
| W2 | `checkUpdateOneFixedWsOpFlag` → `updateOneFixedWsOpFlag/v27280` | 运营策略（两步均须result=1） | wholesaleId + operationFlag(1自动/2手动) |
| W3 | `/pms-main/ykjWholesaleOperation/updateYkjWsActivityTime/v27280` | 活动期间 | wholeSaleId + beginDate/endDate + wholeSaleType |
| W4 | `/pms-main/ykjWholesaleOperation/updateGoodsSaleLimitConf/v27280` | 限购参数 | wholesaleId + minQty/step/maxAmountPerStore/calculatePeriod |
| W5 | `/pms-main/ykjWholesaleOperation/updateGoodsSaleAreaConf/v27280` | 定向管理 | wholesaleId + areaGroupId/storetypeGroupId/isRestrict/restrictId |
| W6 | `/pms-main/channel/fastAdjustPriceBatch/v1540` | 快速调价（审批流） | provDrugCode + providerId + warehouseId + fastAdjustPriceRequestList[] |
| W7 | `/api/sale/cancelAudit/v351`（form） | 撤销审批 | wsdlId |

**前置规则**：operationFlag=1（自动运营）下架前必须先 W2 切手动；重上架会强制切手动；PMS 无活动结束终态（须网页端）。

## 三、导出接口（同步 xlsx 二进制流）
| # | 路径 | 用途 |
|---|---|---|
| E1 | `/pms-main/ykjWholesaleOperation/exportOneFixedWsList/v27280` | 一口价 |
| E2 | `/pms-main/ykjWholesaleOperation/downloadSpecialProductWholeSaleList/v27280` | 特价 |
| E3 | `/pms-main/wholesaleOperation/exportWholeSaleByType/v24100` | 批购包邮/整件购/随心购（tabType 2/3/4） |

- 请求体 = 对应查询筛选去掉分页字段；`stream=True`，body 即 xlsx
- E2 无 pricingStatusList/abnPricingTypeList，多 operationFlagList/linkFlagList
- E3 多 negMarginProfitRate/operationFlag(单值)/linkFlag(单值)
- 并发 ≤6（高并发会连接重置）

## 四、下拉数据源
| # | 筛选项 | 接口 |
|---|---|---|
| R18 | 平台店铺 | `getSubProviderList/v2050`（凭证/缓存） |
| R19 | 商品 | `goodsOption/pv7240`（远程搜索，取值 goodsCode） |
| R20 | 品种/运营负责人 | `drugInfo/getChildrenValidUser/v7160`（userType=contactor/operator） |
| R21 | 厂牌项目经理 | `common/bpManagerChooseListWithSubUser/v15120` |
| R22 | 业务标签 | `tagManage/getDiyTagListForFilter/v1630` → leyoTags/provTags |
| R23 | 定价异常类型 | 同 R11 |
| R24 | 均价开关 | `common/avgPriceSwtich/v910` |

## 五、枚举字典
| 枚举 | 码值 |
|---|---|
| wholesaleStatus | 0待开始/5进行中/3已下架/4缺货下架/6未销售（无终态码） |
| operationFlag | 1自动/2手动/8临时手动/0非自动态 |
| linkFlagList(一口价) | 1长期/2短期 |
| linkFlag(E3) | 1省内/2省外（单值，勿与 linkFlagList 混） |
| busiFlag | 5普品/3集采 |
| specialFlag | 0无/2集团/3集采/6采购 |
| tabType | 2批购包邮/3整件购/4随心购 |
| wholesaleType(写) | 1一口价/2特价 |
| calculatePeriod | 0活动期内/1每笔/2每天/3每周/4每月 |
| isRestrict | 0否/1控销/2禁销 |

## 六、响应与错误码
- 成功：`code=="40001"`；写接口另需 `data.data.result===1`
- 列表：一口价/特价 `data.total`+`data.results[]`；批购包邮系 `data.total`+`data.list[]`
- 响应行关键字段：`wholesaleId`、`wholesaleStatusStr`、`operationFlag`、`cnName`/`drugName`、`salePriceList[]`、`minQty`/`maxAmountPerStore`、`providers`/`restrictDesc`、各类7/28天统计字段（详见权威源 §2.4）
- 常见错误：40003（前置不满足，如 operationFlag=0 切手动）、40004（参数异常/缺 providerId）、40000/40020（token 失效）
- ⚠️ 字段完整释义与踩坑以权威源为准（见 pointer.md）
