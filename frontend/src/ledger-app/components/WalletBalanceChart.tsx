import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { DashboardCard } from './DashboardPanels'
import { api, type WalletRow } from '../lib/api'
import { WALLET_UPDATED_EVENT } from '../lib/ledgerEvents'

type Props = {
  refreshTrigger?: number
}

type ChartPoint = {
  key: string
  label: string
  微信: number
  支付宝: number
  卡片: number
  小荷包: number
  总计: number
}

const SERIES = [
  { key: '微信', color: '#67c23a' },
  { key: '支付宝', color: '#409eff' },
  { key: '卡片', color: '#e6a23c' },
  { key: '小荷包', color: '#f56c6c' },
  { key: '总计', color: '#606266' },
] as const

function digit(n: unknown) {
  const x = typeof n === 'number' && Number.isFinite(n) ? n : Number(n)
  const v = Number.isFinite(x) ? x : 0
  return v.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

function parseRecordTime(recordAt: string) {
  const raw = String(recordAt || '').trim()
  if (!raw) return 0
  const normalized = raw.includes('T') ? raw : raw.replace(' ', 'T')
  const ts = Date.parse(normalized)
  return Number.isFinite(ts) ? ts : 0
}

function chartLabel(recordAt: string) {
  const raw = String(recordAt || '').trim()
  if (raw.length >= 16) return raw.slice(5, 16)
  if (raw.length >= 10) return raw.slice(5, 10)
  return raw || '—'
}

function toChartPoints(rows: WalletRow[]): ChartPoint[] {
  return [...rows]
    .sort((a, b) => {
      const ta = parseRecordTime(a.recordAt)
      const tb = parseRecordTime(b.recordAt)
      if (ta !== tb) return ta - tb
      return a.id.localeCompare(b.id)
    })
    .map((r) => ({
      key: r.id,
      label: chartLabel(r.recordAt),
      微信: Number(r.wechat) || 0,
      支付宝: Number(r.alipay) || 0,
      卡片: Number(r.card) || 0,
      小荷包: Number(r.pocket) || 0,
      总计: Number(r.total) || 0,
    }))
}

export function WalletBalanceChart({ refreshTrigger = 0 }: Props) {
  const [rows, setRows] = useState<WalletRow[]>([])
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    setLoading(true)
    api
      .walletList()
      .then((list) => {
        setRows(list)
        setErr(null)
      })
      .catch((e: Error) => {
        setRows([])
        setErr(e.message)
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load, refreshTrigger])

  useEffect(() => {
    const onWalletUpdated = () => load()
    window.addEventListener(WALLET_UPDATED_EVENT, onWalletUpdated)
    return () => window.removeEventListener(WALLET_UPDATED_EVENT, onWalletUpdated)
  }, [load])

  const points = useMemo(() => toChartPoints(rows), [rows])

  const latest = points.at(-1)

  return (
    <DashboardCard
      title="余额曲线"
      hint="按记录时间展示微信 / 支付宝 / 卡片 / 小荷包 / 总计的变化趋势"
    >
      {err ? <p className="error">{err}</p> : null}
      {loading ? <div className="ep-chart-box ep-chart-box--loading ep-skeleton" /> : null}
      {!loading && !err && !points.length ? (
        <p className="ep-empty">暂无记录，保存第一条后将在此显示曲线</p>
      ) : null}
      {!loading && !err && points.length > 0 ? (
        <>
          {latest ? (
            <div className="wallet-chart-kpis">
              {SERIES.map((s) => (
                <div key={s.key} className="wallet-chart-kpi">
                  <span className="wallet-chart-kpi__dot" style={{ backgroundColor: s.color }} />
                  <span className="wallet-chart-kpi__label">{s.key}</span>
                  <span className="wallet-chart-kpi__value">{digit(latest[s.key])}</span>
                </div>
              ))}
            </div>
          ) : null}
          <div className="ep-chart-box">
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={points} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ebeef5" />
                <XAxis dataKey="label" tick={{ fontSize: 12 }} stroke="#909399" />
                <YAxis tick={{ fontSize: 12 }} stroke="#909399" tickFormatter={(v) => digit(v)} />
                <Tooltip
                  formatter={(v: number) => digit(v)}
                  labelFormatter={(_label, payload) => {
                    const item = payload?.[0]?.payload as ChartPoint | undefined
                    const row = item ? rows.find((r) => r.id === item.key) : undefined
                    return row?.recordAt ? `记录时间 ${row.recordAt}` : item?.label ?? ''
                  }}
                />
                <Legend />
                {SERIES.map((s) => (
                  <Line
                    key={s.key}
                    type="monotone"
                    dataKey={s.key}
                    stroke={s.color}
                    strokeWidth={s.key === '总计' ? 2.5 : 2}
                    dot={{ r: s.key === '总计' ? 4 : 3 }}
                    activeDot={{ r: 6 }}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      ) : null}
    </DashboardCard>
  )
}
