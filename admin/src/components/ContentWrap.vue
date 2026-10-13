<script setup lang="ts">
// 页面内容卡片：标题 + 内容区（与职员端 ContentWrap 的用法保持一致，admin 自带一份精简版）
import { ElCard } from 'element-plus'

defineProps<{ title?: string }>()
</script>

<template>
  <ElCard class="content-wrap" shadow="never">
    <template v-if="title" #header>
      <span class="title">{{ title }}</span>
      <slot name="header" />
    </template>
    <slot />
  </ElCard>
</template>

<style scoped>
.content-wrap {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}
.content-wrap :deep(.el-card__header) {
  padding: 16px 24px;
}
.content-wrap :deep(.el-card__body) {
  padding: 24px;
}
.title {
  font-size: 16px;
  font-weight: 700;
}
</style>
