<script setup lang="tsx">
import * as echarts from 'echarts'
import { echartsThemeName, registerEchartsThemes } from '@/utils/echartsTheme'
import { baseAnimation, barSeriesAnimation, lineRevealAfter, lineSeriesAnimation, type AnimMode } from '@/utils/chartAnimation'
import { OdometerNumber } from '@/components/OdometerNumber'
import { useAppStore } from '@/store/modules/app'
import { computed, nextTick, onActivated, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  ElAlert,
  ElCard,
  ElCol,
  ElOption,
  ElProgress,
  ElRow,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag
} from 'element-plus'
import { Refresh, FullScreen } from '@element-plus/icons-vue'
import { BaseButton } from '@/components/Button'
import { fetchDataScreen } from '@/api/xinhuo/dashboard'
import { useFullscreen } from '@vueuse/core'

defineOptions({ name: 'DataScreen' })

const pageRef = ref<HTMLElement | null>(null)
const { isFullscreen, toggle: toggleFullscreen, exit: exitFullscreen } = useFullscreen(pageRef)

const payload = ref<any>(null)
const loading = ref(true)
const error = ref('')
const chartRefs = new Map<string, echarts.ECharts>()

const periodDefs = [
  { key: 'month', label: '本月' },
  { key: 'week', label: '本周' },
  { key: 'prev_month', label: '上月' },
  { key: 'year', label: '年度' }
]
const activePeriod = ref('month')

function activePeriodDef() {
  return periodDefs.find((d) => d.key === activePeriod.value) || periodDefs[0]
}

function safeNum(v: any) {
  const n = Number(v || 0)
  return Number.isFinite(n) ? n : 0
}
function fmt(v: any) {
  return safeNum(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function fmtInt(v: any) {
  return Math.round(safeNum(v)).toLocaleString('zh-CN')
}
function fmtPct(v: any) {
  if (v === null || v === undefined || v === '') return '—'
  const n = Number(v)
  if (!Number.isFinite(n)) return '—'
  const sign = n > 0 ? '+' : ''
  return `${sign}${n.toFixed(2)}%`
}
function deltaTone(delta: any) {
  const n = Number(delta)
  if (!Number.isFinite(n) || n === 0) return 'flat'
  return n > 0 ? 'up' : 'down'
}
function periodData(def: { key: string }) {
  return payload.value?.[def.key] || { summary: {}, staff: [], bot_business: [] }
}

const summary = computed(() => periodData(activePeriodDef()).summary || {})

/** 收款概览：4 项主 KPI */
const kpiCards = computed(() => {
  const s = summary.value
  return [
    {
      key: 'gmv',
      title: 'GMV',
      value: safeNum(s.total_gmv),
      prefix: '¥',
      precision: 2,
      footer: '环比增长',
      delta: s.gmv_change_pct,
      tone: 'money',
      icon: '💰'
    },
    {
      key: 'shilei',
      title: '十类收款',
      value: safeNum(s.shilei),
      prefix: '¥',
      precision: 2,
      footer: '占比',
      ratioText: s.shilei_ratio != null && s.shilei_ratio !== '' ? `${fmt(s.shilei_ratio)}%` : undefined,
      tone: 'shopping',
      icon: '🏦'
    },
    {
      key: 'orders',
      title: '订单数',
      value: safeNum(s.order_count),
      prefix: '',
      precision: 0,
      footer: '环比增长',
      delta: s.order_change_pct,
      tone: 'message',
      icon: '📋'
    },
    {
      key: 'refund',
      title: '退款金额',
      value: safeNum(s.refund),
      prefix: '¥',
      precision: 2,
      footer: '退款率',
      ratioText: s.refund_rate != null && s.refund_rate !== '' ? `${fmt(s.refund_rate)}%` : undefined,
      tone: 'peoples',
      icon: '⏳'
    }
  ]
})

const BOT_CARD_META: Record<string, { icon: string; tone: string }> = {
  pixivcoban: { icon: '🪙', tone: 'money' },
  once_card: { icon: '🎫', tone: 'shopping' },
  shared: { icon: '👥', tone: 'peoples' },
  package: { icon: '📦', tone: 'message' },
  openrouter: { icon: '🔌', tone: 'money' },
  patreon: { icon: '🧡', tone: 'shopping' },
  booth: { icon: '🏪', tone: 'message' },
  pictspace: { icon: '🖼', tone: 'money' },
  premium: { icon: '⭐', tone: 'shopping' },
  mega: { icon: '💾', tone: 'peoples' },
  chatgpt: { icon: '🤖', tone: 'message' },
  usdt: { icon: '💵', tone: 'money' }
}

/** 微信BOT 各业务卡（并入收款概览） */
const botBusinessCards = computed(() => {
    const rows = periodData(activePeriodDef()).bot_business || []
    return rows.map((r: any) => {
      const meta = BOT_CARD_META[r.key] || { icon: '📊', tone: 'message' }
      const isUsdt = r.unit === 'usd' || r.layout === 'usdt'
      return {
        key: r.key,
        title: r.label || r.key,
        value: safeNum(r.value),
        prefix: isUsdt ? '$' : '',
        precision: isUsdt ? 2 : 0,
        footer: '环比',
        delta: r.change_pct,
        tone: meta.tone,
        icon: meta.icon
      }
    })
})

/** 收款概览统一网格：主 KPI + BOT，卡片尺寸一致 */
const overviewCards = computed(() => [...kpiCards.value, ...botBusinessCards.value])

const memberPanels = [
  { id: 'ds-period-gmv', title: '各成员 GMV', icon: '💰', tone: 'money' },
  { id: 'ds-period-shilei', title: '各成员十类收款', icon: '🏦', tone: 'shopping' },
  { id: 'ds-period-orders', title: '各成员订单数', icon: '📋', tone: 'message' },
  { id: 'ds-period-refund', title: '各成员退款金额', icon: '⏳', tone: 'peoples' }
] as const

function hasKpiFooter(card: {
  delta?: any
  ratioText?: string
  footer?: string
}) {
  if (card.delta !== null && card.delta !== undefined && card.delta !== '') return true
  if (card.ratioText) return true
  if (card.footer) return true
  return false
}

const channelRankData = computed(() => periodData(activePeriodDef()).channel_rank_list || [])
const staffRankData = computed(() => {
  const staff = [...(periodData(activePeriodDef()).staff || [])].sort(
    (a: any, b: any) => safeNum(b.gmv) - safeNum(a.gmv)
  )
  const max = Math.max(...staff.map((s: any) => safeNum(s.gmv)), 1)
  return staff.map((s: any) => ({
    ...s,
    percent: Math.round((safeNum(s.gmv) / max) * 100)
  }))
})

// 「各成员每日收款趋势」折线图的线条颜色。
// 个别成员指定固定色；其余成员按他在列表中的位置，从下面这组「彼此差异明显」的颜色里取。
// 调色板刻意避开黄 / 橙 / 绿，把这三类留给指定成员，防止和亮金色、绿色混淆。
const STAFF_LINE_COLORS: Record<string, string> = {
  李振宇: '#FFB300', // 亮金色
  金凤: '#16A34A' // 绿色
}
const STAFF_LINE_PALETTE = [
  '#2563EB', // 蓝
  '#DC2626', // 红
  '#7C3AED', // 紫
  '#06B6D4', // 青
  '#DB2777', // 玫红
  '#92400E', // 棕
  '#64748B', // 灰蓝
  '#111827' // 近黑
]

const staffDailyTitle = computed(() => `${activePeriodDef().label}各成员每日收款趋势`)

registerEchartsThemes()
const appStore = useAppStore()
const isDark = computed(() => appStore.getIsDark)
// 每个图表创建时所用的主题；切换白天 / 黑夜后与当前主题不一致就重建
const chartTheme = new Map<string, boolean>()
// 递增一次 = 数字卡全部「从 0 重新滚动」（首次加载 / 切换周期）；静默刷新不递增，数字只是平滑变到新值
const animEpoch = ref(0)
// 记录每个图表上一次 resize 时的容器尺寸：加载过程中 handleResize 会被连续调用好几次，
// 而 echarts 的 resize() 会打断正在播放的入场动画（柱状图因此瞬间弹出）。
// 所以只有容器宽高真的变了才 resize，布局行为不变，动画也不会被打断。
const chartSize = new Map<string, string>()

// 下一次绘制要用的动画模式：
//   enter  = 首次加载 / 切换周期 / 切换主题 → 播放完整入场动画（数字滚动、柱子生长、折线从左到右）
//   update = 每 8 秒的静默刷新 → 只做短促的数值过渡，不重播入场动画
let animMode: AnimMode = 'enter'
// 每个图表上一次绘制时的「数据指纹」；静默刷新时数据没变就不重绘，避免无谓闪动
const chartSig = new Map<string, string>()
const symbolTimers = new Map<string, number>() // 折线圆点的延迟显示计时器

function withAnimation(option: any, mode: AnimMode) {
  const out = { ...option, ...baseAnimation(mode) }
  if (Array.isArray(out.series)) {
    let lineIdx = 0
    out.series = out.series.map((s: any) => {
      if (s.type === 'bar') return { ...s, ...barSeriesAnimation(mode) }
      if (s.type === 'line') {
        const anim = lineSeriesAnimation(mode, lineIdx++)
        // 入场期间先藏圆点（否则圆点会比线先蹦出来），线画完后由 mountChart 再把它们亮出来
        return mode === 'enter' && s.symbol !== 'none' ? { ...s, ...anim, showSymbol: false } : { ...s, ...anim }
      }
      return s
    })
  }
  return out
}

// ---- 「滚到才播」：入场动画只在图表进入可视区时播放 ----
// 折线图 / 渠道图等在页面下方，一屏看不到；如果刷新就播，用户滚下去时动画早就结束了。
// 做法：入场时，屏幕外的图表先「静态画好」（不播动画，保证有内容），
//       等它第一次滚进视口（可见 35%）时，再按入场参数重画一遍 → 此时才播放。
// IntersectionObserver 默认以浏览器视口为根，页面内部容器滚动同样适用。
const pendingEnter = new Map<string, echarts.EChartsOption>() // 还没播过入场动画的图表 → 它的 option
let visObserver: IntersectionObserver | null = null

function ensureObserver() {
  if (visObserver || typeof IntersectionObserver === 'undefined') return
  visObserver = new IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        if (!e.isIntersecting) continue
        const id = (e.target as HTMLElement).id
        const opt = pendingEnter.get(id)
        if (!opt) continue
        pendingEnter.delete(id)
        visObserver?.unobserve(e.target)
        drawChart(id, opt, 'enter') // 现在才播入场动画
      }
    },
    { threshold: 0.35 }
  )
}

const inViewport = (el: HTMLElement) => {
  const r = el.getBoundingClientRect()
  const vh = window.innerHeight || document.documentElement.clientHeight
  const visible = Math.min(r.bottom, vh) - Math.max(r.top, 0)
  return r.height > 0 && visible / r.height >= 0.35
}

function mountChart(id: string, option: echarts.EChartsOption) {
  const el = document.getElementById(id)
  if (!el) return
  if (animMode === 'enter') {
    ensureObserver()
    pendingEnter.delete(id)
    visObserver?.unobserve(el)
    if (!inViewport(el) && visObserver) {
      // 屏幕外：先静态画好（'update' 模式 = 不播入场动画），再登记，等滚进来时重播
      drawChart(id, option, 'static')
      pendingEnter.set(id, option)
      visObserver.observe(el)
      return
    }
  } else {
    // 静默刷新：若这张图还没播过入场动画，只更新它排队等待的数据，不抢先播放
    if (pendingEnter.has(id)) pendingEnter.set(id, option)
  }
  drawChart(id, option, animMode === 'enter' ? 'enter' : 'update')
}

type DrawMode = 'enter' | 'update' | 'static'

function drawChart(id: string, option: echarts.EChartsOption, drawMode: DrawMode) {
  const el = document.getElementById(id)
  if (!el) return
  const mode: AnimMode = drawMode === 'enter' ? 'enter' : 'update'
  let chart = chartRefs.get(id)
  if (chart && chartTheme.get(id) !== isDark.value) {
    chart.dispose()
    chartRefs.delete(id)
    chartSize.delete(id)
    chart = undefined
  }
  // 静默刷新且数据没变：什么都不做（既不闪也不重播）
  const sig = JSON.stringify(option, (_k, v) => (typeof v === 'function' ? undefined : v))
  if (chart && drawMode === 'update' && chartSig.get(id) === sig) return
  if (!chart) {
    chart = echarts.init(el, echartsThemeName(isDark.value), { renderer: 'canvas' })
    chartRefs.set(id, chart)
    chartTheme.set(id, isDark.value)
  }
  chartSig.set(id, sig)
  // 静态绘制：整张图不要动画（直接出现最终样子）；入场：从头播；更新：合并并平滑变化
  const opt = withAnimation(option, mode) as any
  if (drawMode === 'static') opt.animation = false
  chart.setOption(opt as echarts.EChartsOption, { notMerge: drawMode !== 'update' })

  // 折线图入场结束后，把入场期间藏起来的圆点亮出来（只对原本要显示圆点的线）
  const lines = ((option as any).series || []).filter((x: any) => x.type === 'line' && x.symbol !== 'none')
  clearTimeout(symbolTimers.get(id))
  if (drawMode === 'enter' && lines.length) {
    const target = chart
    symbolTimers.set(
      id,
      window.setTimeout(() => {
        if (chartRefs.get(id) !== target) return // 期间被重建 / 销毁了
        target.setOption(
          { series: ((option as any).series || []).map((x: any) => (x.type === 'line' && x.symbol !== 'none' ? { showSymbol: true } : {})) },
          { notMerge: false, lazyUpdate: false, silent: true }
        )
      }, lineRevealAfter(lines.length))
    )
  }
}

function barOption(staff: any[], field: string, color: string, isInt = false) {
  const rows = (staff || []).map((x) => ({
    name: x.user__username || '-',
    value: safeNum(x[field])
  }))
  // 数值高的排前面；配合 inverse 后「第一名」在条形图顶部
  rows.sort((a, b) => b.value - a.value)
  return {
    grid: { left: 8, right: 14, top: 8, bottom: 8, containLabel: true },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(15,31,24,.08)' } },
      axisLabel: { color: '#64748b' }
    },
    yAxis: {
      type: 'category',
      data: rows.map((x) => x.name),
      inverse: true,
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: { color: '#475569', width: 72, overflow: 'truncate' }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      order: 'valueDesc',
      valueFormatter: (v: any) => (isInt ? fmtInt(v) : fmt(v))
    },
    series: [
      {
        type: 'bar',
        data: rows.map((x) => x.value),
        barMaxWidth: 18,
        itemStyle: { color, borderRadius: [0, 6, 6, 0] }
      }
    ]
  }
}

function renderFixedCharts() {
  if (!payload.value) return

  const monthTrend = payload.value.month_sales_trend || []
  mountChart('ds-chart-month-trend', {
    grid: { left: '2%', right: '2%', bottom: '4%', top: '10%', containLabel: true },
    tooltip: { trigger: 'axis', valueFormatter: (v: any) => fmt(v) },
    xAxis: {
      type: 'category',
      data: monthTrend.map((x: any) => x.date),
      axisLabel: {
        color: '#64748b',
        interval: monthTrend.length > 20 ? Math.floor(monthTrend.length / 10) : 0
      },
      axisLine: { lineStyle: { color: '#e2e8f0' } }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#64748b' },
      splitLine: { lineStyle: { color: 'rgba(15,31,24,.08)' } }
    },
    series: [
      {
        type: 'line',
        smooth: true,
        data: monthTrend.map((x: any) => safeNum(x.sales)),
        lineStyle: { color: '#0f6a4f', width: 2 },
        areaStyle: { color: 'rgba(15,106,79,.12)' },
        symbol: monthTrend.length > 40 ? 'none' : 'circle',
        symbolSize: 6
      }
    ]
  })

  const historyGmv = payload.value.history_month_gmv || []
  mountChart('ds-chart-history-gmv', {
    grid: { left: '2%', right: '2%', bottom: '4%', top: '10%', containLabel: true },
    tooltip: { trigger: 'axis', valueFormatter: (v: any) => fmt(v) },
    xAxis: {
      type: 'category',
      data: historyGmv.map((x: any) => x.date),
      axisLabel: { color: '#64748b' },
      axisLine: { lineStyle: { color: '#e2e8f0' } }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#64748b' },
      splitLine: { lineStyle: { color: 'rgba(15,31,24,.08)' } }
    },
    series: [
      {
        type: 'line',
        smooth: true,
        data: historyGmv.map((x: any) => safeNum(x.gmv)),
        lineStyle: { color: '#6366f1', width: 2 },
        areaStyle: { color: 'rgba(99,102,241,.12)' },
        symbol: historyGmv.length > 24 ? 'none' : 'circle',
        symbolSize: 6
      }
    ]
  })
}

function renderPeriodCharts() {
  if (!payload.value) return
  const def = activePeriodDef()
  const d = periodData(def)
  mountChart('ds-period-gmv', barOption(d.staff, 'gmv', '#0f6a4f'))
  mountChart('ds-period-shilei', barOption(d.staff, 'shilei', '#c2410c'))
  mountChart('ds-period-orders', barOption(d.staff, 'order_count', '#0e7490', true))
  mountChart('ds-period-refund', barOption(d.staff, 'refund', '#7c3aed'))

  const channelRank = [...(d.channel_rank_list || [])].sort(
    (a: any, b: any) => safeNum(b.c) - safeNum(a.c)
  )
  mountChart('ds-chart-channel', {
    tooltip: { trigger: 'item', order: 'valueDesc' },
    legend: { bottom: 0, textStyle: { color: '#64748b' } },
    series: [
      {
        type: 'pie',
        radius: ['42%', '68%'],
        data: channelRank.map((x: any) => ({ name: x.channel || '-', value: safeNum(x.c) })),
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 }
      }
    ]
  })

  const channelAmount = [...(d.channel_amount_bar || [])].sort(
    (a: any, b: any) => safeNum(b.amount) - safeNum(a.amount)
  )
  mountChart('ds-chart-channel-bar', {
    grid: { left: '2%', right: '2%', bottom: '18%', top: '8%', containLabel: true },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      order: 'valueDesc',
      valueFormatter: (v: any) => fmt(v)
    },
    xAxis: {
      type: 'category',
      data: channelAmount.map((x: any) => x.channel || '-'),
      axisLabel: { color: '#64748b', rotate: 30 }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#64748b' },
      splitLine: { lineStyle: { color: 'rgba(15,31,24,.08)' } }
    },
    series: [
      {
        type: 'bar',
        data: channelAmount.map((x: any) => safeNum(x.amount)),
        barMaxWidth: 36,
        itemStyle: { color: '#0f6a4f', borderRadius: [6, 6, 0, 0] }
      }
    ]
  })

  const staffDaily = d.staff_daily || { dates: [], series: [] }
  mountChart('ds-chart-staff-daily', {
    legend: { type: 'scroll', bottom: 0 },
    grid: { left: '2%', right: '2%', bottom: '18%', top: '10%', containLabel: true },
    tooltip: {
      trigger: 'axis',
      // 按「当天」收款额从高到低排名字（截图示例：张佳兴应排第一）
      order: 'valueDesc',
      valueFormatter: (v: any) => fmt(v)
    },
    xAxis: {
      type: 'category',
      data: staffDaily.dates || [],
      axisLabel: { color: '#64748b' }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#64748b' },
      splitLine: { lineStyle: { color: 'rgba(15,31,24,.08)' } }
    },
    series: (staffDaily.series || []).map((s: any, idx: number) => {
      // 默认色 = 他在列表中第 idx 位对应的调色板颜色；被指定的成员覆盖成固定色。
      // 调色板只有 8 种，成员超过 8 人时会循环复用。
      const color =
        STAFF_LINE_COLORS[String(s.name || '').trim()] ??
        STAFF_LINE_PALETTE[idx % STAFF_LINE_PALETTE.length]
      return {
        name: s.name,
        type: 'line',
        smooth: true,
        symbolSize: 3,
        data: s.data || [],
        itemStyle: { color },
        lineStyle: { color }
      }
    })
  })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await fetchDataScreen()
    payload.value = data
    // 默认保持「本月」，不自动改周期
  } catch (e: any) {
    payload.value = null
    const status = e?.response?.status
    const d = e?.response?.data
    let msg =
      (typeof d === 'string' && d.trim() && d) ||
      (d && (d.detail || d.message)) ||
      e?.message ||
      '数据大屏加载失败'
    // 后端未启动时，Vite 代理常返回空 body 的 500
    if (
      status === 500 &&
      (!d || (typeof d === 'string' && !d.trim()) || (typeof d === 'object' && !d.detail && !d.message))
    ) {
      msg =
        '无法连接后端 API（127.0.0.1:8001）。请在薪火项目根目录启动：python backend/manage.py runserver 8001'
    } else if (e?.code === 'ERR_NETWORK' || /Network Error/i.test(String(e?.message || ''))) {
      msg = '网络错误：请确认薪火后端已在 8001 端口运行'
    }
    error.value = String(msg)
  } finally {
    loading.value = false
  }
  await nextTick()
  try {
    animMode = 'enter'
    animEpoch.value++ // 数字卡随之重新从 0 滚动
    renderPeriodCharts()
    renderFixedCharts()
    requestAnimationFrame(() => {
      handleResize()
      setTimeout(handleResize, 120)
    })
  } catch (e: any) {
    console.error(e)
    error.value = e?.message ? `图表渲染失败：${e.message}` : '图表渲染失败，请刷新或联系管理员。'
  }
}

/** 静默拉取：BOT 推送后大屏三卡可近实时更新（不闪 loading） */
async function silentRefresh() {
  if (document.visibilityState !== 'visible') return
  try {
    const { data } = await fetchDataScreen()
    payload.value = data
    await nextTick()
    animMode = 'update'
    renderPeriodCharts()
    renderFixedCharts()
    animMode = 'enter' // 复位：下一次由用户操作触发的绘制仍然是入场动画
    handleResize()
  } catch {
    /* 轮询失败不打断页面 */
  }
}

let pollTimer: ReturnType<typeof setInterval> | null = null

function handleResize() {
  chartRefs.forEach((c, id) => {
    const el = c.getDom()
    const size = `${el.clientWidth}x${el.clientHeight}`
    if (chartSize.get(id) === size) return
    chartSize.set(id, size)
    c.resize()
  })
}

function toggleInternalImmersive() {
  toggleFullscreen()
  nextTick(() => handleResize())
}

function onEscapeKey(e: KeyboardEvent) {
  if (e.key === 'Escape' && isFullscreen.value) {
    exitFullscreen()
    nextTick(() => handleResize())
  }
}

watch(isFullscreen, () => nextTick(() => handleResize()))

watch(activePeriod, () => {
  nextTick(() => {
    animMode = 'enter'
    animEpoch.value++
    renderPeriodCharts()
    handleResize()
  })
})

// 白天 / 黑夜切换：echarts 的主题只能在创建时指定，所以主题一变就按新主题重绘全部图表
watch(isDark, () => {
  nextTick(() => {
    if (!payload.value) return
    animMode = 'enter'
    renderPeriodCharts()
    renderFixedCharts()
    handleResize()
  })
})

onMounted(() => {
  if (!payload.value) load()
  window.addEventListener('resize', handleResize, { passive: true })
  window.addEventListener('keydown', onEscapeKey)
  pollTimer = setInterval(silentRefresh, 8000)
})

// keep-alive 下，页面第一次进入时 onMounted 和 onActivated 都会触发；
// 第一次只由 load() 负责（含入场动画），否则 onActivated 会紧接着再画一遍，把入场动画吞掉。
// 只有「从别的页面切回来」（再次激活）才需要补一次刷新 + 重画。
let firstActivation = true
onActivated(() => {
  if (firstActivation) {
    firstActivation = false
    return
  }
  if (!payload.value) {
    load()
    return
  }
  silentRefresh()
  nextTick(() => {
    animMode = 'enter' // 切回来也让数字 / 图表重新动一遍
    animEpoch.value++
    renderPeriodCharts()
    renderFixedCharts()
    handleResize()
    requestAnimationFrame(() => handleResize())
  })
})

onBeforeUnmount(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
  if (isFullscreen.value) exitFullscreen()
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('keydown', onEscapeKey)
  chartRefs.forEach((c) => c.dispose())
  chartRefs.clear()
  // 滚动入场的观察器与排队中的图表一并清理，避免泄漏
  visObserver?.disconnect()
  visObserver = null
  pendingEnter.clear()
  symbolTimers.forEach((t) => clearTimeout(t))
  symbolTimers.clear()
})
</script>

<template>
  <div ref="pageRef" class="ds-page" :class="{ 'is-fullscreen': isFullscreen }" v-loading="loading">
    <header class="ds-toolbar">
      <div class="ds-toolbar__info">
        <h2 class="ds-title">薪火电商数据大屏</h2>
        <p class="ds-sub">
          按周期查看 GMV、收款与成员表现
          <span v-if="summary.date_from">（{{ summary.date_from }} ~ {{ summary.date_to }}）</span>
        </p>
      </div>
      <div class="ds-toolbar-actions">
        <ElSelect v-model="activePeriod" placeholder="选择周期" style="width: 120px">
          <ElOption
            v-for="def in periodDefs"
            :key="def.key"
            :label="def.label"
            :value="def.key"
          />
        </ElSelect>
        <BaseButton :icon="Refresh" @click="load">刷新</BaseButton>
        <BaseButton type="primary" :icon="FullScreen" @click="toggleInternalImmersive">
          {{ isFullscreen ? '退出全屏' : '全屏' }}
        </BaseButton>
      </div>
    </header>

    <ElAlert v-if="error" type="error" :closable="false" :title="error" />
    <ElAlert v-else-if="!loading && !payload" type="info" :closable="false" title="暂无数据" />

    <template v-if="payload">
      <!-- 1. 收款概览（含微信BOT业务卡） -->
      <section class="ds-section">
        <div class="ds-section__header">
          <h3 class="ds-section__title">收款概览</h3>
          <span class="ds-section__hint">随周期 · {{ activePeriodDef().label }}（含微信BOT）</span>
        </div>
        <div class="kpi-mosaic">
          <article
            v-for="card in overviewCards"
            :key="card.key"
            class="kpi-tile"
            :class="`kpi-tile--${card.tone || 'message'}`"
          >
            <div class="kpi-tile__head">
              <span class="kpi-tile__icon" aria-hidden="true">{{ card.icon }}</span>
              <span class="kpi-tile__title">{{ card.title }}</span>
            </div>
            <div class="kpi-tile__value">
              <span v-if="card.prefix" class="kpi-tile__prefix">{{ card.prefix }}</span>
              <span class="kpi-tile__num">
                <OdometerNumber
                  :key="`${card.key}-${animEpoch}`"
                  :value="card.value"
                  :precision="card.precision === 2 ? 2 : 0"
                  :from-zero="true"
                />
              </span>
            </div>
            <div class="kpi-tile__meta">
              <template v-if="hasKpiFooter(card)">
                <span v-if="card.footer" class="kpi-tile__meta-label">{{ card.footer }}</span>
                <span
                  v-if="card.delta !== null && card.delta !== undefined && card.delta !== ''"
                  class="kpi-tile__delta"
                  :class="`is-${deltaTone(card.delta)}`"
                >
                  {{ fmtPct(card.delta) }}
                </span>
                <span v-else-if="card.ratioText" class="kpi-tile__delta is-flat">{{
                  card.ratioText
                }}</span>
              </template>
              <span v-else class="kpi-tile__meta-spacer">&nbsp;</span>
            </div>
          </article>
        </div>
      </section>

      <!-- 2. 成员表现 -->
      <section class="ds-section">
        <div class="ds-section__header">
          <h3 class="ds-section__title">成员表现</h3>
          <span class="ds-section__hint">随周期 · {{ activePeriodDef().label }}</span>
        </div>
        <ElRow :gutter="16">
          <ElCol
            v-for="item in memberPanels"
            :key="item.id"
            :xs="24"
            :sm="12"
            :lg="6"
          >
            <ElCard shadow="never" class="ds-panel">
              <template #header>
                <div class="ds-panel-head">
                  <span class="ds-soft-icon" :class="`ds-soft-icon--${item.tone}`" aria-hidden="true">{{
                    item.icon
                  }}</span>
                  <span>{{ item.title }}</span>
                </div>
              </template>
              <div :id="item.id" class="ds-member-chart" />
            </ElCard>
          </ElCol>
        </ElRow>
      </section>

      <!-- 3. 销售趋势 -->
      <section class="ds-section">
        <div class="ds-section__header">
          <h3 class="ds-section__title">销售趋势</h3>
          <span class="ds-section__hint">不随周期筛选</span>
        </div>
        <ElRow :gutter="16">
          <ElCol :xs="24" :lg="12">
            <ElCard shadow="never" class="ds-panel">
              <template #header>
                <div class="ds-panel-head">
                  <span class="ds-soft-icon ds-soft-icon--shopping" aria-hidden="true">📈</span>
                  <span>本月销售趋势</span>
                </div>
              </template>
              <div id="ds-chart-month-trend" class="ds-chart" />
            </ElCard>
          </ElCol>
          <ElCol :xs="24" :lg="12">
            <ElCard shadow="never" class="ds-panel">
              <template #header>
                <div class="ds-panel-head">
                  <span class="ds-soft-icon ds-soft-icon--message" aria-hidden="true">📉</span>
                  <span>每月 GMV 趋势（近12个月）</span>
                </div>
              </template>
              <div id="ds-chart-history-gmv" class="ds-chart" />
            </ElCard>
          </ElCol>
        </ElRow>
      </section>

      <!-- 4. 渠道分析 -->
      <section class="ds-section">
        <div class="ds-section__header">
          <h3 class="ds-section__title">渠道分析</h3>
          <span class="ds-section__hint">随周期 · {{ activePeriodDef().label }}</span>
        </div>
        <ElRow :gutter="16">
          <ElCol :xs="24" :lg="8">
            <ElCard shadow="never" class="ds-panel">
              <template #header>
                <div class="ds-panel-head">
                  <span class="ds-soft-icon ds-soft-icon--money" aria-hidden="true">🥧</span>
                  <span>渠道订单占比</span>
                </div>
              </template>
              <div id="ds-chart-channel" class="ds-chart" />
            </ElCard>
          </ElCol>
          <ElCol :xs="24" :lg="8">
            <ElCard shadow="never" class="ds-panel">
              <template #header>
                <div class="ds-panel-head">
                  <span class="ds-soft-icon ds-soft-icon--shopping" aria-hidden="true">📊</span>
                  <span>各渠道收款净额</span>
                </div>
              </template>
              <div id="ds-chart-channel-bar" class="ds-chart" />
            </ElCard>
          </ElCol>
          <ElCol :xs="24" :lg="8">
            <ElCard shadow="never" class="ds-panel">
              <template #header>
                <div class="ds-panel-head">
                  <span class="ds-soft-icon ds-soft-icon--peoples" aria-hidden="true">🏅</span>
                  <span>渠道订单排行</span>
                </div>
              </template>
              <ElTable :data="channelRankData" stripe style="width: 100%" max-height="260">
                <ElTableColumn prop="channel" label="渠道" min-width="100" />
                <ElTableColumn label="订单数" min-width="80">
                  <template #default="scope">
                    {{ scope?.row ? fmtInt(scope.row.c) : '' }}
                  </template>
                </ElTableColumn>
              </ElTable>
            </ElCard>
          </ElCol>
        </ElRow>
      </section>

      <!-- 5. 成员明细 -->
      <section class="ds-section">
        <div class="ds-section__header">
          <h3 class="ds-section__title">成员明细</h3>
          <span class="ds-section__hint">随周期 · {{ activePeriodDef().label }}</span>
        </div>
        <ElRow :gutter="16">
          <ElCol :xs="24" :lg="14">
            <ElCard shadow="never" class="ds-panel">
              <template #header>
                <div class="ds-panel-head">
                  <span class="ds-soft-icon ds-soft-icon--message" aria-hidden="true">📈</span>
                  <span>{{ staffDailyTitle }}</span>
                </div>
              </template>
              <div id="ds-chart-staff-daily" class="ds-chart ds-chart--tall" />
            </ElCard>
          </ElCol>
          <ElCol :xs="24" :lg="10">
            <ElCard shadow="never" class="ds-panel ds-panel--rank">
              <template #header>
                <div class="ds-panel-head">
                  <span class="ds-soft-icon ds-soft-icon--money" aria-hidden="true">🏆</span>
                  <span>成员收款额排行</span>
                  <ElTag size="small" type="warning" effect="plain" class="ml-8px">
                    共 {{ staffRankData.length }} 人
                  </ElTag>
                </div>
              </template>
              <div v-for="r in staffRankData" :key="r.user__username" class="ds-rank-row">
                <div class="ds-rank-head">
                  <span>{{ r.user__username }}</span>
                  <span class="ds-rank-value"
                    >¥<OdometerNumber :key="`${r.user__username}-${animEpoch}`" :value="r.gmv" :precision="2" :from-zero="true" :wait-visible="true"
                  /></span>
                </div>
                <ElProgress
                  :percentage="r.percent"
                  :stroke-width="10"
                  :show-text="false"
                  color="var(--el-color-primary)"
                />
              </div>
              <div v-if="!staffRankData.length" class="ds-empty">暂无数据</div>
            </ElCard>
          </ElCol>
        </ElRow>
      </section>
    </template>
  </div>
</template>

<style scoped>
.ds-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
  width: 100%;
  min-height: 100%;
  padding: 16px;
  box-sizing: border-box;
  background: var(--app-content-bg-color, #f5f7fa);
}

.ds-page.is-fullscreen {
  overflow: auto;
}

/* Toolbar */
.ds-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding: 16px 20px;
  border-radius: 12px;
  background: var(--ui-surface, #fff);
  border: 1px solid var(--ui-border-soft, #eef2f7);
}

.ds-toolbar__info {
  min-width: 0;
}

.ds-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: var(--ui-text, #303133);
}

.ds-sub {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--ui-muted, #909399);
}

.ds-toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

/* Section hierarchy */
.ds-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.ds-section__header {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
}

.ds-section__title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: var(--ui-text, #1f2937);
}

.ds-section__hint {
  font-size: 12px;
  color: var(--ui-muted, #9ca3af);
}

/* KPI grids (legacy charts sections may still reference) */
.ds-kpi-grid {
  display: grid;
  gap: 12px;
}

.ds-kpi-grid--primary,
.ds-kpi-grid--secondary,
.ds-kpi-grid--bot,
.ds-kpi-grid--overview {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  align-items: stretch;
}

@media (max-width: 1199px) {
  .ds-kpi-grid--primary,
  .ds-kpi-grid--secondary,
  .ds-kpi-grid--bot,
  .ds-kpi-grid--overview {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 575px) {
  .ds-kpi-grid--primary,
  .ds-kpi-grid--secondary,
  .ds-kpi-grid--bot,
  .ds-kpi-grid--overview {
    grid-template-columns: 1fr;
  }
}

/*
 * KPI 磁贴：宽屏多列收紧，避免卡片横向拉空
 */
.kpi-mosaic {
  display: grid;
  grid-template-columns: repeat(8, minmax(0, 1fr));
  gap: 8px;
}

.kpi-tile {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-height: 0;
  padding: 10px 12px 8px;
  background: var(--ui-surface, #fff);
  border: 1px solid var(--ui-border, #e8ecf1);
  border-radius: 10px;
  box-shadow: var(--ui-shadow-sm, 0 1px 2px rgba(16, 24, 40, 0.04));
  overflow: hidden;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease,
    transform 0.15s ease;
}

.kpi-tile::before {
  content: '';
  position: absolute;
  inset: 0 auto 0 0;
  width: 3px;
  border-radius: 10px 0 0 10px;
  background: var(--kpi-accent, #36a3f7);
  opacity: 0.85;
}

.kpi-tile:hover {
  border-color: #d5dde8;
  box-shadow: var(--ui-shadow-md, 0 3px 10px rgba(16, 24, 40, 0.07));
  transform: translateY(-1px);
}

.kpi-tile--money {
  --kpi-accent: #40c9c6;
  --kpi-soft: rgba(64, 201, 198, 0.14);
  --kpi-ink: #1a9e9b;
}

.kpi-tile--message {
  --kpi-accent: #36a3f7;
  --kpi-soft: rgba(54, 163, 247, 0.14);
  --kpi-ink: #1d7ed4;
}

.kpi-tile--shopping {
  --kpi-accent: #34bfa3;
  --kpi-soft: rgba(52, 191, 163, 0.14);
  --kpi-ink: #1f9a82;
}

.kpi-tile--peoples {
  --kpi-accent: #f4516c;
  --kpi-soft: rgba(244, 81, 108, 0.12);
  --kpi-ink: #d63b54;
}

.kpi-tile__head {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}

.kpi-tile__icon {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 7px;
  font-size: 13px;
  line-height: 1;
  background: var(--kpi-soft, rgba(54, 163, 247, 0.14));
}

.kpi-tile__title {
  min-width: 0;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.2;
  color: var(--ui-text-2, #4b5563);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.kpi-tile__value {
  display: flex;
  align-items: baseline;
  gap: 2px;
  min-width: 0;
  padding-left: 1px;
  color: var(--ui-text, #111827);
  line-height: 1.1;
}

.kpi-tile__prefix {
  font-size: 12px;
  font-weight: 650;
  color: var(--ui-text-2, #374151);
}

.kpi-tile__num {
  font-size: 20px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.03em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.kpi-tile__meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  min-height: 16px;
  margin-top: auto;
  padding-left: 1px;
  font-size: 11px;
  line-height: 1.2;
}

.kpi-tile__meta-label {
  color: var(--ui-muted, #9ca3af);
}

.kpi-tile__meta-spacer {
  display: inline-block;
  min-height: 16px;
}

.kpi-tile__delta {
  font-weight: 650;
  font-variant-numeric: tabular-nums;
}

.kpi-tile__delta.is-up {
  color: #16a34a;
}

.kpi-tile__delta.is-down {
  color: #dc2626;
}

.kpi-tile__delta.is-flat {
  color: var(--ui-muted, #6b7280);
}

@media (max-width: 1399px) {
  .kpi-mosaic {
    grid-template-columns: repeat(6, minmax(0, 1fr));
  }
}

@media (max-width: 1099px) {
  .kpi-mosaic {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 767px) {
  .kpi-mosaic {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 420px) {
  .kpi-mosaic {
    grid-template-columns: 1fr;
  }

  .kpi-tile__num {
    font-size: 18px;
  }
}

/* Panel cards */
.ds-panel {
  height: 100%;
  border: 1px solid var(--ui-border-soft, #eef2f7);
  border-radius: 12px;
  background: var(--ui-surface, #fff);
  box-shadow: none;
}

.ds-panel :deep(.el-card__header) {
  padding: 14px 16px;
  border-bottom: 1px solid #f0f0f0;
}

.ds-panel :deep(.el-card__body) {
  padding: 16px;
}

.ds-panel-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--ui-text, #303133);
}

.ds-panel--rank :deep(.el-card__body) {
  max-height: 320px;
  overflow-y: auto;
}

/* Soft pastel icons for chart panel headers */
.ds-soft-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  font-size: 15px;
  line-height: 1;
  flex-shrink: 0;
}

.ds-soft-icon--peoples {
  background: rgba(64, 201, 198, 0.12);
}

.ds-soft-icon--message {
  background: rgba(54, 163, 247, 0.12);
}

.ds-soft-icon--money {
  background: rgba(244, 81, 108, 0.12);
}

.ds-soft-icon--shopping {
  background: rgba(52, 191, 163, 0.12);
}

/* Chart sizes */
.ds-member-chart {
  width: 100%;
  height: 200px;
}

.ds-chart {
  width: 100%;
  height: 260px;
}

.ds-chart--tall {
  height: 320px;
}

/* Rank list */
.ds-rank-row {
  margin-bottom: 14px;
}

.ds-rank-head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
  font-size: 13px;
  color: var(--ui-text-2, #606266);
}

.ds-rank-value {
  color: var(--el-color-primary);
  font-weight: 600;
}

.ds-empty {
  padding: 24px 0;
  text-align: center;
  color: var(--ui-muted, #909399);
}
</style>
