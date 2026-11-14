<script setup lang="ts">
/**
 * 教程+话术管理：内嵌 public/knowledge.html?manage=1（新增 / 编辑 / 删除），数据走 /api/knowledge/。
 * 按平台分，平台里分「问答 / 教程 / 快捷语」；和「业务+价格」分开。
 */
defineOptions({ name: 'KnowledgeManage' })

// 带时间戳，避免浏览器一直用缓存里的旧版 knowledge.html
const src = `/knowledge.html?manage=1&v=${Date.now()}`
</script>

<template>
  <div class="knowledge-base">
    <iframe :src="src" title="教程+话术管理" class="knowledge-base__frame"></iframe>
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
