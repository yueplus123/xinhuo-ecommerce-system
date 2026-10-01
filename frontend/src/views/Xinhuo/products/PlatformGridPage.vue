<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElAlert, ElCard, ElCol, ElMessage, ElRow, ElTag } from 'element-plus'
import { ContentWrap } from '@/components/ContentWrap'
import { Search } from '@/components/Search'
import { BaseButton } from '@/components/Button'
import { FormSchema } from '@/components/Form'
import { listPlatforms, exportPlatformBusinesses } from '@/api/xinhuo/platforms'
import { showCopySuccess } from '@/copyFeedback'

defineOptions({ name: 'ProductPlatforms' })

const route = useRoute()
const router = useRouter()
const items = ref<any[]>([])
const q = ref('')
const status = ref('')
const loadError = ref('')
const loading = ref(true)
const exporting = ref(false)

function onSearch(data?: Recordable) {
  q.value = String(data?.q ?? '').trim()
  status.value = String(data?.status ?? '').trim()
  load()
}

function onReset(data?: Recordable) {
  q.value = String(data?.q ?? '').trim()
  status.value = String(data?.status ?? '').trim()
  load()
}

const searchSchema = computed<FormSchema[]>(() => [
  {
    field: 'q',
    label: '关键词',
    component: 'Input',
    componentProps: { placeholder: '关键词', clearable: true }
  },
  {
    field: 'status',
    label: '状态',
    component: 'Select',
    componentProps: {
      placeholder: '全部状态',
      clearable: true,
      options: [
        { label: '在售', value: 'on_sale' },
        { label: '禁售', value: 'off_sale' },
        { label: '待测试', value: 'pending_test' }
      ]
    }
  }
])

const skuStatusSummary = computed(() => {
  let onSale = 0
  let offSale = 0
  let pending = 0
  for (const p of items.value) {
    onSale += Number(p?.sku_on_sale_count || 0)
    offSale += Number(p?.sku_off_sale_count || 0)
    pending += Number(p?.sku_pending_test_count || 0)
  }
  return { onSale, offSale, pending }
})

const pillColorPairs = [
  { bg: '#ffe4e6', text: '#be123c' },
  { bg: '#ffedd5', text: '#c2410c' },
  { bg: '#fef3c7', text: '#b45309' },
  { bg: '#dcfce7', text: '#15803d' },
  { bg: '#cffafe', text: '#0f766e' },
  { bg: '#dbeafe', text: '#1d4ed8' },
  { bg: '#e0e7ff', text: '#4338ca' },
  { bg: '#f3e8ff', text: '#7e22ce' }
]

function platformTagList(p: any) {
  return (p.platform_tags || []).filter((t: any) => t?.name)
}

function tagPillStyle(tag: any) {
  const key = String(tag?.id ?? tag?.name ?? '')
  let hash = 0
  for (let i = 0; i < key.length; i += 1) hash = (hash * 31 + key.charCodeAt(i)) >>> 0
  const pair = pillColorPairs[hash % pillColorPairs.length]
  return { backgroundColor: pair.bg, color: pair.text, borderColor: pair.text + '33' }
}

function statusLabel(s: string) {
  if (s === 'on_sale') return '在售'
  if (s === 'pending_test') return '待测试'
  if (s === 'off_sale') return '禁售'
  return s || '—'
}

function statusTagType(s: string) {
  if (s === 'on_sale') return 'success'
  if (s === 'pending_test') return 'warning'
  if (s === 'off_sale') return 'danger'
  return 'info'
}

function normalizeList(data: any) {
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.results)) return data.results
  return []
}

async function load() {
  loadError.value = ''
  loading.value = true
  try {
    const { data } = await listPlatforms({ q: q.value || undefined, status: status.value || undefined })
    const list = normalizeList(data).slice()
    list.sort((a, b) => {
      const ao = Number(a?.sort_order ?? 0)
      const bo = Number(b?.sort_order ?? 0)
      if (ao !== bo) return ao - bo
      return (Number(a?.id) || 0) - (Number(b?.id) || 0)
    })
    items.value = list
  } catch (e: any) {
    items.value = []
    loadError.value =
      e?.response?.data?.detail || e?.response?.data?.message || e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

function goBusinesses(platformId: number | string) {
  const kw = (q.value || '').trim()
  router.push({
    name: 'PlatformBusinesses',
    params: { platformId: String(platformId) },
    query: kw ? { q: kw } : undefined
  })
}

async function copyText(text: string) {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
  } catch (_) {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.setAttribute('readonly', '')
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
  }
  showCopySuccess()
}

async function onCopyUrl(e: MouseEvent, text: string) {
  e.stopPropagation()
  e.preventDefault()
  await copyText(text)
}

async function exportBusinesses() {
  if (exporting.value) return
  exporting.value = true
  try {
    const resp = await exportPlatformBusinesses({
      q: q.value || undefined,
      status: status.value || undefined
    })
    const blob = resp.data instanceof Blob ? resp.data : new Blob([resp.data], { type: 'text/plain' })
    const text = await blob.text()
    if (!String(text || '').trim()) {
      ElMessage.warning('当前筛选下没有可导出的业务')
      return
    }
    const url = URL.createObjectURL(new Blob([text], { type: 'text/plain;charset=utf-8' }))
    const a = document.createElement('a')
    a.href = url
    a.download = '薪火business.txt'
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('已导出业务列表')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '导出失败')
  } finally {
    exporting.value = false
  }
}

watch(
  () => route.fullPath,
  () => {
    load()
  },
  { immediate: true }
)
</script>

<template>
  <ContentWrap
    title="平台"
    message="点选平台卡片进入商品；仅 1 个业务的平台将直接展示 SKU，多个业务的平台先进入业务列表。"
  >
    <Search
      :schema="searchSchema"
      :search-loading="loading"
      @search="onSearch"
      @reset="onReset"
    >
      <template #action-extra>
        <BaseButton type="primary" :loading="exporting" @click="exportBusinesses">
          {{ exporting ? '导出中…' : '一键导出业务' }}
        </BaseButton>
      </template>
    </Search>

    <div class="mb-16px flex flex-wrap gap-8px">
      <ElTag type="success" size="large">在售商品数 {{ skuStatusSummary.onSale }}</ElTag>
      <ElTag type="danger" size="large">禁售商品数 {{ skuStatusSummary.offSale }}</ElTag>
      <ElTag type="warning" size="large">待测试商品数 {{ skuStatusSummary.pending }}</ElTag>
    </div>

    <ElAlert v-if="loadError" type="error" :closable="false" class="mb-12px" :title="loadError" />
    <div v-else-if="loading" v-loading="loading" class="min-h-120px" />
    <ElAlert v-else-if="!items.length" type="info" :closable="false" title="暂无平台数据" />

    <ElRow v-else :gutter="16">
      <ElCol
        v-for="p in items"
        :key="p.id"
        :xs="24"
        :sm="12"
        :md="8"
        :lg="6"
        class="mb-16px"
      >
        <ElCard
          shadow="hover"
          class="platform-card cursor-pointer h-full"
          @click="goBusinesses(p.id)"
        >
          <div class="flex items-start justify-between gap-8px mb-10px">
            <span class="text-16px font-700 text-[var(--el-text-color-primary)]">{{ p.name }}</span>
            <ElTag :type="statusTagType(p.status)" size="small">{{ statusLabel(p.status) }}</ElTag>
          </div>

          <div class="platform-card__tags">
            <template v-if="platformTagList(p).length">
              <span
                v-for="tag in platformTagList(p)"
                :key="`${p.id}-${tag.id || tag.name}`"
                class="tag-pill"
                :style="tagPillStyle(tag)"
              >
                {{ tag.name }}
              </span>
            </template>
            <span v-else class="text-13px text-[var(--el-text-color-secondary)]">—</span>
          </div>

          <div
            class="flex items-center gap-8px pt-8px border-t border-[var(--el-border-color-lighter)] mb-10px"
          >
            <span
              class="flex-1 min-w-0 text-12px text-[var(--el-text-color-secondary)] truncate"
              :title="p.url || ''"
            >
              {{ p.url || '—' }}
            </span>
            <BaseButton v-if="p.url" size="small" @click="onCopyUrl($event, p.url)">一键复制</BaseButton>
          </div>

          <div class="flex items-center justify-between text-12px text-[var(--el-text-color-secondary)]">
            <span>在售sku数 {{ p.sku_count ?? 0 }}</span>
            <span class="text-[var(--el-color-primary)] font-600">
              {{ Number(p.business_count) === 1 ? '直接看商品 ›' : '进入业务 ›' }}
            </span>
          </div>
        </ElCard>
      </ElCol>
    </ElRow>
  </ContentWrap>
</template>

<style scoped>
.platform-card {
  height: 220px;
}
.platform-card :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  height: 100%;
  box-sizing: border-box;
  overflow: hidden;
}
.platform-card__tags {
  flex: 1 1 auto;
  min-height: 0;
  max-height: 72px;
  margin-bottom: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-content: flex-start;
  overflow: hidden;
}
.tag-pill {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 8px;
  border-radius: 4px;
  border: 1px solid transparent;
  font-size: 12px;
  line-height: 1;
  white-space: nowrap;
}
</style>
