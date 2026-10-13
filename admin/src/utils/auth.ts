// 管理后台自己的登录存储：键名带 admin_ 前缀，与职员端（access_token 等）互不覆盖
const ACCESS = 'admin_access_token'
const REFRESH = 'admin_refresh_token'
const EXPIRES = 'admin_session_expires_at'
export const SESSION_MAX_MS = 12 * 60 * 60 * 1000 // 与后端 SIMPLE_JWT 一致

export const getAccess = () => localStorage.getItem(ACCESS)
export const getRefresh = () => localStorage.getItem(REFRESH)
export const setAccess = (t: string) => localStorage.setItem(ACCESS, t)

export function saveTokens(access: string, refresh: string) {
  localStorage.setItem(ACCESS, access)
  localStorage.setItem(REFRESH, refresh)
  localStorage.setItem(EXPIRES, String(Date.now() + SESSION_MAX_MS))
}

export function clearAuth() {
  localStorage.removeItem(ACCESS)
  localStorage.removeItem(REFRESH)
  localStorage.removeItem(EXPIRES)
}

export function isSessionExpired() {
  const n = Number(localStorage.getItem(EXPIRES))
  return Number.isFinite(n) && n > 0 && Date.now() >= n
}
