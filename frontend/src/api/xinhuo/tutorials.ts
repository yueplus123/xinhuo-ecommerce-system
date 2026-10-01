import api from './client'

export const listPaymentTutorials = (params?: Recordable) =>
  api.get('/payment-tutorials/', params ? { params } : undefined)

export const listNannyTutorials = (params?: Recordable) =>
  api.get('/nanny-tutorials/', params ? { params } : undefined)
