import api from '@/api/client'

// 薪火卡管家（汇通卡 Chrome 插件）权限：每个职员能看哪些备注关键词的卡（仅超级管理员）
export interface CardScopeRow {
  id: number
  username: string
  is_admin: boolean // 超级管理员 / 老板 / CEO：插件里能看全部，不用设关键词
  keywords: string[]
  updated_at: string | null
  updated_by: string
}

export const listCardScopes = () => api.get<{ results: CardScopeRow[] }>('/card-manager/scopes/')

export const saveCardScope = (userId: number, keywords: string[]) =>
  api.put<CardScopeRow>(`/card-manager/scopes/${userId}/`, { keywords })
