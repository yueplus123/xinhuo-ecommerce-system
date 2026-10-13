// 记账模块的纯函数：北京时间、金额输入、展示与月度聚合
import type { LedgerRow } from '@/api/xinhuo/ledger'

/** 北京时间 YYYY-MM-DD HH:mm:ss */
export function formatBeijing(d: Date = new Date()): string {
  try {
    const m: Record<string, string> = {}
    for (const p of new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Asia/Shanghai',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    }).formatToParts(d)) {
      if (p.type !== 'literal') m[p.type] = p.value
    }
    return `${m.year}-${m.month}-${m.day} ${m.hour === '24' ? '00' : m.hour}:${m.minute}:${m.second}`
  } catch {
    return new Date().toISOString().slice(0, 19).replace('T', ' ')
  }
}

export function beijingYearMonth(d = new Date()): string {
  return formatBeijing(d).slice(0, 7)
}

/** 从 recordAt 取 YYYY-MM；支持 2026-05-13、2026/5/3；无法解析返回 null */
export function recordAtToYearMonth(s: string | null | undefined): string | null {
  const match = typeof s === 'string' ? s.trim().match(/^(\d{4})[-/](\d{1,2})\b/) : null
  if (!match) return null
  const mo = Number(match[2])
  return mo >= 1 && mo <= 12 ? `${match[1]}-${String(mo).padStart(2, '0')}` : null
}

export type LedgerMonthAgg = { month: string; count: number; amount: number; profit: number }

/** 基于记账全量记录按月聚合，并给出本月金额 / 利润 / 笔数 */
export function computeDashboardStats(ledger: LedgerRow[]) {
  const thisYm = beijingYearMonth()
  const map = new Map<string, LedgerMonthAgg>()
  for (const r of ledger) {
    const ym = recordAtToYearMonth(r.recordAt)
    if (!ym) continue
    const o = map.get(ym) || { month: ym, count: 0, amount: 0, profit: 0 }
    o.count += 1
    o.amount += Number(r.amount) || 0
    o.profit += Number(r.profit) || 0
    map.set(ym, o)
  }
  const byMonth = [...map.values()].sort((a, b) => a.month.localeCompare(b.month))
  const cur = map.get(thisYm)
  return {
    byMonth,
    thisMonthAmount: cur?.amount ?? 0,
    thisMonthProfit: cur?.profit ?? 0,
    thisMonthCount: cur?.count ?? 0
  }
}

/** 列表展示：项目名（一级 + 二级） */
export function formatLedgerBusinessLine(
  r: Pick<LedgerRow, 'projectName' | 'businessName' | 'optionLabel'>
) {
  return r.projectName || [r.businessName, r.optionLabel].filter(Boolean).join(' ')
}

export function isLedgerUnsettled(r: Pick<LedgerRow, 'status' | 'settledAt'>) {
  if (r.status === 'REVERSED' || r.status === 'PROCESSED') return false
  if (r.status === 'ACTIVE') return true
  return !r.settledAt
}

/** Element Plus Tag 类型 */
export function ledgerStatusTagType(r: Pick<LedgerRow, 'statusLabel' | 'settledAt'>) {
  const label = r.statusLabel || (r.settledAt ? '已清账' : '未清账')
  if (label === '未清账') return 'warning'
  if (label === '已撤销') return 'info'
  return 'success'
}

export function digit(n: unknown, max = 2) {
  const x = Number(n)
  return (Number.isFinite(x) ? x : 0).toLocaleString('zh-CN', { maximumFractionDigits: max })
}

/** 钱包金额输入：全角转半角、仅数字与一个小数点、小数最多 2 位 */
export function sanitizeMoneyInput(raw: unknown): string {
  const cleaned = String(raw ?? '')
    .replace(/[\u200b-\u200d\ufeff]/g, '')
    .replace(/[\uFF10-\uFF19]/g, (ch) => String.fromCharCode(ch.charCodeAt(0) - 0xff10 + 0x30))
    .replace(/[^\d.]/g, '')
  const [int, ...rest] = cleaned.split('.')
  return rest.length ? `${int}.${rest.join('').slice(0, 2)}` : int
}

/** 失焦时格式化为两位小数；空或无效则清空 */
export function formatMoneyOnBlur(s: string): string {
  const t = sanitizeMoneyInput(s).trim()
  if (t === '' || t === '.') return ''
  const n = Number(t)
  return Number.isFinite(n) && n >= 0 ? n.toFixed(2) : ''
}

/** 提交用：非负，四舍五入到分 */
export function parseMoney(s: string): number {
  const n = Number(sanitizeMoneyInput(String(s).replace(/,/g, '')))
  return Number.isFinite(n) && n >= 0 ? Math.round(n * 100) / 100 : 0
}

/** 清账小票文本 */
export type ReceiptLine = {
  recordAt: string
  business: string
  amount: number
  give: number
  take: number
  profit: number
}

export function buildReceiptText(settledAt: string, lines: ReceiptLine[]) {
  const w = 32
  const row = (a: string, b = '') => `${a.padEnd(w)}${b}\n`
  const sum = (k: 'amount' | 'give' | 'take' | 'profit') => lines.reduce((a, r) => a + r[k], 0)
  let t = row('======== 记账 · 清账 ========') + row('【业务记账 清账凭证】') + row('-'.repeat(w))
  t += row('清账时间', settledAt) + row('本次笔数', `${lines.length} 笔`) + row('-'.repeat(w))
  lines.forEach((r, i) => {
    t += row(`#${i + 1}`, r.recordAt) + row('  业务', r.business)
    t += row(
      '  金额/给你/给我/利润',
      [r.amount, r.give, r.take, r.profit].map((n) => digit(n, 4)).join(' / ')
    )
    t += row('')
  })
  t += row('-'.repeat(w))
  t += row('合计 金额', digit(sum('amount'), 4)) + row('合计 给你', digit(sum('give'), 4))
  t += row('合计 给我', digit(sum('take'), 4)) + row('合计 利润', digit(sum('profit'), 4))
  t += row('='.repeat(w)) + row('感谢您的使用')
  return t.trimEnd()
}

/** 通知数据大屏刷新（记账 / 钱包变更后） */
export const LEDGER_UPDATED_EVENT = 'xinhuo-ledger-updated'
export const WALLET_UPDATED_EVENT = 'xinhuo-wallet-updated'
export const notifyLedgerUpdated = () => window.dispatchEvent(new CustomEvent(LEDGER_UPDATED_EVENT))
export const notifyWalletUpdated = () => window.dispatchEvent(new CustomEvent(WALLET_UPDATED_EVENT))
