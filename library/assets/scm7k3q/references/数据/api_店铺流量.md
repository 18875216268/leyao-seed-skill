# 店铺流量（API）

> 子板块：数据 → **店铺流量**（页面 `#/statistic-analysis/store-traffic`）。
> **账号归属：③ 仅自营**（**注意**：同板块的品种分析/销售报表是 ① 通用，本子板块单独为自营专属——用户 2026-11-13 明确）。
> 请求约定同 `sy.md §3`。**本子板块只有 2 个接口，且「下载数据」没有服务端接口**（前端本地生成 xlsx）。
> 参数与字段来自真实抓包 + 参考文档实测示例双核对。

## 1. 总览

| 界面 | 后端 | 说明 |
|---|---|---|
| 统计方式：按天 / 按周 / 按月 | `getFlowInfo.granularity` = `1/2/3` | 同一接口切粒度 |
| 时间周期：近8天 / 近30天 / 近3个月 / 自定义 | `getFlowInfo.rangeFlag` = `1/2/3/4` | `4` 需另传 `startTime`/`endTime` |
| 查询结果三指标（趋势） | `getFlowInfo` 的三条列表 | 曝光/点击/访客 |
| 查询结果三指标（汇总卡 + 同比） | `topExposureStat` | 9 字段 |
| 下载数据（xlsx） | **无接口**，前端 SheetJS 生成 | 见 §3 |

> **两个接口分属两套前缀**：趋势在 `/scm-setting/flow/`，汇总卡在 `/scm-base/saleReport/`。都不在 `scm-goods` 下。

---

## 2. 读取

### 2.1 读取接口总表

| # | 接口 | 用途 | 业务参数 |
|---|---|---|---|
| R1 | `POST /scm-setting/flow/getFlowInfo` | 三指标趋势（按天/周/月） | `granularity`、`rangeFlag`（自定义加 `startTime`/`endTime`） |
| R2 | `POST /scm-base/saleReport/topExposureStat` | 三指标汇总卡 + 同比 | 无 |

> body 需带公共参数（`token`/`platform`/`version`/`ua`/`ex`/`lastBuildTime`），**`ex` = `StoreTraffic`**。

### 2.2 三指标趋势 R1 `getFlowInfo`

```json
{ "granularity": 1, "rangeFlag": 2 }
```

| 界面项 | 参数 | 取值 |
|---|---|---|
| 统计方式 | `granularity` | `1` 按天 / `2` 按周 / `3` 按月 |
| 时间周期 | `rangeFlag` | `1` 近 8 天 / `2` 近 30 天 / `3` 近 3 个月 / `4` 自定义 |
| 自定义起止 | `startTime` / `endTime` | **仅 `rangeFlag=4` 时传**，纯日期 `"YYYY-MM-DD"`（**不带时分**） |

**响应** `data` 含三条趋势列表，每条为 `[{ key, num, numAvrg }]`：

| 字段 | 含义 | 对应 UI 指标 |
|---|---|---|
| `storeVisitList` | 店铺访客数趋势 | 店铺访客数 |
| `wsDetailVisitList` | 店铺详情点击数趋势 | 详情点击数 |
| `exposureList` | 活动曝光数趋势 | 活动曝光数 |

- `num`：当期数值
- `numAvrg`：对比基准值（图上灰线），非当期
- `key`：时间标签，**格式随粒度变化**：

| `granularity` | `key` 格式 | 实测样例 |
|---|---|---|
| `1` 按天 | **`YYYYMMDD`（8 位，无分隔）** | `"20261014"` |
| `2` 按周 | `YYYYWW`（年 + 周序号） | `"202642"` |
| `3` 按月 | `YYYYMM`（预期格式，**未实采**） | `"202611"`（参考文档示例） |

> ⚠️ 历史参考文档的按天示例曾写成 `"2026-11-06"`（带横线），**与实测不符**——实测返回 `"20261014"`。**以本文 `YYYYMMDD` 为准**（不要照抄带横线格式）。

**实测行数**：`rangeFlag=2`（近 30 天）+ `granularity=1` → 每条 **30 行**；`granularity=2` → 5 行（约 5 周）。

### 2.3 三指标汇总卡 R2 `topExposureStat`

```json
{}   // 仅公共参数
```

| 字段 | 含义 |
|---|---|
| `exposureNum` | 活动曝光数（当期） |
| `exposureNumSame` | 对比期曝光数 |
| `exposureUpRatio` | 曝光变化率（`-0.07` = -7%） |
| `detailClickNum` | 详情点击数（当期） |
| `detailClickNumSame` | 对比期点击数 |
| `detailClickNumUpRatio` | 点击变化率（`14.24` = +1424%） |
| `visitNums` | 店铺访客数（当期） |
| `visitNumsSame` | 对比期访客数 |
| `visitNumsUpRatio` | 访客变化率（`0.33` = +33%） |

> `*Ratio` 是**小数比率**（`0.33` = 33%），不是百分数；展示时 ×100 加 `%`。
> 与 R1 的关系：R2 给**汇总 + 同比**（不吃粒度/时间参数，返回固定口径），R1 给**时间趋势**。要"完整视图"两个都要调。

---

## 3. 导出（**无服务端接口**）

- 界面按钮文本是「**下载数据**」，不是「导出」。
- 点击后前端用**已加载的 `getFlowInfo` 数据**通过 SheetJS 等本地生成 xlsx（blob 下载，文件名「店铺流量.xlsx」），**不触发任何网络导出请求**。
- 因此：**不要去找 `exportXxx` 端点**（本子板块没有）。

**自动化落盘的正确做法**（三选一）：

1. 调 `getFlowInfo` 拿三列表 → 自行写 xlsx（推荐，与界面数据同源）；
2. 浏览器会话内调完再点「下载数据」，走前端 blob（需接管下载）；
3. 若只清"是否有服务端导出"，答案是**没有**。

```python
# 结构示例：三列表按 key 对齐后落盘
# rows[i] = {"时间": key, "店铺访客数": storeVisitList[i].num,
#            "详情点击数": wsDetailVisitList[i].num, "活动曝光数": exposureList[i].num}
```

---

## 4. 枚举

| 项 | 取值 |
|---|---|
| `granularity` | `1` 按天 / `2` 按周 / `3` 按月 |
| `rangeFlag` | `1` 近 8 天 / `2` 近 30 天 / `3` 近 3 个月 / `4` 自定义 |
| 自定义时间 | `startTime`/`endTime` = `"YYYY-MM-DD"`（**纯日期，不带时分**） |
| `key` | 天 `YYYYMMDD` / 周 `YYYYWW` / 月 `YYYYMM` |
| `ex` | `StoreTraffic` |

---

## 5. 已知坑与待确认

1. **两个接口两套前缀**：`/scm-setting/flow/getFlowInfo` 与 `/scm-base/saleReport/topExposureStat`——搜不到 `scm-goods` 版本。
2. **自定义时间必须是纯日期**：`startTime`/`endTime` 传 `"2026-11-06 00:00:00"`（带时分）→ `40002 店铺流量获取失败`；且必须配 `rangeFlag=4`。
3. **`key` 按天是 8 位无分隔**（`20261014`），不是 `2026-10-14`。
4. **`numAvrg` 是对比基准**，不是当期值；做求和/画柱状图时别把它算进去。
5. **`*Ratio` 是小数不是百分数**（`0.33` = 33%）。
6. **导出无接口**：不要找 `export*`；自动化请用 `getFlowInfo` 自行生成 xlsx。
7. **`topExposureStat` 不吃参数**：改统计方式/时间周期不会影响汇总卡（它返回固定口径的当期+对比），只有趋势会变。
8. **同前缀的 `topOnsaleStat`/`topOrderStat` 不属于本子板块**（分别对应在售/订单看板），已在 `modules/data/__init__.py` 登记但无参数文档；如需使用另行抓包。
9. **未实测组合**：本次只验证了 `rangeFlag=2` × `granularity=1/2`（30 天 / 5 周）。`rangeFlag=1/3`（近 8 天 / 近 3 月）与 `granularity=3`（按月）的**行数与 `key` 形态未实采**，首次调用先打印首行确认格式（按预期：8 天→8 行、3 月→约 90 行或 3 行，视粒度）。
10. **`key` 不支持直接当日期解析**：按天是 `YYYYMMDD`（无 `-`），按周是 `YYYYWW`（不是 ISO 周，需按"年 + 第几周"理解），跨年周需注意（如 `202652` 与 `202601` 的边界）。
