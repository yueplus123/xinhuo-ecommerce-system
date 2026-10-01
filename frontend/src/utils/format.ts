/** 把 DRF 错误响应体整理成一句可展示的中文提示 */
export function formatApiErrorData(data: any, fallback: string): string {
  if (data == null) return fallback
  if (typeof data === 'string') return data
  if (typeof data.detail === 'string') return data.detail
  if (Array.isArray(data.detail)) return data.detail.map(String).join('；') || fallback
  if (typeof data === 'object') {
    const parts: string[] = []
    for (const [k, v] of Object.entries(data)) {
      if (k === 'detail') continue
      const msg = Array.isArray(v) ? v.map(String).join('；') : String(v)
      if (msg) parts.push(msg)
    }
    if (parts.length) return parts.join('；')
  }
  return fallback
}

export function formatRequestError(e: any, fallback: string): string {
  const fromData = formatApiErrorData(e?.response?.data, '')
  if (fromData) return fromData
  if (e?.message) return String(e.message)
  return fallback
}

function formatBeijingDateTime(iso: string, withSeconds: boolean): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso)
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    ...(withSeconds ? { second: '2-digit' as const } : {}),
    hour12: false
  })
    .format(d)
    .replace(/\//g, '-')
}

/** 北京时间 YYYY-MM-DD HH:mm */
export const formatDateTime = (iso: string) => formatBeijingDateTime(iso, false)

/** 北京时间 YYYY-MM-DD HH:mm:ss */
export const formatDateTimeSeconds = (iso: string) => formatBeijingDateTime(iso, true)
