<script setup lang="tsx">
import { onMounted, reactive, ref, watch } from 'vue'
import {
  ElAutocomplete,
  ElDatePicker,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElTag
} from 'element-plus'
import { ContentWrap } from '@/components/ContentWrap'
import { Search } from '@/components/Search'
import { Table, TableColumn } from '@/components/Table'
import { BaseButton } from '@/components/Button'
import { FormSchema } from '@/components/Form'
import {
  listSubscriptionPlatformOptions,
  listSubscriptionReminders,
  createSubscriptionReminder,
  updateSubscriptionReminder,
  markSubscriptionRenewed,
  deleteSubscriptionReminder
} from '@/api/xinhuo/subscriptionReminders'
import { formatRequestError, formatDateTime } from '@/utils/format'
import { addMonthsYmd, daysFromToday, isoToDateOnly, todayYmd } from '@/utils/ymd'

defineOptions({ name: 'SubscriptionReminders' })

const rows = ref<any[]>([])
const platformOptions = ref<any[]>([])
const loading = ref(false)
const searchParams = reactive({ q: '' })
const page = ref(1)
const totalCount = ref(0)
const pageSize = ref(30)

const form = ref({
  wechat_label: '',
  platform_input: '',
  next_reminder_at: '',
  remark: ''
})

const editOpen = ref(false)
const editId = ref<number | null>(null)
const editForm = ref({
  wechat_label: '',
  platform_input: '',
  next_reminder_at: '',
  remark: ''
})

const renewOpen = ref(false)
const renewRow = ref<any>(null)
const renewDate = ref('')

const searchSchema = ref<FormSchema[]>([
  {
    field: 'q',
    label: '关键词',
    component: 'Input',
    componentProps: { placeholder: '搜微信/平台/备注' }
  }
])

function formatReminderDate(ymdOrIso: string) {
  const s = isoToDateOnly(ymdOrIso)
  return s || '—'
}

function statusLabel(ymdOrIso: string) {
  const diff = daysFromToday(ymdOrIso)
  if (diff === null) return '—'
  if (diff < 0) return '已逾期'
  if (diff === 0) return '今日待跟进'
  return '待提醒'
}

function statusTagType(ymdOrIso: string): 'danger' | 'warning' | 'success' | 'info' {
  const lab = statusLabel(ymdOrIso)
  if (lab === '已逾期') return 'danger'
  if (lab === '今日待跟进') return 'warning'
  return 'success'
}

function queryPlatform(queryString: string, cb: (results: { value: string }[]) => void) {
  const q = queryString.trim().toLowerCase()
  const list = platformOptions.value
    .map((p) => p.name)
    .filter((name) => !q || String(name).toLowerCase().includes(q))
    .map((name) => ({ value: name }))
  cb(list)
}

async function loadPlatformOptions() {
  try {
    const { data } = await listSubscriptionPlatformOptions()
    const list = Array.isArray(data) ? data : data?.results || []
    platformOptions.value = list.slice().sort((a, b) => {
      const ao = Number(a?.sort_order ?? 0)
      const bo = Number(b?.sort_order ?? 0)
      if (ao !== bo) return ao - bo
      return (Number(a?.id) || 0) - (Number(b?.id) || 0)
    })
  } catch (_) {
    platformOptions.value = []
  }
}

async function loadRows() {
  loading.value = true
  try {
    const params: Recordable = { page: page.value }
    const q = searchParams.q.trim()
    if (q) params.q = q
    const { data } = await listSubscriptionReminders(params)
    if (Array.isArray(data)) {
      rows.value = data
      totalCount.value = data.length
      return
    }
    rows.value = data.results || []
    totalCount.value = data.count ?? rows.value.length
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '加载失败'))
    rows.value = []
    totalCount.value = 0
  } finally {
    loading.value = false
  }
}

function onSearch(params: Recordable = {}) {
  Object.assign(searchParams, { q: params.q || '' })
  if (page.value === 1) {
    loadRows()
  } else {
    page.value = 1
  }
}

watch(page, (next, prev) => {
  if (next !== prev) loadRows()
})

async function onCreate() {
  const w = String(form.value.wechat_label || '').trim()
  const plat = String(form.value.platform_input || '').trim()
  const dt = String(form.value.next_reminder_at || '').trim()
  if (!w || !plat || !dt) {
    ElMessage.warning('请填写微信名/微信号、订阅平台（可输入新名称）并选择下次提醒日期。')
    return
  }
  try {
    await createSubscriptionReminder({
      wechat_label: w,
      platform_input: plat,
      next_reminder_at: dt,
      remark: String(form.value.remark || '').trim().slice(0, 500)
    })
    form.value = { wechat_label: '', platform_input: '', next_reminder_at: '', remark: '' }
    ElMessage.success('添加成功')
    await loadPlatformOptions()
    await loadRows()
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '保存失败'))
  }
}

function openEdit(r: any) {
  editId.value = r.id
  editForm.value = {
    wechat_label: r.wechat_label || '',
    platform_input: r.platform_name || '',
    next_reminder_at: isoToDateOnly(r.next_reminder_at),
    remark: r.remark || ''
  }
  editOpen.value = true
}

async function saveEdit() {
  try {
    await updateSubscriptionReminder(editId.value, {
      wechat_label: String(editForm.value.wechat_label || '').trim(),
      platform_input: String(editForm.value.platform_input || '').trim(),
      next_reminder_at: String(editForm.value.next_reminder_at || '').trim(),
      remark: String(editForm.value.remark || '').trim().slice(0, 500)
    })
    editOpen.value = false
    ElMessage.success('更新成功')
    await loadPlatformOptions()
    await loadRows()
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '更新失败'))
  }
}

function openRenew(r: any) {
  renewRow.value = r
  renewDate.value = isoToDateOnly(r.next_reminder_at) || todayYmd()
  renewOpen.value = true
}

function bumpRenew(months: number) {
  const base = renewDate.value || todayYmd()
  renewDate.value = addMonthsYmd(base, months)
}

async function confirmRenew() {
  const id = renewRow.value?.id
  if (!id) return
  const dt = String(renewDate.value || '').trim()
  if (!dt) {
    ElMessage.warning('请选择下一次提醒日期。')
    return
  }
  try {
    await markSubscriptionRenewed(id, { next_reminder_at: dt })
    renewOpen.value = false
    ElMessage.success('登记成功')
    await loadRows()
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '登记失败'))
  }
}

async function onDelete(r: any) {
  try {
    await ElMessageBox.confirm(
      `确定删除「${r.wechat_label}」的这条订阅提醒吗？`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await deleteSubscriptionReminder(r.id)
    ElMessage.success('删除成功')
    await loadRows()
  } catch (e: any) {
    if (e !== 'cancel' && e?.action !== 'cancel') {
      ElMessage.error(formatRequestError(e, '删除失败'))
    }
  }
}

const columns: TableColumn[] = [
  { field: 'wechat_label', label: '微信名或微信号', minWidth: 140 },
  { field: 'platform_name', label: '订阅平台', minWidth: 120 },
  {
    field: 'remark',
    label: '备注',
    minWidth: 160,
    showOverflowTooltip: true,
    formatter: (_r, _c, v) => v || '—'
  },
  {
    field: 'next_reminder_at',
    label: '下次提醒',
    minWidth: 110,
    formatter: (_r, _c, v) => formatReminderDate(v)
  },
  {
    field: 'last_renewed_at',
    label: '上次续费登记',
    minWidth: 150,
    formatter: (_r, _c, v) => formatDateTime(v)
  },
  {
    field: 'status',
    label: '状态',
    minWidth: 110,
    slots: {
      default: (data) => (
        <ElTag type={statusTagType(data.row.next_reminder_at)}>
          {statusLabel(data.row.next_reminder_at)}
        </ElTag>
      )
    }
  },
  {
    field: 'action',
    label: '操作',
    width: 240,
    fixed: 'right',
    slots: {
      default: (data) => (
        <>
          <BaseButton type="primary" link onClick={() => openEdit(data.row)}>
            编辑
          </BaseButton>
          <BaseButton type="warning" link onClick={() => openRenew(data.row)}>
            已续费，约下次
          </BaseButton>
          <BaseButton type="danger" link onClick={() => onDelete(data.row)}>
            删除
          </BaseButton>
        </>
      )
    }
  }
]

onMounted(async () => {
  await loadPlatformOptions()
  await loadRows()
})
</script>

<template>
  <ContentWrap title="订阅到期提醒">
    <p class="mb-16px text-14px text-[var(--el-text-color-secondary)] leading-relaxed max-w-4xl">
      每条记录对应一位客户在一个平台上的订阅。客户续费后请用「已续费，约下次」选择下一次提醒日期；「订阅平台」可输入新名称或从浏览器提示中选择已有项。
    </p>

    <div class="mb-20px">
      <div class="mb-12px text-15px font-600">新建</div>
      <ElForm class="sub-create-form" inline label-width="auto" @submit.prevent="onCreate">
        <ElFormItem label="微信">
          <ElInput
            v-model="form.wechat_label"
            maxlength="200"
            placeholder="微信名/微信号"
            style="width: 132px"
          />
        </ElFormItem>
        <ElFormItem label="平台">
          <ElAutocomplete
            v-model="form.platform_input"
            :fetch-suggestions="queryPlatform"
            maxlength="200"
            placeholder="输入或选择"
            style="width: 128px"
          />
        </ElFormItem>
        <ElFormItem label="下次提醒">
          <ElDatePicker
            v-model="form.next_reminder_at"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            style="width: 136px"
          />
        </ElFormItem>
        <ElFormItem label="备注">
          <ElInput
            v-model="form.remark"
            maxlength="500"
            placeholder="选填"
            style="width: 140px"
          />
        </ElFormItem>
        <ElFormItem>
          <BaseButton type="primary" :loading="loading" @click="onCreate">添加</BaseButton>
        </ElFormItem>
      </ElForm>
    </div>

    <Search :schema="searchSchema" @search="onSearch" @reset="onSearch" />
    <Table
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :columns="columns"
      :data="rows"
      :loading="loading"
      :pagination="{ total: totalCount, pageSizes: [30], layout: 'total, prev, pager, next' }"
    />

    <ElDialog v-model="editOpen" title="编辑" width="460px" destroy-on-close>
      <ElForm label-width="120px">
        <ElFormItem label="微信名或微信号">
          <ElInput v-model="editForm.wechat_label" maxlength="200" />
        </ElFormItem>
        <ElFormItem label="订阅平台">
          <ElAutocomplete
            v-model="editForm.platform_input"
            :fetch-suggestions="queryPlatform"
            maxlength="200"
            placeholder="输入或从提示中选择"
            style="width: 100%"
          />
        </ElFormItem>
        <ElFormItem label="下次提醒日期">
          <ElDatePicker
            v-model="editForm.next_reminder_at"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            style="width: 100%"
          />
        </ElFormItem>
        <ElFormItem label="备注">
          <ElInput
            v-model="editForm.remark"
            type="textarea"
            maxlength="500"
            :rows="2"
            placeholder="内部备注"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <BaseButton @click="editOpen = false">取消</BaseButton>
        <BaseButton type="primary" @click="saveEdit">保存</BaseButton>
      </template>
    </ElDialog>

    <ElDialog v-model="renewOpen" title="客户已续费 — 预约下次提醒" width="460px" destroy-on-close>
      <p class="mb-12px text-13px text-[var(--el-text-color-secondary)]">
        选择新的提醒日期后保存，系统会记录本次登记时间（精确到日）。
      </p>
      <ElForm label-width="120px">
        <ElFormItem label="下次提醒日期">
          <ElDatePicker
            v-model="renewDate"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            style="width: 100%"
          />
        </ElFormItem>
        <ElFormItem label="快捷顺延">
          <div class="flex flex-wrap gap-8px">
            <BaseButton @click="bumpRenew(1)">+1 月</BaseButton>
            <BaseButton @click="bumpRenew(3)">+3 月</BaseButton>
            <BaseButton @click="bumpRenew(12)">+1 年</BaseButton>
          </div>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <BaseButton @click="renewOpen = false">取消</BaseButton>
        <BaseButton type="primary" @click="confirmRenew">保存</BaseButton>
      </template>
    </ElDialog>
  </ContentWrap>
</template>

<style scoped>
.sub-create-form {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 4px 10px;
  overflow-x: auto;
}
.sub-create-form :deep(.el-form-item) {
  margin-right: 0;
  margin-bottom: 0;
}
.sub-create-form :deep(.el-form-item__label) {
  padding-right: 6px;
}
</style>
