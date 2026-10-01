import type { LedgerRow } from './api'

/** 列表展示：项目名（一级 + 二级） */
export function formatLedgerBusinessLine(
  r: Pick<LedgerRow, 'projectName' | 'businessName' | 'optionLabel'>,
) {
  if (r.projectName) return r.projectName
  return [r.businessName, r.optionLabel].filter(Boolean).join(' ')
}

export function isLedgerUnsettled(r: Pick<LedgerRow, 'status' | 'settledAt'>) {
  if (r.status === 'REVERSED') return false
  if (r.status === 'PROCESSED') return false
  if (r.status === 'ACTIVE') return true
  return !r.settledAt
}

export function ledgerStatusClass(r: Pick<LedgerRow, 'status' | 'statusLabel' | 'settledAt'>) {
  const label = r.statusLabel || (r.settledAt ? '已清账' : '未清账')
  if (label === '未清账') return 'status-unsettled'
  if (label === '已撤销') return 'status-reversed'
  return 'status-settled'
}
