import api from '@/api/client'

// 月度 GMV 目标（仅超级管理员）：数据大屏「本月目标」读这里
export interface GmvTargetRow {
  month: string
  is_current: boolean
  is_future: boolean
  target: number | null
  gmv: number | null
  done_pct: number | null
  updated_by: string
}

export const listGmvTargets = () => api.get<{ rows: GmvTargetRow[] }>('/admin/gmv-targets/')

/** target 传空字符串 = 删除这个月的目标 */
export const saveGmvTarget = (month: string, target: string) =>
  api.put<{ rows: GmvTargetRow[] }>('/admin/gmv-targets/', { month, target })
