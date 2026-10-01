<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElAlert } from 'element-plus'
import { ContentWrap } from '@/components/ContentWrap'
import api from '@/api/xinhuo/client'

defineOptions({ name: 'PictCart' })

const pages = ref<any[]>([])
const loading = ref(false)
const loadError = ref('')

const selectedUrl = computed(() => {
  const first = pages.value[0]
  return first?.share_url || ''
})

async function loadPages() {
  loading.value = true
  loadError.value = ''
  try {
    const { data } = await api.get('/pict-cart-pages/')
    const raw = data?.results || data
    const list = Array.isArray(raw) ? raw.slice() : []
    list.sort((a, b) => {
      const ao = Number(a?.sort_order ?? 0)
      const bo = Number(b?.sort_order ?? 0)
      if (ao !== bo) return ao - bo
      return (Number(a?.id) || 0) - (Number(b?.id) || 0)
    })
    pages.value = list
  } catch (e: any) {
    pages.value = []
    loadError.value = e?.response?.data?.detail || e?.message || '加载 pict加购物车 页面失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadPages)
</script>

<template>
  <ContentWrap class="pict-page">
    <ElAlert v-if="loadError" type="error" :closable="false" class="mb-8px" :title="loadError" />
    <ElAlert
      v-else-if="!loading && !pages.length"
      type="info"
      :closable="false"
      class="mb-8px"
      title="管理员还未配置链接，请到后台「pict加购物车页面管理」添加"
    />
    <ElAlert
      v-else-if="!loading && pages.length && !selectedUrl"
      type="warning"
      :closable="false"
      class="mb-8px"
      title="当前链接为空，请联系管理员配置。"
    />

    <div v-if="selectedUrl" class="pict-frame-wrap">
      <iframe
        :src="selectedUrl"
        class="pict-frame"
        title="pict加购物车"
        allow="clipboard-read; clipboard-write; fullscreen"
      />
    </div>
  </ContentWrap>
</template>

<style scoped>
.pict-page :deep(.el-card__header) {
  display: none;
}
.pict-page :deep(.el-card__body) {
  padding: 0;
}
.pict-frame-wrap {
  width: 100%;
  height: calc(100dvh - 90px);
  min-height: 480px;
  box-sizing: border-box;
  overflow: hidden;
  background: #fff;
}
.pict-frame {
  display: block;
  width: 100%;
  height: 100%;
  border: 0;
}
@media (max-width: 900px) {
  .pict-frame-wrap {
    height: calc(100dvh - 100px);
    min-height: 420px;
  }
}
</style>
