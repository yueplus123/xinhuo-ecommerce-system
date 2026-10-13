<script setup lang="ts">
// 通用「后台配置外链 → iframe 嵌入」页：取列表第一条的 share_url 展示
import { computed, onMounted, ref } from 'vue'
import { ElAlert } from 'element-plus'
import { ContentWrap } from '@/components/ContentWrap'

const props = defineProps<{
  fetchPages: () => Promise<{ data: any }>
  frameTitle: string // iframe title，也用于加载失败提示
  emptyHint: string // 未配置链接时的提示
}>()

const pages = ref<any[]>([])
const loading = ref(false)
const loadError = ref('')

const selectedUrl = computed(() => pages.value[0]?.share_url || '')

async function loadPages() {
  loading.value = true
  loadError.value = ''
  try {
    const { data } = await props.fetchPages()
    const raw = data?.results || data
    const list = Array.isArray(raw) ? raw.slice() : []
    list.sort(
      (a, b) =>
        Number(a?.sort_order ?? 0) - Number(b?.sort_order ?? 0) ||
        (Number(a?.id) || 0) - (Number(b?.id) || 0)
    )
    pages.value = list
  } catch (e: any) {
    pages.value = []
    loadError.value = e?.response?.data?.detail || e?.message || `加载${props.frameTitle}页面失败`
  } finally {
    loading.value = false
  }
}

onMounted(loadPages)
</script>

<template>
  <ContentWrap class="embed-page">
    <ElAlert v-if="loadError" type="error" :closable="false" class="mb-8px" :title="loadError" />
    <ElAlert
      v-else-if="!loading && !pages.length"
      type="info"
      :closable="false"
      class="mb-8px"
      :title="emptyHint"
    />
    <ElAlert
      v-else-if="!loading && pages.length && !selectedUrl"
      type="warning"
      :closable="false"
      class="mb-8px"
      title="当前链接为空，请联系管理员配置。"
    />

    <div v-if="selectedUrl" class="embed-frame-wrap">
      <iframe
        :src="selectedUrl"
        class="embed-frame"
        :title="frameTitle"
        allow="clipboard-read; clipboard-write; fullscreen"
      />
    </div>
  </ContentWrap>
</template>

<style scoped>
.embed-page :deep(.el-card__header) {
  display: none;
}
.embed-page :deep(.el-card__body) {
  padding: 0;
}
.embed-frame-wrap {
  width: 100%;
  height: calc(100dvh - 90px);
  min-height: 480px;
  box-sizing: border-box;
  overflow: hidden;
  background: #fff;
}
.embed-frame {
  display: block;
  width: 100%;
  height: 100%;
  border: 0;
}
@media (max-width: 900px) {
  .embed-frame-wrap {
    height: calc(100dvh - 100px);
    min-height: 420px;
  }
}
</style>
