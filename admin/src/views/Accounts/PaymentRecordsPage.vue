<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  ElButton,
  ElCheckbox,
  ElDatePicker,
  ElDialog,
  ElForm,
  ElFormItem,
  ElImage,
  ElInput,
  ElInputNumber,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElPagination,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElUpload,
  type UploadUserFile
} from 'element-plus'
import ContentWrap from '@/components/ContentWrap.vue'
import { formatRequestError, formatDateTimeSeconds } from '@/utils/format'
import {
  createManagePayment,
  deleteManagePayment,
  exportManagePayments,
  getAccountsOptions,
  listManagePayments,
  updateManagePayment,
  type AccountsOptions,
  type PaymentImage,
  type PaymentRecordRow
} from '@/api/modules/accounts'

defineOptions({ name: 'ManagePaymentRecords' })

const opts = ref<AccountsOptions | null>(null)
const rows = ref<PaymentRecordRow[]>([])
const loading = ref(false)
const saving = ref(false)
const page = ref(1)
const pageSize = ref(30)
const total = ref(0)
const filter = ref<{ user: number | ''; channel: string; range: [string, string] | undefined }>({
  user: '',
  channel: '',
  range: undefined
})

function filterParams() {
  const p: Recordable = {}
  if (filter.value.user) p.user = filter.value.user
  if (filter.value.channel) p.channel = filter.value.channel
  if (filter.value.range?.[0]) p.date_from = filter.value.range[0]
  if (filter.value.range?.[1]) p.date_to = filter.value.range[1]
  return p
}

async function load() {
  loading.value = true
  try {
    const { data } = await listManagePayments({ ...filterParams(), page: page.value })
    rows.value = data.results
    total.value = data.count
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
  filter.value = { user: '', channel: '', range: undefined }
  search()
}

async function onExport() {
  try {
    const resp = await exportManagePayments(filterParams())
    const url = URL.createObjectURL(resp.data)
    const a = document.createElement('a')
    a.href = url
    a.download = 'payment_records.xlsx'
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '导出失败'))
  }
}

const dialogOpen = ref(false)
const editId = ref<number | null>(null)
const form = ref({
  user: undefined as number | undefined,
  channel: '',
  order_count: 0,
  amount: '0',
  note: '',
  record_date: ''
})
const existingImages = ref<PaymentImage[]>([])
const deleteMain = ref(false)
const deleteExtraIds = ref<number[]>([])
const newFiles = ref<UploadUserFile[]>([])

function openAdd() {
  editId.value = null
  form.value = { user: undefined, channel: '', order_count: 0, amount: '0', note: '', record_date: '' }
  existingImages.value = []
  deleteMain.value = false
  deleteExtraIds.value = []
  newFiles.value = []
  dialogOpen.value = true
}

function openEdit(row: PaymentRecordRow) {
  editId.value = row.id
  form.value = {
    user: row.user,
    channel: row.channel,
    order_count: row.order_count,
    amount: row.amount,
    note: row.note,
    record_date: row.record_date || ''
  }
  existingImages.value = row.images
  deleteMain.value = false
  deleteExtraIds.value = []
  newFiles.value = []
  dialogOpen.value = true
}

function toggleExtra(id: number | null, on: boolean) {
  if (id === null) return
  deleteExtraIds.value = on ? [...deleteExtraIds.value, id] : deleteExtraIds.value.filter((x) => x !== id)
}

async function save() {
  const f = form.value
  if (!f.user) return ElMessage.warning('请选择填写人。')
  if (!f.channel) return ElMessage.warning('请选择收款渠道。')
  const fd = new FormData()
  fd.append('user', String(f.user))
  fd.append('channel', f.channel)
  fd.append('order_count', String(f.order_count ?? 0))
  fd.append('amount', String(f.amount ?? '0'))
  fd.append('note', f.note.trim().slice(0, 500))
  if (f.record_date) fd.append('record_date', f.record_date)
  if (editId.value !== null) {
    if (deleteMain.value) fd.append('delete_main_screenshot', 'on')
    deleteExtraIds.value.forEach((id) => fd.append('delete_extra_image_ids', String(id)))
  }
  newFiles.value.forEach((u) => u.raw && fd.append('payment_images', u.raw))
  saving.value = true
  try {
    if (editId.value === null) await createManagePayment(fd)
    else await updateManagePayment(editId.value, fd)
    ElMessage.success(editId.value === null ? '记录已添加' : '记录已更新')
    dialogOpen.value = false
    await load()
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '保存失败'))
  } finally {
    saving.value = false
  }
}

async function onDelete(row: PaymentRecordRow) {
  try {
    await ElMessageBox.confirm(
      `确定删除「${row.channel_label} / ${row.amount} / ${row.user_name}」这条记录吗？`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await deleteManagePayment(row.id)
    ElMessage.success('已删除')
    await load()
  } catch (e: any) {
    if (e !== 'cancel' && e?.action !== 'cancel') ElMessage.error(formatRequestError(e, '删除失败'))
  }
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
  <ContentWrap title="收款记录管理">
    <div class="mb-12px text-13px text-[var(--el-text-color-secondary)]">
      与职员端「收款统计」同源数据；仅超级管理员可在此增删改查并管理截图。
    </div>
    <div class="mb-12px flex flex-wrap items-center gap-8px">
      <ElSelect v-model="filter.user" clearable filterable placeholder="全部人员" style="width: 160px">
        <ElOption v-for="u in opts?.all_staff_users ?? []" :key="u.id" :label="u.username" :value="u.id" />
      </ElSelect>
      <ElSelect v-model="filter.channel" clearable placeholder="全部渠道" style="width: 160px">
        <ElOption v-for="c in opts?.channels ?? []" :key="c.value" :label="c.label" :value="c.value" />
      </ElSelect>
      <ElDatePicker
        v-model="filter.range"
        type="daterange"
        value-format="YYYY-MM-DD"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        style="width: 260px"
      />
      <ElButton type="primary" @click="search">查询</ElButton>
      <ElButton @click="resetFilter">重置</ElButton>
      <ElButton @click="onExport">导出 Excel</ElButton>
      <ElButton type="primary" @click="openAdd">新增记录</ElButton>
    </div>

    <ElTable v-loading="loading" :data="rows" border>
      <ElTableColumn prop="channel_label" label="渠道" min-width="110" />
      <ElTableColumn prop="order_count" label="订单数" width="80" />
      <ElTableColumn prop="amount" label="金额" min-width="100" />
      <ElTableColumn prop="user_name" label="填写人" min-width="100" />
      <ElTableColumn label="订单时间" width="110">
        <template #default="{ row }">{{ row.record_date || '—' }}</template>
      </ElTableColumn>
      <ElTableColumn label="填写时间" min-width="165">
        <template #default="{ row }">{{ row.created_at ? formatDateTimeSeconds(row.created_at) : '—' }}</template>
      </ElTableColumn>
      <ElTableColumn label="备注" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.note || '—' }}</template>
      </ElTableColumn>
      <ElTableColumn label="截图" min-width="130">
        <template #default="{ row }">
          <div v-if="row.images.length" class="flex gap-4px">
            <ElImage
              v-for="(img, i) in row.images.slice(0, 3)"
              :key="img.url"
              :src="img.url"
              :preview-src-list="row.images.map((x: PaymentImage) => x.url)"
              :initial-index="i"
              preview-teleported
              fit="cover"
              style="width: 36px; height: 36px; border-radius: 4px"
            />
            <span v-if="row.images.length > 3" class="self-center text-12px">+{{ row.images.length - 3 }}</span>
          </div>
          <span v-else>—</span>
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
      :title="editId === null ? '新增订单记录' : '编辑订单记录'"
      width="560px"
      destroy-on-close
    >
      <ElForm label-width="90px">
        <ElFormItem label="填写人">
          <ElSelect v-model="form.user" filterable placeholder="请选择" style="width: 100%">
            <ElOption v-for="u in opts?.staff_users ?? []" :key="u.id" :label="u.username" :value="u.id" />
            <ElOption
              v-if="form.user && !(opts?.staff_users ?? []).some((u) => u.id === form.user)"
              :label="rows.find((r) => r.user === form.user)?.user_name ?? String(form.user)"
              :value="form.user"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="收款渠道">
          <ElSelect v-model="form.channel" placeholder="请选择" style="width: 100%">
            <ElOption v-for="c in opts?.channels ?? []" :key="c.value" :label="c.label" :value="c.value" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="订单数">
          <ElInputNumber v-model="form.order_count" :min="0" :precision="0" />
        </ElFormItem>
        <ElFormItem label="金额">
          <ElInput v-model="form.amount" placeholder="例如 128.50" />
        </ElFormItem>
        <ElFormItem label="订单时间">
          <ElDatePicker
            v-model="form.record_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="留空则为今天"
            style="width: 100%"
          />
        </ElFormItem>
        <ElFormItem label="备注">
          <ElInput v-model="form.note" type="textarea" :rows="3" maxlength="500" show-word-limit />
        </ElFormItem>
        <ElFormItem v-if="existingImages.length" label="已有截图">
          <div class="flex flex-wrap gap-12px">
            <div v-for="img in existingImages" :key="img.url" class="flex flex-col items-center gap-4px">
              <ElImage
                :src="img.url"
                :preview-src-list="existingImages.map((x) => x.url)"
                preview-teleported
                fit="cover"
                style="width: 72px; height: 72px; border-radius: 4px"
              />
              <ElCheckbox
                v-if="img.kind === 'main'"
                v-model="deleteMain"
                label="删除"
              />
              <ElCheckbox
                v-else
                :model-value="deleteExtraIds.includes(img.id as number)"
                label="删除"
                @update:model-value="(v: any) => toggleExtra(img.id, !!v)"
              />
            </div>
          </div>
        </ElFormItem>
        <ElFormItem label="上传截图">
          <ElUpload
            v-model:file-list="newFiles"
            list-type="picture-card"
            multiple
            accept="image/*"
            :auto-upload="false"
          >
            +
          </ElUpload>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="dialogOpen = false">取消</ElButton>
        <ElButton type="primary" :loading="saving" @click="save">保存</ElButton>
      </template>
    </ElDialog>
  </ContentWrap>
</template>
