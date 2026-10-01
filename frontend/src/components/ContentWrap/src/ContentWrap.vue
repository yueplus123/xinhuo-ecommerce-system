<script setup lang="ts">
import { ElCard, ElTooltip } from 'element-plus'
import { propTypes } from '@/utils/propTypes'
import { useDesign } from '@/hooks/web/useDesign'

const { getPrefixCls } = useDesign()

const prefixCls = getPrefixCls('content-wrap')

defineProps({
  title: propTypes.string.def(''),
  message: propTypes.string.def('')
})
</script>

<template>
  <ElCard :class="[prefixCls]" shadow="never">
    <template v-if="title" #header>
      <div class="flex items-center">
        <span class="text-16px font-700">{{ title }}</span>
        <ElTooltip v-if="message" effect="dark" placement="right">
          <template #content>
            <div class="max-w-200px">{{ message }}</div>
          </template>
          <Icon class="ml-5px" icon="vi-bi:question-circle-fill" :size="14" />
        </ElTooltip>
        <div class="flex pl-20px flex-grow">
          <slot name="header"></slot>
        </div>
      </div>
    </template>
    <div>
      <slot></slot>
    </div>
  </ElCard>
</template>

<style lang="less" scoped>
@prefix-cls: ~'@{adminNamespace}-content-wrap';

/* 外圈 24px 由 AppView 负责；卡片内边距对齐 Ant Design / Material 的 16–24 档 */
.@{prefix-cls} {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  margin: 0;

  :deep(.el-card__header) {
    padding: 16px 24px;
    border-bottom: 1px solid var(--el-border-color-lighter);
  }

  :deep(.el-card__body) {
    padding: 24px;
  }
}
</style>
