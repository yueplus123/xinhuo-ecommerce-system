import api from './client'

type Id = string | number

export const batchDeleteWechatBotRecords = (ids: Id[]) =>
  api.post('/wechat-bot/records/batch-delete/', { ids })
export const listWechatBotEmployees = (table: string) =>
  api.get('/wechat-bot/employees/', { params: { table } })
export const listWechatBotRecords = (params: Recordable) =>
  api.get('/wechat-bot/records/', { params })
export const createWechatBotRecord = (body: Recordable) => api.post('/wechat-bot/records/', body)
export const updateWechatBotRecord = (id: Id, body: Recordable) =>
  api.patch(`/wechat-bot/records/${id}/`, body)
export const deleteWechatBotRecord = (id: Id) => api.delete(`/wechat-bot/records/${id}/`)
