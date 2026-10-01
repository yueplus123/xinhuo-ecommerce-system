import api from './client'

export const listFanboxStatsPages = () => api.get('/fanbox-stats-pages/')
export const listPictCartPages = () => api.get('/pict-cart-pages/')
export const listServiceMonitorPages = () => api.get('/service-monitor-pages/')
export const listSharedAppleIdPages = () => api.get('/shared-apple-id-pages/')
export const listPlatformAccounts = () => api.get('/platform-accounts/')
