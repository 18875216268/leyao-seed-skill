# 导出任务服务（API）

> 前置：`api_认证与公共约定.md`（公共参数、`provideridm`、错误码）
> 适用：**所有板块的导出**。本文件只负责"任务与文件"；**筛选条件与提交接口由各板块自己负责**。

## 1. 职责边界

| 层 | 负责 | 不负责 |
|---|---|---|
| 通用（本文件） | 导出列表、任务轮询、下载、中断 | 筛选参数、导出哪些数据 |
| 板块（各子板块文档） | 前置筛选 + 提交导出任务 | 轮询与下载 |

> 关键：`getExportTaskRecord` 不参与任何筛选；同一份导出列表汇总全系统所有板块的任务。

## 2. 接口总表

| # | 功能 | 方法 | 路径 | 必需参数 | 可选参数 | 返回要点 |
|---|---|---|---|---|---|---|
| 1 | 导出列表 / 轮询 | POST | `/export-file/file/getExportTaskRecord/v100` | `pageNo` `pageSize` | — | `exportTaskRecordPageResult.results[]` |
| 2 | 中断任务 | POST | `/export-file/file/interruptTask/v100` | `recordId` | — | 操作结果 |
| 3 | 下载文件 | GET | `{qiniuUrl}` | — | — | CSV（GBK） |

> 旧版入口：`GET /provider.php/Admin/ApiRouter/exportOrderTask`（不建议使用）

## 3. 导出列表 / 轮询

### 3.1 请求参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `pageNo` | int | 是 | 页码，从 1 开始 |
| `pageSize` | int | 是 | 每页条数（实测 10 / 20 / 100 可用） |
| 公共参数 | — | 是 | 见`api_认证与公共约定.md`§3 |
| 请求头 `provideridm` | string | 是 | `md5(providerId)` |

### 3.2 返回结构

```json
{
  "code": "40001",
  "message": "获取导出记录成功",
  "data": {
    "exportTaskRecordPageResult": {
      "pageNo": 1, "pageSize": 10, "totalRecord": 56, "totalPage": 6,
      "results": [
        {
          "recordId": 7916087,
          "templateId": 468,
          "name": "活动信息",
          "status": 5,
          "statusStr": "已过期",
          "account": "自营账号",
          "owner": true,
          "fileName": null,
          "qiniuUrl": "",
          "stime": "2026-10-26 18:18:30"
        }
      ]
    }
  }
}
```

| 字段 | 说明 |
|---|---|
| `recordId` | 任务 ID，提交导出时返回，用于定位 |
| `name` | 导出模板名（如「活动信息」「订单明细」） |
| `templateId` | 模板 ID |
| `status` / `statusStr` | 任务状态，见 §4 |
| `qiniuUrl` | 完成后为下载地址（七牛） |
| `stime` | 提交时间 |

### 3.3 轮询建议（与 `core/export_task.py::wait_url()` 实现一致）

- 间隔 5 秒，**默认超时 900 秒（15 分钟）**——覆盖「`status=4` 约 10 分钟后转 3」的实测延迟；CLI 可用 `--poll-timeout <秒>` 调整；
- 按 `recordId` 精确匹配，避免拿到同名历史任务；
- 命中 `status == 3` 立即取 `qiniuUrl`；
- `status == 4` **继续轮询**（短暂态），连续超过 600 秒才判服务端持续异常；
- `status == 5` 立即失败（已过期属终态，等待无意义）；
- 任何失败都提示「勿重复提交」，避免触发 `40003` 限流。

## 4. 任务状态

| `status` | `statusStr` | 含义 | 处理 |
|---|---|---|---|
| 1 | 进行中 | 生成中 | 继续轮询 |
| 2 | 等待中 | 排队 | 继续轮询 |
| 3 | 已完成 | 成功 | 取 `qiniuUrl` 下载 |
| 4 | 异常 | 生成中可能出现**短暂异常态** | ⚠️ **不要立即判失败/重提**：2026-11-08 实测 5 个任务先显示 `status=4`，约 10 分钟后全部转为 `status=3 已完成` 并产出文件。实现按 §3.3 继续轮询（宽限 600 秒），超时后才报持续异常 |
| 5 | 已过期 | 文件已清理（终态） | 立即报 `EXPORT_EXPIRED`，重新提交 |

## 5. 下载

```
GET {qiniuUrl}
Header: Referer: https://scm.ysbang.cn/
```

| 项 | 说明 |
|---|---|
| 文件格式 | CSV |
| 编码 | **GBK**（读取时用 `gbk`，异常字符 `ignore`） |
| 列数 | 随账号配置动态变化（基础列 + 动态列），见对应板块文档 |

## 6. 中断任务

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `recordId` | int | 是 | 目标任务 |
| 公共参数 | — | 是 | — |

> 写操作，仅在需要取消长时间任务时使用。

## 7. 最小示例

```python
import hashlib, requests, time

BASE = "https://scm.ysbang.cn"
headers = {"provideridm": hashlib.md5(provider_id.encode()).hexdigest()}
def common(token):
    return {"token": token, "platform": "scm-admin", "version": "1.0.3",
            "ua": "Mozilla/5.0 Chrome 120", "ex": "goodsOnShelves",
            "lastBuildTime": "2026-11-01 12:00"}

def wait_url(token, record_id, max_try=60):
    for _ in range(max_try):
        time.sleep(5)
        p = common(token); p.update({"pageNo": 1, "pageSize": 20})
        r = requests.post(f"{BASE}/export-file/file/getExportTaskRecord/v100",
                          json=p, headers=headers).json()
        for t in (r.get("data", {}).get("exportTaskRecordPageResult", {}) or {}).get("results", []):
            if str(t.get("recordId")) == str(record_id):
                if t.get("status") == 3:
                    return t.get("qiniuUrl")
                if t.get("status") == 4:
                    raise RuntimeError("导出异常")
    raise TimeoutError("轮询超时")
```

## 8. 注意

- 导出**提交**接口的限流（`40003`）由各板块负责说明；本服务只读，基本不受限。
- 同一账号 10 分钟内提交次数有限，批量导出需间隔（实测 75 秒可连续 9 次）。
