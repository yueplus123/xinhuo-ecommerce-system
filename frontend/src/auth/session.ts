/** 与后端 SIMPLE_JWT / SESSION_COOKIE_AGE 一致：登录后最多在线 12 小时 */
export const SESSION_MAX_MS = 12 * 60 * 60 * 1000

const EXPIRES_KEY = 'session_expires_at'

export function markSessionExpiry() {
  localStorage.setItem(EXPIRES_KEY, String(Date.now() + SESSION_MAX_MS))
}

export function clearSessionExpiry() {
  localStorage.removeItem(EXPIRES_KEY)
}

export function isSessionExpired() {
  const raw = localStorage.getItem(EXPIRES_KEY)
  if (!raw) return false
  const expires = Number(raw)
  return Number.isFinite(expires) && Date.now() >= expires
}

export function clearAuthStorage() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  clearSessionExpiry()
}
