<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElAlert, ElOption, ElSelect, ElTabPane, ElTabs } from 'element-plus'
import { ContentWrap } from '@/components/ContentWrap'
import { BaseButton } from '@/components/Button'
import api from '@/api/xinhuo/client'

defineOptions({ name: 'FanboxStats' })

const FALLBACK_URL = 'https://fanbox.xinhuo.pro/'

const pages = ref<any[]>([])
const selectedId = ref<number | null>(null)
const loading = ref(false)
const loadError = ref('')

const selectedPage = computed(
  () => pages.value.find((item) => item.id === selectedId.value) || null
)
const selectedUrl = computed(
  () => selectedPage.value?.share_url || (pages.value.length ? '' : FALLBACK_URL)
)

function pickFirstPage() {
  if (!pages.value.length) {
    selectedId.value = null
    return
  }
  const hasCurrent = pages.value.some((item) => item.id === selectedId.value)
  if (!hasCurrent) {
    selectedId.value = pages.value[0].id
  }
}

async function loadPages() {
  loading.value = true
  loadError.value = ''
  try {
    const { data } = await api.get('/fanbox-stats-pages/')
    const raw = data?.results || data
    const list = Array.isArray(raw) ? raw.slice() : []
    list.sort((a, b) => {
      const ao = Number(a?.sort_order ?? 0)
      const bo = Number(b?.sort_order ?? 0)
      if (ao !== bo) return ao - bo
      return (Number(a?.id) || 0) - (Number(b?.id) || 0)
    })
    pages.value = list
    pickFirstPage()
  } catch (e: any) {
    pages.value = []
    selectedId.value = null
    loadError.value = e?.response?.data?.detail || e?.message || '加载 fanbox 链接失败'
  } finally {
    loading.value = false
  }
}

function onTabChange(name: string | number) {
  selectedId.value = Number(name)
}

onMounted(loadPages)
</script>

<template>
  <ContentWrap title="fanbox投稿作品统计" class="fanbox-page">
    <ElAlert v-if="loadError" type="error" :closable="false" class="mb-8px" :title="loadError" />
    <ElAlert
      v-else-if="!loading && !pages.length"
      type="info"
      :closable="false"
      class="mb-8px"
      title="管理员还未配置链接，请到后台「fanbox投稿作品统计管理」添加（当前暂用默认地址）"
    />

    <div v-if="pages.length" class="fanbox-toolbar">
      <ElSelect
        v-if="pages.length > 1"
        v-model="selectedId"
        placeholder="选择页面"
        class="fanbox-toolbar__select md:!hidden"
        :disabled="loading"
      >
        <ElOption v-for="item in pages" :key="item.id" :label="item.name" :value="item.id" />
      </ElSelect>
      <ElTabs
        v-if="pages.length > 1"
        :model-value="String(selectedId ?? '')"
        class="fanbox-tabs hidden md:flex"
        @tab-change="onTabChange"
      >
        <ElTabPane
          v-for="item in pages"
          :key="item.id"
          :label="item.name"
          :name="String(item.id)"
        />
      </ElTabs>
      <BaseButton class="fanbox-toolbar__refresh" :loading="loading" @click="loadPages">
        刷新
      </BaseButton>
    </div>
    <div v-else class="fanbox-toolbar fanbox-toolbar--solo">
      <BaseButton class="fanbox-toolbar__refresh" :loading="loading" @click="loadPages">
        刷新
      </BaseButton>
    </div>

    <div v-if="selectedUrl" class="fanbox-wrap">
      <iframe
        class="fanbox-frame"
        :src="selectedUrl"
        title="fanbox投稿作品统计"
        allow="clipboard-read; clipboard-write; fullscreen"
      />
    </div>
  </ContentWrap>
</template>

<style scoped>
.fanbox-page :deep(.el-card__body) {
  padding: 10px 12px 12px;
}
.fanbox-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  min-height: 36px;
}
.fanbox-toolbar--solo {
  justify-content: flex-end;
}
.fanbox-toolbar__select {
  width: 200px;
}
.fanbox-toolbar__refresh {
  margin-left: auto;
  flex-shrink: 0;
}
.fanbox-tabs {
  flex: 1;
  min-width: 0;
}
.fanbox-tabs :deep(.el-tabs__header) {
  margin: 0;
}
.fanbox-tabs :deep(.el-tabs__content) {
  display: none;
}
.fanbox-wrap {
  width: 100%;
  height: calc(100dvh - 150px);
  min-height: 480px;
  box-sizing: border-box;
}
.fanbox-frame {
  display: block;
  width: 100%;
  height: 100%;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 8px;
  background: #fff;
}
@media (max-width: 900px) {
  .fanbox-wrap {
    height: calc(100dvh - 170px);
    min-height: 420px;
  }
}
</style>
