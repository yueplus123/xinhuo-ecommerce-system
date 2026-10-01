import { defineStore } from 'pinia'
import { requestAccessToken } from '@/api/xinhuo/client'
import { fetchMe } from '@/api/xinhuo/auth'
import { clearAuthStorage, isSessionExpired, markSessionExpiry } from '@/auth/session'

export type XinhuoMe = {
  id?: number
  username?: string
  is_boss?: boolean
  is_ceo?: boolean
  is_guest?: boolean
  is_superuser?: boolean
  [key: string]: any
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export const useXinhuoAuthStore = defineStore('xinhuoAuth', {
  state: () => ({
    me: null as XinhuoMe | null,
    loaded: false
  }),
  getters: {
    isAuthenticated: (state) => !!state.me,
    isBoss: (state) => !!state.me?.is_boss,
    isCeo: (state) => !!state.me?.is_ceo,
    isGuest: (state) => !!state.me?.is_guest,
    isSuperuser: (state) => !!state.me?.is_superuser
  },
  actions: {
    async login(username: string, password: string) {
      // 先拿新 token，再覆盖本地，避免重复点击时把第一次成功的 token 清掉
      const data = await requestAccessToken(username, password)
      localStorage.setItem('access_token', data.access)
      localStorage.setItem('refresh_token', data.refresh)
      markSessionExpiry()
      this.me = null

      for (let attempt = 0; attempt < 3; attempt++) {
        await this.fetchMe()
        if (this.me) return
        await sleep(200 * (attempt + 1))
      }

      this.me = { username: String(username || '').trim() }
      this.loaded = true
      void this.fetchMe()
    },
    async fetchMe() {
      if (isSessionExpired()) {
        clearAuthStorage()
        this.me = null
        this.loaded = true
        return
      }
      if (!localStorage.getItem('access_token')) {
        this.me = null
        this.loaded = true
        return
      }
      try {
        const { data } = await fetchMe()
        this.me = data
      } catch (e: any) {
        const st = e.response?.status
        if (st === 401 || st === 403) {
          clearAuthStorage()
          this.me = null
        }
        // 网络抖动：保留现有 me / token，不清空
      } finally {
        this.loaded = true
      }
    },
    logout() {
      clearAuthStorage()
      this.me = null
      this.loaded = true
    }
  }
})
