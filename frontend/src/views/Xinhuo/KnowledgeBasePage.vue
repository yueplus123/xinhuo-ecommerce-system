<script setup lang="ts">
/**
 * 教程+话术（知识库）：内嵌 public/knowledge.html，数据走 /api/knowledge/。
 * 按平台分，平台里分「问答 / 教程 / 快捷语」；只能看和复制，内容在管理后台「教程+话术」里维护。
 * 从「业务+价格」点「看教程+话术」会带上 ?p=平台ID&k=类型，直接打开那个平台。
 */
import { computed } from 'vue'
import { useRoute } from 'vue-router'

defineOptions({ name: 'KnowledgeBase' })

const route = useRoute()
// 带时间戳，避免浏览器一直用缓存里的旧版 knowledge.html
const bust = Date.now()

const src = computed(() => {
  const p = String(route.query.p ?? '')
  const k = String(route.query.k ?? '')
  const hash = /^\d+$/.test(p) ? `#/p/${p}` + (/^(faq|tutorial|phrase)$/.test(k) ? `/${k}` : '') : ''
  return `/knowledge.html?v=${bust}${hash}`
})
</script>

<template>
  <div class="knowledge-base">
    <iframe :key="src" :src="src" title="教程+话术" class="knowledge-base__frame"></iframe>
  </div>
</template>

<style scoped>
.knowledge-base {
  height: calc(100vh - 120px);
  min-height: 560px;
}
.knowledge-base__frame {
  display: block;
  width: 100%;
  height: 100%;
  border: 0;
  border-radius: 12px;
  background: transparent;
}
</style>
