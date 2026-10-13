<script setup lang="ts">
// 商品管理 · 平台工作台：编辑平台信息，管理其下 业务 → SKU
import { computed, onMounted, reactive, ref } from 'vue'
import {
  ElButton,
  ElCard,
  ElCollapse,
  ElCollapseItem,
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
import { useRoute, useRouter } from 'vue-router'
import ContentWrap from '@/components/ContentWrap.vue'
import { formatRequestError } from '@/utils/format'
import {
  STATUS_OPTIONS,
  createBusiness,
  createSku,
  deleteBusiness,
  deleteSku,
  duplicateSku,
  getPlatform,
  updateBusiness,
  updateSku,
  type BusinessNode,
  type PlatformRow,
  type SkuNode
} from '@/api/modules/catalog'

defineOptions({ name: 'ManagePlatformWorkbench' })

const route = useRoute()
const router = useRouter()
const platformId = computed(() => Number(route.params.id))

const platform = ref<PlatformRow | null>(null)
const loading = ref(false)
const openNames = ref<number[]>([])
const meta = (s: string) => STATUS_OPTIONS.find((o) => o.value === s)

async function load() {
  loading.value = true
  try {
    platform.value = await getPlatform(platformId.value)
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '加载失败'))
    platform.value = null
  } finally {
    loading.value = false
  }
}
onMounted(load)

// ---- 业务 / SKU 共用的「名称 + 状态」弹窗 ----
type Kind = 'business' | 'sku'
const dlg = reactive({
  visible: false,
  kind: 'business' as Kind,
  editingId: null as number | null,
  parentId: 0, // 新增 SKU 时是业务 id
  name: '',
  status: 'on_sale',
  saving: false
})
const kindLabel = computed(() => (dlg.kind === 'business' ? '业务' : 'SKU'))

function openDlg(kind: Kind, node?: BusinessNode | SkuNode, parentId = 0) {
  dlg.kind = kind
  dlg.editingId = node ? node.id : null
  dlg.parentId = parentId
  dlg.name = node?.name ?? ''
  dlg.status = node?.status ?? 'on_sale'
  dlg.visible = true
}

async function submitDlg() {
  const name = dlg.name.trim()
  if (!name) {
    ElMessage.warning(`请填写${kindLabel.value}名称`)
    return
  }
  dlg.saving = true
  try {
    if (dlg.kind === 'business') {
      const body = { platform: platformId.value, name, status: dlg.status }
      if (dlg.editingId) await updateBusiness(dlg.editingId, body)
      else await createBusiness(body)
    } else {
      const body = { business: dlg.parentId, name, status: dlg.status }
      if (dlg.editingId) await updateSku(dlg.editingId, body)
      else await createSku(body)
      if (!dlg.editingId && !openNames.value.includes(dlg.parentId)) openNames.value.push(dlg.parentId)
    }
    ElMessage.success(dlg.editingId ? '已保存' : '已添加')
    dlg.visible = false
    await load()
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '保存失败'))
  } finally {
    dlg.saving = false
  }
}

async function confirmDelete(text: string) {
  try {
    await ElMessageBox.confirm(text, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    return true
  } catch {
    return false
  }
}

async function removeBusiness(b: BusinessNode) {
  if (!(await confirmDelete(`删除业务「${b.name}」会同时删除其下 ${b.sku_count} 个 SKU，且无法恢复。确定删除吗？`))) return
  try {
    await deleteBusiness(b.id)
    ElMessage.success('已删除')
    await load()
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '删除失败'))
  }
}

async function removeSku(s: SkuNode) {
  if (!(await confirmDelete(`确定删除 SKU「${s.name}」吗？其快捷话术、价格档等一并删除。`))) return
  try {
    await deleteSku(s.id)
    ElMessage.success('已删除')
    await load()
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '删除失败'))
  }
}

async function copySku(s: SkuNode) {
  try {
    await duplicateSku(s.id)
    ElMessage.success('已复制（含快捷话术与渠道标签）')
    await load()
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '复制失败'))
  }
}
</script>

<template>
  <ContentWrap :title="platform ? `平台工作台 · ${platform.name}` : '平台工作台'">
    <div class="toolbar">
      <ElButton @click="router.push('/platforms')">← 返回平台列表</ElButton>
      <ElButton v-if="platform" type="primary" @click="openDlg('business')">新增业务</ElButton>
    </div>

    <div v-loading="loading">
      <ElCard v-if="platform" shadow="never" class="mb-12px">
        <div class="info">
          <ElTag :type="meta(platform.status)?.tag">{{ platform.status_label }}</ElTag>
          <span>{{ platform.business_count }} 个业务 · {{ platform.sku_count }} 个 SKU</span>
          <span v-if="platform.url" class="muted">{{ platform.url }}</span>
          <ElTag v-for="t in platform.platform_tags" :key="t.id" size="small">{{ t.name }}</ElTag>
        </div>
        <div v-if="platform.note" class="muted mt-8px">{{ platform.note }}</div>
      </ElCard>

      <ElCollapse v-if="platform?.businesses?.length" v-model="openNames">
        <ElCollapseItem v-for="b in platform.businesses" :key="b.id" :name="b.id">
          <template #title>
            <span class="biz-title">{{ b.name }}</span>
            <ElTag :type="meta(b.status)?.tag" size="small" class="ml-8px">{{ b.status_label }}</ElTag>
            <span class="muted ml-8px">{{ b.sku_count }} 个 SKU</span>
          </template>
          <div class="biz-actions">
            <ElButton size="small" type="primary" @click="router.push(`/skus/new?business=${b.id}`)">新增 SKU</ElButton>
            <ElButton size="small" @click="openDlg('business', b)">编辑业务</ElButton>
            <ElButton size="small" type="danger" plain @click="removeBusiness(b)">删除业务</ElButton>
          </div>
          <table v-if="b.skus.length" class="tbl">
            <thead>
              <tr>
                <th>SKU</th>
                <th style="width: 90px">状态</th>
                <th style="width: 110px">快捷话术</th>
                <th style="width: 220px">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in b.skus" :key="s.id">
                <td>{{ s.name }}</td>
                <td><ElTag :type="meta(s.status)?.tag" size="small">{{ s.status_label }}</ElTag></td>
                <td>{{ s.quick_phrase_count }} 条</td>
                <td>
                  <ElButton link type="primary" @click="router.push(`/skus/${s.id}`)">编辑</ElButton>
                  <ElButton link type="primary" @click="copySku(s)">复制</ElButton>
                  <ElButton link type="danger" @click="removeSku(s)">删除</ElButton>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="muted">暂无 SKU</div>
        </ElCollapseItem>
      </ElCollapse>
      <div v-else-if="platform && !loading" class="muted empty">该平台下暂无业务，点右上「新增业务」开始。</div>
    </div>

    <ElDialog
      v-model="dlg.visible"
      :title="(dlg.editingId ? '编辑' : '新增') + kindLabel"
      width="440px"
      destroy-on-close
    >
      <ElForm label-width="96px" @submit.prevent="submitDlg">
        <ElFormItem :label="kindLabel + '名称'" required><ElInput v-model="dlg.name" maxlength="200" /></ElFormItem>
        <ElFormItem label="状态">
          <ElSelect v-model="dlg.status" style="width: 100%">
            <ElOption v-for="o in STATUS_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
          </ElSelect>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="dlg.visible = false">取消</ElButton>
        <ElButton type="primary" :loading="dlg.saving" @click="submitDlg">保存</ElButton>
      </template>
    </ElDialog>
  </ContentWrap>
</template>

<style scoped>
.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 14px;
}
.mb-12px {
  margin-bottom: 12px;
}
.mt-8px {
  margin-top: 8px;
}
.ml-8px {
  margin-left: 8px;
}
.info {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}
.muted {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.empty {
  padding: 24px 0;
  text-align: center;
}
.biz-title {
  font-weight: 600;
}
.biz-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}
.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
.tbl th,
.tbl td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.tbl th {
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-light);
  font-weight: 600;
}
</style>
