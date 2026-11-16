# 示例 2：查某商品的活动链接

**用户说法**：「查一下来曲唑在售的活动」

```bash
python scm.py scene ljgl find --drug 来曲唑
```

**返回（节选）**：按商品编码分组，进行中优先。

```json
{"ok": true, "candidates": [
  {"wholesaleId": 223640346, "wholesaleType": 1, "statusName": "进行中",
   "provDrugCode": "SP0000001", "drugName": "示例商品 200mg*28片",
   "unitPrice": "83.99", "activityCount": 2, "alsoIds": [252710684]}
], "hint": ""}
```

> 候选 >10 时会给出 `hint`，建议改用国药准字 / 商品编码 / 规格精确查询。
