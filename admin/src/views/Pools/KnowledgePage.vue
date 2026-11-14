<script setup lang="ts">
// 教程+话术：职员端「教程+话术」页面的内容（问答 / 教程 / 快捷语），在这里新增 / 编辑 / 删除。
// 旧的教程池、话术池、SKU 快捷话术已经搬进来（seed_knowledge_base），原来的页面已删除。
import ContentWrap from '@/components/ContentWrap.vue'
import KnowledgeManager from './KnowledgeManager.vue'

defineOptions({ name: 'ManageKnowledge' })
</script>

<template>
  <ContentWrap title="教程+话术">
    <KnowledgeManager />
  </ContentWrap>
</template>
