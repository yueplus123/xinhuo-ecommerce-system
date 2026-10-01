/** 记账数据在薪火侧变更后通知（如数据大屏刷新），不回传机器人。 */
export const LEDGER_UPDATED_EVENT = 'xinhuo-ledger-updated'

export function notifyLedgerUpdated() {
  window.dispatchEvent(new CustomEvent(LEDGER_UPDATED_EVENT))
}

/** 钱包余额变更后通知数据大屏刷新曲线。 */
export const WALLET_UPDATED_EVENT = 'xinhuo-wallet-updated'

export function notifyWalletUpdated() {
  window.dispatchEvent(new CustomEvent(WALLET_UPDATED_EVENT))
}
