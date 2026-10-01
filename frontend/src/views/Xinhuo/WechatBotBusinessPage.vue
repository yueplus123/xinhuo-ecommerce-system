<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import WechatBotTablePanel from './WechatBotTablePanel.vue'
import { WECHAT_BOT_TABLE_KEYS, wechatBotTableLabel } from './wechatBotTables'

defineOptions({ name: 'WechatBotBusiness' })

const route = useRoute()

const tableKey = computed(() => {
  const key = String(route.params.tableKey || '').trim()
  return WECHAT_BOT_TABLE_KEYS.has(key) ? key : 'pixivcoban'
})

const tableTitle = computed(() => wechatBotTableLabel(tableKey.value))
</script>

<template>
  <WechatBotTablePanel :key="tableKey" :table-type="tableKey" :table-title="tableTitle" />
</template>
