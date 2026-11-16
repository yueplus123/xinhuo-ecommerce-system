import api from '@/api/client'

// 日元充值汇率（仅超级管理员）：汇率自动取数，这里只改系数
export interface CardFxPayload {
  has_data: boolean
  rate_date: string | null
  usd_jpy: string | null
  usd_cny: string | null
  source: string | null
  fetched_at: string | null
  factor: string
  factor_percent: string
  saved_factor: string
  stale_days: number | null
  is_stale: boolean
  items: Array<{ jpy: number; usd: string }>
  settings_updated_at: string | null
  settings_updated_by: string
}

export const getCardFxSettings = (factor?: string) =>
  api.get<CardFxPayload>('/card-fx/settings/', { params: factor ? { factor } : {} })

export const saveCardFxFactor = (factor: string) =>
  api.patch<CardFxPayload>('/card-fx/settings/', { factor })
