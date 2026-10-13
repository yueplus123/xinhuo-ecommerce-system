<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElSelect
} from 'element-plus'
import { VueDraggable } from 'vue-draggable-plus'
import ContentWrap from '@/components/ContentWrap.vue'
import { formatRequestError } from '@/utils/format'
import {
  createPoolItem,
  deletePoolItem,
  listPool,
  quickAddPoolTag,
  reorderPool,
  updatePoolItem,
  type PoolKey,
  type PoolRow
} from '@/api/modules/pools'

export interface PoolField {
  prop: string
  label: string
  type?: 'text' | 'textarea' | 'number' | 'select'
  required?: boolean
  placeholder?: string
  /** 表格列宽，不填则自适应 */
  width?: number
  /** 只在表格显示，不出现在表单中 */
  tableOnly?: boolean
  /** 只在表单出现，不在表格显示 */
  formOnly?: boolean
  /** select 类型的选项 */
  options?: Array<{ id: number; label: string }>
  /** 表格中显示用的字段（例如 select 显示 sku_name） */
  displayProp?: string
  precision?: number
  min?: number
  max?: number
}

const props = withDefaults(
  defineProps<{
    poolKey: PoolKey
    title: string
    fields: PoolField[]
    hint?: string
    /** 标签池：顶部的「快速添加」输入框 */
    quickAdd?: boolean
    quickAddPlaceholder?: string
    /** 顶部筛选（值作为查询参数传给后端） */
    filterProp?: string
    filterLabel?: string
    filterOptions?: Array<{ id: number; label: string }>
  }>(),
  { quickAdd: false }
)

const loading = ref(false)
const rows = ref<PoolRow[]>([])
const reorderable = ref(false)
const filterValue = ref<number | undefined>(undefined)

const tableFields = computed(() => props.fields.filter((f) => !f.formOnly))
const formFields = computed(() => props.fields.filter((f) => !f.tableOnly))

async function load() {
  loading.value = true
  try {
    const params: Record<string, any> = {}
    if (props.filterProp && filterValue.value) params[props.filterProp] = filterValue.value
    const data = await listPool(props.poolKey, params)
    rows.value = data.results
    reorderable.value = data.reorderable
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '加载失败'))
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(filterValue, load)

// ---- 新增/编辑 ----
const dialogVisible = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
const form = reactive<Record<string, any>>({})

function blankValue(f: PoolField) {
  return f.type === 'number' ? 0 : f.type === 'select' ? undefined : ''
}

function openDialog(row?: PoolRow) {
  editingId.value = row ? row.id : null
  for (const f of formFields.value) {
    form[f.prop] = row ? row[f.prop] : blankValue(f)
  }
  if (!row && props.filterProp && filterValue.value && props.filterProp in form) {
    form[props.filterProp] = filterValue.value
  }
  dialogVisible.value = true
}

async function submit() {
  for (const f of formFields.value) {
    const v = form[f.prop]
    if (f.required && (v === '' || v === undefined || v === null)) {
      ElMessage.warning(`请填写${f.label}`)
      return
    }
  }
  saving.value = true
  try {
    const payload: Record<string, any> = {}
    for (const f of formFields.value) payload[f.prop] = form[f.prop]
    if (editingId.value) {
      await updatePoolItem(props.poolKey, editingId.value, payload)
      ElMessage.success('已保存')
    } else {
      await createPoolItem(props.poolKey, payload)
      ElMessage.success('已添加')
    }
    dialogVisible.value = false
    await load()
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '保存失败'))
  } finally {
    saving.value = false
  }
}

async function remove(row: PoolRow) {
  const first = props.fields[0]
  const label = row[first.displayProp || first.prop]
  try {
    await ElMessageBox.confirm(`确定删除「${String(label ?? '').slice(0, 40)}」吗？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }
  try {
    await deletePoolItem(props.poolKey, row.id)
    ElMessage.success('已删除')
    await load()
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '删除失败'))
  }
}

// ---- 拖动排序 ----
async function onSortEnd() {
  try {
    await reorderPool(
      props.poolKey,
      rows.value.map((r) => r.id)
    )
    ElMessage.success('排序已保存')
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '排序保存失败'))
    await load()
  }
}

// ---- 快速添加（标签池） ----
const quickName = ref('')
const quickBusy = ref(false)

async function doQuickAdd() {
  const name = quickName.value.trim()
  if (!name) {
    ElMessage.warning('请输入名称')
    return
  }
  quickBusy.value = true
  try {
    const res = await quickAddPoolTag(props.poolKey, name)
    ElMessage.success(res.message || '已添加')
    quickName.value = ''
    await load()
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '添加失败'))
  } finally {
    quickBusy.value = false
  }
}

function cellText(row: PoolRow, f: PoolField) {
  const v = row[f.displayProp || f.prop]
  return v === null || v === undefined || v === '' ? '—' : v
}

defineExpose({ reload: load })
</script>

<template>
  <ContentWrap :title="title">
    <div class="pool-toolbar">
      <ElSelect
        v-if="filterProp && filterOptions"
        v-model="filterValue"
        :placeholder="filterLabel || '筛选'"
        clearable
        filterable
        style="width: 320px"
      >
        <ElOption v-for="o in filterOptions" :key="o.id" :label="o.label" :value="o.id" />
      </ElSelect>
      <template v-if="quickAdd">
        <ElInput
          v-model="quickName"
          :placeholder="quickAddPlaceholder || '输入名称后回车快速添加'"
          style="width: 260px"
          maxlength="100"
          @keyup.enter="doQuickAdd"
        />
        <ElButton :loading="quickBusy" @click="doQuickAdd">快速添加</ElButton>
      </template>
      <ElButton type="primary" @click="openDialog()">新增</ElButton>
      <span v-if="hint" class="pool-hint">{{ hint }}</span>
    </div>

    <div v-loading="loading" class="pool-table-wrap">
      <table class="pool-table">
        <thead>
          <tr>
            <th v-if="reorderable" style="width: 48px">拖动</th>
            <th
              v-for="f in tableFields"
              :key="f.prop"
              :style="f.width ? { width: f.width + 'px' } : {}"
            >
              {{ f.label }}
            </th>
            <th style="width: 140px">操作</th>
          </tr>
        </thead>
        <VueDraggable
          v-model="rows"
          tag="tbody"
          handle=".drag-handle"
          :animation="150"
          :disabled="!reorderable"
          @end="onSortEnd"
        >
          <tr v-for="row in rows" :key="row.id">
            <td v-if="reorderable" class="drag-handle" title="按住拖动排序">⠿</td>
            <td v-for="f in tableFields" :key="f.prop" class="pool-cell">{{ cellText(row, f) }}</td>
            <td>
              <ElButton link type="primary" @click="openDialog(row)">编辑</ElButton>
              <ElButton link type="danger" @click="remove(row)">删除</ElButton>
            </td>
          </tr>
        </VueDraggable>
        <tbody v-if="!rows.length && !loading">
          <tr>
            <td :colspan="tableFields.length + (reorderable ? 2 : 1)" class="pool-empty">
              暂无数据
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <ElDialog
      v-model="dialogVisible"
      :title="(editingId ? '编辑' : '新增') + title"
      width="520px"
      destroy-on-close
    >
      <ElForm label-width="96px" @submit.prevent="submit">
        <ElFormItem v-for="f in formFields" :key="f.prop" :label="f.label" :required="f.required">
          <ElSelect
            v-if="f.type === 'select'"
            v-model="form[f.prop]"
            filterable
            :placeholder="f.placeholder || '请选择'"
            style="width: 100%"
          >
            <ElOption v-for="o in f.options || []" :key="o.id" :label="o.label" :value="o.id" />
          </ElSelect>
          <ElInputNumber
            v-else-if="f.type === 'number'"
            v-model="form[f.prop]"
            :precision="f.precision"
            :min="f.min"
            :max="f.max"
            controls-position="right"
          />
          <ElInput
            v-else
            v-model="form[f.prop]"
            :type="f.type === 'textarea' ? 'textarea' : 'text'"
            :rows="5"
            :placeholder="f.placeholder"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="dialogVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="saving" @click="submit">保存</ElButton>
      </template>
    </ElDialog>
  </ContentWrap>
</template>

<style scoped>
.pool-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin-bottom: 14px;
}

.pool-hint {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.pool-table-wrap {
  overflow-x: auto;
}

.pool-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.pool-table :deep(th),
.pool-table :deep(td) {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid var(--el-border-color-lighter);
  vertical-align: top;
}

.pool-table :deep(th) {
  color: var(--el-text-color-secondary);
  font-weight: 600;
  background: var(--el-fill-color-light);
  white-space: nowrap;
}

.pool-table :deep(.pool-cell) {
  word-break: break-all;
  white-space: pre-wrap;
}

.pool-table :deep(.drag-handle) {
  cursor: grab;
  color: var(--el-text-color-secondary);
  user-select: none;
  text-align: center;
  font-size: 18px;
}

.pool-table :deep(.pool-empty) {
  text-align: center;
  color: var(--el-text-color-secondary);
  padding: 24px 0;
}
</style>
