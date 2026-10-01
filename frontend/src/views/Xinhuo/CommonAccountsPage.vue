<script setup lang="tsx">
import { onMounted, ref, watch } from 'vue'
import {
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElMessageBox
} from 'element-plus'
import { Table, TableColumn } from '@/components/Table'
import { BaseButton } from '@/components/Button'
import api from '@/api/xinhuo/client'

defineOptions({ name: 'CommonAccounts' })

const emptyForm = () => ({
  platform: '',
  account: '',
  password: '',
  remark: ''
})

const rows = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const page = ref(1)
const pageSize = ref(20)
const totalCount = ref(0)
const form = ref(emptyForm())
const editOpen = ref(false)
const editId = ref<number | null>(null)
const editForm = ref(emptyForm())

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

function formatDateTimeSeconds(iso: string) {
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
    second: '2-digit',
    hour12: false
  })
    .format(d)
    .replace(/\//g, '-')
}

function payloadFrom(src: Recordable) {
  return {
    platform: String(src.platform || '').trim(),
    account: String(src.account || '').trim(),
    password: String(src.password || '').trim(),
    remark: String(src.remark || '').trim().slice(0, 500)
  }
}

function validatePayload(p: ReturnType<typeof payloadFrom>) {
  if (!p.platform || !p.account || !p.password) {
    ElMessage.warning('请填写平台、账号和密码。')
    return false
  }
  return true
}

async function loadRows() {
  loading.value = true
  try {
    const { data } = await api.get('/common-accounts/', {
      params: { page: page.value, page_size: pageSize.value }
    })
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

watch(page, (next, prev) => {
  if (next !== prev) loadRows()
})

async function onCreate() {
  const body = payloadFrom(form.value)
  if (!validatePayload(body)) return
  saving.value = true
  try {
    await api.post('/common-accounts/', body)
    form.value = emptyForm()
    ElMessage.success('添加成功')
    page.value = 1
    await loadRows()
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '保存失败'))
  } finally {
    saving.value = false
  }
}

function openEdit(r: any) {
  editId.value = r.id
  editForm.value = {
    platform: r.platform || '',
    account: r.account || '',
    password: r.password || '',
    remark: r.remark || ''
  }
  editOpen.value = true
}

async function saveEdit() {
  if (!editId.value) return
  const body = payloadFrom(editForm.value)
  if (!validatePayload(body)) return
  saving.value = true
  try {
    await api.patch(`/common-accounts/${editId.value}/`, body)
    editOpen.value = false
    ElMessage.success('更新成功')
    await loadRows()
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '更新失败'))
  } finally {
    saving.value = false
  }
}

async function onDelete(r: any) {
  try {
    await ElMessageBox.confirm(
      `确定删除「${r.platform}」账号「${r.account}」吗？`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await api.delete(`/common-accounts/${r.id}/`)
    ElMessage.success('已删除')
    await loadRows()
  } catch (e: any) {
    if (e !== 'cancel' && e?.action !== 'cancel') {
      ElMessage.error(formatRequestError(e, '删除失败'))
    }
  }
}

const columns: TableColumn[] = [
  {
    field: 'updated_at',
    label: '更新时间',
    minWidth: 160,
    formatter: (_r, _c, v) => formatDateTimeSeconds(v)
  },
  { field: 'account', label: '账号', minWidth: 140 },
  { field: 'password', label: '密码', minWidth: 120 },
  { field: 'platform', label: '平台', minWidth: 110 },
  {
    field: 'remark',
    label: '备注',
    minWidth: 140,
    showOverflowTooltip: true,
    formatter: (_r, _c, v) => v || '—'
  },
  {
    field: 'action',
    label: '操作',
    width: 130,
    fixed: 'right',
    slots: {
      default: (data) => (
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
]

onMounted(() => {
  loadRows()
})
</script>

<template>
  <div>
    <div class="mb-20px">
      <div class="mb-12px text-15px font-600">新建</div>
      <ElForm class="common-acc-create" inline label-width="auto" @submit.prevent="onCreate">
        <ElFormItem label="平台">
          <ElInput v-model="form.platform" maxlength="100" placeholder="平台" style="width: 120px" />
        </ElFormItem>
        <ElFormItem label="账号">
          <ElInput v-model="form.account" maxlength="200" placeholder="账号" style="width: 150px" />
        </ElFormItem>
        <ElFormItem label="密码">
          <ElInput v-model="form.password" maxlength="500" placeholder="密码" style="width: 140px" />
        </ElFormItem>
        <ElFormItem label="备注">
          <ElInput v-model="form.remark" maxlength="500" placeholder="选填" style="width: 140px" />
        </ElFormItem>
        <ElFormItem>
          <BaseButton type="primary" :loading="saving" @click="onCreate">添加</BaseButton>
        </ElFormItem>
      </ElForm>
    </div>

    <Table
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :columns="columns"
      :data="rows"
      :loading="loading"
      :pagination="{ total: totalCount, pageSizes: [20], layout: 'total, prev, pager, next' }"
    />

    <ElDialog v-model="editOpen" title="编辑常用号" width="460px" destroy-on-close>
      <ElForm label-width="80px">
        <ElFormItem label="平台">
          <ElInput v-model="editForm.platform" maxlength="100" />
        </ElFormItem>
        <ElFormItem label="账号">
          <ElInput v-model="editForm.account" maxlength="200" />
        </ElFormItem>
        <ElFormItem label="密码">
          <ElInput v-model="editForm.password" maxlength="500" />
        </ElFormItem>
        <ElFormItem label="备注">
          <ElInput v-model="editForm.remark" maxlength="500" type="textarea" :rows="2" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <BaseButton @click="editOpen = false">取消</BaseButton>
        <BaseButton type="primary" :loading="saving" @click="saveEdit">保存</BaseButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.common-acc-create {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 4px 10px;
  overflow-x: auto;
}
.common-acc-create :deep(.el-form-item) {
  margin-right: 0;
  margin-bottom: 0;
  flex-shrink: 0;
}
.common-acc-create :deep(.el-form-item__label) {
  padding-right: 6px;
}
.mb-12px {
  margin-bottom: 12px;
}
.mb-20px {
  margin-bottom: 20px;
}
</style>
