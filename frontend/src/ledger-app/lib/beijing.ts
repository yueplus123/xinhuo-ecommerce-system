/** 北京时间 Asia/Shanghai，格式 YYYY-MM-DD HH:mm:ss（始终返回字符串，避免把 parts 对象渲染进 React） */
export function formatBeijing(d: Date = new Date()): string {
  try {
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Asia/Shanghai',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    }).formatToParts(d)
    const m: Record<string, string> = {}
    for (const p of parts) {
      if (p.type !== 'literal') m[p.type] = p.value
    }
    const y = m.year || '1970'
    const mo = m.month || '01'
    const day = m.day || '01'
    const h = m.hour || '00'
    const mi = m.minute || '00'
    const s = m.second || '00'
    return `${y}-${mo}-${day} ${h}:${mi}:${s}`
  } catch {
    return new Date().toISOString().slice(0, 19).replace('T', ' ')
  }
}
