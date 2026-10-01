import { useEffect, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { DashboardCard, DashboardPanel } from '../components/DashboardPanels'
import { WalletBalanceChart } from '../components/WalletBalanceChart'
import { api, type LedgerRow } from '../lib/api'
import { computeDashboardStats, beijingYearMonth, type DashboardStatsView } from '../lib/dashboardStats'
import { isLedgerUnsettled } from '../lib/ledgerDisplay'
import { LEDGER_UPDATED_EVENT } from '../lib/ledgerEvents'

function digit(n: unknown) {
  const x = typeof n === 'number' && Number.isFinite(n) ? n : Number(n)
  const v = Number.isFinite(x) ? x : 0
  return v.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

function intStr(n: unknown) {
  const x = typeof n === 'number' && Number.isFinite(n) ? n : Number(n)
  const v = Number.isFinite(x) ? Math.round(x) : 0
  return v.toLocaleString('zh-CN')
}

export function Dashboard() {
  const [s, setS] = useState<DashboardStatsView | null>(null)
  const [ledger, setLedger] = useState<LedgerRow[]>([])
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    const load = () => {
      api
        .ledgerList()
        .then((ledgerRows) => {
          if (alive) {
            setLedger(ledgerRows)
            setS(computeDashboardStats(ledgerRows))
            setErr(null)
          }
        })
        .catch((e: Error) => {
          if (alive) setErr(e.message)
        })
    }
    load()
    const onUpdated = () => load()
    window.addEventListener(LEDGER_UPDATED_EVENT, onUpdated)
    const id = window.setInterval(load, 30000)
    return () => {
      alive = false
      window.removeEventListener(LEDGER_UPDATED_EVENT, onUpdated)
      window.clearInterval(id)
    }
  }, [])

  const ledgerRows = useMemo(
    () => (s ? [...s.ledgerByMonth].sort((a, b) => a.month.localeCompare(b.month)) : []),
    [s],
  )

  const chartLedger = useMemo(
    () =>
      ledgerRows.map((r) => ({
        month: r.month,
        收款: r.amount,
        利润: r.profit,
        笔数: r.count,
      })),
    [ledgerRows],
  )

  const thisMonthLedgerCount = useMemo(() => {
    if (!s) return 0
    const ym = beijingYearMonth()
    return s.ledgerByMonth.find((r) => r.month === ym)?.count ?? 0
  }, [s])

  const unsettled = useMemo(() => {
    let count = 0
    for (const r of ledger) {
      if (!isLedgerUnsettled(r)) continue
      count += 1
    }
    return { count }
  }, [ledger])

  if (err) {
    return (
      <div className="ep-card ep-card--warn">
        <div className="ep-card__body">
          <p>无法连接后端 API：{err}</p>
          <p className="ep-card__hint">请确认已登录 CEO 账号，且服务器 /api/ledger 可用。</p>
        </div>
      </div>
    )
  }

  if (!s) {
    return (
      <div className="ep-dashboard ep-dashboard--loading">
        <div className="ep-skeleton ep-skeleton--title" />
        <div className="ep-panel-grid">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="ep-skeleton ep-skeleton--panel" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="ep-dashboard">
      <div className="ep-dashboard__head">
        <h1 className="ep-dashboard__title">数据大屏</h1>
        <p className="ep-dashboard__subtitle">记账与钱包数据汇总 · 编辑保存后自动刷新</p>
      </div>

      <div className="ep-panel-grid">
        <DashboardPanel
          tone="money"
          label="本月收款金额"
          value={digit(s.ledgerThisMonthAmount)}
          icon={<span aria-hidden>💰</span>}
        />
        <DashboardPanel
          tone="shopping"
          label="本月利润"
          value={digit(s.ledgerThisMonthProfit)}
          icon={<span aria-hidden>📈</span>}
        />
        <DashboardPanel
          tone="message"
          label="本月记账笔数"
          value={intStr(thisMonthLedgerCount)}
          icon={<span aria-hidden>📋</span>}
        />
        <DashboardPanel
          tone="peoples"
          label="未清账笔数"
          value={intStr(unsettled.count)}
          icon={<span aria-hidden>⏳</span>}
        />
      </div>

      <div className="ep-chart-row">
        <DashboardCard title="记录表 · 月度收款" hint="柱状图：各月收款金额">
          <div className="ep-chart-box">
            {chartLedger.length ? (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={chartLedger} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ebeef5" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} stroke="#909399" />
                  <YAxis tick={{ fontSize: 12 }} stroke="#909399" />
                  <Tooltip formatter={(v: number) => digit(v)} />
                  <Legend />
                  <Bar dataKey="收款" fill="#409eff" radius={[4, 4, 0, 0]} maxBarSize={48} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="ep-empty">暂无数据</p>
            )}
          </div>
        </DashboardCard>

        <DashboardCard title="记录表 · 月度利润" hint="折线图：各月利润趋势">
          <div className="ep-chart-box">
            {chartLedger.length ? (
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={chartLedger} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ebeef5" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} stroke="#909399" />
                  <YAxis tick={{ fontSize: 12 }} stroke="#909399" />
                  <Tooltip formatter={(v: number) => digit(v)} />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="利润"
                    stroke="#67c23a"
                    strokeWidth={2}
                    dot={{ r: 4 }}
                    activeDot={{ r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <p className="ep-empty">暂无数据</p>
            )}
          </div>
        </DashboardCard>
      </div>

      <DashboardCard
        title="记录表 · 历史每月汇总"
        hint="数据来自记账全量记录；本月按「记录时间」北京时间自然月汇总。"
      >
        {chartLedger.length ? (
          <div className="ep-chart-row ep-chart-row--triple">
            <div className="ep-chart-box">
              <p className="ep-chart-mini-title">月度笔数</p>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={chartLedger} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ebeef5" />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} stroke="#909399" />
                  <YAxis tick={{ fontSize: 11 }} stroke="#909399" allowDecimals={false} />
                  <Tooltip formatter={(v: number) => intStr(v)} />
                  <Bar dataKey="笔数" fill="#e6a23c" radius={[4, 4, 0, 0]} maxBarSize={40} name="笔数" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="ep-chart-box">
              <p className="ep-chart-mini-title">月度收款</p>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={chartLedger} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ebeef5" />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} stroke="#909399" />
                  <YAxis tick={{ fontSize: 11 }} stroke="#909399" />
                  <Tooltip formatter={(v: number) => digit(v)} />
                  <Bar dataKey="收款" fill="#409eff" radius={[4, 4, 0, 0]} maxBarSize={40} name="收款" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="ep-chart-box">
              <p className="ep-chart-mini-title">月度利润</p>
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={chartLedger} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ebeef5" />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} stroke="#909399" />
                  <YAxis tick={{ fontSize: 11 }} stroke="#909399" />
                  <Tooltip formatter={(v: number) => digit(v)} />
                  <Line
                    type="monotone"
                    dataKey="利润"
                    stroke="#67c23a"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    activeDot={{ r: 5 }}
                    name="利润"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        ) : (
          <p className="ep-empty">暂无数据</p>
        )}
      </DashboardCard>

      <WalletBalanceChart />
    </div>
  )
}
