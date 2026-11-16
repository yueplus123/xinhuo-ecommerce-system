<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getCardFx, type CardFxPayload } from '@/api/xinhuo/cardFx'
import { useXinhuoAuthStore } from '@/store/modules/xinhuoAuth'

defineOptions({ name: 'CardFxStrip' })

const MIN_KEY = 'xh_fx_min'
const data = ref<CardFxPayload | null>(null)
const state = ref<'loading' | 'ok' | 'hidden' | 'error'>('loading')
const min = ref(false)
try {
  min.value = localStorage.getItem(MIN_KEY) === '1'
} catch {
  /* 无痕模式等读不到就默认展开 */
}

function toggle() {
  min.value = !min.value
  try {
    localStorage.setItem(MIN_KEY, min.value ? '1' : '0')
  } catch {
    /* ignore */
  }
}

function md(s: string | null) {
  if (!s) return ''
  const [, m, d] = s.split('-')
  return `${Number(m)}月${Number(d)}日`
}

const peek = computed(() => {
  const it = data.value?.items || []
  return [it[0], it[4], it[9]].filter(Boolean)
})

async function load() {
  if (useXinhuoAuthStore().isGuest) {
    state.value = 'hidden'
    return
  }
  state.value = 'loading'
  try {
    const res = await getCardFx()
    data.value = res.data
    state.value = 'ok'
  } catch (e: any) {
    // 游客没有权限：整块不显示
    state.value = e?.response?.status === 403 || e?.response?.status === 401 ? 'hidden' : 'error'
  }
}

onMounted(load)
</script>

<template>
  <section
    v-if="state !== 'hidden'"
    class="fx mb-16px"
    :class="{ stale: data?.is_stale, min: min }"
    aria-label="日元充值汇率"
  >
    <div class="fx-h">
      <span class="ic">¥</span>
      <template v-if="state === 'loading'">
        <span class="tt">日元充值</span><span class="meta">加载中…</span>
      </template>
      <template v-else-if="state === 'error'">
        <span class="tt">日元充值</span>
        <span class="meta">汇率加载失败</span>
        <span class="sp"></span>
        <button type="button" class="tg" @click="load">重试</button>
      </template>
      <template v-else-if="data && !data.has_data">
        <span class="tt">日元充值</span><span class="sp"></span>
        <button type="button" class="tg" :aria-expanded="!min" @click="toggle">
          {{ min ? '展开 ▾' : '收起 ▴' }}
        </button>
      </template>
      <template v-else-if="data">
        <span class="tt">日元充值该充多少美元</span>
        <span class="meta">
          <span class="pill">× <b>{{ data.factor_percent }}%</b></span>
          <span class="pill">1 美元 = {{ data.usd_cny }} 人民币</span>
          <span v-if="data.is_stale" class="fx-warn">
            ⚠️ 汇率已 {{ data.stale_days }} 天未更新，充值请多留余量（{{ md(data.rate_date) }}）
          </span>
          <span v-else>汇率日期 {{ md(data.rate_date) }}</span>
        </span>
        <span class="sp"></span>
        <span v-if="min" class="meta">
          <span v-for="it in peek" :key="it.jpy" class="pill">
            {{ it.jpy.toLocaleString('en-US') }} → <b>{{ it.usd }}</b>
          </span>
        </span>
        <button type="button" class="tg" :aria-expanded="!min" @click="toggle">
          {{ min ? '展开 ▾' : '收起 ▴' }}
        </button>
      </template>
    </div>
    <template v-if="state === 'ok' && data && !min">
      <div v-if="!data.has_data" class="fx-empty">还没有汇率数据，请联系管理员执行一次取数</div>
      <div v-else class="fx-grid">
        <div v-for="it in data.items" :key="it.jpy" class="fx-it">
          <span class="j">{{ it.jpy.toLocaleString('en-US') }} 日元</span>
          <span class="u">{{ it.usd }}</span>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.fx {
  --g: #00704a;
  --house: #1e3932;
  --g-soft: #d4e9e2;
  --g-bg: #eef6f2;
  --card: #fff;
  --line: #e4e7ed;
  --muted: #6b7280;
  --ink2: #374151;
  --warn: #b45309;
  --warn-bg: #fff7e0;
  --warn-line: #f5d58a;
  --mono: ui-monospace, 'SF Mono', 'JetBrains Mono', Menlo, Consolas, monospace;

  overflow: hidden;
  background: var(--g-bg);
  border: 1.5px solid var(--g);
  border-radius: 12px;
}

:global(html.dark) .fx {
  --g: #2fa37a;
  --house: #a7e3c9;
  --g-soft: #173a2e;
  --g-bg: #122a21;
  --card: #1d1e1f;
  --line: #2a312e;
  --muted: #9ca3af;
  --ink2: #d1d5db;
  --warn: #fbbf24;
  --warn-bg: #2e2610;
  --warn-line: #6b5520;
}

.fx-h {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
}

.fx-h .ic {
  display: flex;
  width: 30px;
  height: 30px;
  font-size: 16px;
  color: #fff;
  background: var(--g);
  border-radius: 8px;
  flex: none;
  align-items: center;
  justify-content: center;
}

.fx-h .tt {
  font-size: 16px;
  font-weight: 800;
  color: var(--house);
}

.fx-h .meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--muted);
}

.fx-h .pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  font-family: var(--mono);
  font-variant-numeric: tabular-nums;
  color: var(--ink2);
  white-space: nowrap;
  background: var(--card);
  border: 1px solid var(--g-soft);
  border-radius: 999px;
}

.fx-h .pill b {
  color: var(--g);
}

.fx-h .sp {
  flex: 1;
}

.fx-h .tg {
  min-height: 30px;
  padding: 0 10px;
  font-size: 13px;
  color: var(--g);
  white-space: nowrap;
  cursor: pointer;
  background: var(--card);
  border: 1px solid var(--g-soft);
  border-radius: 8px;
}

.fx-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
  padding: 0 14px 12px;
}

.fx-it {
  display: flex;
  min-width: 0;
  padding: 6px 10px;
  background: var(--card);
  border: 1px solid var(--line);
  border-left: 4px solid var(--g);
  border-radius: 8px;
  flex-direction: column;
  gap: 1px;
}

.fx-it .j {
  font-family: var(--mono);
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  color: var(--muted);
  white-space: nowrap;
}

.fx-it .u {
  font-family: var(--mono);
  font-size: 24px;
  font-variant-numeric: tabular-nums;
  font-weight: 800;
  line-height: 1.15;
  color: var(--g);
  white-space: nowrap;
}

.fx.stale {
  background: var(--warn-bg);
  border-color: var(--warn-line);
}

.fx.stale .fx-h .ic {
  background: var(--warn);
}

.fx-warn {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 700;
  color: var(--warn);
}

.fx-empty {
  padding: 0 14px 12px;
  font-size: 14px;
  color: var(--muted);
}

@media (width <= 900px) {
  .fx-h .tt {
    min-width: 0;
    flex: 1;
  }

  .fx-h .sp {
    display: none;
  }

  .fx-h .tg {
    order: 2;
  }

  .fx-h .meta {
    order: 3;
    width: 100%;
  }

  .fx-h .meta + .meta {
    order: 4;
  }

  .fx-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    grid-template-rows: repeat(5, auto);
    grid-auto-flow: column;
  }

  .fx-it .u {
    font-size: 22px;
  }
}
</style>
