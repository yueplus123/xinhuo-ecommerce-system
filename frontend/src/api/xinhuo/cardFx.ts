import api from './client'

export interface CardFxItem {
  jpy: number
  usd: string
}

export interface CardFxPayload {
  has_data: boolean
  rate_date: string | null
  usd_jpy: string | null
  usd_cny: string | null
  factor: string
  factor_percent: string
  stale_days: number | null
  is_stale: boolean
  items: CardFxItem[]
}

/** 日元充值汇率（职员可看，游客 403）。金额全部由后端算好。 */
export const getCardFx = () => api.get<CardFxPayload>('/card-fx/')
