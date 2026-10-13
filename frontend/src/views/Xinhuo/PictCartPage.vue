<script setup lang="ts">
import { listPictCartPages } from '@/api/xinhuo/infoPages'
import EmbedPage from './EmbedPage.vue'

defineOptions({ name: 'PictCart' })
</script>

<template>
  <EmbedPage
    :fetch-pages="listPictCartPages"
    frame-title="pict加购物车"
    empty-hint="管理员还未配置链接，请到后台「pict加购物车页面管理」添加"
  />
</template>
