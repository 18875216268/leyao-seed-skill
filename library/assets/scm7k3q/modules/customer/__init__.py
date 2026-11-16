"""客户板块（待开发）。

状态：todo —— 仅采集到端点清单，参数未实现。
实现方式见 modules/goods/__init__.py 的结构。
"""

NAME = "客户"
STATUS = "todo"
GUIDE = "modules/customer/GUIDE.md"

ENDPOINTS = [
    "/provider.php/Admin/Chat/consultWebSocket",
    "/scm-setting/customer/banword",
    "/scm-setting/customer/chatDetailChart",
    "/scm-setting/customer/chatUserStorePurchaseInfo",
    "/scm-setting/customer/chooseNeedToChatUser",
    "/scm-setting/customer/consultWebSocket",
    "/scm-setting/customer/doSomethingAfterServerAck",
    "/scm-setting/customer/getAccount",
    "/scm-setting/customer/getAllcontactsList",
    "/scm-setting/customer/getAllcontactsListDB",
    "/scm-setting/customer/getAllcontactsListNoReply",
    "/scm-setting/customer/getCity",
    "/scm-setting/customer/getLastMessage",
    "/scm-setting/customer/getListUserInfo",
    "/scm-setting/customer/getMessageList",
    "/scm-setting/customer/getNewMessageNum",
    "/scm-setting/customer/getNewMessageNumBatch",
    "/scm-setting/customer/getOneUserInfo",
    "/scm-setting/customer/getReadTime",
    "/scm-setting/customer/getRoomUser",
    "/scm-setting/customer/getThirtyData",
    "/scm-setting/customer/getTime",
    "/scm-setting/customer/indexJava",
    "/scm-setting/customer/refreshWebSocketToken",
    "/scm-setting/customer/searchChatUserInfoByNickName",
    "/scm-setting/customer/sendMsgCheck",
    "/scm-setting/storetypeGroup/getStoretypeGroupListAct",
    "/scm-setting/storetypeGroup/getStoretypeGroupListCountAct",
    "/scm-setting/storetypeGroup/getNoSelectAndSelectStoreType",
    "/scm-setting/storetypeGroup/getSubType",
    "/scm-setting/storetypeGroup/addStoretypeGroupAct",
    "/scm-setting/storetypeGroup/updateStoretypeGroupName",
    "/scm-setting/storetypeGroup/setDefaultSg",

]
