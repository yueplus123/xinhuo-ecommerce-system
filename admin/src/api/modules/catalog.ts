import api from '@/api/client'

// 商品管理接口（/api/admin/catalog/*）：平台 → 业务 → SKU 三层，仅超级管理员可用
export type SaleStatus = 'on_sale' | 'off_sale' | 'pending_test'

export const STATUS_OPTIONS: Array<{ value: SaleStatus; label: string; tag: 'success' | 'danger' | 'warning' }> = [
  { value: 'on_sale', label: '在售', tag: 'success' },
  { value: 'off_sale', label: '禁售', tag: 'danger' },
  { value: 'pending_test', label: '待测试', tag: 'warning' }
]

export interface TagItem {
  id: number
  name: string
}
export interface SkuNode {
  id: number
  business: number
  name: string
  status: SaleStatus
  status_label: string
  quick_phrase_count: number
}
export interface BusinessNode {
  id: number
  platform: number
  name: string
  status: SaleStatus
  status_label: string
  sku_count: number
  skus: SkuNode[]
}
export interface PlatformRow {
  id: number
  name: string
  status: SaleStatus
  status_label?: string // 仅工作台详情接口返回，列表接口没有
  url: string
  note: string
  sort_order: number
  platform_tags: TagItem[]
  business_count: number
  sku_count: number
  businesses?: BusinessNode[]
}

const B = '/admin/catalog/'

export const listPlatforms = async (q = '') => {
  const { data } = await api.get<PlatformRow[] | { results: PlatformRow[] }>(`${B}platforms/`, {
    params: q ? { q } : undefined
  })
  return Array.isArray(data) ? data : data.results
}
export const getPlatform = async (id: number) => (await api.get<PlatformRow>(`${B}platforms/${id}/`)).data
export const createPlatform = async (body: Record<string, any>) => (await api.post<PlatformRow>(`${B}platforms/`, body)).data
export const updatePlatform = async (id: number, body: Record<string, any>) =>
  (await api.put<PlatformRow>(`${B}platforms/${id}/`, body)).data
export const deletePlatform = (id: number) => api.delete(`${B}platforms/${id}/`)
export const reorderPlatforms = (ids: number[]) => api.post(`${B}platforms/reorder/`, { order: ids })

export const createBusiness = async (body: Record<string, any>) => (await api.post<BusinessNode>(`${B}businesses/`, body)).data
export const updateBusiness = async (id: number, body: Record<string, any>) =>
  (await api.put<BusinessNode>(`${B}businesses/${id}/`, body)).data
export const deleteBusiness = (id: number) => api.delete(`${B}businesses/${id}/`)

export const createSku = async (body: Record<string, any>) => (await api.post<SkuNode>(`${B}skus/`, body)).data
export const updateSku = async (id: number, body: Record<string, any>) =>
  (await api.put<SkuNode>(`${B}skus/${id}/`, body)).data
export const deleteSku = (id: number) => api.delete(`${B}skus/${id}/`)
export const duplicateSku = async (id: number) => (await api.post<SkuNode>(`${B}skus/${id}/duplicate/`)).data

// ---- SKU 详细编辑（/api/manage/sku-editor/*）----
export interface SkuPriceItem {
  id?: number
  label: string
  rmb_amount: string
  notice: string
}
export interface SkuPhrase {
  id?: number
  content: string
}
export interface SkuImageItem {
  id: number
  url: string
}
export interface SkuEditorOptions {
  channel_tags: Array<{ id: number; name: string }>
  tutorials: Array<{ id: number; name: string }>
  phrases: Array<{ id: number; name: string; content: string }>
  price_types: Array<{ value: string; label: string }>
  statuses: Array<{ value: SaleStatus; label: string }>
  usd_tiers: Array<{ id: number; usd_range: string; rate_percent: string }>
}
export interface SkuDetail {
  id: number
  business: number
  business_name: string
  platform: number
  platform_name: string
  name: string
  status: SaleStatus
  precaution: string
  price_type: string
  price_notice: string
  channel_tag_ids: number[]
  tutorial_ids: number[]
  price_items: SkuPriceItem[]
  quick_phrases: SkuPhrase[]
  images: SkuImageItem[]
  options: SkuEditorOptions
}

const S = '/manage/sku-editor/'
export const getSkuEditor = async (id: number) => (await api.get<SkuDetail>(`${S}${id}/`)).data
export const getSkuEditorOptions = async () => (await api.get<SkuEditorOptions>(`${S}options/`)).data
export const createSkuEditor = async (fd: FormData) => (await api.post<SkuDetail>(S, fd)).data
export const saveSkuEditor = async (id: number, fd: FormData) => (await api.put<SkuDetail>(`${S}${id}/`, fd)).data
