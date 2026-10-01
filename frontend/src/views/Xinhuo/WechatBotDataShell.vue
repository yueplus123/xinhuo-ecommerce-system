<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ContentWrap } from '@/components/ContentWrap'
import { ElTabs, ElTabPane } from 'element-plus'
import { WECHAT_BOT_TABLES } from './wechatBotTables'

defineOptions({ name: 'WechatBotData' })

const route = useRoute()
const router = useRouter()

const tabs = WECHAT_BOT_TABLES

const active = computed(() => {
  const path = route.path.replace(/\/+$/, '')
  const hit = tabs.find((t) => path === t.path || path.startsWith(`${t.path}/`))
  return hit?.path ?? tabs[0].path
})

function onTab(name: string | number) {
  router.push(String(name))
}
</script>

<template>
  <ContentWrap title="微信BOT数据">
    <ElTabs :model-value="active" @tab-change="onTab">
      <ElTabPane v-for="tab in tabs" :key="tab.key" :label="tab.label" :name="tab.path" />
    </ElTabs>
    <router-view v-slot="{ Component }">
      <keep-alive :max="16">
        <component :is="Component" />
      </keep-alive>
    </router-view>
  </ContentWrap>
</template>
