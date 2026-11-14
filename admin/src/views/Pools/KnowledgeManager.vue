<script setup lang="ts">
// 教程+话术管理：按平台分，平台里分「问答 / 教程 / 快捷语」。
// 职员端「教程+话术」页面只能看和复制，新增 / 编辑 / 删除都在这里做。
import { computed, onMounted, reactive, ref } from 'vue'
import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElRadioButton,
  ElRadioGroup,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag
} from 'element-plus'
import { formatRequestError } from '@/utils/format'
import {
  createKnowledge,
  deleteKnowledge,
  listKnowledge,
  updateKnowledge,
  type KnowledgeEntry,
  type KnowledgeKind,
  type KnowledgePlatform
} from '@/api/modules/knowledge'

defineOptions({ name: 'KnowledgeManager' })

const KINDS: Array<{ value: KnowledgeKind; label: string }> = [
  { value: 'faq', label: '问答' },
  { value: 'tutorial', label: '教程' },
  { value: 'phrase', label: '快捷语' }
]
const GENERAL = 0 // 「通用」在下拉框里用 0 表示，提交时转成 null
const ALL = -1

// ---- 平台按首字母 A-Z 排序（汉字按拼音首字母），和职员端一致 ----
const collator = (() => {
  try {
    return new Intl.Collator('zh-Hans-CN-u-co-pinyin', { sensitivity: 'base', numeric: true })
  } catch {
    return null
  }
})()
const PY_BOUND = '阿芭擦搭蛾发噶哈击喀垃妈拿哦啪期然撒塌挖昔压匝'
const PY_LET = 'ABCDEFGHJKLMNOPQRSTWXYZ'
function firstLetter(name: string): string {
  const c = String(name || '').trim().charAt(0)
  if (/[a-z]/i.test(c)) return c.toUpperCase()
  if (collator && /[一-鿿]/.test(c)) {
    let L = '#'
    for (let i = 0; i < PY_BOUND.length; i++) {
      if (collator.compare(c, PY_BOUND.charAt(i)) >= 0) L = PY_LET.charAt(i)
      else break
    }
    return L
  }
  return '#'
}
function byLetter(a: string, b: string): number {
  const la = firstLetter(a)
  const lb = firstLetter(b)
  if (la !== lb) return la === '#' ? 1 : lb === '#' ? -1 : la < lb ? -1 : 1
  return collator ? collator.compare(a, b) : a.localeCompare(b)
}

const loading = ref(false)
const platforms = ref<KnowledgePlatform[]>([])
const entries = ref<KnowledgeEntry[]>([])
const platformFilter = ref<number>(ALL)
const kind = ref<KnowledgeKind>('faq')
const keyword = ref('')

const pmap = computed(() => {
  const m: Record<number, KnowledgePlatform> = {}
  for (const p of platforms.value) m[p.id] = p
  return m
})
function pname(id: number | null) {
  if (id == null) return '通用'
  return pmap.value[id]?.name || '（已删除的平台）'
}
const sortedPlatforms = computed(() => platforms.value.slice().sort((a, b) => byLetter(a.name, b.name)))
function countOf(pid: number | null) {
  return entries.value.filter((e) => e.platform_id === pid).length
}
const kindCount = computed(() => {
  const c: Record<string, number> = { faq: 0, tutorial: 0, phrase: 0 }
  for (const e of entries.value) if (platformOk(e)) c[e.kind]++
  return c
})
function platformOk(e: KnowledgeEntry) {
  if (platformFilter.value === ALL) return true
  if (platformFilter.value === GENERAL) return e.platform_id == null
  return e.platform_id === platformFilter.value
}
const rows = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return entries.value
    .filter((e) => e.kind === kind.value && platformOk(e))
    .filter((e) => !kw || (e.title + ' ' + e.content + ' ' + e.url).toLowerCase().includes(kw))
    .slice()
    .sort((a, b) => {
      if (a.platform_id !== b.platform_id) {
        if (a.platform_id == null) return -1
        if (b.platform_id == null) return 1
        return byLetter(pname(a.platform_id), pname(b.platform_id))
      }
      return a.sort_order - b.sort_order || a.id - b.id
    })
})
const byId = computed(() => {
  const m: Record<number, KnowledgeEntry> = {}
  for (const e of entries.value) m[e.id] = e
  return m
})
function attOf(e: KnowledgeEntry) {
  return (e.tutorials || []).map((id) => byId.value[id]).filter((t) => t && t.kind === 'tutorial')
}
function usedBy(t: KnowledgeEntry) {
  return entries.value.filter((e) => (e.tutorials || []).includes(t.id)).length
}
function fmt(ms: number | null) {
  if (!ms) return ''
  const d = new Date(ms)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

async function load() {
  loading.value = true
  try {
    const d = await listKnowledge()
    platforms.value = d.platforms || []
    entries.value = d.entries || []
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '加载失败'))
  } finally {
    loading.value = false
  }
}
onMounted(load)

// ---- 新增 / 编辑 ----
const dialogOpen = ref(false)
const saving = ref(false)
const editId = ref<number | null>(null)
const form = reactive({
  platform: GENERAL as number,
  kind: 'faq' as KnowledgeKind,
  title: '',
  content: '',
  url: '',
  tutorials: [] as number[]
})
const titleLabel = computed(() => (form.kind === 'faq' ? '客户的问题' : form.kind === 'tutorial' ? '教程名称' : '标题'))
const contentLabel = computed(() =>
  form.kind === 'faq' ? '答案' : form.kind === 'tutorial' ? '说明' : '快捷语内容'
)
const contentHint = computed(() =>
  form.kind === 'tutorial' ? '给同事看：什么时候发这篇（可不填）' : '复制给客户的内容；附带的教程会自动加在后面'
)
const tutorialOptions = computed(() => {
  const pid = form.platform === GENERAL ? null : form.platform
  return entries.value
    .filter((t) => t.kind === 'tutorial' && (t.platform_id === pid || t.platform_id == null || form.tutorials.includes(t.id)))
    .map((t) => ({ id: t.id, label: t.platform_id === pid ? t.title : `${t.title}（${pname(t.platform_id)}）` }))
})

function openDialog(row?: KnowledgeEntry) {
  editId.value = row ? row.id : null
  form.platform = row
    ? row.platform_id ?? GENERAL
    : platformFilter.value === ALL
      ? GENERAL
      : platformFilter.value
  form.kind = row ? row.kind : kind.value
  form.title = row ? row.title : ''
  form.content = row ? row.content : ''
  form.url = row ? row.url : ''
  form.tutorials = row ? (row.tutorials || []).slice() : []
  dialogOpen.value = true
}

async function submit() {
  const payload = {
    platform_id: form.platform === GENERAL ? null : form.platform,
    kind: form.kind,
    title: form.title.trim(),
    content: form.content,
    url: form.kind === 'tutorial' ? form.url.trim() : '',
    tutorials: form.kind === 'tutorial' ? [] : form.tutorials.slice()
  }
  saving.value = true
  try {
    if (editId.value) await updateKnowledge(editId.value, payload)
    else await createKnowledge(payload)
    ElMessage.success('已保存，职员端刷新就能看到')
    dialogOpen.value = false
    kind.value = payload.kind
    await load()
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '保存失败'))
  } finally {
    saving.value = false
  }
}

async function remove(row: KnowledgeEntry) {
  const n = row.kind === 'tutorial' ? usedBy(row) : 0
  const extra = n ? `\n有 ${n} 条问答 / 快捷语附带了这篇教程，删除后会自动去掉。` : ''
  try {
    await ElMessageBox.confirm(`确定删除「${row.title.slice(0, 40)}」吗？${extra}`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }
  try {
    await deleteKnowledge(row.id)
    ElMessage.success('已删除')
    await load()
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '删除失败'))
  }
}
</script>

<template>
  <div class="kb">
    <div class="kb-toolbar">
      <ElSelect v-model="platformFilter" filterable placeholder="平台" style="width: 220px">
        <ElOption :value="ALL" :label="`全部平台（${entries.length}）`" />
        <ElOption :value="GENERAL" :label="`通用（所有平台）（${countOf(null)}）`" />
        <ElOption v-for="p in sortedPlatforms" :key="p.id" :value="p.id" :label="`${p.name}（${countOf(p.id)}）`" />
      </ElSelect>
      <ElRadioGroup v-model="kind">
        <ElRadioButton v-for="k in KINDS" :key="k.value" :value="k.value">
          {{ k.label }} {{ kindCount[k.value] }}
        </ElRadioButton>
      </ElRadioGroup>
      <ElInput v-model="keyword" placeholder="搜标题、内容、链接" clearable style="width: 220px" />
      <ElButton type="primary" @click="openDialog()">新增</ElButton>
      <span class="kb-hint">职员端「教程+话术」只能看和复制，内容在这里维护</span>
    </div>

    <ElTable v-loading="loading" :data="rows" border stripe empty-text="暂无数据">
      <ElTableColumn label="平台" width="130">
        <template #default="{ row }"><span class="kb-plat">{{ pname(row.platform_id) }}</span></template>
      </ElTableColumn>
      <ElTableColumn :label="kind === 'faq' ? '问题' : kind === 'tutorial' ? '教程名称' : '标题'" min-width="200">
        <template #default="{ row }"><b>{{ row.title }}</b></template>
      </ElTableColumn>
      <ElTableColumn v-if="kind === 'tutorial'" label="链接" min-width="220">
        <template #default="{ row }">
          <a :href="row.url" target="_blank" rel="noopener" class="kb-url">{{ row.url }}</a>
        </template>
      </ElTableColumn>
      <ElTableColumn :label="kind === 'faq' ? '答案' : kind === 'tutorial' ? '说明' : '内容'" min-width="280">
        <template #default="{ row }"><div class="kb-text">{{ row.content || '—' }}</div></template>
      </ElTableColumn>
      <ElTableColumn v-if="kind !== 'tutorial'" label="附带教程" min-width="200">
        <template #default="{ row }">
          <ElTag v-for="t in attOf(row)" :key="t.id" size="small" class="kb-tag">{{ t.title }}</ElTag>
          <span v-if="!attOf(row).length" class="kb-muted">—</span>
        </template>
      </ElTableColumn>
      <ElTableColumn v-else label="被带上" width="80" align="center">
        <template #default="{ row }">{{ usedBy(row) || '—' }}</template>
      </ElTableColumn>
      <ElTableColumn label="最后修改" width="150">
        <template #default="{ row }">
          <div class="kb-muted">{{ row.updated_by }}</div>
          <div class="kb-muted">{{ fmt(row.updated_at) }}</div>
        </template>
      </ElTableColumn>
      <ElTableColumn label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <ElButton link type="primary" @click="openDialog(row)">编辑</ElButton>
          <ElButton link type="danger" @click="remove(row)">删除</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>

    <ElDialog v-model="dialogOpen" :title="editId ? '编辑' : '新增'" width="640px" :close-on-click-modal="false">
      <ElForm label-width="90px" @submit.prevent>
        <ElFormItem label="平台">
          <ElSelect v-model="form.platform" filterable style="width: 100%">
            <ElOption :value="GENERAL" label="通用（所有平台）" />
            <ElOption v-for="p in sortedPlatforms" :key="p.id" :value="p.id" :label="p.status === 'off_sale' ? `${p.name}（禁售）` : p.name" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="类型">
          <ElRadioGroup v-model="form.kind">
            <ElRadioButton v-for="k in KINDS" :key="k.value" :value="k.value">{{ k.label }}</ElRadioButton>
          </ElRadioGroup>
        </ElFormItem>
        <ElFormItem :label="titleLabel" required>
          <ElInput v-model="form.title" maxlength="300" :placeholder="form.kind === 'phrase' ? '给同事看的简短标题，可不填' : ''" />
        </ElFormItem>
        <ElFormItem v-if="form.kind === 'tutorial'" label="教程链接" required>
          <ElInput v-model="form.url" placeholder="https://" />
        </ElFormItem>
        <ElFormItem :label="contentLabel" :required="form.kind !== 'tutorial'">
          <ElInput v-model="form.content" type="textarea" :rows="form.kind === 'tutorial' ? 2 : 7" :placeholder="contentHint" />
        </ElFormItem>
        <ElFormItem v-if="form.kind !== 'tutorial'" label="附带教程">
          <ElSelect v-model="form.tutorials" multiple filterable placeholder="复制时自动加在后面（选这个平台和通用的教程）" style="width: 100%">
            <ElOption v-for="o in tutorialOptions" :key="o.id" :value="o.id" :label="o.label" />
          </ElSelect>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="dialogOpen = false">取消</ElButton>
        <ElButton type="primary" :loading="saving" @click="submit">保存</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.kb-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  margin-bottom: 16px;
}
.kb-hint {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.kb-plat {
  color: #c45656;
  font-weight: 700;
}
.kb-text {
  white-space: pre-wrap;
  line-height: 1.6;
  word-break: break-word;
}
.kb-url {
  color: var(--el-color-primary);
  word-break: break-all;
  font-size: 13px;
}
.kb-tag {
  margin: 2px 4px 2px 0;
}
.kb-muted {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
</style>
