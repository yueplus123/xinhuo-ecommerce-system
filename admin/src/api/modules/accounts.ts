import api from '@/api/client'

type Id = string | number

const BASE = '/manage/accounts'

export interface StaffUserRow {
  id: number
  username: string
  role: string
  role_label: string
  is_active: boolean
  last_login: string | null
  last_login_ip: string
}

export interface PaymentImage {
  kind: 'main' | 'extra'
  id: number | null
  url: string
}

export interface PaymentRecordRow {
  id: number
  user: number
  user_name: string
  channel: string
  channel_label: string
  order_count: number
  amount: string
  note: string
  record_date: string | null
  created_at: string | null
  images: PaymentImage[]
}

export interface ReminderRow {
  id: number
  user: number
  user_name: string
  wechat_label: string
  platform_name: string
  remark: string
  next_reminder_at: string | null
  last_renewed_at: string | null
  status: 'none' | 'overdue' | 'today' | 'pending'
  status_text: string
}

export interface AccountsOptions {
  staff_users: { id: number; username: string; is_active: boolean }[]
  all_staff_users: { id: number; username: string; is_active: boolean }[]
  channels: { value: string; label: string }[]
  roles: { value: string; label: string }[]
  platform_options: string[]
}

export const getAccountsOptions = () => api.get<AccountsOptions>(`${BASE}/options/`)

export const listManageUsers = () => api.get<StaffUserRow[]>(`${BASE}/users/`)
export const createManageUser = (body: Recordable) => api.post(`${BASE}/users/`, body)
export const updateManageUser = (id: Id, body: Recordable) => api.patch(`${BASE}/users/${id}/`, body)
export const deleteManageUser = (id: Id) => api.delete(`${BASE}/users/${id}/`)

export const listManagePayments = (params?: Recordable) =>
  api.get(`${BASE}/payment-records/`, { params })
export const createManagePayment = (body: FormData) => api.post(`${BASE}/payment-records/`, body)
export const updateManagePayment = (id: Id, body: FormData) =>
  api.patch(`${BASE}/payment-records/${id}/`, body)
export const deleteManagePayment = (id: Id) => api.delete(`${BASE}/payment-records/${id}/`)
export const exportManagePayments = (params?: Recordable) =>
  api.get(`${BASE}/payment-records/export/`, { params, responseType: 'blob' })

export const listManageReminders = (params?: Recordable) =>
  api.get(`${BASE}/subscription-reminders/`, { params })
export const createManageReminder = (body: Recordable) =>
  api.post(`${BASE}/subscription-reminders/`, body)
export const updateManageReminder = (id: Id, body: Recordable) =>
  api.patch(`${BASE}/subscription-reminders/${id}/`, body)
export const deleteManageReminder = (id: Id) => api.delete(`${BASE}/subscription-reminders/${id}/`)
