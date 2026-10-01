import api from './client'

export const fetchDataScreen = () => api.get('/data-screen/')
export const listHallBlocks = () => api.get('/hall-blocks/')
