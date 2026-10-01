/**
 * 记账 API：并入薪火 Django（/api/ledger/*），复用主站 axios 与 JWT。
 */
import apiClient from '@/api/xinhuo/client'

function errMsg(e: unknown): string {
  const ax = e as {
    response?: { status?: number; data?: { error?: string; detail?: string } }
    message?: string
  }
  const st = ax.response?.status
  const d = ax.response?.data
  if (st === 401 || st === 403) {
    return '无权限或未登录，请使用 CEO 账号登录后重试。'
  }
  if (d?.error) return String(d.error)
  if (d?.detail) return String(d.detail)
  if (st) return `记账 API 错误（HTTP ${st}）`
  return ax.message || '请求失败'
}

async function wrap<T>(p: Promise<{ data: T }>): Promise<T> {
  try {
    const { data } = await p
    return data
  } catch (e) {
    throw new Error(errMsg(e))
  }
}

const L = '/ledger'

export type CatalogOption = { id: string; label: string }
export type Business = { id: string; name: string; options: CatalogOption[] }
export type LedgerRow = {
  id: string
  recordAt: string
  recordNo: string
  businessId: string
  businessName: string
  projectName: string
  optionId: string | null
  optionLabel: string
  amount: number
  giveAmount: number
  takeAmount: number
  profit: number
  employeeName: string
  chatName: string
  status: 'ACTIVE' | 'PROCESSED' | 'REVERSED'
  statusLabel: string
  settledAt: string | null
  externalId?: string | null
}
export type LedgerMeta = {
  employees: string[]
  chats: string[]
}
export type WalletRow = {
  id: string
  recordAt: string
  wechat: number
  alipay: number
  card: number
  pocket: number
  total: number
}
export type Stats = {
  ledgerCount: number
  sumAmount: number
  sumGive: number
  sumTake: number
  sumProfit: number
  unsettledLedger: number
  byBiz: Record<string, number>
  recentLedger: LedgerRow[]
  ledgerThisMonthProfit: number
  ledgerThisMonthAmount: number
  ledgerLastMonthProfit: number
  ledgerLastMonthAmount: number
  ledgerByMonth: { month: string; count: number; amount: number; profit: number }[]
  bizFrequency: { label: string; count: number }[]
}

export const api = {
  catalog: () => wrap(apiClient.get<{ businesses: Business[] }>(`${L}/catalog/`)),
  addBusiness: (name: string) =>
    wrap(apiClient.post<Business>(`${L}/catalog/`, { name })),
  updateBusiness: (id: string, name: string) =>
    wrap(apiClient.put<Business>(`${L}/catalog/businesses/${id}/`, { name })),
  deleteBusiness: (id: string) =>
    wrap(apiClient.delete<{ ok: boolean }>(`${L}/catalog/businesses/${id}/`)),
  addOption: (businessId: string, label: string) =>
    wrap(
      apiClient.post<CatalogOption>(`${L}/catalog/businesses/${businessId}/options/`, {
        label,
      }),
    ),
  deleteOption: (businessId: string, optionId: string) =>
    wrap(
      apiClient.delete<{ ok: boolean }>(
        `${L}/catalog/businesses/${businessId}/options/${optionId}/`,
      ),
    ),
  updateOption: (businessId: string, optionId: string, label: string) =>
    wrap(
      apiClient.put<CatalogOption>(
        `${L}/catalog/businesses/${businessId}/options/${optionId}/`,
        { label },
      ),
    ),
  ledgerList: (q?: string) =>
    wrap(apiClient.get<LedgerRow[]>(`${L}/ledger/`, { params: q ? { q } : undefined })),
  ledgerMeta: () => wrap(apiClient.get<LedgerMeta>(`${L}/meta/`)),
  ledgerCreate: (body: {
    recordAt: string
    recordNo?: string
    businessName: string
    amount: number
    giveAmount: number
    takeAmount: number
    profit: number
    employeeName: string
    chatName: string
  }) => wrap(apiClient.post<LedgerRow>(`${L}/ledger/`, body)),
  ledgerSettle: (id: string, settledAt: string) =>
    wrap(apiClient.patch<LedgerRow>(`${L}/ledger/${id}/settle/`, { settledAt })),
  ledgerSetStatus: (id: string, status: LedgerRow['status']) =>
    wrap(apiClient.patch<LedgerRow>(`${L}/ledger/${id}/status/`, { status })),
  ledgerBulkStatus: (ids: string[], status: LedgerRow['status']) =>
    wrap(apiClient.post<{ ok: boolean; updated: number }>(`${L}/ledger/bulk-status/`, { ids, status })),
  ledgerUpdate: (
    id: string,
    body: {
      recordAt: string
      recordNo?: string
      businessName: string
      amount: number
      giveAmount: number
      takeAmount: number
      profit: number
      employeeName?: string
      chatName?: string
    },
  ) => wrap(apiClient.put<LedgerRow>(`${L}/ledger/${id}/`, body)),
  ledgerDelete: (id: string) =>
    wrap(apiClient.delete<{ ok: boolean }>(`${L}/ledger/${id}/`)),
  ledgerBatchImport: (
    rows: {
      recordAt: string
      businessName: string
      amount: number
      giveAmount: number
      takeAmount: number
      profit: number
      settled: boolean
    }[],
  ) =>
    wrap(
      apiClient.post<{ ok: boolean; count: number; skipped: number; warnings: string[] }>(
        `${L}/ledger/batch-import/`,
        { rows },
      ),
    ),
  walletList: () => wrap(apiClient.get<WalletRow[]>(`${L}/wallet/`)),
  walletCreate: (body: {
    recordAt: string
    wechat: number
    alipay: number
    card: number
    pocket: number
  }) => wrap(apiClient.post<WalletRow>(`${L}/wallet/`, body)),
  walletUpdate: (
    id: string,
    body: { recordAt: string; wechat: number; alipay: number; card: number; pocket: number },
  ) => wrap(apiClient.put<WalletRow>(`${L}/wallet/${id}/`, body)),
  walletDelete: (id: string) =>
    wrap(apiClient.delete<{ ok: boolean }>(`${L}/wallet/${id}/`)),
  stats: () => wrap(apiClient.get<Stats>(`${L}/stats/`)),
}
