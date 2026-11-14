<script setup lang="ts">
/**
 * 业务+价格（原「平台/商品」，淘宝样式）：内嵌 public/library.html。
 * 数据来自 /api/catalog/library/；页面内的 全部平台 → 平台 → 方式 → 档位 跳转都在内嵌页里完成。
 * 旧版页面已删除，/products/classic 跳到这里。
 */
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

defineOptions({ name: 'ProductPlatforms' })

const route = useRoute()
const router = useRouter()

// 内嵌页里点「看教程+话术」时发消息过来，由这里切到「教程+话术」（只接受同源、站内路径）
function onMessage(e: MessageEvent) {
  if (e.origin !== window.location.origin) return
  const d = e.data
  if (!d || d.type !== 'xh-navigate' || typeof d.path !== 'string') return
  if (!d.path.startsWith('/knowledge')) return
  router.push(d.path)
}
onMounted(() => window.addEventListener('message', onMessage))
onBeforeUnmount(() => window.removeEventListener('message', onMessage))

// 每次打开都带上时间戳，避免浏览器一直用缓存里的旧版 library.html
const bust = Date.now()

const src = computed(() => {
  const raw = route.params.platformId
  const id = Array.isArray(raw) ? raw[0] : raw
  return `/library.html?v=${bust}` + (id && /^\d+$/.test(String(id)) ? `#/p/${id}` : '#/')
})
</script>

<template>
  <div class="catalog-library">
    <iframe :key="src" :src="src" title="业务+价格" class="catalog-library__frame"></iframe>
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
  background: transparent;
}
</style>
