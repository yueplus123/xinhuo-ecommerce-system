import api from './client'

type Id = string | number | null

export const listSubscriptionPlatformOptions = () => api.get('/subscription-platform-options/')
export const listSubscriptionReminders = (params?: Recordable) =>
  api.get('/subscription-reminders/', { params })
export const createSubscriptionReminder = (body: Recordable) =>
  api.post('/subscription-reminders/', body)
export const updateSubscriptionReminder = (id: Id, body: Recordable) =>
  api.patch(`/subscription-reminders/${id}/`, body)
export const markSubscriptionRenewed = (id: Id, body: Recordable) =>
  api.post(`/subscription-reminders/${id}/mark-renewed/`, body)
export const deleteSubscriptionReminder = (id: Id) => api.delete(`/subscription-reminders/${id}/`)
