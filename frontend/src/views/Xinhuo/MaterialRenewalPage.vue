<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  ElDatePicker,
  ElDialog,
  ElDropdown,
  ElDropdownItem,
  ElDropdownMenu,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElSelect,
  ElSkeleton,
  ElSwitch
} from 'element-plus'
import { ContentWrap } from '@/components/ContentWrap'
import { BaseButton } from '@/components/Button'
import { Icon } from '@/components/Icon'
import api from '@/api/xinhuo/client'

defineOptions({ name: 'MaterialRenewal' })

const rows = ref<any[]>([])
const loading = ref(false)
const searchQ = ref('')

const emptyForm = () => ({
  name: '',
  category: '',
  amount: null as number | null,
  currency: 'CNY',
  cycle_type: 'yearly',
  cycle_days: null as number | null,
  next_due_at: '',
  remark: '',
  is_active: true
})

const createOpen = ref(false)
const createForm = ref(emptyForm())
const editOpen = ref(false)
const editId = ref<number | null>(null)
const editForm = ref(emptyForm())
const renewOpen = ref(false)
const renewRow = ref<any>(null)
const renewDate = ref('')
const renewAuto = ref(true)

const detailOpen = ref(false)
const detailRow = ref<any>(null)

const cycleOptions = [
  { value: 'monthly', label: '每月' },
  { value: 'yearly', label: '每年' },
  { value: 'days', label: '自定义天数' }
]

const ACCENT = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#14b8a6', '#3b82f6', '#8b5cf6', '#ec4899']

function pad2(n: number) {
  return String(n).padStart(2, '0')
}

function formatApiErrorData(data: any, fallback: string) {
  if (data == null) return fallback
  if (typeof data === 'string') return data
  if (typeof data.detail === 'string') return data.detail
  if (Array.isArray(data.detail)) return data.detail.map(String).join('；') || fallback
  if (typeof data === 'object') {
    const parts: string[] = []
    for (const [k, v] of Object.entries(data)) {
      if (k === 'detail') continue
      const msg = Array.isArray(v) ? v.map(String).join('；') : String(v)
      if (msg) parts.push(msg)
    }
    if (parts.length) return parts.join('；')
  }
  return fallback
}

function formatRequestError(e: any, fallback: string) {
  const fromData = formatApiErrorData(e?.response?.data, '')
  if (fromData) return fromData
  if (e?.message) return String(e.message)
  return fallback
}

function nowDateValue() {
  const d = new Date()
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`
}

function isoToDateOnly(iso: string) {
  if (!iso) return ''
  const m = String(iso).match(/^(\d{4}-\d{2}-\d{2})/)
  return m ? m[1] : ''
}

function parseLocalYmd(s: string) {
  const ymd = isoToDateOnly(s)
  if (!ymd) return null
  const p = ymd.split('-').map(Number)
  if (p.length !== 3 || p.some((n) => Number.isNaN(n))) return null
  return new Date(p[0], p[1] - 1, p[2])
}

function daysUntil(ymdOrIso: string) {
  const d = parseLocalYmd(ymdOrIso)
  if (!d || Number.isNaN(d.getTime())) return null
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const t0 = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  return Math.round((t0.getTime() - today.getTime()) / 86400000)
}

function formatDueShort(ymdOrIso: string) {
  const d = parseLocalYmd(ymdOrIso)
  if (!d) return '—'
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

function formatDueFull(ymdOrIso: string) {
  const d = parseLocalYmd(ymdOrIso)
  if (!d) return '—'
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`
}

function formatDateTime(iso: string) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso)
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
    .format(d)
    .replace(/\//g, '-')
}

function statusBadge(r: any) {
  if (!r?.is_active) return { text: '已停用', tone: 'off' as const }
  const diff = daysUntil(r.next_due_at)
  if (diff == null) return { text: '周期续费', tone: 'ok' as const }
  if (diff < 0) return { text: '已逾期', tone: 'urgent' as const }
  if (diff === 0) return { text: '今日到期', tone: 'soon' as const }
  if (diff <= 7) return { text: `${diff} 天内到期`, tone: 'soon' as const }
  return { text: '周期续费', tone: 'ok' as const }
}

function formatAmount(r: any) {
  if (r?.amount == null || r.amount === '') return '—'
  const cur = r.currency === 'USD' ? '$' : r.currency === 'CNY' ? '¥' : `${r.currency || ''} `
  const n = Number(r.amount)
  if (Number.isNaN(n)) return String(r.amount)
  return `${cur}${n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function cycleLabel(r: any) {
  if (r?.cycle_type === 'days') return `每 ${r.cycle_days || '?'} 天`
  if (r?.cycle_type === 'monthly') return '每月'
  if (r?.cycle_type === 'yearly') return '每年'
  return r?.cycle_type_label || '—'
}

function cycleDaysOf(r: any) {
  if (r?.cycle_type === 'monthly') return 30
  if (r?.cycle_type === 'yearly') return 365
  const n = Number(r?.cycle_days)
  return n > 0 ? n : 30
}

function countdownText(r: any) {
  const diff = daysUntil(r?.next_due_at)
  if (diff == null) return '—'
  if (diff < 0) return `已逾期 ${Math.abs(diff)} 天`
  if (diff === 0) return '今日到期'
  if (diff === 1) return '明天到期'
  return `剩余 ${diff} 天`
}

function dueProgress(r: any) {
  const diff = daysUntil(r?.next_due_at)
  const total = cycleDaysOf(r)
  if (diff == null || total < 1) return 0
  if (diff < 0) return 100
  const elapsed = Math.max(0, total - diff)
  return Math.min(100, Math.round((elapsed / total) * 100))
}

function cardTone(r: any): 'urgent' | 'soon' | 'ok' | 'off' {
  if (!r?.is_active) return 'off'
  const diff = daysUntil(r.next_due_at)
  if (diff == null) return 'ok'
  if (diff < 0) return 'urgent'
  if (diff <= 7) return 'soon'
  return 'ok'
}

function avatarLetter(name: string) {
  const s = String(name || '').trim()
  return s ? s.slice(0, 1).toUpperCase() : '?'
}

function avatarColor(id: number | string) {
  const n = Number(id) || 0
  return ACCENT[Math.abs(n) % ACCENT.length]
}

const filteredRows = computed(() => {
  const q = searchQ.value.trim().toLowerCase()
  const list = rows.value.slice()
  list.sort((a, b) => {
    const aa = a.is_active === false ? 1 : 0
    const bb = b.is_active === false ? 1 : 0
    if (aa !== bb) return aa - bb
    const da = isoToDateOnly(a.next_due_at) || '9999'
    const db = isoToDateOnly(b.next_due_at) || '9999'
    if (da !== db) return da < db ? -1 : 1
    return (Number(a.id) || 0) - (Number(b.id) || 0)
  })
  if (!q) return list
  return list.filter((r) => {
    const hay = `${r.name || ''} ${r.category || ''} ${r.remark || ''}`.toLowerCase()
    return hay.includes(q)
  })
})

const activeRows = computed(() => filteredRows.value.filter((r) => r.is_active !== false))
const inactiveRows = computed(() => filteredRows.value.filter((r) => r.is_active === false))

async function loadRows() {
  loading.value = true
  try {
    const { data } = await api.get('/material-renewals/', { params: { page: 1 } })
    const list = Array.isArray(data) ? data : data?.results || []
    rows.value = list
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '加载失败'))
    rows.value = []
  } finally {
    loading.value = false
  }
}

function payloadFrom(form: ReturnType<typeof emptyForm>) {
  const body: Recordable = {
    name: String(form.name || '').trim(),
    category: String(form.category || '').trim(),
    currency: String(form.currency || 'CNY').trim() || 'CNY',
    cycle_type: form.cycle_type,
    next_due_at: String(form.next_due_at || '').trim(),
    remark: String(form.remark || '').trim().slice(0, 500),
    is_active: !!form.is_active
  }
  if (form.amount != null && form.amount !== ('' as any)) body.amount = form.amount
  else body.amount = null
  if (form.cycle_type === 'days') body.cycle_days = form.cycle_days
  else body.cycle_days = null
  return body
}

function openCreate() {
  createForm.value = emptyForm()
  createForm.value.next_due_at = nowDateValue()
  createOpen.value = true
}

async function saveCreate() {
  const body = payloadFrom(createForm.value)
  if (!body.name || !body.next_due_at) {
    ElMessage.warning('请填写物料名称和下次到期日')
    return
  }
  if (body.cycle_type === 'days' && !(Number(body.cycle_days) > 0)) {
    ElMessage.warning('自定义天数请填写 ≥ 1')
    return
  }
  try {
    await api.post('/material-renewals/', body)
    createOpen.value = false
    ElMessage.success('已添加')
    await loadRows()
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '保存失败'))
  }
}

function openEdit(r: any) {
  editId.value = r.id
  editForm.value = {
    name: r.name || '',
    category: r.category || '',
    amount: r.amount != null ? Number(r.amount) : null,
    currency: r.currency || 'CNY',
    cycle_type: r.cycle_type || 'yearly',
    cycle_days: r.cycle_days != null ? Number(r.cycle_days) : null,
    next_due_at: isoToDateOnly(r.next_due_at),
    remark: r.remark || '',
    is_active: r.is_active !== false
  }
  editOpen.value = true
}

async function saveEdit() {
  const body = payloadFrom(editForm.value)
  if (!body.name || !body.next_due_at) {
    ElMessage.warning('请填写物料名称和下次到期日')
    return
  }
  try {
    await api.patch(`/material-renewals/${editId.value}/`, body)
    editOpen.value = false
    ElMessage.success('已更新')
    await loadRows()
    syncDetailFromList()
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '更新失败'))
  }
}

function openDetail(r: any) {
  detailRow.value = r
  detailOpen.value = true
}

function syncDetailFromList() {
  if (!detailOpen.value || !detailRow.value?.id) return
  const fresh = rows.value.find((x) => x.id === detailRow.value.id)
  if (fresh) detailRow.value = fresh
}

function openRenew(r: any) {
  renewRow.value = r
  renewAuto.value = true
  renewDate.value = ''
  renewOpen.value = true
}

async function confirmRenew() {
  if (!renewRow.value?.id) return
  try {
    const body: Recordable = {}
    if (!renewAuto.value) {
      const d = String(renewDate.value || '').trim()
      if (!d) {
        ElMessage.warning('请选择下次到期日，或勾选按周期自动顺延')
        return
      }
      body.next_due_at = d
    }
    const { data } = await api.post(`/material-renewals/${renewRow.value.id}/mark-renewed/`, body)
    renewOpen.value = false
    ElMessage.success('已登记续费')
    await loadRows()
    if (detailOpen.value && detailRow.value?.id === renewRow.value.id) {
      detailRow.value = data || rows.value.find((x) => x.id === renewRow.value.id) || detailRow.value
    }
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '续费登记失败'))
  }
}

async function onDelete(r: any) {
  try {
    await ElMessageBox.confirm(`确定删除「${r.name}」？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await api.delete(`/material-renewals/${r.id}/`)
    if (detailOpen.value && detailRow.value?.id === r.id) detailOpen.value = false
    ElMessage.success('已删除')
    await loadRows()
  } catch (e: any) {
    if (e !== 'cancel' && e?.action !== 'cancel') {
      ElMessage.error(formatRequestError(e, '删除失败'))
    }
  }
}

function onCardCommand(cmd: string, r: any) {
  if (cmd === 'renew') openRenew(r)
  else if (cmd === 'edit') openEdit(r)
  else if (cmd === 'delete') onDelete(r)
  else if (cmd === 'detail') openDetail(r)
}

const showCycleDaysCreate = computed(() => createForm.value.cycle_type === 'days')
const showCycleDaysEdit = computed(() => editForm.value.cycle_type === 'days')
const detailBadge = computed(() => (detailRow.value ? statusBadge(detailRow.value) : null))

onMounted(loadRows)
</script>

<template>
  <ContentWrap class="mr-page">
    <header class="mr-toolbar">
      <BaseButton type="danger" class="mr-new-btn" @click="openCreate">
        <Icon icon="vi-ep:plus" class="mr-4px" />
        新增物料
      </BaseButton>
      <div class="mr-search">
        <Icon icon="vi-ep:search" class="mr-search__icon" />
        <input
          v-model="searchQ"
          class="mr-search__input"
          type="search"
          placeholder="搜索物料、分类、备注"
          autocomplete="off"
        />
      </div>
    </header>

    <ElSkeleton :loading="loading" animated :rows="6">
      <template #default>
        <ElEmpty v-if="!filteredRows.length" description="暂无物料，点击左上角新增" />

        <section v-if="activeRows.length" class="mr-grid">
          <article
            v-for="r in activeRows"
            :key="r.id"
            class="mr-card"
            :class="`is-${cardTone(r)}`"
            role="button"
            tabindex="0"
            @click="openDetail(r)"
            @keydown.enter.prevent="openDetail(r)"
          >
            <div class="mr-card__top">
              <div
                class="mr-card__avatar"
                :style="{ background: avatarColor(r.id) }"
              >
                {{ avatarLetter(r.name) }}
              </div>
              <ElDropdown trigger="click" @command="(c: string) => onCardCommand(c, r)">
                <button
                  type="button"
                  class="mr-card__more"
                  aria-label="更多"
                  @click.stop
                >
                  <Icon icon="vi-ep:more-filled" />
                </button>
                <template #dropdown>
                  <ElDropdownMenu>
                    <ElDropdownItem command="detail">详情</ElDropdownItem>
                    <ElDropdownItem command="renew">已续费</ElDropdownItem>
                    <ElDropdownItem command="edit">编辑</ElDropdownItem>
                    <ElDropdownItem command="delete" divided>删除</ElDropdownItem>
                  </ElDropdownMenu>
                </template>
              </ElDropdown>
            </div>

            <h3 class="mr-card__name" :title="r.name">{{ r.name }}</h3>
            <div class="mr-card__price">{{ formatAmount(r) }}</div>
            <div v-if="r.category" class="mr-card__cat">{{ r.category }}</div>

            <div class="mr-card__due" :class="`is-${cardTone(r)}`">
              <div class="mr-card__due-row">
                <span class="mr-card__countdown">{{ countdownText(r) }}</span>
                <span class="mr-card__due-date">{{ formatDueShort(r.next_due_at) }}</span>
              </div>
              <div class="mr-card__bar" aria-hidden="true">
                <span class="mr-card__bar-fill" :style="{ width: `${dueProgress(r)}%` }" />
              </div>
              <div class="mr-card__meta">
                <span class="mr-card__meta-item">
                  <Icon icon="vi-ep:refresh" />
                  {{ cycleLabel(r) }}
                </span>
                <span class="mr-card__meta-item">{{ dueProgress(r) }}%</span>
              </div>
            </div>
          </article>
        </section>

        <template v-if="inactiveRows.length">
          <h4 class="mr-section-title">已停用</h4>
          <section class="mr-grid">
            <article
              v-for="r in inactiveRows"
              :key="r.id"
              class="mr-card is-off"
              role="button"
              tabindex="0"
              @click="openDetail(r)"
              @keydown.enter.prevent="openDetail(r)"
            >
              <div class="mr-card__top">
                <div
                  class="mr-card__avatar"
                  :style="{ background: avatarColor(r.id) }"
                >
                  {{ avatarLetter(r.name) }}
                </div>
                <ElDropdown trigger="click" @command="(c: string) => onCardCommand(c, r)">
                  <button
                    type="button"
                    class="mr-card__more"
                    aria-label="更多"
                    @click.stop
                  >
                    <Icon icon="vi-ep:more-filled" />
                  </button>
                  <template #dropdown>
                    <ElDropdownMenu>
                      <ElDropdownItem command="detail">详情</ElDropdownItem>
                      <ElDropdownItem command="edit">编辑</ElDropdownItem>
                      <ElDropdownItem command="delete" divided>删除</ElDropdownItem>
                    </ElDropdownMenu>
                  </template>
                </ElDropdown>
              </div>
              <h3 class="mr-card__name" :title="r.name">{{ r.name }}</h3>
              <div class="mr-card__price">{{ formatAmount(r) }}</div>
              <div class="mr-card__due is-off">
                <div class="mr-card__due-row">
                  <span class="mr-card__countdown">{{ countdownText(r) }}</span>
                  <span class="mr-card__due-date">{{ formatDueShort(r.next_due_at) }}</span>
                </div>
                <div class="mr-card__bar" aria-hidden="true">
                  <span class="mr-card__bar-fill" :style="{ width: `${dueProgress(r)}%` }" />
                </div>
              </div>
            </article>
          </section>
        </template>
      </template>
    </ElSkeleton>

    <ElDialog
      v-model="detailOpen"
      width="480px"
      class="mr-detail-dialog"
      :show-close="true"
      destroy-on-close
      align-center
    >
      <template #header>
        <div v-if="detailRow" class="mr-detail__head">
          <div
            class="mr-detail__avatar"
            :style="{ background: avatarColor(detailRow.id) }"
          >
            {{ avatarLetter(detailRow.name) }}
          </div>
          <div class="mr-detail__title-wrap">
            <div class="mr-detail__title-row">
              <h3 class="mr-detail__title">{{ detailRow.name }}</h3>
              <span
                v-if="detailBadge"
                class="mr-detail__badge"
                :class="`is-${detailBadge.tone}`"
              >
                {{ detailBadge.text }}
              </span>
            </div>
          </div>
        </div>
      </template>

      <div v-if="detailRow" class="mr-detail">
        <div class="mr-detail__price-row">
          <div>
            <div class="mr-detail__price">{{ formatAmount(detailRow) }}</div>
            <div class="mr-detail__cycle">{{ cycleLabel(detailRow) }}</div>
          </div>
          <button
            type="button"
            class="mr-detail__cal"
            title="登记续费"
            @click="openRenew(detailRow)"
          >
            <Icon icon="vi-ep:calendar" />
          </button>
        </div>
        <div class="mr-detail__due" :class="`is-${cardTone(detailRow)}`">
          <div class="mr-detail__due-row">
            <span class="mr-detail__countdown">{{ countdownText(detailRow) }}</span>
            <span>{{ formatDueFull(detailRow.next_due_at) }}</span>
          </div>
          <div class="mr-card__bar" aria-hidden="true">
            <span class="mr-card__bar-fill" :style="{ width: `${dueProgress(detailRow)}%` }" />
          </div>
        </div>

        <div class="mr-detail__grid">
          <div class="mr-detail__field">
            <div class="mr-detail__label">下次到期</div>
            <div class="mr-detail__value">{{ formatDueFull(detailRow.next_due_at) }}</div>
          </div>
          <div class="mr-detail__field">
            <div class="mr-detail__label">上次续费</div>
            <div class="mr-detail__value">{{ formatDateTime(detailRow.last_renewed_at) }}</div>
          </div>
          <div class="mr-detail__field">
            <div class="mr-detail__label">分类</div>
            <div class="mr-detail__value">{{ detailRow.category || '—' }}</div>
          </div>
          <div class="mr-detail__field">
            <div class="mr-detail__label">周期</div>
            <div class="mr-detail__value">{{ cycleLabel(detailRow) }}</div>
          </div>
        </div>

        <div v-if="detailRow.remark" class="mr-detail__note">
          <span class="mr-detail__note-dot" />
          <span>{{ detailRow.remark }}</span>
        </div>
      </div>

      <template #footer>
        <BaseButton @click="detailOpen = false">关闭</BaseButton>
        <BaseButton @click="openEdit(detailRow)">编辑</BaseButton>
        <BaseButton type="warning" @click="openRenew(detailRow)">已续费</BaseButton>
      </template>
    </ElDialog>

    <ElDialog v-model="createOpen" title="新增物料" width="520px" destroy-on-close>
      <ElForm label-width="96px">
        <ElFormItem label="名称" required>
          <ElInput v-model="createForm.name" placeholder="如：QQ会员、域名、服务器" />
        </ElFormItem>
        <ElFormItem label="分类">
          <ElInput v-model="createForm.category" placeholder="可选，如：会员 / 域名 / 工具" />
        </ElFormItem>
        <ElFormItem label="费用">
          <div class="flex gap-8px w-full">
            <ElSelect v-model="createForm.currency" style="width: 100px">
              <ElOption label="CNY" value="CNY" />
              <ElOption label="USD" value="USD" />
            </ElSelect>
            <ElInputNumber v-model="createForm.amount" :min="0" :precision="2" class="flex-1" />
          </div>
        </ElFormItem>
        <ElFormItem label="周期" required>
          <ElSelect v-model="createForm.cycle_type" style="width: 100%">
            <ElOption v-for="o in cycleOptions" :key="o.value" :label="o.label" :value="o.value" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem v-if="showCycleDaysCreate" label="天数" required>
          <ElInputNumber v-model="createForm.cycle_days" :min="1" :precision="0" />
        </ElFormItem>
        <ElFormItem label="下次到期" required>
          <ElDatePicker v-model="createForm.next_due_at" type="date" value-format="YYYY-MM-DD" />
        </ElFormItem>
        <ElFormItem label="备注">
          <ElInput v-model="createForm.remark" type="textarea" :rows="2" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <BaseButton @click="createOpen = false">取消</BaseButton>
        <BaseButton type="primary" @click="saveCreate">保存</BaseButton>
      </template>
    </ElDialog>

    <ElDialog v-model="editOpen" title="编辑物料" width="520px" destroy-on-close>
      <ElForm label-width="96px">
        <ElFormItem label="名称" required>
          <ElInput v-model="editForm.name" />
        </ElFormItem>
        <ElFormItem label="分类">
          <ElInput v-model="editForm.category" />
        </ElFormItem>
        <ElFormItem label="费用">
          <div class="flex gap-8px w-full">
            <ElSelect v-model="editForm.currency" style="width: 100px">
              <ElOption label="CNY" value="CNY" />
              <ElOption label="USD" value="USD" />
            </ElSelect>
            <ElInputNumber v-model="editForm.amount" :min="0" :precision="2" class="flex-1" />
          </div>
        </ElFormItem>
        <ElFormItem label="周期" required>
          <ElSelect v-model="editForm.cycle_type" style="width: 100%">
            <ElOption v-for="o in cycleOptions" :key="o.value" :label="o.label" :value="o.value" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem v-if="showCycleDaysEdit" label="天数" required>
          <ElInputNumber v-model="editForm.cycle_days" :min="1" :precision="0" />
        </ElFormItem>
        <ElFormItem label="下次到期" required>
          <ElDatePicker v-model="editForm.next_due_at" type="date" value-format="YYYY-MM-DD" />
        </ElFormItem>
        <ElFormItem label="启用">
          <ElSwitch v-model="editForm.is_active" />
        </ElFormItem>
        <ElFormItem label="备注">
          <ElInput v-model="editForm.remark" type="textarea" :rows="2" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <BaseButton @click="editOpen = false">取消</BaseButton>
        <BaseButton type="primary" @click="saveEdit">保存</BaseButton>
      </template>
    </ElDialog>

    <ElDialog v-model="renewOpen" title="登记续费" width="440px" destroy-on-close>
      <p class="mb-12px text-14px text-[var(--el-text-color-regular)]">
        {{ renewRow?.name }} · 当前到期 {{ isoToDateOnly(renewRow?.next_due_at) || '—' }}
      </p>
      <ElForm label-width="120px">
        <ElFormItem label="按周期顺延">
          <ElSwitch v-model="renewAuto" />
        </ElFormItem>
        <ElFormItem v-if="!renewAuto" label="下次到期日" required>
          <ElDatePicker v-model="renewDate" type="date" value-format="YYYY-MM-DD" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <BaseButton @click="renewOpen = false">取消</BaseButton>
        <BaseButton type="primary" @click="confirmRenew">确认</BaseButton>
      </template>
    </ElDialog>
  </ContentWrap>
</template>

<style scoped>
.mr-page :deep(.el-card__body) {
  background: #f4f5f7;
}

.mr-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.mr-new-btn {
  border-radius: 10px !important;
  font-weight: 600;
}

.mr-search {
  position: relative;
  flex: 1;
  min-width: 200px;
  max-width: 420px;
}

.mr-search__icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #9ca3af;
  font-size: 16px;
  pointer-events: none;
}

.mr-search__input {
  width: 100%;
  height: 40px;
  padding: 0 14px 0 38px;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  background: #fff;
  font-size: 14px;
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.mr-search__input:focus {
  border-color: #f87171;
  box-shadow: 0 0 0 3px rgba(248, 113, 113, 0.15);
}

.mr-section-title {
  margin: 28px 0 14px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #9ca3af;
  text-transform: uppercase;
}

.mr-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.mr-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 168px;
  padding: 16px 16px 14px;
  background: #fff;
  border: 1px solid #e8eaed;
  border-radius: 14px;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
}

.mr-card:hover {
  box-shadow: 0 6px 18px rgba(16, 24, 40, 0.08);
  transform: translateY(-1px);
}

.mr-card.is-urgent {
  border-color: #f87171;
  box-shadow: 0 0 0 1px rgba(248, 113, 113, 0.25);
}

.mr-card.is-soon {
  border-color: #fdba74;
}

.mr-card.is-off {
  opacity: 0.55;
  filter: grayscale(0.35);
}

.mr-card__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 4px;
}

.mr-card__avatar {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.mr-card__more {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #9ca3af;
  cursor: pointer;
}

.mr-card__more:hover {
  background: #f3f4f6;
  color: #4b5563;
}

.mr-card__name {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #111827;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mr-card__price {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #111827;
  font-variant-numeric: tabular-nums;
}

.mr-card__cat {
  font-size: 12px;
  color: #9ca3af;
}

.mr-card__due {
  margin-top: auto;
  padding: 10px 10px 8px;
  border-radius: 10px;
  background: #f3f4f6;
}

.mr-card__due.is-soon {
  background: #fff7ed;
}

.mr-card__due.is-urgent {
  background: #fef2f2;
}

.mr-card__due-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.mr-card__countdown {
  font-size: 15px;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: #111827;
}

.mr-card__due.is-soon .mr-card__countdown {
  color: #c2410c;
}

.mr-card__due.is-urgent .mr-card__countdown {
  color: #dc2626;
}

.mr-card__due-date {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
}

.mr-card__bar {
  height: 7px;
  margin-top: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(17, 24, 39, 0.08);
}

.mr-card__bar-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #22c55e;
  transition: width 0.25s ease;
}

.mr-card__due.is-soon .mr-card__bar-fill {
  background: #f97316;
}

.mr-card__due.is-urgent .mr-card__bar-fill {
  background: #ef4444;
}

.mr-card__meta {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 8px;
  margin-top: 8px;
  padding-top: 0;
  font-size: 12px;
  color: #6b7280;
}

.mr-card__meta-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.mr-detail__due {
  margin: 12px 0 16px;
  padding: 12px;
  border-radius: 12px;
  background: #f3f4f6;
}

.mr-detail__due.is-soon {
  background: #fff7ed;
}

.mr-detail__due.is-urgent {
  background: #fef2f2;
}

.mr-detail__due-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  font-size: 13px;
  color: #6b7280;
}

.mr-detail__countdown {
  font-size: 18px;
  font-weight: 800;
  color: #111827;
}

.mr-detail__due.is-soon .mr-detail__countdown {
  color: #c2410c;
}

.mr-detail__due.is-urgent .mr-detail__countdown {
  color: #dc2626;
}

.mr-detail__head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-right: 28px;
}

.mr-detail__avatar {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 20px;
  font-weight: 700;
  flex-shrink: 0;
}

.mr-detail__title-wrap {
  min-width: 0;
}

.mr-detail__title-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.mr-detail__title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #111827;
  line-height: 1.25;
}

.mr-detail__badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  background: #fee2e2;
  color: #b91c1c;
}

.mr-detail__badge.is-soon {
  background: #ffedd5;
  color: #c2410c;
}

.mr-detail__badge.is-ok {
  background: #ecfdf5;
  color: #047857;
}

.mr-detail__badge.is-off {
  background: #f3f4f6;
  color: #6b7280;
}

.mr-detail__price-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.mr-detail__price {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: #111827;
  font-variant-numeric: tabular-nums;
}

.mr-detail__cycle {
  margin-top: 2px;
  font-size: 14px;
  color: #9ca3af;
}

.mr-detail__cal {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: 1px solid #fecaca;
  border-radius: 10px;
  background: #fff;
  color: #ef4444;
  cursor: pointer;
}

.mr-detail__cal:hover {
  background: #fef2f2;
}

.mr-detail__accent {
  height: 3px;
  margin: 14px 0 18px;
  border-radius: 999px;
  background: linear-gradient(90deg, #f97316, #ef4444);
}

.mr-detail__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px 20px;
}

.mr-detail__label {
  margin-bottom: 4px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: #9ca3af;
  text-transform: uppercase;
}

.mr-detail__value {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  word-break: break-word;
}

.mr-detail__note {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-top: 18px;
  padding: 12px 14px;
  border-radius: 12px;
  background: #f3f4f6;
  color: #4b5563;
  font-size: 13px;
  line-height: 1.45;
}

.mr-detail__note-dot {
  width: 14px;
  height: 14px;
  margin-top: 2px;
  border-radius: 4px;
  background: #ef4444;
  flex-shrink: 0;
}

@media (max-width: 1100px) {
  .mr-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .mr-grid {
    grid-template-columns: 1fr;
  }

  .mr-search {
    max-width: none;
  }
}
</style>
