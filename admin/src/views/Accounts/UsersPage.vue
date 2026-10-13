<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElSelect,
  ElSwitch,
  ElTable,
  ElTableColumn,
  ElTag
} from 'element-plus'
import ContentWrap from '@/components/ContentWrap.vue'
import { formatRequestError, formatDateTimeSeconds } from '@/utils/format'
import {
  createManageUser,
  deleteManageUser,
  getAccountsOptions,
  listManageUsers,
  updateManageUser,
  type StaffUserRow
} from '@/api/modules/accounts'

defineOptions({ name: 'ManageUsers' })

const rows = ref<StaffUserRow[]>([])
const roles = ref<{ value: string; label: string }[]>([])
const loading = ref(false)
const saving = ref(false)
const dialogOpen = ref(false)
const editId = ref<number | null>(null)
const form = ref({ username: '', role: 'employee', is_active: true, password: '' })

async function load() {
  loading.value = true
  try {
    const { data } = await listManageUsers()
    rows.value = data
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '加载失败'))
  } finally {
    loading.value = false
  }
}

function openAdd() {
  editId.value = null
  form.value = { username: '', role: 'employee', is_active: true, password: '' }
  dialogOpen.value = true
}

function openEdit(row: StaffUserRow) {
  editId.value = row.id
  form.value = { username: row.username, role: row.role, is_active: row.is_active, password: '' }
  dialogOpen.value = true
}

async function save() {
  const f = form.value
  const username = f.username.trim()
  if (!username) return ElMessage.warning('请填写用户名。')
  if (editId.value === null && !f.password.trim()) return ElMessage.warning('请设置密码。')
  const body: Recordable = { username, role: f.role, is_active: f.is_active }
  if (f.password.trim()) body.password = f.password
  saving.value = true
  try {
    if (editId.value === null) await createManageUser(body)
    else await updateManageUser(editId.value, body)
    ElMessage.success(editId.value === null ? '用户已创建' : '用户已更新')
    dialogOpen.value = false
    await load()
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '保存失败'))
  } finally {
    saving.value = false
  }
}

async function onDelete(row: StaffUserRow) {
  try {
    await ElMessageBox.confirm(`确定删除用户「${row.username}」吗？其名下的收款记录、订阅提醒等数据会一并删除。`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await deleteManageUser(row.id)
    ElMessage.success('用户已删除')
    await load()
  } catch (e: any) {
    if (e !== 'cancel' && e?.action !== 'cancel') ElMessage.error(formatRequestError(e, '删除失败'))
  }
}

function roleTagType(role: string): 'success' | 'warning' | 'info' | 'primary' | 'danger' {
  if (role === 'admin') return 'danger'
  if (role === 'boss') return 'warning'
  if (role === 'ceo') return 'success'
  if (role === 'guest') return 'info'
  return 'primary'
}

onMounted(async () => {
  load()
  try {
    roles.value = (await getAccountsOptions()).data.roles
  } catch {
    roles.value = []
  }
})
</script>

<template>
  <ContentWrap title="职员账号管理">
    <div class="mb-12px flex items-center justify-between">
      <span class="text-13px text-[var(--el-text-color-secondary)]">
        维护职员端登录账号：可新增员工、CEO、管理员、老板与游客/访客，并分配权限等级。
      </span>
      <ElButton type="primary" @click="openAdd">新增用户</ElButton>
    </div>

    <ElTable v-loading="loading" :data="rows" border>
      <ElTableColumn prop="username" label="用户名" min-width="140" />
      <ElTableColumn label="权限等级" width="110">
        <template #default="{ row }">
          <ElTag :type="roleTagType(row.role)" effect="plain">{{ row.role_label }}</ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn label="状态" width="90">
        <template #default="{ row }">
          <ElTag :type="row.is_active ? 'success' : 'info'" effect="plain">
            {{ row.is_active ? '启用' : '停用' }}
          </ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn label="最近登录" min-width="170">
        <template #default="{ row }">{{ row.last_login ? formatDateTimeSeconds(row.last_login) : '—' }}</template>
      </ElTableColumn>
      <ElTableColumn label="最近IP" min-width="130">
        <template #default="{ row }">{{ row.last_login_ip || '—' }}</template>
      </ElTableColumn>
      <ElTableColumn label="操作" width="130" fixed="right">
        <template #default="{ row }">
          <ElButton type="primary" link @click="openEdit(row)">编辑</ElButton>
          <ElButton type="danger" link @click="onDelete(row)">删除</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>

    <ElDialog v-model="dialogOpen" :title="editId === null ? '新增用户' : '编辑用户'" width="440px" destroy-on-close>
      <ElForm label-width="90px" @submit.prevent="save">
        <ElFormItem label="用户名">
          <ElInput v-model="form.username" maxlength="150" autocomplete="off" />
        </ElFormItem>
        <ElFormItem label="权限等级">
          <ElSelect v-model="form.role" style="width: 100%">
            <ElOption v-for="r in roles" :key="r.value" :label="r.label" :value="r.value" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="启用账号">
          <ElSwitch v-model="form.is_active" />
        </ElFormItem>
        <ElFormItem label="密码">
          <ElInput
            v-model="form.password"
            type="password"
            show-password
            autocomplete="new-password"
            :placeholder="editId === null ? '请设置登录密码' : '留空表示不修改'"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="dialogOpen = false">取消</ElButton>
        <ElButton type="primary" :loading="saving" @click="save">保存</ElButton>
      </template>
    </ElDialog>
  </ContentWrap>
</template>
