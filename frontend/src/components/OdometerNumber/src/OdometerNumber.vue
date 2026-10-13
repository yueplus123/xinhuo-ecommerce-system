<script setup lang="ts">
// 里程表式数字：页面刷新 / 数值变化时，从 0（或上一个值）滚动到目标值后固定。
// 实现：requestAnimationFrame + easeOutExpo，逐帧更新文本；等宽数字（tabular-nums）避免宽度抖动。
// 遵守系统「减少动态效果」：开启时直接显示最终值。
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    value: number | string | null | undefined
    /** 小数位数；0 表示整数 */
    precision?: number
    /** 动画时长（毫秒） */
    duration?: number
    /** 为 true 时每次 value 变化都从 0 重新滚（用于刷新页面 / 切换周期）；false 则从当前显示值滚到新值 */
    fromZero?: boolean
    /** 为 true 时：数字不在屏幕内就先停在 0，等它第一次滚进视口再开始滚动（页面下方的数字不会在看不见时就滚完） */
    waitVisible?: boolean
  }>(),
  { precision: 0, duration: 1400, fromZero: false, waitVisible: false }
)

const display = ref('')
let raf = 0
let current = 0 // 当前已显示（动画中）的数值

const toNum = (v: unknown) => {
  const n = Number(v ?? 0)
  return Number.isFinite(n) ? n : 0
}
const format = (n: number) =>
  n.toLocaleString('zh-CN', { minimumFractionDigits: props.precision, maximumFractionDigits: props.precision })

// easeOutExpo：开头飞快、末尾缓缓停住，像里程表减速
const ease = (t: number) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t))

const reduceMotion = () =>
  typeof window !== 'undefined' && !!window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches

function run(from: number, to: number) {
  cancelAnimationFrame(raf)
  if (from === to || reduceMotion() || props.duration <= 0) {
    current = to
    display.value = format(to)
    return
  }
  const t0 = performance.now()
  const step = (now: number) => {
    const p = Math.min(1, (now - t0) / props.duration)
    current = from + (to - from) * ease(p)
    display.value = format(p >= 1 ? to : current)
    if (p < 1) raf = requestAnimationFrame(step)
    else current = to
  }
  raf = requestAnimationFrame(step)
}

const root = ref<HTMLElement | null>(null)
let io: IntersectionObserver | null = null
let started = !props.waitVisible // 是否已经开始过第一次滚动
let pendingTo: number | null = null // 还没进入视口时，先记住目标值

const inView = (el: HTMLElement) => {
  const r = el.getBoundingClientRect()
  const vh = window.innerHeight || document.documentElement.clientHeight
  return r.height >= 0 && r.bottom > 0 && r.top < vh
}

function start(to: number) {
  started = true
  pendingTo = null
  io?.disconnect()
  io = null
  run(0, to)
}

watch(
  () => toNum(props.value),
  (to, old) => {
    if (!started) {
      // 屏幕外：先显示 0，值先记下；滚进视口时再开始
      pendingTo = to
      display.value = format(0)
      current = 0
      if (root.value && inView(root.value)) start(to)
      return
    }
    run(props.fromZero || old === undefined ? 0 : current, to)
  },
  { immediate: true }
)

onMounted(() => {
  if (started || !root.value) return
  if (inView(root.value)) {
    if (pendingTo !== null) start(pendingTo)
    return
  }
  if (typeof IntersectionObserver === 'undefined') {
    start(pendingTo ?? toNum(props.value))
    return
  }
  io = new IntersectionObserver(
    (entries) => {
      if (entries.some((e) => e.isIntersecting)) start(pendingTo ?? toNum(props.value))
    },
    { threshold: 0.2 }
  )
  io.observe(root.value)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  io?.disconnect()
})
</script>

<template>
  <span ref="root" class="odometer" :data-final="format(toNum(value))">{{ display }}</span>
</template>

<style scoped>
.odometer {
  font-variant-numeric: tabular-nums;
  font-feature-settings: 'tnum';
}
</style>
