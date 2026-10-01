import type { TableColumn } from '@/components/Table'

/** 列布局：qty=数量表；sku=多SKU；usdt=人民币/美金 */
export type WechatBotColumnLayout = 'qty' | 'sku' | 'usdt'

export type WechatBotTableDef = {
  key: string
  label: string
  path: string
  layout: WechatBotColumnLayout
}

const COL_TIME: TableColumn = { field: 'occurred_at', label: '时间', minWidth: 170 }
const COL_QTY: TableColumn = { field: 'quantity_label', label: '数量', width: 100 }
const COL_BIZ: TableColumn = { field: 'business_name', label: '业务名', minWidth: 140 }
const COL_EMP: TableColumn = { field: 'employee_name', label: '人员', minWidth: 100 }
const COL_CLEAR: TableColumn = { field: 'clear_status', label: '清空状态', width: 100 }
const COL_REMARK: TableColumn = { field: 'remark', label: '备注', minWidth: 140 }
const COL_CNY: TableColumn = { field: 'amount_cny', label: '人民币数', minWidth: 110 }
const COL_USD: TableColumn = { field: 'amount_usd', label: '美金数', minWidth: 110 }

export const WECHAT_BOT_COLUMNS: Record<WechatBotColumnLayout, TableColumn[]> = {
  qty: [COL_TIME, COL_QTY, COL_EMP, COL_CLEAR, COL_REMARK],
  sku: [COL_TIME, COL_BIZ, COL_QTY, COL_EMP, COL_CLEAR, COL_REMARK],
  usdt: [COL_TIME, COL_CNY, COL_USD, COL_EMP, COL_CLEAR, COL_REMARK]
}

export const WECHAT_BOT_TABLES: WechatBotTableDef[] = [
  { key: 'pixivcoban', label: '充币', path: '/wechat-bot-data/pixivcoban', layout: 'qty' },
  { key: 'once_card', label: '一次卡', path: '/wechat-bot-data/once_card', layout: 'qty' },
  { key: 'shared', label: '共享', path: '/wechat-bot-data/shared', layout: 'qty' },
  { key: 'package', label: '打包', path: '/wechat-bot-data/package', layout: 'qty' },
  { key: 'openrouter', label: 'openrouter', path: '/wechat-bot-data/openrouter', layout: 'qty' },
  { key: 'patreon', label: 'patreon', path: '/wechat-bot-data/patreon', layout: 'qty' },
  { key: 'commission', label: '约稿', path: '/wechat-bot-data/commission', layout: 'qty' },
  { key: 'booth', label: 'booth', path: '/wechat-bot-data/booth', layout: 'qty' },
  { key: 'pictspace', label: 'pictspace', path: '/wechat-bot-data/pictspace', layout: 'qty' },
  { key: 'premium', label: '高级会员', path: '/wechat-bot-data/premium', layout: 'sku' },
  { key: 'mega', label: 'mega', path: '/wechat-bot-data/mega', layout: 'sku' },
  { key: 'chatgpt', label: 'gpt', path: '/wechat-bot-data/chatgpt', layout: 'sku' },
  { key: 'usdt', label: 'USDT', path: '/wechat-bot-data/usdt', layout: 'usdt' }
]

export const WECHAT_BOT_TABLE_KEYS = new Set(WECHAT_BOT_TABLES.map((t) => t.key))

export function wechatBotTableLabel(key: string) {
  return WECHAT_BOT_TABLES.find((t) => t.key === key)?.label || key
}

export function wechatBotTableColumns(key: string): TableColumn[] {
  const layout = WECHAT_BOT_TABLES.find((t) => t.key === key)?.layout || 'qty'
  return WECHAT_BOT_COLUMNS[layout]
}
