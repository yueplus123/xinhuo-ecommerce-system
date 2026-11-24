import api from '@/api/client'

// 邮件推送（QQ 邮箱 → 企微群），仅超级管理员。授权码只写不读：接口只返回 has_auth_code
export type MailPushStatus = 'pushed' | 'dry_run' | 'ignored' | 'excluded' | 'failed'
export type MailPushStyle = 'summary' | 'code' | 'title_only'

export interface MailPushSettings {
  webhook_url: string // 打码后的地址
  has_webhook: boolean
  dry_run: boolean
  poll_interval: number
  summary_chars: number
  exclude_senders: string[]
  exclude_keywords: string[]
  worker_alive: boolean
  worker_heartbeat_at: string | null
  last_round_at: string | null
  check_pending: boolean
}

export interface MailPushAccount {
  id: number
  name: string
  email: string
  has_auth_code: boolean
  enabled: boolean
  last_check_at: string | null
  last_ok: boolean | null
  last_error: string
  fail_count: number
  today: Partial<Record<MailPushStatus, number>>
}

export interface MailPushRule {
  id: number
  name: string
  senders: string[]
  subject_keywords: string[]
  style: MailPushStyle
  account_ids: number[]
  account_names: string[]
  enabled: boolean
  sort_order: number
  today_hits: number
}

export interface MailPushOverview {
  settings: MailPushSettings
  accounts: MailPushAccount[]
  rules: MailPushRule[]
  today: Partial<Record<MailPushStatus, number>>
  counts: Partial<Record<MailPushStatus, number>>
}

export interface MailPushRecord {
  id: number
  created_at: string
  account_id: number
  account_name: string
  status: MailPushStatus
  rule_name: string
  sender: string
  subject: string
  attempts: number
  error: string
}

export interface RuleInput {
  name: string
  senders: string
  subject_keywords: string
  style: MailPushStyle
  account_ids: number[]
  enabled?: boolean
}

export const getMailPush = () => api.get<MailPushOverview>('/mail-push/')
export const saveMailPushSettings = (data: Partial<Record<string, unknown>>) =>
  api.patch<MailPushOverview>('/mail-push/settings/', data)

export const createMailAccount = (data: { name: string; email: string; auth_code: string }) =>
  api.post<MailPushAccount>('/mail-push/accounts/', data)
export const updateMailAccount = (id: number, data: Partial<{ name: string; email: string; auth_code: string; enabled: boolean }>) =>
  api.patch<MailPushAccount>(`/mail-push/accounts/${id}/`, data)
export const deleteMailAccount = (id: number) => api.delete(`/mail-push/accounts/${id}/`)
export const testMailAccount = (data: { id?: number | null; email?: string; auth_code?: string }) =>
  api.post<{ ok: boolean; detail: string }>('/mail-push/accounts/test/', data)

export const createMailRule = (data: RuleInput) => api.post<MailPushRule>('/mail-push/rules/', data)
export const updateMailRule = (id: number, data: Partial<RuleInput>) => api.patch<MailPushRule>(`/mail-push/rules/${id}/`, data)
export const deleteMailRule = (id: number) => api.delete(`/mail-push/rules/${id}/`)
export const previewMailRule = (data: Partial<RuleInput>) => api.post<{ content: string }>('/mail-push/preview/', data)

export const listMailRecords = (params: { status?: string; q?: string; account?: string }) =>
  api.get<{ results: MailPushRecord[] }>('/mail-push/records/', { params })
export const retryMailRecord = (id: number) => api.post(`/mail-push/records/${id}/retry/`)
export const mailCheckNow = () => api.post('/mail-push/check-now/')
export const mailTestPush = () => api.post('/mail-push/test-push/')
