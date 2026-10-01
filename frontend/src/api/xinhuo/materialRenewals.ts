import api from './client'

type Id = string | number | null

export const listMaterialRenewals = (params?: Recordable) =>
  api.get('/material-renewals/', { params })
export const createMaterialRenewal = (body: Recordable) => api.post('/material-renewals/', body)
export const updateMaterialRenewal = (id: Id, body: Recordable) =>
  api.patch(`/material-renewals/${id}/`, body)
export const markMaterialRenewed = (id: Id, body: Recordable) =>
  api.post(`/material-renewals/${id}/mark-renewed/`, body)
export const deleteMaterialRenewal = (id: Id) => api.delete(`/material-renewals/${id}/`)
