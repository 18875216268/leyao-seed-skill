# 动态字典与枚举（API）

> 前置：`api_认证与公共约定.md`
> 适用：所有"选项由账号配置决定"的参数。**值随账号/配置变化，必须运行时获取，禁止硬编码。**

## 1. 两类参数

| 类型 | 特征 | 归属 |
|---|---|---|
| **固定枚举** | 全账号一致，值域写死在代码里 | 写在**所属板块文档**（如 `status`、`wholesaleType`、`condition`） |
| **动态字典** | 随账号配置变化 | 本文件覆盖**商品 11 类**；客户/数据的级联与枚举字典见各板块 `api_*.md`（如 `客户/api_客户列表.md`、`数据/api_品种分析.md §2.5`） |

## 2. 能力开关：getProviderInfo4List2

`POST /scm-goods/wholesaleDrug/getProviderInfo4List2`

返回账号能力，决定**显示哪些筛选字段、哪些导出入口、哪些导出列**。

| 字段 | 类型 | 影响 |
|---|---|---|
| `providerId` | int | 供应商 ID（`provideridm` 的来源） |
| `cashcow` | bool | `true` 显示「关联自动上架拼团」（`virtualType` 语义为已关联/已解除）；`false` 显示「虚拟供应商」 |
| `isGroupCenterOrder` | int | `1` 才显示「导出组单中心活动」入口 |
| `beVideo` | int | 控制「是否有视频」筛选项 |
| `canHostedDrug` | int | 控制「是否托管」筛选项 |
| `hasGoods` | int | 是否开通商品模块 |
| `useTimeLimit` | int | 是否支持限时特价 |
| `canOpenSpecialTicket` | int | 控制「可开专票」筛选项 |
| `canAddRebateCommission` | int | 控制「是否返佣返利」 |
| `partnerType` / `storeOperType` | int | 账号类型，影响可见字段组合 |

> 使用建议：进入页面先调本接口，按返回决定 UI 与导出列，不要假设字段一定存在。

## 3. 字典接口总表

| # | 接口 | 驱动参数 | 返回结构 | 实测条数 |
|---|---|---|---|---|
| 1 | `getPriceTypes` | 价格档位列（`unitPriceN`） | `[{priceType, priceTypeName}]` | 按账号 |
| 2 | `getStoreTypeGroup` | `storeType`（供货对象） | `[{id, groupName, storeSubtypes}]` | 15 |
| 3 | `getDeliverAlones` | `deliverAlone`（开单组合） | `[{deliverAlone, desc}]` | 20 |
| 4 | `getDiscountType` | `disType`（阶梯价/赠品） | `[{disType, desc}]` | 6 |
| 5 | `getBusiScopeForProvider` | `busiScope`（经营范围） | `[{id, busiScope, isAccessible}]` | 21 |
| 6 | `getBusiScopeList` | `busiScope`（分页版） | `{results:[{id,busiScope}]}` | 20/页 |
| 7 | `getDeliveryProviders` | `deliveryProviderId`（配送商） | `[{deliveryProviderId, name}]` | 22 |
| 8 | `getAllGroupTheme` | `promotionTypeId`（端口主题） | `[{id, title, describe}]` | 18 |
| 9 | `getAreaGroupDropList` | `areaGroupId`（商圈） | `[{id, groupName, nationwide}]` | 172 |
| 10 | `wsListRankFilterOptions` | `near7dStoreDrugRankRangeKeys` / `near7dPlatformDrugRankRangeKeys` | `{near7dStoreDrugRankRanges:[{key,label}], near7dPlatformDrugRankRanges:[...]}` | 8 / 9 |
| 11 | `provider/getWarehouseListByProviderId` | `warehouseCode`（发货仓） | 仓库列表 | 按账号 |
| 12 | `getStoreTypeGroupForClinic` | `storeType`（诊所） | 同 `getStoreTypeGroup` | 按账号 |
| 13 | `getStoreGroupList` | 未采集 | 未知 | — |

> 所有路径前缀为 `https://scm.ysbang.cn/scm-goods/`（第 11 项为 `/scm-goods/provider/`）；均为 `POST` + 公共参数。
> `modules/goods/dicts.py` 已接入第 1–10、12 项（共 11 类）；第 11、13 项未接入，`dict` 命令不提供。

## 4. 各字典说明

### 4.1 价格档位 `getPriceTypes`

```
POST /scm-goods/wholesaleDrug/getPriceTypes
body: 公共参数
→ [{ "priceType": 1, "priceTypeName": "单体周边价" }, ...]
```

- `priceType` = 导出列 `unitPriceN` 的下标 N；
- `priceTypeName` = 该列在导出 CSV 中的**列名**；
- **导出列动态生成规则**：基础列（64 列）+ 每个档位一列；列名即 `priceTypeName`。

### 4.2 供货对象 `getStoreTypeGroup`

```
→ [{ "id": 122690, "groupName": "零售单体", "storeSubtypes": "0" }, ...]
```

- 参数 `storeType` 传 **id（整数）**；传数组会报 `40004`；
- `storeSubtypes` 为可用子类型编码串（如 `012345`）。

### 4.3 开单组合 `getDeliverAlones`

```
→ [{ "deliverAlone": 0, "desc": "正常开单" }, { "deliverAlone": 1, "desc": "单品独立开单" }, { "deliverAlone": 2, "desc": "中药" }, ...]
```

### 4.4 阶梯价/赠品 `getDiscountType`

```
→ [{ "disType": 1, "desc": "单品阶梯价" }, { "disType": 3, "desc": "送赠品" },
   { "disType": 4, "desc": "新赠品_阶梯满赠" }, { "disType": 5, "desc": "新赠品_每满赠" }, ...]
```

### 4.5 经营范围 `getBusiScopeForProvider` / `getBusiScopeList`

```
→ [{ "id": 1, "busiScope": "中成药（除冷藏）", "isAccessible": 1 },
   { "id": 2, "busiScope": "化学药(除冷藏)" }, { "id": 3, "busiScope": "化学药(仅冷藏)" }, ...]
```

- 参数 `busiScope` 传 **id**，支持多选（数组）。

### 4.6 配送商 `getDeliveryProviders`

```
→ [{ "deliveryProviderId": 23919, "name": "小药桂" }, ...]
```

### 4.7 端口主题 `getAllGroupTheme`

```
→ [{ "id": 22811, "title": "连锁优选专区链接提报" }, ...]
```

- 参数 `promotionTypeId` 支持多选（数组）。

### 4.8 商圈 `getAreaGroupDropList`

```
→ [{ "id": 8161, "groupName": "全国通用除（西藏）", "nationwide": 1 }, ...]
```

- 参数 `areaGroupId` 传 id。

### 4.9 排名区间 `wsListRankFilterOptions`

```
→ {
    "near7dStoreDrugRankRanges":    [{ "key": 1, "label": "TOP1-10" }, ... 共 8 档],
    "near7dPlatformDrugRankRanges": [{ "key": 1, "label": "TOP50" },   ... 共 9 档]
  }
```

- 参数 `near7dStoreDrugRankRangeKeys` / `near7dPlatformDrugRankRangeKeys` 传 `key`（整数）。

### 4.10 发货仓 `provider/getWarehouseListByProviderId`

```
POST /scm-goods/provider/getWarehouseListByProviderId
→ [{ "warehouseCode": "...", "whName": "..." }, ...]
```

- 参数 `warehouseCode` 传仓库编码；账号无仓库时返回空数组，此时筛选字段不显示。

## 5. 使用规则

1. **先能力开关、后字典**：`getProviderInfo4List2` 决定"显示什么"，字典接口决定"有哪些选项"。
2. **不缓存跨账号**：不同账号值域不同，禁止把某账号的值写进代码或文档。
3. **失败降级**：字典接口异常时，筛选字段置空并允许不传，不要伪造默认值。

## 6. 未采集端点

`getStoreGroupList`（`/scm-goods/wholesaleDrug/getStoreGroupList`）仅在《附录/接口总表》登记，参数与返回结构尚未采集，**暂不提供查询**；需要时先补采集再接入。
4. **导出列**：必须用 `getPriceTypes` 动态生成列名，不可写死「单体采购价」等。
