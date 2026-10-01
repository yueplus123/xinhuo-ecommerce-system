<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElAlert, ElOption, ElSelect, ElTabPane, ElTabs } from 'element-plus'
import { ContentWrap } from '@/components/ContentWrap'
import { BaseButton } from '@/components/Button'
import api from '@/api/xinhuo/client'

defineOptions({ name: 'SharedAppleId' })

const pages = ref<any[]>([])
const selectedId = ref<number | null>(null)
const loading = ref(false)
const loadError = ref('')

const selectedPage = computed(
  () => pages.value.find((item) => item.id === selectedId.value) || null
)
const selectedUrl = computed(() => selectedPage.value?.share_url || '')

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
    const { data } = await api.get('/shared-apple-id-pages/')
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
    loadError.value = e?.response?.data?.detail || e?.message || '加载共享苹果ID分享页失败'
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
  <ContentWrap title="共享苹果ID">
    <div class="mb-12px flex flex-wrap items-center justify-between gap-10px">
      <ElSelect
        v-if="pages.length"
        v-model="selectedId"
        placeholder="选择分享页"
        class="!w-220px md:!hidden"
        :disabled="loading"
      >
        <ElOption v-for="item in pages" :key="item.id" :label="item.name" :value="item.id" />
      </ElSelect>
      <div class="hidden md:block flex-1" />
      <BaseButton :loading="loading" @click="loadPages">刷新</BaseButton>
    </div>

    <ElAlert v-if="loadError" type="error" :closable="false" class="mb-12px" :title="loadError" />
    <ElAlert
      v-else-if="!loading && !pages.length"
      type="info"
      :closable="false"
      class="mb-12px"
      title="管理员还未配置分享页链接"
    />

    <template v-else-if="pages.length">
      <ElTabs
        :model-value="String(selectedId ?? '')"
        class="hidden md:block mb-10px"
        @tab-change="onTabChange"
      >
        <ElTabPane
          v-for="item in pages"
          :key="item.id"
          :label="item.name"
          :name="String(item.id)"
        />
      </ElTabs>

      <div v-if="selectedUrl" class="apple-frame-wrap">
        <iframe :src="selectedUrl" class="apple-frame" title="共享苹果ID分享页" />
      </div>
      <ElAlert
        v-else
        type="warning"
        :closable="false"
        title="当前链接为空，请联系管理员配置。"
      />
    </template>
  </ContentWrap>
</template>

<style scoped>
.apple-frame-wrap {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}
.apple-frame {
  width: 100%;
  height: 68vh;
  border: 0;
}
@media (max-width: 768px) {
  .apple-frame {
    height: 62vh;
  }
}
</style>
