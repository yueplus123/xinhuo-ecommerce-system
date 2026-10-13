<script setup lang="ts">
// 商品管理 · 平台列表：搜索 / 拖动排序 / 新增编辑（含标签）/ 删除 / 进入工作台
import { onMounted, reactive, ref } from 'vue'
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
  ElTag
} from 'element-plus'
import { VueDraggable } from 'vue-draggable-plus'
import { useRouter } from 'vue-router'
import ContentWrap from '@/components/ContentWrap.vue'
import { formatRequestError } from '@/utils/format'
import {
  STATUS_OPTIONS,
  createPlatform,
  deletePlatform,
  listPlatforms,
  reorderPlatforms,
  updatePlatform,
  type PlatformRow
} from '@/api/modules/catalog'
import { listPool } from '@/api/modules/pools'

defineOptions({ name: 'ManagePlatforms' })

const router = useRouter()
const rows = ref<PlatformRow[]>([])
const loading = ref(false)
const q = ref('')
const tagOptions = ref<Array<{ id: number; name: string }>>([])

const statusMeta = (s: string) => STATUS_OPTIONS.find((o) => o.value === s)

async function load() {
  loading.value = true
  try {
    rows.value = await listPlatforms(q.value.trim())
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '加载失败'))
  } finally {
    loading.value = false
  }
}
onMounted(async () => {
  void load()
  try {
    tagOptions.value = (await listPool('platform-tag-pool')).results as any
  } catch {
    tagOptions.value = []
  }
})

// 搜索时不允许拖动排序：排序接口要求提交全部平台
const sortable = () => !q.value.trim()
async function onSortEnd() {
  try {
    await reorderPlatforms(rows.value.map((r) => r.id))
    ElMessage.success('排序已保存')
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '排序保存失败'))
    await load()
  }
}

// ---- 新增 / 编辑 ----
const visible = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({ name: '', status: 'on_sale', url: '', note: '', platform_tag_ids: [] as number[] })

function open(row?: PlatformRow) {
  editingId.value = row ? row.id : null
  form.name = row?.name ?? ''
  form.status = row?.status ?? 'on_sale'
  form.url = row?.url ?? ''
  form.note = row?.note ?? ''
  form.platform_tag_ids = row ? row.platform_tags.map((t) => t.id) : []
  visible.value = true
}

async function submit() {
  if (!form.name.trim()) {
    ElMessage.warning('请填写平台名称')
    return
  }
  saving.value = true
  try {
    const body = { ...form, name: form.name.trim() }
    if (editingId.value) await updatePlatform(editingId.value, body)
    else await createPlatform(body)
    ElMessage.success(editingId.value ? '已保存' : '已添加')
    visible.value = false
    await load()
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '保存失败'))
  } finally {
    saving.value = false
  }
}

async function remove(row: PlatformRow) {
  try {
    await ElMessageBox.confirm(
      `删除平台「${row.name}」会同时删除其下 ${row.business_count} 个业务、${row.sku_count} 个 SKU，且无法恢复。确定删除吗？`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  try {
    await deletePlatform(row.id)
    ElMessage.success('已删除')
    await load()
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '删除失败'))
  }
}

const goWorkbench = (row: PlatformRow) => router.push(`/platforms/${row.id}`)
</script>

<template>
  <ContentWrap title="平台管理">
    <div class="toolbar">
      <ElButton type="primary" @click="open()">新增平台</ElButton>
      <ElInput
        v-model="q"
        clearable
        placeholder="搜索平台名 / 网址 / 备注 / 标签"
        style="width: 280px"
        @keyup.enter="load"
        @clear="load"
      />
      <ElButton @click="load">搜索</ElButton>
      <span class="hint">{{ sortable() ? '拖动左侧手柄调整平台顺序' : '搜索结果中不能拖动排序，清空搜索后可排序' }}</span>
    </div>

    <div v-loading="loading" class="wrap">
      <table class="tbl">
        <thead>
          <tr>
            <th style="width: 48px">拖动</th>
            <th>平台</th>
            <th style="width: 90px">状态</th>
            <th>标签</th>
            <th style="width: 110px">业务 / SKU</th>
            <th>网址</th>
            <th style="width: 200px">操作</th>
          </tr>
        </thead>
        <VueDraggable v-model="rows" tag="tbody" handle=".drag" :animation="150" :disabled="!sortable()" @end="onSortEnd">
          <tr v-for="row in rows" :key="row.id">
            <td class="drag" :class="{ off: !sortable() }">⠿</td>
            <td>
              <a class="link" @click="goWorkbench(row)">{{ row.name }}</a>
              <div v-if="row.note" class="sub">{{ row.note }}</div>
            </td>
            <td>
              <ElTag :type="statusMeta(row.status)?.tag" size="small">{{ statusMeta(row.status)?.label || row.status }}</ElTag>
            </td>
            <td>
              <ElTag v-for="t in row.platform_tags" :key="t.id" size="small" class="tag">{{ t.name }}</ElTag>
              <span v-if="!row.platform_tags.length">—</span>
            </td>
            <td>{{ row.business_count }} / {{ row.sku_count }}</td>
            <td class="url">{{ row.url || '—' }}</td>
            <td>
              <ElButton link type="primary" @click="goWorkbench(row)">工作台</ElButton>
              <ElButton link type="primary" @click="open(row)">编辑</ElButton>
              <ElButton link type="danger" @click="remove(row)">删除</ElButton>
            </td>
          </tr>
        </VueDraggable>
        <tbody v-if="!rows.length && !loading">
          <tr>
            <td colspan="7" class="empty">暂无平台</td>
          </tr>
        </tbody>
      </table>
    </div>

    <ElDialog v-model="visible" :title="editingId ? '编辑平台' : '新增平台'" width="520px" destroy-on-close>
      <ElForm label-width="84px" @submit.prevent="submit">
        <ElFormItem label="名称" required><ElInput v-model="form.name" maxlength="100" /></ElFormItem>
        <ElFormItem label="状态">
          <ElSelect v-model="form.status" style="width: 100%">
            <ElOption v-for="o in STATUS_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="网址"><ElInput v-model="form.url" placeholder="选填，可省略 https://" /></ElFormItem>
        <ElFormItem label="标签">
          <ElSelect v-model="form.platform_tag_ids" multiple filterable placeholder="从标签池选择" style="width: 100%">
            <ElOption v-for="t in tagOptions" :key="t.id" :label="t.name" :value="t.id" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="备注"><ElInput v-model="form.note" type="textarea" :rows="3" /></ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="visible = false">取消</ElButton>
        <ElButton type="primary" :loading="saving" @click="submit">保存</ElButton>
      </template>
    </ElDialog>
  </ContentWrap>
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
.tbl :deep(.drag) {
  cursor: grab;
  color: var(--el-text-color-secondary);
  user-select: none;
  text-align: center;
  font-size: 18px;
}
.tbl :deep(.drag.off) {
  cursor: not-allowed;
  opacity: 0.35;
}
.tbl :deep(.empty) {
  text-align: center;
  color: var(--el-text-color-secondary);
  padding: 24px 0;
}
.link {
  color: var(--el-color-primary);
  cursor: pointer;
  font-weight: 600;
}
.sub {
  margin-top: 2px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.url {
  word-break: break-all;
}
.tag {
  margin: 0 4px 4px 0;
}
</style>
