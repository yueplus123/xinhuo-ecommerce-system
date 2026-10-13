// 数据大屏图表动画：柱状图「逐根生长」、折线图「从左到右蜿蜒展开」。
// 只在「首次加载 / 切换周期 / 切换主题」时播放完整入场动画；8 秒一次的静默刷新只做短促的数值过渡，
// 否则每隔几秒整屏图表重播一次会很烦人。
import type { EChartsOption } from 'echarts'

export type AnimMode = 'enter' | 'update'

const prefersReducedMotion = () =>
  typeof window !== 'undefined' && !!window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches

/** 全局动画参数（入场：慢而有节奏；更新：快速平滑） */
export function baseAnimation(mode: AnimMode): Partial<EChartsOption> {
  if (prefersReducedMotion()) return { animation: false }
  return mode === 'enter'
    ? {
        animation: true,
        animationDuration: 1600,
        animationEasing: 'cubicOut',
        animationDelay: 0,
        animationDurationUpdate: 600,
        animationEasingUpdate: 'cubicInOut'
      }
    : { animation: true, animationDuration: 0, animationDurationUpdate: 500, animationEasingUpdate: 'cubicInOut' }
}

/** 柱状图：每根柱子依次错开生长（越靠后越晚开始），有「一根接一根升起来」的节奏。
 *  实测（echarts 5.6，7 根柱）：duration 1200ms + 每根错开 160ms → 第 1 根 0ms 起、第 7 根约 960ms 起，
 *  整体约 2.1 秒收尾；比默认约 0.5 秒的「一闪而过」明显得多，又不会拖沓。 */
export function barSeriesAnimation(mode: AnimMode, perItemDelay = 160) {
  if (prefersReducedMotion() || mode !== 'enter') return {}
  return {
    animationDuration: 1200,
    animationEasing: 'cubicOut',
    // 超过 12 根时压缩错开间隔，避免最后一根要等好几秒
    animationDelay: (idx: number) => Math.min(idx * perItemDelay, 1600)
  }
}

/** 折线图：从左往右「蜿蜒」描绘，最后停住。
 *  - 线条由 echarts 的 clip 动画实现（左→右）；quarticInOut：起笔缓、中段快、收笔缓。
 *  - 实测圆点（symbol）会比线先蹦出来（700ms 时内容已到 38%，而线本身只到 15%），画面显得散。
 *    所以入场期间先不显示圆点，线画完（DRAW + 错开）后再一起亮出来。
 *  - 多条线依次错开 160ms 出发，各自停在终点。 */
export const LINE_DRAW_MS = 2200
export const LINE_STAGGER_MS = 160

export function lineSeriesAnimation(mode: AnimMode, seriesIndex = 0) {
  if (prefersReducedMotion() || mode !== 'enter') return {}
  return {
    animationDuration: LINE_DRAW_MS,
    animationEasing: 'quarticInOut',
    animationDelay: seriesIndex * LINE_STAGGER_MS
  }
}

/** 入场动画全部结束需要的毫秒数（给「线画完再显示圆点」用） */
export const lineRevealAfter = (seriesCount: number) => LINE_DRAW_MS + Math.max(0, seriesCount - 1) * LINE_STAGGER_MS + 80
