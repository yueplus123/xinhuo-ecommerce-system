<script setup lang="ts">
// 大厅板块管理：标题 + 正文 + 排序 + 置顶 + 多张配图（上传 / 删除已有）
import { onMounted, reactive, ref } from 'vue'
import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElImage,
  ElInput,
  ElInputNumber,
  ElMessage,
  ElMessageBox,
  ElSwitch,
  ElTable,
  ElTableColumn,
  ElTag,
  ElUpload,
  type UploadFile
} from 'element-plus'
import ContentWrap from '@/components/ContentWrap.vue'
import api from '@/api/client'
import { formatRequestError } from '@/utils/format'

defineOptions({ name: 'ManageHallBlocks' })

interface HallImage {
  id: number
  url: string
  sort_order: number
}
interface HallRow {
  id: number
  title: string
  body: string
  sort_order: number
  is_pinned: boolean
  images: HallImage[]
  image_count: number
  body_preview: string
}

const BASE = '/manage/content/hall-blocks/'
const MAX_IMAGE_MB = 5

const rows = ref<HallRow[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await api.get<HallRow[] | { results: HallRow[] }>(BASE)
    rows.value = Array.isArray(data) ? data : data.results
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
const form = reactive({ title: '', body: '', sort_order: 0, is_pinned: false })
const existing = ref<HallImage[]>([]) // 已有配图
const removeIds = ref<number[]>([]) // 待删除的已有配图
const newFiles = ref<UploadFile[]>([]) // 待上传的新配图

function open(row?: HallRow) {
  editingId.value = row ? row.id : null
  form.title = row?.title ?? ''
  form.body = row?.body ?? ''
  form.sort_order = row?.sort_order ?? 0
  form.is_pinned = row?.is_pinned ?? false
  existing.value = row ? [...row.images] : []
  removeIds.value = []
  newFiles.value = []
  visible.value = true
}

function beforeUpload(file: File) {
  if (!file.type.startsWith('image/')) {
    ElMessage.warning('仅支持图片文件')
    return false
  }
  if (file.size > MAX_IMAGE_MB * 1024 * 1024) {
    ElMessage.warning(`单张图片不能超过 ${MAX_IMAGE_MB}MB`)
    return false
  }
  return true
}

function toggleRemove(img: HallImage) {
  const i = removeIds.value.indexOf(img.id)
  if (i >= 0) removeIds.value.splice(i, 1)
  else removeIds.value.push(img.id)
}

async function submit() {
  if (!form.title.trim()) {
    ElMessage.warning('请填写标题')
    return
  }
  const fd = new FormData()
  fd.append('title', form.title.trim())
  fd.append('body', form.body)
  fd.append('sort_order', String(form.sort_order ?? 0))
  fd.append('is_pinned', form.is_pinned ? 'true' : 'false')
  for (const id of removeIds.value) fd.append('delete_member_image_ids', String(id))
  for (const f of newFiles.value) if (f.raw) fd.append('member_images', f.raw)
  saving.value = true
  try {
    if (editingId.value) await api.put(`${BASE}${editingId.value}/`, fd)
    else await api.post(BASE, fd)
    ElMessage.success(editingId.value ? '已保存' : '已添加')
    visible.value = false
    await load()
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '保存失败'))
  } finally {
    saving.value = false
  }
}

async function remove(row: HallRow) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.title}」吗？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }
  try {
    await api.delete(`${BASE}${row.id}/`)
    ElMessage.success('已删除')
    await load()
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '删除失败'))
  }
}

async function togglePin(row: HallRow) {
  try {
    const fd = new FormData()
    fd.append('title', row.title)
    fd.append('body', row.body)
    fd.append('sort_order', String(row.sort_order))
    fd.append('is_pinned', row.is_pinned ? 'false' : 'true')
    await api.put(`${BASE}${row.id}/`, fd)
    await load()
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '操作失败'))
  }
}
</script>

<template>
  <ContentWrap title="大厅板块管理">
    <div class="toolbar">
      <ElButton type="primary" @click="open()">新增板块</ElButton>
      <span class="hint">置顶的板块在职员端大厅最前展示；同组内按「排序」数字从小到大</span>
    </div>

    <ElTable v-loading="loading" :data="rows" border stripe empty-text="暂无板块">
      <ElTableColumn prop="sort_order" label="排序" width="80" />
      <ElTableColumn label="置顶" width="80">
        <template #default="{ row }">
          <ElTag v-if="row.is_pinned" type="warning" size="small">置顶</ElTag>
          <span v-else>—</span>
        </template>
      </ElTableColumn>
      <ElTableColumn prop="title" label="标题" min-width="180" show-overflow-tooltip />
      <ElTableColumn prop="body_preview" label="正文预览" min-width="260" show-overflow-tooltip />
      <ElTableColumn label="配图" width="90">
        <template #default="{ row }">{{ row.image_count }} 张</template>
      </ElTableColumn>
      <ElTableColumn label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <ElButton link type="primary" @click="open(row)">编辑</ElButton>
          <ElButton link type="warning" @click="togglePin(row)">
            {{ row.is_pinned ? '取消置顶' : '置顶' }}
          </ElButton>
          <ElButton link type="danger" @click="remove(row)">删除</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>

    <ElDialog
      v-model="visible"
      :title="editingId ? '编辑板块' : '新增板块'"
      width="640px"
      destroy-on-close
    >
      <ElForm label-width="84px" @submit.prevent="submit">
        <ElFormItem label="标题" required><ElInput v-model="form.title" maxlength="200" /></ElFormItem>
        <ElFormItem label="正文">
          <ElInput v-model="form.body" type="textarea" :rows="6" />
        </ElFormItem>
        <ElFormItem label="排序">
          <ElInputNumber v-model="form.sort_order" :min="0" controls-position="right" />
        </ElFormItem>
        <ElFormItem label="置顶"><ElSwitch v-model="form.is_pinned" /></ElFormItem>

        <ElFormItem v-if="existing.length" label="已有配图">
          <div class="imgs">
            <div
              v-for="img in existing"
              :key="img.id"
              class="img-item"
              :class="{ removed: removeIds.includes(img.id) }"
            >
              <ElImage :src="img.url" fit="cover" class="thumb" :preview-src-list="[img.url]" preview-teleported />
              <ElButton size="small" link :type="removeIds.includes(img.id) ? 'primary' : 'danger'" @click="toggleRemove(img)">
                {{ removeIds.includes(img.id) ? '撤销删除' : '删除' }}
              </ElButton>
            </div>
          </div>
        </ElFormItem>

        <ElFormItem label="新增配图">
          <ElUpload
            v-model:file-list="newFiles"
            list-type="picture-card"
            multiple
            accept="image/*"
            :auto-upload="false"
            :before-upload="beforeUpload"
          >
            +
          </ElUpload>
        </ElFormItem>
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
.imgs {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.img-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.img-item.removed {
  opacity: 0.4;
}
.thumb {
  width: 96px;
  height: 96px;
  border-radius: 4px;
}
</style>
