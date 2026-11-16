"""资金板块（待开发）。

状态：todo —— 仅采集到端点清单，参数未实现。
实现方式见 modules/goods/__init__.py 的结构。
"""

NAME = "资金"
STATUS = "todo"
GUIDE = "modules/finance/GUIDE.md"

ENDPOINTS = [
    "/provider.php/Admin/PinganAcc/index2",
    "/provider.php/Admin/PinganAcc/unbindBankcard",
    "/provider.php/Admin/PinganAcc/unbindBankcardV2",
    "/scm-base/creditpay/getAccountInfo",
    "/scm-base/creditpay/getApplyLoanInfo",
    "/scm-base/creditpay/getCreditApplyInfo",
    "/scm-base/creditpay/getCreditpayIntroductionJdhProv",
    "/scm-base/creditpay/getCreditpayIntroductionLklProv",
    "/scm-base/creditpay/getJdhProvCreditpayApply",
    "/scm-base/creditpay/getLaKaLaProviderLoanContract",
    "/scm-base/creditpay/getProviderCapitalType",
    "/scm-base/creditpay/getProviderCreditpayStatus",
    "/scm-base/creditpay/getPublicAccountInfo",
    "/scm-base/creditpay/providerCreditpay/applyLoan",
    "/scm-base/creditpay/providerCreditpay/getCreditApplyUrl",
    "/scm-base/creditpay/providerCreditpay/repaymentByProvider",
    "/scm-base/creditpay/repaymentInfo",
    "/scm-base/electronicwallet/bindCardCheckAmount",
    "/scm-base/electronicwallet/electronicWalletBindCard",
    "/scm-base/electronicwallet/exportElectronicWalletLog",
    "/scm-base/electronicwallet/getAccountInfo",
    "/scm-base/electronicwallet/getCreditpayAdvInfo",
    "/scm-base/electronicwallet/getElectronicReceipt",
    "/scm-base/electronicwallet/getElectronicWalletLogPage",
    "/scm-base/electronicwallet/getElectronicWalletStatus",
    "/scm-base/electronicwallet/getProviderPapersInfo",
    "/scm-base/electronicwallet/getTransactionDetailList",
    "/scm-base/electronicwallet/hasBindPinganAccount",
    "/scm-base/electronicwallet/openElectronicWallet",
    "/scm-base/electronicwallet/rechargePinganAccount",
    "/scm-base/electronicwallet/unbindBankCard",
    "/scm-base/electronicwallet/uploadFile",
    "/scm-base/electronicwallet/withdraw",

]
