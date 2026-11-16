# 示例 4：链接已创建，用户只改其中一项

`create` 是一气呵成的；建完后常见的「只改一项」需求，**用单项动作，不要重建**。

## 改库存

**用户说法**：「库存改成 3000」「别同步库存，给 3000」

```bash
python scm.py scene ljgl ws-stock --id 1458150813 --sync off --qty 3000 --confirm
```

## 改备注

**用户说法**：「备注写双十一特供」

```bash
python scm.py scene ljgl ws-desc --id 1458150813 --desc "双十一特供" --confirm
```

> 复验只能看 `wsList` 的 `wsDesc`（`getWholesale` 恒不返回该字段）。

## 改价（先出两个方案，不擅自改）

**用户说法**：「价格改成 88」「满 2 盒 88」

```bash
python scm.py scene ljgl reprice --id 1458150813 --price 88 --min-qty 2
```

返回 `need_choice: true` 与两个候选：

| 方案 | 效果 | 代价 |
|---|---|---|
| `plan=ladder` | 设阶梯价（满 N 件享目标价），**链接/二维码不变**、秒级生效 | 原价仍可单买；最多 2 档；仅自营 |
| `plan=rebuild` | 下架旧的，按新价复制一条 | **活动ID/链接/二维码都会变**，约 1~2 分钟 |

选定后执行：

```bash
python scm.py scene ljgl reprice --id 1458150813 --price 88 --min-qty 2 --plan ladder --confirm
```

## 改限购

**用户说法**：「每店最多 500」

```bash
python scm.py scene ljgl pms-limit --id 1458150813 --max-per-store 500 --confirm
```

## 改活动时间

**用户说法**：「活动延到后天」

```bash
python scm.py scene ljgl pms-time --id 1458150813 --end "2026-11-18 23:59:59" --confirm
```

> `end` 必须晚于 `begin`，否则本地直接 `PARAM_INVALID`（不发请求）。

## 加 / 删参与药店

**用户说法**：「这家店也加上」「把这家店从控销组去掉」

```bash
python scm.py scene ljgl group-add    --group 169342 --store 3573654 --confirm
python scm.py scene ljgl group-remove --group 169342 --store 3573654 --confirm
```

## 下架 / 重上架 / 结束

```bash
python scm.py scene ljgl off     --id 1458150813 --confirm
python scm.py scene ljgl restart --id 1458150813 --confirm
python scm.py scene ljgl end     --id 1458150813 --confirm   # 内部先下架再结束
```

## 定时下架（引导为主）

**用户说法**：「今晚 10 点自动下架」

```bash
python scm.py scene ljgl schedule --id 1458150813 --at "2026-11-16 22:00"
```

只输出 IDE `automation_update` 的参数（`scheduleType=once` / `scheduledAt` / `prompt`），
技能内**不起常驻进程**；到点由 Agent 执行 `off --confirm`。

> 所有写动作：不带 `--confirm` 只输出 `dry_run=true`；每次变更都会追加到台账 `link-records.jsonl`。
> 完整动作表见 `assets/ljgl/GUIDE.md §0`。
