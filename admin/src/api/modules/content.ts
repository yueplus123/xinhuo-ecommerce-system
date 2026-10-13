import api from '@/api/client'

// 内容类管理接口（/api/manage/content/*）：均为可拖动排序的列表资源，仅超级管理员可用
export type ContentKey =
  | 'payment-tutorials'
  | 'shared-apple-id-pages'
  | 'pict-cart-pages'
  | 'fanbox-stats-pages'
  | 'service-monitor-pages'
  | 'platform-accounts'

export interface ContentRow {
  id: number
  sort_order: number
  [field: string]: any
}

const base = (key: ContentKey) => `/manage/content/${key}/`

export async function listContent(key: ContentKey) {
  const { data } = await api.get<ContentRow[] | { results: ContentRow[] }>(base(key))
  return Array.isArray(data) ? data : data.results
}

export async function createContent(key: ContentKey, payload: Record<string, any>) {
  const { data } = await api.post<ContentRow>(base(key), payload)
  return data
}

export async function updateContent(key: ContentKey, id: number, payload: Record<string, any>) {
  const { data } = await api.put<ContentRow>(`${base(key)}${id}/`, payload)
  return data
}

export async function deleteContent(key: ContentKey, id: number) {
  await api.delete(`${base(key)}${id}/`)
}

export async function reorderContent(key: ContentKey, ids: number[]) {
  await api.post(`${base(key)}reorder/`, { order: ids })
}
