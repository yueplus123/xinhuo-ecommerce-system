<script setup lang="ts">
/**
 * 平台/商品（新版，淘宝样式）：内嵌 public/library.html。
 * 数据来自 /api/catalog/library/；页面内的 全部平台 → 平台 → 方式 → 档位 跳转都在内嵌页里完成。
 * 旧版页面保留在 /products/classic。
 */
import { computed } from 'vue'
import { useRoute } from 'vue-router'

defineOptions({ name: 'ProductPlatforms' })

const route = useRoute()

const src = computed(() => {
  const raw = route.params.platformId
  const id = Array.isArray(raw) ? raw[0] : raw
  return '/library.html' + (id && /^\d+$/.test(String(id)) ? `#/p/${id}` : '#/')
})
</script>

<template>
  <div class="catalog-library">
    <iframe :key="src" :src="src" title="平台/商品" class="catalog-library__frame"></iframe>
  </div>
</template>

<style scoped>
.catalog-library {
  height: calc(100vh - 120px);
  min-height: 560px;
}
.catalog-library__frame {
  display: block;
  width: 100%;
  height: 100%;
  border: 0;
  border-radius: 12px;
  background: #f3f3f3;
}
</style>
