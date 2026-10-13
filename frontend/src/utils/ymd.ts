// 提醒 / 续费类页面共用的「日期（YYYY-MM-DD）」工具。
// 「今天」统一按北京时间（与后端 TIME_ZONE=Asia/Shanghai 一致），不依赖浏览器本地时区。
const pad2 = (n: number) => String(n).padStart(2, '0')

/** 北京时间今天 YYYY-MM-DD */
export function todayYmd(): string {
  const m: Record<string, string> = {}
  for (const p of new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }).formatToParts(new Date())) {
    if (p.type !== 'literal') m[p.type] = p.value
  }
  return `${m.year}-${m.month}-${m.day}`
}

/** 取 ISO / 日期时间字符串里的 YYYY-MM-DD，取不到返回空串 */
export function isoToDateOnly(iso: string | null | undefined): string {
  const m = String(iso ?? '').match(/^(\d{4}-\d{2}-\d{2})/)
  return m ? m[1] : ''
}

/** YYYY-MM-DD → [年, 月, 日]；非法返回 null */
export function parseYmd(s: string | null | undefined): [number, number, number] | null {
  const ymd = isoToDateOnly(s)
  if (!ymd) return null
  const [y, m, d] = ymd.split('-').map(Number)
  if (!y || m < 1 || m > 12 || d < 1 || d > 31) return null
  return [y, m, d]
}

/** 与北京时间今天相差的天数（负数=已过期）；日期非法返回 null。用 UTC 毫秒做差，避开夏令时和本地时区。 */
export function daysFromToday(ymdOrIso: string | null | undefined): number | null {
  const t = parseYmd(ymdOrIso)
  const n = parseYmd(todayYmd())
  if (!t || !n) return null
  return Math.round((Date.UTC(t[0], t[1] - 1, t[2]) - Date.UTC(n[0], n[1] - 1, n[2])) / 86400000)
}

/** 日期加 N 个月；目标月没有该日时落到当月最后一天（1/31 + 1 月 = 2/28，而不是 3/3） */
export function addMonthsYmd(ymd: string, months: number): string {
  const p = parseYmd(ymd)
  if (!p) return ''
  const total = p[0] * 12 + (p[1] - 1) + months
  const y = Math.floor(total / 12)
  const m = (total % 12) + 1
  const lastDay = new Date(Date.UTC(y, m, 0)).getUTCDate()
  return `${y}-${pad2(m)}-${pad2(Math.min(p[2], lastDay))}`
}
