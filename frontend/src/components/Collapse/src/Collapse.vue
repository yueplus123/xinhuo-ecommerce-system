<script setup lang="ts">
import { computed, unref } from 'vue'
import { ElIcon } from 'element-plus'
import { Expand, Fold } from '@element-plus/icons-vue'
import { useAppStore } from '@/store/modules/app'
import { propTypes } from '@/utils/propTypes'
import { useDesign } from '@/hooks/web/useDesign'

const { getPrefixCls } = useDesign()

const prefixCls = getPrefixCls('collapse')

defineProps({
  color: propTypes.string.def('')
})

const appStore = useAppStore()

const collapse = computed(() => appStore.getCollapse)

const toggleCollapse = () => {
  const collapsed = unref(collapse)
  appStore.setCollapse(!collapsed)
}
</script>

<template>
  <button
    type="button"
    :class="[prefixCls, 'sidebar-collapse-btn']"
    :title="collapse ? '展开侧栏' : '收起侧栏'"
    aria-label="展开或收起侧栏"
    @click="toggleCollapse"
  >
    <ElIcon :size="20" :color="color || 'var(--top-header-text-color, #333)'">
      <Expand v-if="collapse" />
      <Fold v-else />
    </ElIcon>
  </button>
</template>

<style scoped>
.sidebar-collapse-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  margin: 0 2px 0 2px;
  padding: 0;
  border: 0;
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
  flex-shrink: 0;
  z-index: 20;
  position: relative;
}
.sidebar-collapse-btn:hover {
  background: var(--top-header-hover-color, #f8f9fa);
}
</style>
