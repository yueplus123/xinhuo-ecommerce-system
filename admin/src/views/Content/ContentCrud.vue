<script setup lang="ts">
// 通用「可排序内容列表」管理组件：表格 + 拖动排序 + 新增/编辑弹窗 + 删除
// 与 PoolCrud 同构，区别是对接 /manage/content/*，并支持「启用」开关列
import { computed, onMounted, reactive, ref } from 'vue'
import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElSwitch,
  ElTag
} from 'element-plus'
import { VueDraggable } from 'vue-draggable-plus'
import { formatRequestError } from '@/utils/format'
import {
  createContent,
  deleteContent,
  listContent,
  reorderContent,
  updateContent,
  type ContentKey,
  type ContentRow
} from '@/api/modules/content'

export interface ContentField {
  prop: string
  label: string
  type?: 'text' | 'textarea' | 'switch'
  required?: boolean
  placeholder?: string
  width?: number
  /** 密码等敏感列：表格里打码，仅编辑弹窗可见明文 */
  masked?: boolean
}

const props = defineProps<{
  contentKey: ContentKey
  noun: string // 「教程」「分享页」…用于弹窗标题与提示
  fields: ContentField[]
  hint?: string
}>()

const loading = ref(false)
const rows = ref<ContentRow[]>([])

async function load() {
  loading.value = true
  try {
    rows.value = await listContent(props.contentKey)
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '加载失败'))
  } finally {
    loading.value = false
  }
}
onMounted(load)

// ---- 新增 / 编辑 ----
const visible = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
const form = reactive<Record<string, any>>({})

const blank = (f: ContentField) => (f.type === 'switch' ? true : '')

function open(row?: ContentRow) {
  editingId.value = row ? row.id : null
  for (const f of props.fields) form[f.prop] = row ? row[f.prop] : blank(f)
  visible.value = true
}

async function submit() {
  for (const f of props.fields) {
    const v = form[f.prop]
    if (f.required && (v === '' || v === undefined || v === null)) {
      ElMessage.warning(`请填写${f.label}`)
      return
    }
  }
  const payload: Record<string, any> = {}
  for (const f of props.fields) payload[f.prop] = form[f.prop]
  saving.value = true
  try {
    if (editingId.value) await updateContent(props.contentKey, editingId.value, payload)
    else await createContent(props.contentKey, payload)
    ElMessage.success(editingId.value ? '已保存' : '已添加')
    visible.value = false
    await load()
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '保存失败'))
  } finally {
    saving.value = false
  }
}

async function remove(row: ContentRow) {
  const label = String(row[props.fields[0].prop] ?? '').slice(0, 40)
  try {
    await ElMessageBox.confirm(`确定删除「${label}」吗？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }
  try {
    await deleteContent(props.contentKey, row.id)
    ElMessage.success('已删除')
    await load()
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '删除失败'))
  }
}

// ---- 拖动排序 ----
async function onSortEnd() {
  try {
    await reorderContent(
      props.contentKey,
      rows.value.map((r) => r.id)
    )
    ElMessage.success('排序已保存')
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '排序保存失败'))
    await load()
  }
}

const tableFields = computed(() => props.fields)
function cell(row: ContentRow, f: ContentField) {
  const v = row[f.prop]
  if (v === null || v === undefined || v === '') return '—'
  return f.masked ? '••••••' : v
}

defineExpose({ reload: load })
</script>

<template>
  <div>
    <div class="toolbar">
      <ElButton type="primary" @click="open()">新增{{ noun }}</ElButton>
      <span v-if="hint" class="hint">{{ hint }}</span>
    </div>

    <div v-loading="loading" class="wrap">
      <table class="tbl">
        <thead>
          <tr>
            <th style="width: 48px">拖动</th>
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
          handle=".drag"
          :animation="150"
          @end="onSortEnd"
        >
          <tr v-for="row in rows" :key="row.id">
            <td class="drag" title="按住拖动排序">⠿</td>
            <td v-for="f in tableFields" :key="f.prop" class="cell">
              <ElTag
                v-if="f.type === 'switch'"
                :type="row[f.prop] ? 'success' : 'info'"
                size="small"
              >
                {{ row[f.prop] ? '启用' : '停用' }}
              </ElTag>
              <template v-else>{{ cell(row, f) }}</template>
            </td>
            <td>
              <ElButton link type="primary" @click="open(row)">编辑</ElButton>
              <ElButton link type="danger" @click="remove(row)">删除</ElButton>
            </td>
          </tr>
        </VueDraggable>
        <tbody v-if="!rows.length && !loading">
          <tr>
            <td :colspan="tableFields.length + 2" class="empty">暂无数据</td>
          </tr>
        </tbody>
      </table>
    </div>

    <ElDialog
      v-model="visible"
      :title="(editingId ? '编辑' : '新增') + noun"
      width="520px"
      destroy-on-close
    >
      <ElForm label-width="96px" @submit.prevent="submit">
        <ElFormItem v-for="f in fields" :key="f.prop" :label="f.label" :required="f.required">
          <ElSwitch v-if="f.type === 'switch'" v-model="form[f.prop]" />
          <ElInput
            v-else
            v-model="form[f.prop]"
            :type="f.type === 'textarea' ? 'textarea' : 'text'"
            :rows="4"
            :placeholder="f.placeholder"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="visible = false">取消</ElButton>
        <ElButton type="primary" :loading="saving" @click="submit">保存</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin-bottom: 14px;
}
.hint {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.wrap {
  overflow-x: auto;
}
.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
.tbl :deep(th),
.tbl :deep(td) {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid var(--el-border-color-lighter);
  vertical-align: top;
}
.tbl :deep(th) {
  color: var(--el-text-color-secondary);
  font-weight: 600;
  background: var(--el-fill-color-light);
  white-space: nowrap;
}
.tbl :deep(.cell) {
  word-break: break-all;
  white-space: pre-wrap;
}
.tbl :deep(.drag) {
  cursor: grab;
  color: var(--el-text-color-secondary);
  user-select: none;
  text-align: center;
  font-size: 18px;
}
.tbl :deep(.empty) {
  text-align: center;
  color: var(--el-text-color-secondary);
  padding: 24px 0;
}
</style>
