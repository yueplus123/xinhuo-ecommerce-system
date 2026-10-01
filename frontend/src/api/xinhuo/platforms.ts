import api from './client'

type Id = string | number

export const listPlatforms = (params?: Recordable) => api.get('/platforms/', { params })
export const exportPlatformBusinesses = (params?: Recordable) =>
  api.get('/platforms/export-businesses/', { params, responseType: 'blob' })
export const getPlatform = (id: Id) => api.get(`/platforms/${id}/`)
export const listUsdProxyPriceTiers = () => api.get('/usd-proxy-price-tiers/')
