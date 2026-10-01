<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  ElAlert,
  ElDialog,
  ElEmpty,
  ElImage,
  ElImageViewer,
  ElInput,
  ElTag
} from 'element-plus'
import { ContentWrap } from '@/components/ContentWrap'
import { BaseButton } from '@/components/Button'
import { Icon } from '@/components/Icon'
import { listHallBlocks } from '@/api/xinhuo/dashboard'

defineOptions({ name: 'Hall' })

type FilterKey = 'all' | 'pinned'

const rows = ref<any[]>([])
const active = ref<any>(null)
const detailVisible = ref(false)
const loadError = ref('')
const loading = ref(false)
const q = ref('')
const filter = ref<FilterKey>('all')
const imagePreviewUrl = ref('')
const imagePreviewVisible = ref(false)

const coverTones = [
  { bg: '#ecf5ff', fg: '#409eff' },
  { bg: '#f0f9eb', fg: '#67c23a' },
  { bg: '#fdf6ec', fg: '#e6a23c' },
  { bg: '#fef0f0', fg: '#f56c6c' },
  { bg: '#f4f4f5', fg: '#909399' },
  { bg: '#e8f8f5', fg: '#0d9488' }
]

function normalizeHallList(data: any) {
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.results)) return data.results
  if (data && typeof data === 'object' && data.detail != null) return []
  return []
}

function hallImageSrc(row: any) {
  const u = row?.image
  if (!u || typeof u !== 'string') return ''
  if (/^https?:\/\//i.test(u)) return u
  return u.startsWith('/') ? u : `/${u}`
}

function sortHallRows(list: any[]) {
  return [...list].sort((a, b) => {
    const pa = !!a.is_pinned
    const pb = !!b.is_pinned
    if (pa !== pb) return pa ? -1 : 1
    const sa = Number(a.sort_order) || 0
    const sb = Number(b.sort_order) || 0
    if (sa !== sb) return sa - sb
    return (a.id || 0) - (b.id || 0)
  })
}

function formatUpdatedAt(iso: string) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso)
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
    .format(d)
    .replace(/\//g, '-')
}

function coverTone(row: any) {
  const key = String(row?.id ?? row?.title ?? '')
  let hash = 0
  for (let i = 0; i < key.length; i += 1) hash = (hash * 31 + key.charCodeAt(i)) >>> 0
  return coverTones[hash % coverTones.length]
}

const pinnedCount = computed(() => rows.value.filter((r) => !!r.is_pinned).length)

const visibleRows = computed(() => {
  const kw = q.value.trim().toLowerCase()
  return rows.value.filter((r) => {
    if (filter.value === 'pinned' && !r.is_pinned) return false
    if (!kw) return true
    const hay = `${r.title || ''} ${r.body || ''}`.toLowerCase()
    return hay.includes(kw)
  })
})

async function load() {
  loadError.value = ''
  loading.value = true
  try {
    const { data } = await listHallBlocks()
    rows.value = sortHallRows(normalizeHallList(data))
  } catch (e: any) {
    rows.value = []
    loadError.value =
      e?.response?.data?.detail || e?.response?.data?.message || e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

function openDetail(row: any) {
  active.value = row
  detailVisible.value = true
}

function closeDetail() {
  detailVisible.value = false
  active.value = null
}

function openImagePreview(url: string) {
  if (!url) return
  imagePreviewUrl.value = url
  imagePreviewVisible.value = true
}

function closeImagePreview() {
  imagePreviewVisible.value = false
  imagePreviewUrl.value = ''
}

onMounted(load)
</script>

<template>
  <ContentWrap
    title="大厅"
    message="放与具体商品无关的杂项资料：排班、规范、话术、通道说明、常用入口等。"
  >
    <div class="hall-toolbar mb-16px">
      <ElInput
        v-model="q"
        clearable
        placeholder="搜索标题或内容"
        class="hall-toolbar__search"
      >
        <template #prefix>
          <Icon icon="vi-ep:search" />
        </template>
      </ElInput>
      <div class="hall-toolbar__filters">
        <button
          type="button"
          class="hall-chip"
          :class="{ 'is-active': filter === 'all' }"
          @click="filter = 'all'"
        >
          全部 {{ rows.length }}
        </button>
        <button
          type="button"
          class="hall-chip"
          :class="{ 'is-active': filter === 'pinned' }"
          @click="filter = 'pinned'"
        >
          常用置顶 {{ pinnedCount }}
        </button>
      </div>
    </div>

    <ElAlert v-if="loadError" type="error" :closable="false" class="mb-12px" :title="loadError" />
    <ElAlert
      v-else-if="!loading && !rows.length"
      type="info"
      :closable="false"
      class="mb-12px"
      title="暂无大厅内容。可在管理后台「大厅内容管理」添加排班、规范、话术等杂项资料。"
    />

    <div v-loading="loading" class="min-h-160px">
      <ElEmpty
        v-if="!loading && rows.length && !visibleRows.length"
        description="没有匹配的资料"
        :image-size="80"
      />

      <div v-else-if="visibleRows.length" class="hall-wall">
        <article
          v-for="r in visibleRows"
          :key="r.id"
          class="kb-card"
          :class="{ 'is-inactive': r.is_active === false }"
          @click="openDetail(r)"
        >
          <div class="kb-card__cover">
            <ElImage
              v-if="hallImageSrc(r)"
              :src="hallImageSrc(r)"
              :alt="r.title"
              fit="cover"
              class="kb-card__img"
              lazy
            />
            <div
              v-else
              class="kb-card__avatar"
              :style="{ background: coverTone(r).bg, color: coverTone(r).fg }"
            >
              <span class="kb-card__avatar-title">{{ r.title }}</span>
            </div>
            <ElTag v-if="r.is_pinned" class="kb-card__pin" type="danger" size="small" effect="dark">
              常用
            </ElTag>
          </div>

          <div class="kb-card__body">
            <h3 class="kb-card__title">{{ r.title }}</h3>
            <p class="kb-card__desc">{{ r.body || '暂无说明' }}</p>
          </div>

          <div class="kb-card__foot">
            <span class="kb-card__time">{{ formatUpdatedAt(r.updated_at) || '—' }}</span>
            <span class="kb-card__more">查看</span>
          </div>
        </article>
      </div>
    </div>

    <ElDialog
      v-model="detailVisible"
      :title="active?.title || '资料详情'"
      width="720px"
      destroy-on-close
      class="hall-detail-dialog"
      @close="closeDetail"
    >
      <template v-if="active">
        <div class="hall-detail__meta">
          <ElTag v-if="active.is_pinned" type="danger" size="small" effect="plain">常用置顶</ElTag>
          <ElTag v-if="active.is_active === false" type="warning" size="small">未展示</ElTag>
          <span v-if="active.updated_at" class="hall-detail__time">
            更新于 {{ formatUpdatedAt(active.updated_at) }}
          </span>
        </div>
        <div class="hall-detail__body">{{ active.body || '（暂无正文）' }}</div>
        <div v-if="hallImageSrc(active)" class="hall-detail__media">
          <ElImage
            :src="hallImageSrc(active)"
            :alt="active.title"
            fit="contain"
            class="hall-detail__img cursor-zoom-in"
            @click="openImagePreview(hallImageSrc(active))"
          />
        </div>
      </template>
      <template #footer>
        <BaseButton type="primary" @click="closeDetail">关闭</BaseButton>
      </template>
    </ElDialog>

    <ElImageViewer
      v-if="imagePreviewVisible && imagePreviewUrl"
      :url-list="[imagePreviewUrl]"
      @close="closeImagePreview"
    />
  </ContentWrap>
</template>

<style scoped>
.hall-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}
.hall-toolbar__search {
  width: min(100%, 320px);
}
.hall-toolbar__filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.hall-chip {
  height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid var(--el-border-color);
  background: var(--el-bg-color);
  color: var(--el-text-color-regular);
  font-size: 13px;
  cursor: pointer;
  transition:
    color 0.15s ease,
    border-color 0.15s ease,
    background-color 0.15s ease;
}
.hall-chip:hover {
  color: var(--el-color-primary);
  border-color: var(--el-color-primary-light-5);
}
.hall-chip.is-active {
  color: var(--el-color-primary);
  border-color: var(--el-color-primary);
  background: color-mix(in srgb, var(--el-color-primary) 8%, var(--el-bg-color));
  font-weight: 600;
}
.hall-wall {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}
.kb-card {
  display: flex;
  flex-direction: column;
  min-height: 248px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  background: var(--el-bg-color);
  overflow: hidden;
  cursor: pointer;
  transition:
    transform 0.15s ease,
    box-shadow 0.15s ease,
    border-color 0.15s ease;
}
.kb-card:hover {
  transform: translateY(-2px);
  border-color: var(--el-color-primary-light-5);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}
.kb-card.is-inactive {
  opacity: 0.7;
}
.kb-card__cover {
  position: relative;
  height: 112px;
  background: var(--el-fill-color-light);
}
.kb-card__img {
  width: 100%;
  height: 100%;
}
.kb-card__avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  padding: 14px 16px;
  box-sizing: border-box;
}
.kb-card__avatar-title {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  overflow: hidden;
  max-width: 100%;
  font-size: 18px;
  font-weight: 700;
  line-height: 1.35;
  text-align: center;
  word-break: break-word;
}
.kb-card__pin {
  position: absolute;
  top: 10px;
  right: 10px;
}
.kb-card__body {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px 14px 8px;
  min-height: 0;
}
.kb-card__title {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  line-height: 1.35;
  color: var(--el-text-color-primary);
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}
.kb-card__desc {
  margin: 0;
  flex: 1 1 auto;
  font-size: 13px;
  line-height: 1.55;
  color: var(--el-text-color-regular);
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  overflow: hidden;
  white-space: pre-wrap;
  word-break: break-word;
}
.kb-card__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 14px 14px;
  border-top: 1px solid var(--el-border-color-extra-light);
}
.kb-card__time {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.kb-card__more {
  font-size: 12px;
  font-weight: 600;
  color: var(--el-color-primary);
}
.hall-detail__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}
.hall-detail__time {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.hall-detail__body {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 15px;
  line-height: 1.7;
  color: var(--el-text-color-regular);
}
.hall-detail__media {
  margin-top: 16px;
}
.hall-detail__img {
  max-width: 100%;
  max-height: 280px;
  border-radius: 8px;
  background: var(--el-fill-color-light);
}
</style>
