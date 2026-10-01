/** 嵌入薪火前端 iframe 时为 true（?embed=1 或处于 iframe 内） */
export function isEmbedded(): boolean {
  if (typeof window === 'undefined') return false
  const q = new URLSearchParams(window.location.search)
  if (q.get('embed') === '1') return true
  try {
    return window.self !== window.top
  } catch {
    return true
  }
}
