<script setup lang="ts">
// 日元充值汇率：汇率每天自动取数（只读）；系数只能在这里改，职员端大厅顶部和企微群推送都用它
import { onMounted, ref } from 'vue'
import { ElAlert, ElButton, ElDescriptions, ElDescriptionsItem, ElInput, ElMessage, ElTag } from 'element-plus'
import ContentWrap from '@/components/ContentWrap.vue'
import { getCardFxSettings, saveCardFxFactor, type CardFxPayload } from '@/api/modules/cardFx'
import { formatDateTime, formatRequestError } from '@/utils/format'

defineOptions({ name: 'ManageCardFx' })

const PRESETS = ['1.020', '1.025', '1.028', '1.030']

const saved = ref<CardFxPayload | null>(null)
const preview = ref<CardFxPayload | null>(null)
const factor = ref('')
const err = ref('')
const loadErr = ref('')
const saving = ref(false)
let timer: number | undefined
let seq = 0

function md(s: string | null) {
  if (!s) return ''
  const [y, m, d] = s.split('-')
  return `${y}年${Number(m)}月${Number(d)}日`
}

const sourceName: Record<string, string> = {
  frankfurter: 'Frankfurter（欧洲央行）',
  'er-api': 'ExchangeRate-API',
  'currency-api': 'currency-api'
}

async function load() {
  loadErr.value = ''
  try {
    const { data } = await getCardFxSettings()
    saved.value = data
    preview.value = data
    factor.value = data.saved_factor.replace(/0+$/, '').replace(/\.$/, '.0')
  } catch (e) {
    loadErr.value = formatRequestError(e, '加载失败')
  }
}

function onInput() {
  window.clearTimeout(timer)
  timer = window.setTimeout(runPreview, 250)
}

async function runPreview() {
  const v = factor.value.trim()
  const my = ++seq
  if (!v) {
    err.value = '请输入系数'
    return
  }
  try {
    const { data } = await getCardFxSettings(v)
    if (my !== seq) return
    err.value = ''
    preview.value = data
  } catch (e) {
    if (my !== seq) return
    err.value = formatRequestError(e, '系数不正确')
  }
}

function pick(v: string) {
  factor.value = v
  runPreview()
}

async function save() {
  saving.value = true
  try {
    const { data } = await saveCardFxFactor(factor.value.trim())
    saved.value = data
    preview.value = data
    err.value = ''
    ElMessage.success(`已保存：系数 ${data.factor_percent}%，职员端和下一次群推送立即生效`)
  } catch (e) {
    err.value = formatRequestError(e, '保存失败')
  } finally {
    saving.value = false
  }
}

const dirty = () => !!saved.value && !!preview.value && preview.value.factor !== saved.value.saved_factor

onMounted(load)
</script>

<template>
  <ContentWrap title="日元充值汇率">
    <ElAlert v-if="loadErr" :title="loadErr" type="error" show-icon :closable="false" class="mb" />
    <template v-if="saved">
      <p class="hint">
        应充美元 = 日元 ÷ 美元兑日元汇率 × 系数，向上取整到美分。汇率每天自动更新（23:30、08:00 取数，08:30 推送到企微群），这里只改系数。
      </p>

      <h3 class="sec">当前汇率（自动，只读）</h3>
      <ElAlert
        v-if="!saved.has_data"
        title="还没有汇率数据：请在服务器上执行一次 fetch_card_fx_rate"
        type="warning"
        show-icon
        :closable="false"
        class="mb"
      />
      <ElDescriptions v-else :column="2" border class="mb">
        <ElDescriptionsItem label="汇率日期">
          {{ md(saved.rate_date) }}
          <ElTag v-if="saved.is_stale" type="warning" size="small" class="ml">已 {{ saved.stale_days }} 天未更新</ElTag>
        </ElDescriptionsItem>
        <ElDescriptionsItem label="数据来源">{{ sourceName[saved.source || ''] || saved.source }}</ElDescriptionsItem>
        <ElDescriptionsItem label="1 美元 = 日元"><span class="mono">{{ saved.usd_jpy }}</span></ElDescriptionsItem>
        <ElDescriptionsItem label="1 美元 = 人民币"><span class="mono">{{ saved.usd_cny }}</span></ElDescriptionsItem>
        <ElDescriptionsItem label="取数时间">{{ saved.fetched_at ? formatDateTime(saved.fetched_at) : '—' }}</ElDescriptionsItem>
      </ElDescriptions>

      <h3 class="sec">系数</h3>
      <div class="row">
        <ElInput v-model="factor" class="factor" placeholder="例如 1.025" @input="onInput" @keyup.enter="save">
          <template #append>= {{ preview?.factor_percent ?? '—' }}%</template>
        </ElInput>
        <ElButton v-for="p in PRESETS" :key="p" size="small" @click="pick(p)">{{ p }}</ElButton>
        <ElButton type="primary" :loading="saving" :disabled="!!err || !dirty()" @click="save">保存</ElButton>
      </div>
      <div v-if="err" class="err">{{ err }}</div>
      <div class="sub">
        范围 1.000 – 1.100，最多 4 位小数。已保存：{{ saved.saved_factor }}
        <template v-if="saved.settings_updated_by">
          · 最后修改 {{ saved.settings_updated_by }}
          {{ saved.settings_updated_at ? formatDateTime(saved.settings_updated_at) : '' }}
        </template>
      </div>

      <template v-if="preview?.has_data">
        <h3 class="sec">
          {{ dirty() ? '预览（还没保存）' : '职员看到的金额' }}
        </h3>
        <div class="grid">
          <div v-for="it in preview.items" :key="it.jpy" class="it" :class="{ draft: dirty() }">
            <span class="j">{{ it.jpy.toLocaleString('en-US') }} 日元</span>
            <span class="u">${{ it.usd }}</span>
          </div>
        </div>
      </template>
    </template>
  </ContentWrap>
</template>

<style scoped>
.hint {
  margin: 0 0 16px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.sec {
  margin: 20px 0 10px;
  font-size: 15px;
}
.mb {
  margin-bottom: 12px;
}
.ml {
  margin-left: 8px;
}
.mono,
.it .j,
.it .u {
  font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace;
  font-variant-numeric: tabular-nums;
}
.row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.factor {
  width: 220px;
}
.err {
  margin-top: 6px;
  color: var(--el-color-danger);
  font-size: 13px;
}
.sub {
  margin-top: 6px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
}
.it {
  display: flex;
  flex-direction: column;
  padding: 6px 10px;
  border: 1px solid var(--el-border-color-lighter);
  border-left: 4px solid #00704a;
  border-radius: 8px;
}
.it.draft {
  border-left-color: var(--el-color-warning);
}
.it .j {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.it .u {
  font-size: 20px;
  font-weight: 800;
  color: #00704a;
}
.it.draft .u {
  color: var(--el-color-warning-dark-2);
}
@media (max-width: 900px) {
  .grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
