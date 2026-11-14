import api from '@/api/client'

// 教程+话术：职员端「教程+话术」页面的内容，在管理后台新增 / 编辑 / 删除
export type KnowledgeKind = 'faq' | 'tutorial' | 'phrase'

export interface KnowledgePlatform {
  id: number
  name: string
  status: string
}

export interface KnowledgeEntry {
  id: number
  platform_id: number | null
  kind: KnowledgeKind
  title: string
  content: string
  url: string
  tutorials: number[]
  sort_order: number
  updated_at: number | null
  updated_by: string
}

export interface KnowledgeList {
  platforms: KnowledgePlatform[]
  entries: KnowledgeEntry[]
  can_edit: boolean
  can_delete: boolean
}

export type KnowledgePayload = Pick<KnowledgeEntry, 'platform_id' | 'kind' | 'title' | 'content' | 'url' | 'tutorials'>

export async function listKnowledge() {
  const { data } = await api.get<KnowledgeList>('/knowledge/')
  return data
}

export async function createKnowledge(payload: KnowledgePayload) {
  const { data } = await api.post<KnowledgeEntry>('/knowledge/', payload)
  return data
}

export async function updateKnowledge(id: number, payload: Partial<KnowledgePayload>) {
  const { data } = await api.patch<KnowledgeEntry>(`/knowledge/${id}/`, payload)
  return data
}

export async function deleteKnowledge(id: number) {
  await api.delete(`/knowledge/${id}/`)
}
