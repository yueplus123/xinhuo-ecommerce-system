<script setup lang="tsx">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import {
  ElDatePicker,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElSelect
} from 'element-plus'
import { Table, TableColumn } from '@/components/Table'
import { BaseButton } from '@/components/Button'
import {
  batchDeleteWechatBotRecords,
  listWechatBotEmployees,
  listWechatBotRecords,
  createWechatBotRecord,
  updateWechatBotRecord,
  deleteWechatBotRecord
} from '@/api/xinhuo/wechatBot'
import {
  WECHAT_BOT_TABLES,
  wechatBotTableColumns,
  type WechatBotColumnLayout
} from './wechatBotTables'

const props = defineProps<{
  tableType: string
  tableTitle: string
}>()

const loading = ref(false)
const creating = ref(false)
const empLoading = ref(false)
const batchDeleting = ref(false)
const rows = ref<any[]>([])
const selectedRows = ref<any[]>([])
const employees = ref<string[]>([])
const employeeFilter = ref('')
const keyword = ref('')
const page = ref(1)
const pageSize = ref(30)
const totalCount = ref(0)

const layout = computed<WechatBotColumnLayout>(
  () => WECHAT_BOT_TABLES.find((t) => t.key === props.tableType)?.layout || 'qty'
)

const createForm = reactive({
  occurred_at: '',
  quantity: 1 as number,
  business_name: '',
  employee_name: '',
  clear_status: '未清空',
  remark: '',
  amount_cny: '',
  amount_usd: ''
})

const editOpen = ref(false)
const editSaving = ref(false)
const editId = ref<number | null>(null)
const editForm = reactive({
  occurred_at: '',
  quantity: 1 as number,
  business_name: '',
  employee_name: '',
  clear_status: '未清空',
  remark: '',
  amount_cny: '',
  amount_usd: ''
})

function resetCreateForm() {
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  createForm.occurred_at = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
  createForm.quantity = 1
  createForm.business_name = ''
  createForm.employee_name = ''
  createForm.clear_status = '未清空'
  createForm.remark = ''
  createForm.amount_cny = ''
  createForm.amount_usd = ''
}

const columns = computed<TableColumn[]>(() => [
  {
    field: 'selection',
    type: 'selection',
    width: 48,
    fixed: 'left'
  },
  ...wechatBotTableColumns(props.tableType),
  {
    field: 'action',
    label: '操作',
    width: 130,
    fixed: 'right',
    slots: {
      default: (data: any) => (
        <>
          <BaseButton type="primary" link onClick={() => openEdit(data.row)}>
            编辑
          </BaseButton>
          <BaseButton type="danger" link onClick={() => onDelete(data.row)}>
            删除
          </BaseButton>
        </>
      )
    }
  }
])

function onSelectionChange(selection: any[]) {
  selectedRows.value = selection || []
}

async function onBatchDelete() {
  const ids = selectedRows.value.map((r) => r?.id).filter((id) => id != null)
  if (!ids.length) {
    ElMessage.warning('请先勾选要删除的记录')
    return
  }
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${ids.length} 条记录吗？`, '批量删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    batchDeleting.value = true
    const { data } = await batchDeleteWechatBotRecords(ids)
    const deleted = Number(data?.deleted ?? ids.length)
    ElMessage.success(`已删除 ${deleted} 条`)
    selectedRows.value = []
    await refreshAll()
  } catch (e: any) {
    if (e === 'cancel' || e === 'close') return
    ElMessage.error(e?.response?.data?.detail || e?.message || '批量删除失败')
  } finally {
    batchDeleting.value = false
  }
}

function toPickerValue(iso: string) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) {
    return String(iso).replace('T', ' ').replace(/\+.*/, '').replace(/\.\d+$/, '').slice(0, 19)
  }
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  }).formatToParts(d)
  const get = (type: string) => parts.find((p) => p.type === type)?.value || ''
  return `${get('year')}-${get('month')}-${get('day')} ${get('hour')}:${get('minute')}:${get('second')}`
}

function formatOccurredAt(raw: string) {
  if (!raw) return '—'
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) {
    return raw.replace('T', ' ').replace(/\+.*/, '').replace(/\.\d+$/, '')
  }
  // API 存 UTC；列表按北京时间展示，避免 19:17 显示成 11:17
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  }).formatToParts(d)
  const get = (type: string) => parts.find((p) => p.type === type)?.value || ''
  return `${get('year')}-${get('month')}-${get('day')} ${get('hour')}:${get('minute')}:${get('second')}`
}

async function loadEmployees() {
  if (!props.tableType) {
    employees.value = []
    return
  }
  empLoading.value = true
  try {
    const { data } = await listWechatBotEmployees(props.tableType)
    const list = (data?.employees || []).map((x: string) => String(x || '').trim()).filter(Boolean)
    employees.value = list
    if (employeeFilter.value && !list.includes(employeeFilter.value)) {
      employeeFilter.value = ''
    }
  } catch (e: any) {
    employees.value = []
    ElMessage.error(e?.response?.data?.detail || e?.message || '加载人员列表失败')
  } finally {
    empLoading.value = false
  }
}

async function loadRows() {
  if (!props.tableType) {
    rows.value = []
    totalCount.value = 0
    return
  }
  loading.value = true
  try {
    const { data } = await listWechatBotRecords({
      table: props.tableType,
      employee: employeeFilter.value || undefined,
      q: keyword.value.trim() || undefined,
      page: page.value,
      page_size: pageSize.value
    })
    const list = data?.results || []
    rows.value = list.map((r: any) => ({
      ...r,
      _occurred_at_iso: String(r.occurred_at || ''),
      occurred_at: formatOccurredAt(String(r.occurred_at || ''))
    }))
    totalCount.value = Number(data?.count || 0)
  } catch (e: any) {
    rows.value = []
    totalCount.value = 0
    ElMessage.error(e?.response?.data?.detail || e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function onSearch() {
  page.value = 1
  loadRows()
}

function onResetFilter() {
  employeeFilter.value = ''
  keyword.value = ''
  page.value = 1
  loadRows()
}

function refreshAll() {
  void loadEmployees()
  void loadRows()
}

async function onCreate() {
  const emp = String(createForm.employee_name || '').trim()
  if (!emp) {
    ElMessage.warning('请填写人员')
    return
  }
  if (!createForm.occurred_at) {
    ElMessage.warning('请选择时间')
    return
  }
  if (layout.value === 'sku' && !String(createForm.business_name || '').trim()) {
    ElMessage.warning('请填写业务名')
    return
  }
  if (layout.value === 'usdt') {
    if (createForm.amount_cny === '' && createForm.amount_usd === '') {
      ElMessage.warning('请填写人民币数或美金数')
      return
    }
  }

  creating.value = true
  try {
    const body: Recordable = {
      table_type: props.tableType,
      occurred_at: String(createForm.occurred_at).replace(' ', 'T'),
      employee_name: emp,
      clear_status: createForm.clear_status,
      remark: String(createForm.remark || '').trim()
    }
    if (layout.value === 'usdt') {
      body.amount_cny = createForm.amount_cny || '0'
      body.amount_usd = createForm.amount_usd || '0'
      body.quantity = 0
    } else {
      body.quantity = Number(createForm.quantity) || 1
      if (layout.value === 'sku') {
        body.business_name = String(createForm.business_name || '').trim()
      }
    }
    await createWechatBotRecord(body)
    ElMessage.success('添加成功')
    resetCreateForm()
    page.value = 1
    await refreshAll()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '添加失败')
  } finally {
    creating.value = false
  }
}

async function onDelete(r: any) {
  try {
    await ElMessageBox.confirm(`确定删除这条记录（#${r.id}）吗？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await deleteWechatBotRecord(r.id)
    ElMessage.success('已删除')
    selectedRows.value = selectedRows.value.filter((x) => x?.id !== r.id)
    await refreshAll()
  } catch (e: any) {
    if (e === 'cancel' || e === 'close') return
    ElMessage.error(e?.response?.data?.detail || e?.message || '删除失败')
  }
}

function openEdit(r: any) {
  editId.value = r.id
  editForm.occurred_at = toPickerValue(String(r._occurred_at_iso || r.occurred_at || ''))
  editForm.quantity = Number(r.quantity) || 1
  editForm.business_name = r.business_name || ''
  editForm.employee_name = r.employee_name || ''
  editForm.clear_status = r.clear_status || '未清空'
  editForm.remark = r.remark || ''
  editForm.amount_cny = r.amount_cny != null ? String(r.amount_cny) : ''
  editForm.amount_usd = r.amount_usd != null ? String(r.amount_usd) : ''
  editOpen.value = true
}

async function saveEdit() {
  if (!editId.value) return
  const emp = String(editForm.employee_name || '').trim()
  if (!emp) {
    ElMessage.warning('请填写人员')
    return
  }
  if (!editForm.occurred_at) {
    ElMessage.warning('请选择时间')
    return
  }
  if (layout.value === 'sku' && !String(editForm.business_name || '').trim()) {
    ElMessage.warning('请填写业务名')
    return
  }
  if (layout.value === 'usdt') {
    if (editForm.amount_cny === '' && editForm.amount_usd === '') {
      ElMessage.warning('请填写人民币数或美金数')
      return
    }
  }

  editSaving.value = true
  try {
    const body: Recordable = {
      occurred_at: String(editForm.occurred_at).replace(' ', 'T'),
      employee_name: emp,
      clear_status: editForm.clear_status,
      remark: String(editForm.remark || '').trim()
    }
    if (layout.value === 'usdt') {
      body.amount_cny = editForm.amount_cny || '0'
      body.amount_usd = editForm.amount_usd || '0'
      body.quantity = 0
    } else {
      body.quantity = Number(editForm.quantity) || 1
      if (layout.value === 'sku') {
        body.business_name = String(editForm.business_name || '').trim()
      }
    }
    await updateWechatBotRecord(editId.value, body)
    ElMessage.success('已更新')
    editOpen.value = false
    await refreshAll()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '更新失败')
  } finally {
    editSaving.value = false
  }
}

watch(page, () => loadRows())
watch(
  () => props.tableType,
  () => {
    employeeFilter.value = ''
    keyword.value = ''
    page.value = 1
    selectedRows.value = []
    resetCreateForm()
    refreshAll()
  }
)

onMounted(() => {
  resetCreateForm()
  refreshAll()
})
</script>

<template>
  <div class="wbot-panel">
    <section class="wbot-section">
      <div class="wbot-section__title">新建</div>
      <ElForm inline class="wbot-form" @submit.prevent="onCreate">
        <ElFormItem label="时间">
          <ElDatePicker
            v-model="createForm.occurred_at"
            type="datetime"
            value-format="YYYY-MM-DD HH:mm:ss"
            placeholder="选择时间"
            style="width: 190px"
          />
        </ElFormItem>
        <ElFormItem v-if="layout === 'sku'" label="业务名">
          <ElInput
            v-model="createForm.business_name"
            placeholder="如：一个月 / pro100刀"
            clearable
            style="width: 160px"
          />
        </ElFormItem>
        <ElFormItem v-if="layout !== 'usdt'" label="数量">
          <ElSelect v-model="createForm.quantity" style="width: 90px">
            <ElOption :value="1" label="+1" />
            <ElOption :value="-1" label="-1" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem v-if="layout === 'usdt'" label="人民币数">
          <ElInput v-model="createForm.amount_cny" placeholder="0.00" clearable style="width: 120px" />
        </ElFormItem>
        <ElFormItem v-if="layout === 'usdt'" label="美金数">
          <ElInput v-model="createForm.amount_usd" placeholder="0.00" clearable style="width: 120px" />
        </ElFormItem>
        <ElFormItem label="人员">
          <ElInput v-model="createForm.employee_name" placeholder="员工名" clearable style="width: 120px" />
        </ElFormItem>
        <ElFormItem label="清空状态">
          <ElSelect v-model="createForm.clear_status" style="width: 110px">
            <ElOption value="未清空" label="未清空" />
            <ElOption value="已清空" label="已清空" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="备注">
          <ElInput v-model="createForm.remark" placeholder="选填" clearable style="width: 160px" />
        </ElFormItem>
        <ElFormItem>
          <BaseButton type="primary" :loading="creating" @click="onCreate">添加</BaseButton>
        </ElFormItem>
      </ElForm>
    </section>

    <section class="wbot-section">
      <div class="wbot-section__title">筛选</div>
      <ElForm inline class="wbot-form" @submit.prevent="onSearch">
        <ElFormItem label="人员">
          <ElSelect
            v-model="employeeFilter"
            clearable
            filterable
            :loading="empLoading"
            placeholder="全部人员"
            style="width: 140px"
          >
            <ElOption label="全部人员" value="" />
            <ElOption v-for="name in employees" :key="name" :label="name" :value="name" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="关键词">
          <ElInput
            v-model="keyword"
            clearable
            placeholder="搜人员 / 业务名 / 备注"
            style="width: 220px"
            @keyup.enter="onSearch"
          />
        </ElFormItem>
        <ElFormItem>
          <BaseButton type="primary" :loading="loading" @click="onSearch">查询</BaseButton>
          <BaseButton class="ml-8px" @click="onResetFilter">重置</BaseButton>
          <BaseButton class="ml-8px" :loading="loading || empLoading" @click="refreshAll">刷新</BaseButton>
          <BaseButton
            class="ml-8px"
            type="danger"
            :disabled="!selectedRows.length"
            :loading="batchDeleting"
            @click="onBatchDelete"
          >
            批量删除{{ selectedRows.length ? ` (${selectedRows.length})` : '' }}
          </BaseButton>
        </ElFormItem>
      </ElForm>
    </section>

    <Table
      v-model:current-page="page"
      v-model:page-size="pageSize"
      row-key="id"
      :columns="columns"
      :data="rows"
      :loading="loading"
      :pagination="{ total: totalCount, pageSizes: [30], layout: 'total, prev, pager, next' }"
      @selection-change="onSelectionChange"
    />

    <ElDialog v-model="editOpen" title="编辑记录" width="520px" destroy-on-close>
      <ElForm label-width="90px">
        <ElFormItem label="时间">
          <ElDatePicker
            v-model="editForm.occurred_at"
            type="datetime"
            value-format="YYYY-MM-DD HH:mm:ss"
            placeholder="选择时间"
            style="width: 100%"
          />
        </ElFormItem>
        <ElFormItem v-if="layout === 'sku'" label="业务名">
          <ElInput v-model="editForm.business_name" placeholder="如：一个月 / pro100刀" clearable />
        </ElFormItem>
        <ElFormItem v-if="layout !== 'usdt'" label="数量">
          <ElSelect v-model="editForm.quantity" style="width: 120px">
            <ElOption :value="1" label="+1" />
            <ElOption :value="-1" label="-1" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem v-if="layout === 'usdt'" label="人民币数">
          <ElInput v-model="editForm.amount_cny" placeholder="0.00" clearable />
        </ElFormItem>
        <ElFormItem v-if="layout === 'usdt'" label="美金数">
          <ElInput v-model="editForm.amount_usd" placeholder="0.00" clearable />
        </ElFormItem>
        <ElFormItem label="人员">
          <ElInput v-model="editForm.employee_name" placeholder="员工名" clearable />
        </ElFormItem>
        <ElFormItem label="清空状态">
          <ElSelect v-model="editForm.clear_status" style="width: 140px">
            <ElOption value="未清空" label="未清空" />
            <ElOption value="已清空" label="已清空" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="备注">
          <ElInput v-model="editForm.remark" type="textarea" :rows="2" maxlength="500" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <BaseButton @click="editOpen = false">取消</BaseButton>
        <BaseButton type="primary" :loading="editSaving" @click="saveEdit">保存</BaseButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.wbot-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.wbot-section__title {
  margin-bottom: 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.wbot-form {
  row-gap: 4px;
}

.wbot-form :deep(.el-form-item) {
  margin-right: 12px;
  margin-bottom: 8px;
}

.wbot-form :deep(.el-form-item__label) {
  padding-right: 6px;
}

.ml-8px {
  margin-left: 8px;
}
</style>
