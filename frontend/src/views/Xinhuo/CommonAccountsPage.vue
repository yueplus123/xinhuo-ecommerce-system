<script setup lang="tsx">
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

defineOptions({ name: 'CommonAccounts' })

const emptyForm = () => ({
  platform: '',
  account: '',
  password: '',
  remark: ''
})

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
  onCreate,
  openEdit,
  saveEdit,
  onDelete
} = useCrudPage({
  endpoint: '/common-accounts/',
  pageSize: 20,
  emptyForm,
  payloadFrom,
  validate: validatePayload,
  rowToForm: (r) => ({
    platform: r.platform || '',
    account: r.account || '',
    password: r.password || '',
    remark: r.remark || ''
  }),
  deleteMessage: (r) => `确定删除「${r.platform}」账号「${r.account}」吗？`,
  deleteSuccessText: '已删除',
  resetPageOnCreate: true
})

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
