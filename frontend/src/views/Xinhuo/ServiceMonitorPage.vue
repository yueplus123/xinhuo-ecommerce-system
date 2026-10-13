<script setup lang="ts">
import { listServiceMonitorPages } from '@/api/xinhuo/infoPages'
import EmbedPage from './EmbedPage.vue'

defineOptions({ name: 'ServiceMonitor' })
</script>

<template>
  <EmbedPage
    :fetch-pages="listServiceMonitorPages"
    frame-title="服务监控"
    empty-hint="管理员还未配置监控面板链接，请到后台「服务监控页面管理」添加（默认 Uptime Kuma：http://127.0.0.1:3001/）"
  />
</template>
