import api from '@/api/client'

export type PoolKey =
  | 'platform-tag-pool'
  | 'channel-tag-pool'
  | 'usd-proxy-price-pool'

export interface PoolRow {
  id: number
  [field: string]: any
}

export interface PoolListResult {
  count: number
  results: PoolRow[]
  reorderable: boolean
}

const base = (key: PoolKey) => `/manage/pools/${key}/`

export async function listPool(key: PoolKey, params?: Record<string, any>) {
  const { data } = await api.get<PoolListResult>(base(key), { params })
  return data
}

export async function createPoolItem(key: PoolKey, payload: Record<string, any>) {
  const { data } = await api.post<PoolRow>(base(key), payload)
  return data
}

export async function updatePoolItem(key: PoolKey, id: number, payload: Record<string, any>) {
  const { data } = await api.put<PoolRow>(`${base(key)}${id}/`, payload)
  return data
}

export async function deletePoolItem(key: PoolKey, id: number) {
  await api.delete(`${base(key)}${id}/`)
}

export async function reorderPool(key: PoolKey, ids: number[]) {
  await api.post(`${base(key)}reorder/`, { order: ids })
}

export async function quickAddPoolTag(key: PoolKey, name: string) {
  const { data } = await api.post<{ id: number; name: string; message: string }>(
    `${base(key)}quick-add/`,
    { name }
  )
  return data
}
