import type { LedgerRow } from './api'

export type LedgerMonthAgg = { month: string; count: number; amount: number; profit: number }

export type DashboardStatsView = {
  ledgerThisMonthAmount: number
  ledgerThisMonthProfit: number
  ledgerByMonth: LedgerMonthAgg[]
}

/** 当前北京时间 YYYY-MM（月份固定两位，避免与记录解析不一致） */
export function beijingYearMonth(d = new Date()): string {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: 'numeric',
  }).formatToParts(d)
  const m: Record<string, string> = {}
  for (const p of parts) {
    if (p.type !== 'literal') m[p.type] = p.value
  }
  const y = m.year
  const mo = Number(m.month)
  if (!y || !Number.isFinite(mo) || mo < 1 || mo > 12) return '1970-01'
  return `${y}-${String(mo).padStart(2, '0')}`
}

/** 从 recordAt 取 YYYY-MM；支持 2026-05-13、2026/5/3 等；无法解析则 null */
export function recordAtToYearMonth(s: string | null | undefined): string | null {
  if (typeof s !== 'string') return null
  const t = s.trim()
  const match = t.match(/^(\d{4})[-/](\d{1,2})\b/)
  if (!match) return null
  const mo = Number(match[2])
  if (!Number.isFinite(mo) || mo < 1 || mo > 12) return null
  return `${match[1]}-${String(mo).padStart(2, '0')}`
}

/** 基于原始记账列表聚合（不依赖 /api/stats 版本） */
export function computeDashboardStats(ledger: LedgerRow[]): DashboardStatsView {
  const thisYm = beijingYearMonth()

  let ledgerThisMonthAmount = 0
  let ledgerThisMonthProfit = 0
  const ledgerMonthMap = new Map<string, { count: number; amount: number; profit: number }>()

  for (const r of ledger) {
    const ym = recordAtToYearMonth(r.recordAt)
    const amt = Number(r.amount) || 0
    const prof = Number(r.profit) || 0
    if (ym === thisYm) {
      ledgerThisMonthAmount += amt
      ledgerThisMonthProfit += prof
    }
    if (ym) {
      const o = ledgerMonthMap.get(ym) || { count: 0, amount: 0, profit: 0 }
      o.count += 1
      o.amount += amt
      o.profit += prof
      ledgerMonthMap.set(ym, o)
    }
  }

  const ledgerByMonth = [...ledgerMonthMap.entries()]
    .map(([month, v]) => ({ month, ...v }))
    .sort((a, b) => a.month.localeCompare(b.month))

  return {
    ledgerThisMonthAmount,
    ledgerThisMonthProfit,
    ledgerByMonth,
  }
}
