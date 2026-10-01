<script setup lang="ts">
import { computed, onActivated, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import {
  ElMessage,
  ElTable,
  ElTableColumn,
  ElSelect,
  ElOption,
  ElInput,
  ElUpload,
  ElImage,
  ElPagination
} from 'element-plus'
import { ContentWrap } from '@/components/ContentWrap'
import { Search } from '@/components/Search'
import { BaseButton } from '@/components/Button'
import type { FormSchema } from '@/components/Form'
import api from '@/api/xinhuo/client'

defineOptions({ name: 'PaymentStats' })

const components = {
  ElTable,
  ElTableColumn,
  ElSelect,
  ElOption,
  ElInput,
  ElUpload,
  ElImage,
  ElPagination
}
void components

const channels = ref<any[]>([])
const users = ref<any[]>([])
const records = ref<any[]>([])
const filters = reactive({ platform: '', user_id: '', date_from: '', date_to: '' })
const batchRows = ref<any[]>([])
const previewImageUrl = ref('')
const previewDeleteMeta = ref<any>(null)
const previewImageList = ref<string[]>([])
const previewImageIndex = ref(0)
const page = ref(1)
const totalCount = ref(0)
const pageSize = ref(30)
const OTHER_CHANNEL_KEY = '其他渠道'
const batchSubmitting = ref(false)
const listLoading = ref(false)
const monthOptions = Array.from({ length: 12 }, (_, i) => i + 1)
const dayOptions = Array.from({ length: 31 }, (_, i) => i + 1)

const channelSelectOptions = computed(() =>
  channels.value.map((c) => ({ label: c[1], value: c[0] }))
)
const userSelectOptions = computed(() =>
  users.value.map((u) => ({ label: u.username, value: String(u.id) }))
)

const searchSchema = computed<FormSchema[]>(() => [
  {
    field: 'platform',
    label: '渠道',
    component: 'Select',
    componentProps: {
      options: channelSelectOptions.value,
      clearable: true,
      placeholder: '全部渠道'
    }
  },
  {
    field: 'user_id',
    label: '人员',
    component: 'Select',
    componentProps: {
      options: userSelectOptions.value,
      clearable: true,
      placeholder: '全部人员'
    }
  },
  {
    field: 'date_from',
    label: '开始日期',
    component: 'DatePicker',
    componentProps: { type: 'date', valueFormat: 'YYYY-MM-DD', placeholder: '开始' }
  },
  {
    field: 'date_to',
    label: '结束日期',
    component: 'DatePicker',
    componentProps: { type: 'date', valueFormat: 'YYYY-MM-DD', placeholder: '结束' }
  }
])

function beijingNowParts() {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour12: false
  }).formatToParts(new Date())
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? ''
  return {
    year: get('year'),
    month: String(parseInt(get('month'), 10)),
    day: String(parseInt(get('day'), 10))
  }
}

function defaultOrderDate() {
  const { month, day } = beijingNowParts()
  return { order_month: month, order_day: day }
}

function formatOrderMd(row: any) {
  const m = parseInt(String(row.order_month ?? ''), 10)
  const d = parseInt(String(row.order_day ?? ''), 10)
  if (!m || !d) return ''
  return `${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`
}

function isValidOrderDate(row: any) {
  const m = parseInt(String(row.order_month ?? ''), 10)
  const d = parseInt(String(row.order_day ?? ''), 10)
  if (!m || m < 1 || m > 12 || !d || d < 1 || d > 31) return false
  const year = parseInt(beijingNowParts().year, 10)
  const test = new Date(year, m - 1, d)
  return test.getFullYear() === year && test.getMonth() === m - 1 && test.getDate() === d
}

function parseOrderInt(row: any) {
  const s = String(row.order_count ?? '').trim()
  if (!s) return 0
  const n = parseInt(s, 10)
  return Number.isFinite(n) && n >= 0 ? n : NaN
}

function parseAmountDec(row: any) {
  const s = String(row.amount ?? '').trim()
  if (!s) return 0
  const n = parseFloat(s)
  return Number.isFinite(n) && n >= 0 ? n : NaN
}

function rowHasOrderOrAmount(row: any) {
  const oc = parseOrderInt(row)
  const am = parseAmountDec(row)
  const hasOc = String(row.order_count ?? '').trim() !== '' && Number.isFinite(oc) && oc > 0
  const hasAm = String(row.amount ?? '').trim() !== '' && Number.isFinite(am) && am > 0
  return hasOc || hasAm
}

function onOrderInput(row: any) {
  row.order_count = String(row.order_count ?? '').replace(/\D/g, '')
}

function normalizeOrderRow(row: any) {
  const s = String(row.order_count ?? '').trim()
  if (!s) {
    row.order_count = ''
    return
  }
  const n = parseInt(s.replace(/\D/g, ''), 10)
  row.order_count = Number.isFinite(n) && n >= 0 ? String(n) : ''
}

function onAmountInput(row: any) {
  let s = String(row.amount ?? '')
  let out = ''
  let dotSeen = false
  for (const ch of s) {
    if (ch >= '0' && ch <= '9') out += ch
    else if (ch === '.' && !dotSeen) {
      out += '.'
      dotSeen = true
    }
  }
  if (dotSeen) {
    const parts = out.split('.')
    const intp = parts[0] ?? ''
    const dec = (parts[1] ?? '').slice(0, 2)
    out = dec.length ? `${intp}.${dec}` : intp + '.'
  }
  row.amount = out
}

function normalizeAmountRow(row: any) {
  const s = String(row.amount ?? '').trim()
  if (!s) {
    row.amount = ''
    return
  }
  const n = parseFloat(s)
  if (!Number.isFinite(n) || n < 0) {
    row.amount = ''
    return
  }
  row.amount = n.toFixed(2)
}

function rowHasScreenshots(row: any) {
  return Array.isArray(row.screenshots) && row.screenshots.length > 0
}

function validateBatchRows() {
  const msgs: string[] = []
  for (const r of batchRows.value) {
    normalizeOrderRow(r)
    normalizeAmountRow(r)
    const ocStr = String(r.order_count ?? '').trim()
    if (ocStr && !/^\d+$/.test(ocStr)) msgs.push(`「${r.label}」订单数须为非负整数。`)
    const amStr = String(r.amount ?? '').trim()
    if (amStr && !/^\d+\.\d{2}$/.test(amStr))
      msgs.push(`「${r.label}」金额须保留两位小数（如 12.00）。`)
    const hasOA = rowHasOrderOrAmount(r)
    const hasShot = rowHasScreenshots(r)
    if (hasOA && !hasShot) msgs.push(`「${r.label}」已填写订单数或金额，请上传截图。`)
    if (r.channel === OTHER_CHANNEL_KEY) {
      if ((hasOA || hasShot) && !String(r.note || '').trim()) {
        msgs.push(`「${r.label}」已填写订单数、金额或截图，请填写备注。`)
      }
    }
    if ((hasOA || hasShot) && !isValidOrderDate(r)) {
      msgs.push(`「${r.label}」请选择有效的订单日期（月+日）。`)
    }
  }
  return msgs
}

function onScreenshotsChange(row: any, uploadFile: any) {
  const f = uploadFile?.raw
  if (!f) return
  row.screenshots = [...(row.screenshots || []), f]
  row.preview_urls = [...(row.preview_urls || []), URL.createObjectURL(f)]
}

function revokePreviewUrls(row: any) {
  ;(row.preview_urls || []).forEach((u: string) => {
    try {
      URL.revokeObjectURL(u)
    } catch (_) {}
  })
}

function clearScreenshots(row: any) {
  revokePreviewUrls(row)
  row.screenshots = []
  row.preview_urls = []
}

function clearBatchInputs() {
  const def = defaultOrderDate()
  batchRows.value.forEach((row) => {
    row.order_month = def.order_month
    row.order_day = def.order_day
    row.order_count = ''
    row.amount = ''
    row.note = ''
    clearScreenshots(row)
  })
}

function toBeijingDateTime(v: any) {
  if (!v) return '—'
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return String(v)
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai',
    hour12: false,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
    .format(d)
    .replace(/\//g, '-')
}

function formatOrderDate(v: any) {
  if (!v) return '—'
  return String(v).trim().slice(0, 10) || '—'
}

function applyPreviewAt(index: number) {
  const list = previewImageList.value || []
  if (!list.length) {
    previewImageUrl.value = ''
    previewImageIndex.value = 0
    return
  }
  const idx = Math.max(0, Math.min(index, list.length - 1))
  previewImageIndex.value = idx
  previewImageUrl.value = list[idx] || ''
}

function openBatchImagePreview(row: any, index: number) {
  previewImageList.value = [...(row.preview_urls || [])]
  applyPreviewAt(index)
  previewDeleteMeta.value = { channel: row.channel, index }
}

function closeImagePreview() {
  previewImageUrl.value = ''
  previewDeleteMeta.value = null
  previewImageList.value = []
  previewImageIndex.value = 0
}

function previewPrev() {
  if (previewImageIndex.value <= 0) return
  applyPreviewAt(previewImageIndex.value - 1)
  if (previewDeleteMeta.value) previewDeleteMeta.value.index = previewImageIndex.value
}

function previewNext() {
  if (previewImageIndex.value >= previewImageList.value.length - 1) return
  applyPreviewAt(previewImageIndex.value + 1)
  if (previewDeleteMeta.value) previewDeleteMeta.value.index = previewImageIndex.value
}

function deleteCurrentPreviewImage() {
  if (!previewDeleteMeta.value) return
  const { channel, index } = previewDeleteMeta.value
  const row = batchRows.value.find((r) => r.channel === channel)
  if (!row) {
    closeImagePreview()
    return
  }
  const oldUrl = (row.preview_urls || [])[index]
  if (oldUrl) {
    try {
      URL.revokeObjectURL(oldUrl)
    } catch (_) {}
  }
  row.preview_urls = (row.preview_urls || []).filter((_: any, i: number) => i !== index)
  row.screenshots = (row.screenshots || []).filter((_: any, i: number) => i !== index)
  previewImageList.value = [...row.preview_urls]
  if (!previewImageList.value.length) {
    closeImagePreview()
    return
  }
  applyPreviewAt(Math.min(index, previewImageList.value.length - 1))
  previewDeleteMeta.value.index = previewImageIndex.value
}

async function loadMeta() {
  const [{ data: m }, { data: us }] = await Promise.all([
    api.get('/payment-meta/'),
    api.get('/staff-users/')
  ])
  channels.value = m.channels || []
  users.value = us || []
  const def = defaultOrderDate()
  batchRows.value = channels.value.map((c) => ({
    channel: c[0],
    label: c[1],
    order_month: def.order_month,
    order_day: def.order_day,
    order_count: '',
    amount: '',
    note: '',
    screenshots: [],
    preview_urls: []
  }))
}

async function loadRecords(resetPage = true) {
  if (resetPage) page.value = 1
  listLoading.value = true
  try {
    const { data } = await api.get('/payment-records/', {
      params: { ...filters, page: page.value }
    })
    if (Array.isArray(data)) {
      records.value = data
      totalCount.value = data.length
      return
    }
    records.value = data.results || []
    totalCount.value = data.count ?? records.value.length
  } finally {
    listLoading.value = false
  }
}

function onSearch(params: Recordable) {
  filters.platform = params.platform || ''
  filters.user_id = params.user_id || ''
  filters.date_from = params.date_from || ''
  filters.date_to = params.date_to || ''
  loadRecords(true)
}

function onReset() {
  filters.platform = ''
  filters.user_id = ''
  filters.date_from = ''
  filters.date_to = ''
  loadRecords(true)
}

async function exportExcel() {
  const resp = await api.get('/payment-records/export/', {
    params: { ...filters },
    responseType: 'blob'
  })
  const url = URL.createObjectURL(resp.data)
  const a = document.createElement('a')
  a.href = url
  a.download = 'payment_records.xlsx'
  a.click()
  URL.revokeObjectURL(url)
}

function newBatchId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID()
  return `batch-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

async function submitBatch() {
  if (batchSubmitting.value) return
  const msgs = validateBatchRows()
  if (msgs.length) {
    ElMessage.error(msgs.join('；'))
    return
  }
  batchSubmitting.value = true
  try {
    const fd = new FormData()
    fd.append('batch_id', newBatchId())
    batchRows.value.forEach((row, idx) => {
      fd.append('channels', row.channel)
      fd.append(`order_count_${idx}`, String(parseInt(String(row.order_count || '0'), 10) || 0))
      fd.append(`amount_${idx}`, String(parseFloat(String(row.amount || '0')) || 0))
      fd.append(`note_${idx}`, row.note || '')
      fd.append(`order_md_${idx}`, formatOrderMd(row))
      ;(row.screenshots || []).forEach((f: File) => fd.append(`screenshots_${idx}`, f))
    })
    const { data } = await api.post('/payment-records/batch-submit/', fd, {
      timeout: Number(import.meta.env.VITE_API_TIMEOUT_MS) || 120000
    })
    if (data?.duplicate) {
      ElMessage.error(data.detail || '该批次已提交，请勿重复点击')
      return
    }
    const n = data?.created ?? 0
    clearBatchInputs()
    if (n > 0) ElMessage.success(`已成功提交 ${n} 条，表单已清空。`)
    else ElMessage.warning('没有可提交的数据。')
    loadRecords().catch(() => {})
  } catch (e: any) {
    const d = e?.response?.data
    const msg =
      (typeof d === 'string' && d) ||
      d?.detail ||
      (e?.code === 'ECONNABORTED'
        ? '上传超时，请检查网络后在下方的列表确认是否已成功，勿重复点击。'
        : null) ||
      e?.message ||
      '提交失败，请稍后重试'
    ElMessage.error(String(msg))
  } finally {
    batchSubmitting.value = false
  }
}

function onShotUpload(row: any) {
  return (file: any) => onScreenshotsChange(row, file)
}

function onPageChange(p: number) {
  page.value = p
  loadRecords(false)
}

let metaLoaded = false

async function ensureLoaded() {
  if (metaLoaded) return
  try {
    await Promise.all([loadMeta(), loadRecords()])
    metaLoaded = true
  } catch {
    // 失败时允许下次再试
  }
}

onMounted(() => {
  ensureLoaded()
})

onActivated(() => {
  // keep-alive 回来时不重复拉全量；列表可手动搜索刷新
  ensureLoaded()
})

onBeforeUnmount(() => {
  batchRows.value.forEach((row) => revokePreviewUrls(row))
})
</script>

<template>
  <div>
    <ContentWrap title="批量录入" class="mb-16px">
      <el-table :data="batchRows" border stripe style="width: 100%">
        <el-table-column label="订单时间" min-width="200">
          <template #default="scope">
            <div v-if="scope?.row" class="order-date-cell">
              <el-select v-model="scope.row.order_month" style="width: 88px">
                <el-option v-for="m in monthOptions" :key="m" :label="`${m}月`" :value="String(m)" />
              </el-select>
              <el-select v-model="scope.row.order_day" style="width: 88px">
                <el-option v-for="d in dayOptions" :key="d" :label="`${d}日`" :value="String(d)" />
              </el-select>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="label" label="渠道" min-width="120" />
        <el-table-column label="订单数" width="120">
          <template #default="scope">
            <el-input
              v-if="scope?.row"
              v-model="scope.row.order_count"
              placeholder="整数"
              @input="onOrderInput(scope.row)"
              @blur="normalizeOrderRow(scope.row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="金额" width="130">
          <template #default="scope">
            <el-input
              v-if="scope?.row"
              v-model="scope.row.amount"
              placeholder="0.00"
              @input="onAmountInput(scope.row)"
              @blur="normalizeAmountRow(scope.row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="截图" min-width="200">
          <template #default="scope">
            <div v-if="scope?.row" class="shot-cell">
              <el-upload
                :auto-upload="false"
                :show-file-list="false"
                multiple
                accept="image/*"
                :on-change="onShotUpload(scope.row)"
              >
                <BaseButton type="primary">上传</BaseButton>
              </el-upload>
              <span class="shot-count">{{ (scope.row.screenshots || []).length }} 张</span>
              <BaseButton
                v-if="(scope.row.screenshots || []).length"
                @click="clearScreenshots(scope.row)"
              >
                清空
              </BaseButton>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="预览" min-width="180">
          <template #default="scope">
            <div v-if="scope?.row" class="shot-preview">
              <img
                v-for="(u, i) in (scope.row.preview_urls || []).slice(0, 8)"
                :key="`${scope.row.channel}-${i}`"
                :src="u"
                class="shot-thumb"
                alt="预览"
                @click="openBatchImagePreview(scope.row, i)"
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="140">
          <template #default="scope">
            <el-input v-if="scope?.row" v-model="scope.row.note" />
          </template>
        </el-table-column>
      </el-table>
      <div class="mt-12px flex justify-end">
        <BaseButton type="primary" :loading="batchSubmitting" @click="submitBatch">
          {{ batchSubmitting ? '提交中…' : '一键提交' }}
        </BaseButton>
      </div>
    </ContentWrap>

    <ContentWrap title="收款统计">
      <Search :schema="searchSchema" @search="onSearch" @reset="onReset" />
      <div class="mb-10px">
        <BaseButton type="primary" @click="exportExcel">导出 Excel</BaseButton>
      </div>
      <el-table v-loading="listLoading" :data="records" border stripe style="width: 100%">
        <el-table-column prop="channel_label" label="渠道" min-width="120" />
        <el-table-column prop="order_count" label="订单" width="90" />
        <el-table-column prop="amount" label="金额" width="110" />
        <el-table-column prop="user_name" label="人员" min-width="100" />
        <el-table-column label="备注" min-width="140" show-overflow-tooltip>
          <template #default="scope">
            {{ scope?.row ? (scope.row.note ?? '').trim() || '—' : '' }}
          </template>
        </el-table-column>
        <el-table-column label="截图" min-width="180">
          <template #default="scope">
            <div v-if="scope?.row" class="shot-preview">
              <el-image
                v-for="(u, i) in (scope.row.screenshot_urls || []).slice(0, 6)"
                :key="`${scope.row.id}-${i}`"
                :src="u"
                :preview-src-list="scope.row.screenshot_urls || []"
                :initial-index="i"
                lazy
                fit="cover"
                class="shot-thumb"
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column label="订单时间" min-width="120">
          <template #default="scope">
            {{ scope?.row ? formatOrderDate(scope.row.record_date) : '' }}
          </template>
        </el-table-column>
        <el-table-column label="填写时间" min-width="160">
          <template #default="scope">
            {{ scope?.row ? toBeijingDateTime(scope.row.created_at) : '' }}
          </template>
        </el-table-column>
      </el-table>
      <div class="mt-12px flex justify-end">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          layout="total, prev, pager, next"
          :total="totalCount"
          @current-change="onPageChange"
        />
      </div>
    </ContentWrap>

    <div v-if="previewImageUrl" class="img-preview-mask" @click.self="closeImagePreview">
      <div class="img-preview-panel">
        <BaseButton @click="closeImagePreview">关闭</BaseButton>
        <BaseButton v-if="previewImageList.length > 1" @click="previewPrev">上一张</BaseButton>
        <BaseButton v-if="previewImageList.length > 1" @click="previewNext">下一张</BaseButton>
        <BaseButton v-if="previewDeleteMeta" type="danger" @click="deleteCurrentPreviewImage">
          删除
        </BaseButton>
        <img :src="previewImageUrl" alt="截图大图" class="img-preview-main" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.order-date-cell {
  display: flex;
  gap: 6px;
}
.shot-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.shot-count {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.shot-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.shot-thumb {
  width: 40px;
  height: 40px;
  object-fit: cover;
  border-radius: 4px;
  cursor: pointer;
}
.img-preview-mask {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: rgba(0, 0, 0, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
}
.img-preview-panel {
  position: relative;
  max-width: 90vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
}
.img-preview-main {
  max-width: 85vw;
  max-height: 75vh;
  object-fit: contain;
  border-radius: 8px;
}
</style>
