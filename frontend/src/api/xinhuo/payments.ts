import api from './client'
import type { AxiosRequestConfig } from 'axios'

export const fetchPaymentMeta = () => api.get('/payment-meta/')
export const fetchStaffUsers = () => api.get('/staff-users/')
export const listPaymentRecords = (params: Recordable) => api.get('/payment-records/', { params })
export const exportPaymentRecords = (params: Recordable) =>
  api.get('/payment-records/export/', { params, responseType: 'blob' })
export const batchSubmitPaymentRecords = (body: FormData, config?: AxiosRequestConfig) =>
  api.post('/payment-records/batch-submit/', body, config)
