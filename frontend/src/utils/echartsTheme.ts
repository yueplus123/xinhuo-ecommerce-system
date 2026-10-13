// echarts 暗色主题（GitHub Primer dark）：图表里写死的 '#64748b' 等浅色下的文字 / 网格色，
// 在暗色下用主题的 textStyle / axis 默认值接管，页面不用逐个改配置。
import * as echarts from 'echarts'

export const ECHARTS_DARK = 'xinhuo-dark'

const FG = '#8b949e' // 次要文字
const GRID = 'rgb(240 246 252 / 10%)'
const LINE = '#30363d'

const axis = {
  axisLine: { lineStyle: { color: LINE } },
  axisTick: { lineStyle: { color: LINE } },
  axisLabel: { color: FG },
  splitLine: { lineStyle: { color: GRID } },
  splitArea: { show: false }
}

let registered = false
export function registerEchartsThemes() {
  if (registered) return
  registered = true
  echarts.registerTheme(ECHARTS_DARK, {
    darkMode: true,
    backgroundColor: 'transparent',
    textStyle: { color: FG },
    title: { textStyle: { color: '#e6edf3' }, subtextStyle: { color: FG } },
    legend: { textStyle: { color: FG }, pageTextStyle: { color: FG }, pageIconColor: FG, pageIconInactiveColor: '#484f58' },
    tooltip: {
      backgroundColor: '#1c2128',
      borderColor: LINE,
      textStyle: { color: '#e6edf3' }
    },
    categoryAxis: axis,
    valueAxis: axis,
    logAxis: axis,
    timeAxis: axis,
    line: { symbol: 'circle' },
    pie: { itemStyle: { borderColor: '#161b22' } }
  })
}

/** 当前应使用的主题名；亮色返回 undefined（用 echarts 默认主题，保持原外观） */
export const echartsThemeName = (isDark: boolean) => (isDark ? ECHARTS_DARK : undefined)
