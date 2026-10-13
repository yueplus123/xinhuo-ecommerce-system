<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  ElButton,
  ElDatePicker,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElPagination,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag
} from 'element-plus'
import ContentWrap from '@/components/ContentWrap.vue'
import { formatRequestError, formatDateTime } from '@/utils/format'
import {
  createManageReminder,
  deleteManageReminder,
  getAccountsOptions,
  listManageReminders,
  updateManageReminder,
  type AccountsOptions,
  type ReminderRow
} from '@/api/modules/accounts'

defineOptions({ name: 'ManageSubscriptionReminders' })

const opts = ref<AccountsOptions | null>(null)
const rows = ref<ReminderRow[]>([])
const loading = ref(false)
const saving = ref(false)
const page = ref(1)
const pageSize = ref(30)
const total = ref(0)
const totalAll = ref(0)
const filter = ref<{ q: string; user: number | '' }>({ q: '', user: '' })

async function load() {
  loading.value = true
  try {
    const params: Recordable = { page: page.value }
    if (filter.value.q.trim()) params.q = filter.value.q.trim()
    if (filter.value.user) params.user = filter.value.user
    const { data } = await listManageReminders(params)
    rows.value = data.results
    total.value = data.total_filtered
    totalAll.value = data.total_all
    pageSize.value = data.page_size
    page.value = data.page
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '加载失败'))
    rows.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  load()
}

function resetFilter() {
  filter.value = { q: '', user: '' }
  search()
}

const dialogOpen = ref(false)
const editId = ref<number | null>(null)
const form = ref({
  user: undefined as number | undefined,
  wechat_label: '',
  platform_display: '',
  remark: '',
  next_reminder_at: ''
})

function openAdd() {
  editId.value = null
  form.value = { user: undefined, wechat_label: '', platform_display: '', remark: '', next_reminder_at: '' }
  dialogOpen.value = true
}

function openEdit(row: ReminderRow) {
  editId.value = row.id
  form.value = {
    user: row.user,
    wechat_label: row.wechat_label,
    platform_display: row.platform_name,
    remark: row.remark,
    next_reminder_at: row.next_reminder_at || ''
  }
  dialogOpen.value = true
}

async function save() {
  const f = form.value
  if (!f.user) return ElMessage.warning('请选择负责人。')
  if (!f.wechat_label.trim()) return ElMessage.warning('请填写微信名或微信号。')
  if (!f.platform_display.trim()) return ElMessage.warning('请填写或选择订阅平台。')
  if (!f.next_reminder_at) return ElMessage.warning('请选择下次提醒日期。')
  const body = {
    user: f.user,
    wechat_label: f.wechat_label.trim(),
    platform_display: f.platform_display.trim(),
    remark: f.remark.trim().slice(0, 500),
    next_reminder_at: f.next_reminder_at
  }
  saving.value = true
  try {
    if (editId.value === null) await createManageReminder(body)
    else await updateManageReminder(editId.value, body)
    ElMessage.success(editId.value === null ? '提醒已添加' : '提醒已更新')
    dialogOpen.value = false
    await load()
    opts.value = (await getAccountsOptions()).data
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '保存失败'))
  } finally {
    saving.value = false
  }
}

async function onDelete(row: ReminderRow) {
  try {
    await ElMessageBox.confirm(
      `确定删除「${row.wechat_label} / ${row.platform_name || '—'} / ${row.user_name}」这条提醒吗？`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await deleteManageReminder(row.id)
    ElMessage.success('已删除')
    await load()
  } catch (e: any) {
    if (e !== 'cancel' && e?.action !== 'cancel') ElMessage.error(formatRequestError(e, '删除失败'))
  }
}

function statusType(s: string) {
  if (s === 'overdue') return 'danger'
  if (s === 'today') return 'warning'
  if (s === 'pending') return 'success'
  return 'info'
}

onMounted(async () => {
  load()
  try {
    opts.value = (await getAccountsOptions()).data
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '加载选项失败'))
  }
})
</script>

<template>
  <ContentWrap title="订阅提醒管理">
    <div class="mb-12px text-13px text-[var(--el-text-color-secondary)]">
      共 {{ totalAll }} 条提醒（当前筛选 {{ total }} 条）。仅超级管理员可在此增删改并指定负责人。
    </div>
    <div class="mb-12px flex flex-wrap items-center gap-8px">
      <ElInput
        v-model="filter.q"
        clearable
        placeholder="微信名/微信号/订阅平台/备注"
        style="width: 260px"
        @keyup.enter="search"
      />
      <ElSelect v-model="filter.user" clearable filterable placeholder="全部员工" style="width: 160px">
        <ElOption v-for="u in opts?.staff_users ?? []" :key="u.id" :label="u.username" :value="u.id" />
      </ElSelect>
      <ElButton type="primary" @click="search">查询</ElButton>
      <ElButton @click="resetFilter">重置</ElButton>
      <ElButton type="primary" @click="openAdd">新增提醒</ElButton>
    </div>

    <ElTable v-loading="loading" :data="rows" border>
      <ElTableColumn label="负责人" min-width="130">
        <template #default="{ row }">
          <div>{{ row.user_name }}</div>
          <div class="text-12px text-[var(--el-text-color-secondary)]">用户编号 {{ row.user }}</div>
        </template>
      </ElTableColumn>
      <ElTableColumn prop="wechat_label" label="微信名/微信号" min-width="140" />
      <ElTableColumn label="订阅平台" min-width="120">
        <template #default="{ row }">{{ row.platform_name || '—' }}</template>
      </ElTableColumn>
      <ElTableColumn label="备注" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.remark || '—' }}</template>
      </ElTableColumn>
      <ElTableColumn label="下次提醒" width="110">
        <template #default="{ row }">{{ row.next_reminder_at || '—' }}</template>
      </ElTableColumn>
      <ElTableColumn label="上次续费登记" min-width="150">
        <template #default="{ row }">{{ row.last_renewed_at ? formatDateTime(row.last_renewed_at) : '—' }}</template>
      </ElTableColumn>
      <ElTableColumn label="状态" width="110">
        <template #default="{ row }">
          <ElTag :type="statusType(row.status)" effect="plain">{{ row.status_text }}</ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <ElButton type="primary" link @click="openEdit(row)">编辑</ElButton>
          <ElButton type="danger" link @click="onDelete(row)">删除</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>

    <div class="mt-12px flex justify-end">
      <ElPagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="load"
      />
    </div>

    <ElDialog
      v-model="dialogOpen"
      :title="editId === null ? '新增订阅提醒' : '编辑订阅提醒'"
      width="480px"
      destroy-on-close
    >
      <ElForm label-width="110px">
        <ElFormItem label="负责人">
          <ElSelect v-model="form.user" filterable placeholder="请选择" style="width: 100%">
            <ElOption v-for="u in opts?.staff_users ?? []" :key="u.id" :label="u.username" :value="u.id" />
            <ElOption
              v-if="form.user && !(opts?.staff_users ?? []).some((u) => u.id === form.user)"
              :label="rows.find((r) => r.user === form.user)?.user_name ?? String(form.user)"
              :value="form.user"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="微信名或微信号">
          <ElInput v-model="form.wechat_label" maxlength="200" placeholder="客户微信备注" />
        </ElFormItem>
        <ElFormItem label="订阅平台">
          <ElSelect
            v-model="form.platform_display"
            filterable
            allow-create
            default-first-option
            placeholder="输入或选择已有平台"
            style="width: 100%"
          >
            <ElOption v-for="n in opts?.platform_options ?? []" :key="n" :label="n" :value="n" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="下次提醒日期">
          <ElDatePicker v-model="form.next_reminder_at" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </ElFormItem>
        <ElFormItem label="备注">
          <ElInput v-model="form.remark" type="textarea" :rows="2" maxlength="500" placeholder="选填" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="dialogOpen = false">取消</ElButton>
        <ElButton type="primary" :loading="saving" @click="save">保存</ElButton>
      </template>
    </ElDialog>
  </ContentWrap>
</template>
