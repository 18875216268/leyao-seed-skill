# 客户（customer）

> 状态：🟡 **开放部分**（接口文档已交付、可按文档直接取数；CLI 暂未开放，`customer.query` 返回 `MODULE_TODO`）｜ 已知端点 **26** 个
> 接口文档：`references/客户/sy.md`（客户列表 / 控销组 / 黑名单，已实测）｜ 直连用 `python scm.py call`（`AGENT_GUIDE.md §4.1`）

## 1. 说明

- 客户列表 / 控销组 / 黑名单：接口、参数、字段见 `references/客户/`（CLI 未开放；**只读查询**按文档直连即可，**写操作**须按 `AGENT_GUIDE.md §10` 授权）。
- 下列 26 个端点为 **IM/在线客服**（`/scm-setting/customer/*`），与上述三块业务不同，仅登记，未实现。

## 2. 已知端点（26）

| # | 路径 |
|---|---|
| 1 | `/provider.php/Admin/Chat/consultWebSocket` |
| 2 | `/scm-setting/customer/banword` |
| 3 | `/scm-setting/customer/chatDetailChart` |
| 4 | `/scm-setting/customer/chatUserStorePurchaseInfo` |
| 5 | `/scm-setting/customer/chooseNeedToChatUser` |
| 6 | `/scm-setting/customer/consultWebSocket` |
| 7 | `/scm-setting/customer/doSomethingAfterServerAck` |
| 8 | `/scm-setting/customer/getAccount` |
| 9 | `/scm-setting/customer/getAllcontactsList` |
| 10 | `/scm-setting/customer/getAllcontactsListDB` |
| 11 | `/scm-setting/customer/getAllcontactsListNoReply` |
| 12 | `/scm-setting/customer/getCity` |
| 13 | `/scm-setting/customer/getLastMessage` |
| 14 | `/scm-setting/customer/getListUserInfo` |
| 15 | `/scm-setting/customer/getMessageList` |
| 16 | `/scm-setting/customer/getNewMessageNum` |
| 17 | `/scm-setting/customer/getNewMessageNumBatch` |
| 18 | `/scm-setting/customer/getOneUserInfo` |
| 19 | `/scm-setting/customer/getReadTime` |
| 20 | `/scm-setting/customer/getRoomUser` |
| 21 | `/scm-setting/customer/getThirtyData` |
| 22 | `/scm-setting/customer/getTime` |
| 23 | `/scm-setting/customer/indexJava` |
| 24 | `/scm-setting/customer/refreshWebSocketToken` |
| 25 | `/scm-setting/customer/searchChatUserInfoByNickName` |
| 26 | `/scm-setting/customer/sendMsgCheck` |

## 3. 参考

- `references/附录/接口总表.md`（全量端点索引）
