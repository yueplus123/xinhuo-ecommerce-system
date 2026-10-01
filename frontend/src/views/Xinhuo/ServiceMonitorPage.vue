<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElAlert } from 'element-plus'
import { ContentWrap } from '@/components/ContentWrap'
import api from '@/api/xinhuo/client'

defineOptions({ name: 'ServiceMonitor' })

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
    const { data } = await api.get('/service-monitor-pages/')
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
    loadError.value = e?.response?.data?.detail || e?.message || '加载服务监控页面失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadPages)
</script>

<template>
  <ContentWrap class="sm-page">
    <ElAlert v-if="loadError" type="error" :closable="false" class="mb-8px" :title="loadError" />
    <ElAlert
      v-else-if="!loading && !pages.length"
      type="info"
      :closable="false"
      class="mb-8px"
      title="管理员还未配置监控面板链接，请到后台「服务监控页面管理」添加（默认 Uptime Kuma：http://127.0.0.1:3001/）"
    />
    <ElAlert
      v-else-if="!loading && pages.length && !selectedUrl"
      type="warning"
      :closable="false"
      class="mb-8px"
      title="当前链接为空，请联系管理员配置。"
    />

    <div v-if="selectedUrl" class="sm-frame-wrap">
      <iframe
        :src="selectedUrl"
        class="sm-frame"
        title="服务监控"
        allow="clipboard-read; clipboard-write; fullscreen"
      />
    </div>
  </ContentWrap>
</template>

<style scoped>
.sm-page :deep(.el-card__header) {
  display: none;
}
.sm-page :deep(.el-card__body) {
  padding: 0;
}
.sm-frame-wrap {
  width: 100%;
  height: calc(100dvh - 90px);
  min-height: 480px;
  box-sizing: border-box;
  overflow: hidden;
  background: #fff;
}
.sm-frame {
  display: block;
  width: 100%;
  height: 100%;
  border: 0;
}
@media (max-width: 900px) {
  .sm-frame-wrap {
    height: calc(100dvh - 100px);
    min-height: 420px;
  }
}
</style>
