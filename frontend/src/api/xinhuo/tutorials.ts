import api from './client'

export const listPaymentTutorials = (params?: Recordable) =>
  api.get('/payment-tutorials/', params ? { params } : undefined)
