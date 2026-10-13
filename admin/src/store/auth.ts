import { defineStore } from 'pinia'
import api, { requestToken } from '@/api/client'
import { clearAuth, getAccess, isSessionExpired, saveTokens } from '@/utils/auth'

export interface Me {
  id: number
  username: string
  is_superuser: boolean
  [k: string]: any
}

export const useAuthStore = defineStore('auth', {
  state: () => ({ me: null as Me | null, loaded: false }),
  getters: {
    isSuperuser: (s) => !!s.me?.is_superuser
  },
  actions: {
    /** 登录；只有超级管理员才能进入后台，其余账号立刻登出并报错 */
    async login(username: string, password: string) {
      const t = await requestToken(username.trim(), password)
      saveTokens(t.access, t.refresh)
      await this.fetchMe()
      if (!this.me?.is_superuser) {
        this.logout()
        throw new Error('该账号不是超级管理员，无法进入管理后台')
      }
    },
    async fetchMe() {
      if (isSessionExpired() || !getAccess()) {
        clearAuth()
        this.me = null
        this.loaded = true
        return
      }
      try {
        this.me = (await api.get<Me>('/auth/me/')).data
      } catch (e: any) {
        const st = e?.response?.status
        if (st === 401 || st === 403) {
          clearAuth()
          this.me = null
        }
      } finally {
        this.loaded = true
      }
    },
    logout() {
      clearAuth()
      this.me = null
      this.loaded = true
    }
  }
})
