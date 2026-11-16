# 示例 1：给药店做一条订单链接

**用户说法**：「给药店 3573654 做一条诺欣妥的订单链接，价格 86，库存 1500」

```bash
python scm.py scene ljgl find --store 3573654 --drug 国药准字HJ20170364
python scm.py scene ljgl create --store 3573654 --drug 国药准字HJ20170364 \
       --source <选中的活动ID> --price 86 --stock 1500 --confirm
```

**返回（节选）**

```json
{
  "ok": true, "new_wholesaleId": 1457544853, "group": 169282,
  "link": "https://dian.ysbang.cn/#/drugInfo?wholesaleid=...&scene=1&trafficType=1",
  "ws_desc": "WorkBuddy做单链接，2026/11/13后可下架。",
  "verify": {"unitPrice": "86.00", "unitPrice9": "80.00", "stockAvailable": 1500, "status": 0}
}
```

> 未加 `--confirm` 时只输出 dry-run 摘要（`payload_keys`、时间、商圈），不产生任何写操作。
