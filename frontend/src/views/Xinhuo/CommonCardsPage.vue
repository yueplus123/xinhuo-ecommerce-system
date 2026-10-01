<script setup lang="tsx">
import { reactive } from 'vue'
import {
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage
} from 'element-plus'
import { Table, TableColumn } from '@/components/Table'
import { BaseButton } from '@/components/Button'
import { useCrudPage } from '@/hooks/web/useCrudPage'
import { formatDateTimeSeconds } from '@/utils/format'

defineOptions({ name: 'CommonCardNumbers' })

const searchParams = reactive({ q: '' })

const emptyForm = () => ({
  platform: '',
  card_number: '',
  expiry: '',
  cvv: '',
  remark: ''
})

function payloadFrom(src: Recordable) {
  return {
    platform: String(src.platform || '').trim(),
    card_number: String(src.card_number || '').trim(),
    expiry: String(src.expiry || '').trim(),
    cvv: String(src.cvv || '').trim(),
    remark: String(src.remark || '').trim().slice(0, 500)
  }
}

function validatePayload(p: ReturnType<typeof payloadFrom>) {
  if (!p.platform || !p.card_number || !p.expiry || !p.cvv) {
    ElMessage.warning('请填写平台、卡号、有效期和安全码。')
    return false
  }
  return true
}

const {
  rows,
  loading,
  saving,
  page,
  pageSize,
  totalCount,
  form,
  editOpen,
  editForm,
  loadRows,
  onCreate,
  openEdit,
  saveEdit,
  onDelete
} = useCrudPage({
  endpoint: '/common-cards/',
  pageSize: 50,
  emptyForm,
  payloadFrom,
  validate: validatePayload,
  rowToForm: (r) => ({
    platform: r.platform || '',
    card_number: r.card_number || '',
    expiry: r.expiry || '',
    cvv: r.cvv || '',
    remark: r.remark || ''
  }),
  deleteMessage: (r) => `确定删除「${r.platform}」的卡号记录吗？`,
  extraParams: () => (searchParams.q.trim() ? { q: searchParams.q.trim() } : {})
})

function onSearch(params: Recordable = {}) {
  Object.assign(searchParams, { q: params.q || '' })
  if (page.value === 1) {
    loadRows()
  } else {
    page.value = 1
  }
}

function onResetSearch() {
  searchParams.q = ''
  onSearch({ q: '' })
}

const columns: TableColumn[] = [
  { field: 'platform', label: '平台', minWidth: 120 },
  { field: 'card_number', label: '卡号', minWidth: 180 },
  { field: 'expiry', label: '有效期', minWidth: 100 },
  { field: 'cvv', label: '安全码', minWidth: 90 },
  {
    field: 'updated_at',
    label: '最近更改日期',
    minWidth: 170,
    formatter: (_r, _c, v) => formatDateTimeSeconds(v)
  },
  {
    field: 'remark',
    label: '备注/平台',
    minWidth: 160,
    showOverflowTooltip: true,
    formatter: (_r, _c, v) => v || '—'
  },
  {
    field: 'action',
    label: '操作',
    width: 140,
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

</script>

<template>
  <div>
    <div class="mb-20px">
      <div class="mb-12px text-15px font-600">新建</div>
      <ElForm class="common-card-create" inline label-width="auto" @submit.prevent="onCreate">
        <ElFormItem label="平台">
          <ElInput v-model="form.platform" maxlength="100" placeholder="平台" style="width: 120px" />
        </ElFormItem>
        <ElFormItem label="卡号">
          <ElInput
            v-model="form.card_number"
            maxlength="64"
            placeholder="卡号"
            style="width: 180px"
          />
        </ElFormItem>
        <ElFormItem label="有效期">
          <ElInput v-model="form.expiry" maxlength="16" placeholder="如 12/28" style="width: 100px" />
        </ElFormItem>
        <ElFormItem label="安全码">
          <ElInput v-model="form.cvv" maxlength="8" placeholder="CVV" style="width: 90px" />
        </ElFormItem>
        <ElFormItem label="备注/平台">
          <ElInput v-model="form.remark" maxlength="500" placeholder="选填" style="width: 140px" />
        </ElFormItem>
        <ElFormItem>
          <BaseButton type="primary" :loading="saving" @click="onCreate">添加</BaseButton>
        </ElFormItem>
      </ElForm>
    </div>

    <ElForm
      class="common-card-search"
      inline
      label-width="auto"
      @submit.prevent="() => onSearch({ q: searchParams.q })"
    >
      <ElFormItem label="关键词">
        <ElInput
          v-model="searchParams.q"
          clearable
          placeholder="搜平台、卡号、备注/平台"
          style="width: 220px"
          @keyup.enter="() => onSearch({ q: searchParams.q })"
        />
      </ElFormItem>
      <ElFormItem>
        <BaseButton type="primary" :loading="loading" @click="() => onSearch({ q: searchParams.q })">
          查询
        </BaseButton>
        <BaseButton @click="onResetSearch">重置</BaseButton>
      </ElFormItem>
    </ElForm>
    <Table
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :columns="columns"
      :data="rows"
      :loading="loading"
      :pagination="{ total: totalCount, pageSizes: [50], layout: 'total, prev, pager, next' }"
    />

    <ElDialog v-model="editOpen" title="编辑常用卡" width="460px" destroy-on-close>
      <ElForm label-width="100px">
        <ElFormItem label="平台">
          <ElInput v-model="editForm.platform" maxlength="100" />
        </ElFormItem>
        <ElFormItem label="卡号">
          <ElInput v-model="editForm.card_number" maxlength="64" />
        </ElFormItem>
        <ElFormItem label="有效期">
          <ElInput v-model="editForm.expiry" maxlength="16" placeholder="如 12/28" />
        </ElFormItem>
        <ElFormItem label="安全码">
          <ElInput v-model="editForm.cvv" maxlength="8" />
        </ElFormItem>
        <ElFormItem label="备注/平台">
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
.common-card-create,
.common-card-search {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 4px 10px;
  overflow-x: auto;
}
.common-card-search {
  margin-bottom: 16px;
}
.common-card-create :deep(.el-form-item),
.common-card-search :deep(.el-form-item) {
  margin-right: 0;
  margin-bottom: 0;
  flex-shrink: 0;
}
.common-card-create :deep(.el-form-item__label),
.common-card-search :deep(.el-form-item__label) {
  padding-right: 6px;
}
.common-card-create > :deep(.el-form-item:first-child) .el-form-item__label,
.common-card-search > :deep(.el-form-item:first-child) .el-form-item__label {
  width: 4.5em;
  justify-content: flex-start;
}
.mb-12px {
  margin-bottom: 12px;
}
.mb-20px {
  margin-bottom: 20px;
}
</style>
