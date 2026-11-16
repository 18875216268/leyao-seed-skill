# 示例 3：分析今日销售

**用户说法**：「帮我分析今日销售」

数据板块当前以**接口文档直连**为主（CLI 未封装），用 `call` 按 `references/数据/api_*.md` 取数：

```bash
python scm.py call --path /scm-data/... --param timeRange=... --out today.xlsx
```

**说明**

- 同步 xlsx/CSV 会直接落盘（`--out`），返回 `{kind:"file", path, bytes}`；
- 异步导出走 `createExportTask` + `getExportTaskRecord` 轮询（见 `references/数据/api_导出任务.md`）；
- 沙箱/无凭证环境下会返回 `AUTH_REQUIRED` + `login` 提示，不会崩溃。
