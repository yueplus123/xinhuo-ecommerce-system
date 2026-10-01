import api from './client'

export const fetchMe = () => api.get('/auth/me/')
export const fetchLoginLogs = () => api.get('/auth/me/login-logs/')
export const uploadAvatar = (avatar: string) => api.post('/auth/me/avatar/', { avatar })
export const deleteAvatar = () => api.delete('/auth/me/avatar/')
