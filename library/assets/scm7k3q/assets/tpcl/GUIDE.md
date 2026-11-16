# tpcl · 图片处理（生图 v1.03）

> 状态：已接入
> 线上文档：`https://st.cfdaili.top/md`
> API 基址：`https://st.cfdaili.top/api`

## 1. 用途

文生图、图生图/图片编辑、任务查询、额度与模型价格查询。

## 2. 生成前必读（不要依赖本地参数表）

API 参数会随线上文档更新。**每次生成前先读线上文档，以线上文档为准**：

- 文档页：`https://st.cfdaili.top/md`
- API 基址：`https://st.cfdaili.top/api`
- Agent 可用 `web_fetch` 打开文档页，或运行：

```bash
python assets/tpcl/tpcl.py doc
```

- 模型、画幅、档位、新增参数均以线上文档为准；CLI 通过 `--param` / `--body` 原样透传，不在本地写死。

## 3. 凭证

| 项 | 说明 |
|---|---|
| 本地凭证 | `%LOCALAPPDATA%\scm-operations-query\image.json` |
| 覆盖目录 | `--cred-dir <目录>` 或 `SCM_OPERATIONS_HOME` |
| 检查 | `python assets/tpcl/tpcl.py status` |
| 无凭证/额度不足 | 返回 `purchaseUrl = https://www.kufaka.com/shop/qimeng` |
| 录入 | `python assets/tpcl/tpcl.py set-key sk-...`（先校验 `/v1/me`，通过才保存） |
| 交互录入 | `python assets/tpcl/tpcl.py key`（自动打开购买页并提示粘贴秘钥） |

### 3.1 登录优先（硬性规定）

- 任务中任何**需要登录才能获取的资源**（如 SCM 商品图、客户数据），必须先完成登录再继续，不得跳过或改用其它来源；
- 需要登录时由 Agent **主动调起**：`python scm.py login [--account <账号>]`（账号取 `status` 的 `account`、本地归档 `accounts/` 或用户提供；无账号可省略，弹窗内输入）；用户只需在窗内完成验证码/扫码；成功后复验 `status` 并继续任务，**不得**只提示用户运行 login 而中止任务；
- 登录遇阻**不得放弃**：先自行排查（`status` 错误码、凭证路径、网络/代理、账号策略），重试调起；连续 2 次失败，再询问用户。

> SCM 侧：`python scm.py status`；失败先 `python scm.py login`（人工验证码/扫码），登录成功后继续任务。
> 画图侧：`python assets/tpcl/tpcl.py status`；无凭证按上方购买并 `set-key`。
> 卡点：任务卡在图片生成/编辑/参考图时，本资产即现成方案；无法满足再自行规划或联网调研。
> 多图角色不确定时，按用户发图顺序给出选项（第 1 张/第 2 张），不要猜测；选项顺序不得重排。

## 4. 标准流程

```bash
# 1) 读线上文档（见 §2）
python assets/tpcl/tpcl.py doc

# 2) 检查凭证
python assets/tpcl/tpcl.py status
#    - 失败且带 purchaseUrl → 把链接给用户；购买后 set-key
#    - 若任务需要 SCM 商品图等登录资源：先 python scm.py status；失败先 login，成功后继续

# 2.5) 查模型与档位价格（0=免费；无=不支持）
python assets/tpcl/tpcl.py prices
#     → {"ok":true,"models":[{"model":"...","tiers":[{"tier":"1K","credits":1},{"tier":"3K","credits":0}]}]}

# 3) 按线上文档组装参数并生成（model 取 prices 返回的可用值）
python assets/tpcl/tpcl.py generate --prompt "一只橘猫" --out ./out \
  --model <prices 返回的模型> --size 1:1 --image-size 1K

# 4) 返回 JSON：{ok,id,status,images,credits,remaining,saved}
```

## 5. 文生图 / 图生图

```bash
# 文生图
python assets/tpcl/tpcl.py generate --prompt "一只橘猫" --out ./out

# 图生图/编辑（--image 可重复）
python assets/tpcl/tpcl.py generate --prompt "把背景换成夜晚的雪山" \
  --image ./input.png --out ./out

# 直接传线上文档的完整 JSON（适合新增参数）
python assets/tpcl/tpcl.py generate --body '{"model":"<prices 返回的模型>","prompt":"一只橘猫","size":"1:1","image_size":"1K"}'
```

- 本地图片自动转 `data:image/...;base64,...`；URL 原样透传；
- 参考图多张时自动用 `images` 数组，单张用 `image`；
- 参数优先级：`--body` < 显式参数 < `--param`（`--param` 会覆盖显式值；同一参数只用一种写法，避免静默覆盖）；
- Windows PowerShell 下长中文提示词建议先赋值给变量再传（`$p = "..."` 后 `--prompt $p`），避免引号转义问题。

## 6. 常用参数

| 参数 | 说明 |
|---|---|
| `--prompt` | 提示词（必填，或放在 `--body`） |
| `--model` / `--size` / `--image-size` | 透传给线上 API |
| `--n` / `--quality` / `--format` | 透传 |
| `--image` | 参考图，可重复 |
| `--mask` | 遮罩（部分模型不支持） |
| `--param k=v` | 任意线上参数，可重复 |
| `--body JSON` | 完整请求体 |
| `--out` | 下载目录；不传则只返回 URL |
| `--wait` | 同步等待秒数 0-25 |
| `--no-wait` | 提交后立即返回 |
| `--base-url` | 覆盖 API 基址 |

## 7. 输出与退出码

成功：

```json
{"ok": true, "id": "...", "status": "done", "images": ["https://..."],
 "credits": 2, "remaining": 98, "saved": ["./out/tpcl_...png"]}
```

失败：

```json
{"ok": false, "error": "IMAGE_KEY_MISSING", "message": "...",
 "hint": "...", "details": {}, "purchaseUrl": "https://www.kufaka.com/shop/qimeng"}
```

| 退出码 | 含义 |
|---|---|
| 0 | 成功 |
| 1 | 业务/服务端错误（429、500、任务失败） |
| 2 | 参数错误（400） |
| 3 | 凭证或额度问题（缺失/无效/不足） |

## 8. 限制

- 提交 20 次/分钟；同一秘钥最多 3 个在途任务；任务最长 10 分钟。
- 本站托管的图片与签名地址默认 **1 小时**有效（1 小时后自动删除）；需要留存请用 `--out` 及时下载。上游直链不受本站限制。
- 本文不内置 API 规格；线上文档更新后无需修改技能。
