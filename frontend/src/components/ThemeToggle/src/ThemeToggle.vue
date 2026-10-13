<script setup lang="ts">
// 白天 / 黑夜切换按钮（放在顶栏头像左侧）。
// 状态走全局 store（appStore.isDark，已持久化）；这里只负责切换，并在切换瞬间加上过渡类。
import { computed } from 'vue'
import { ElIcon, ElTooltip } from 'element-plus'
import { Moon, Sunny } from '@element-plus/icons-vue'
import { useAppStore } from '@/store/modules/app'
import { propTypes } from '@/utils/propTypes'

defineProps({
  color: propTypes.string.def('')
})

const appStore = useAppStore()
const isDark = computed(() => appStore.getIsDark)
const label = computed(() => (isDark.value ? '切换到白天模式' : '切换到黑夜模式'))

function toggle() {
  const root = document.documentElement
  // 只在点击的这一刻开启过渡，避免页面首次加载或其他样式变化时也出现动画
  root.classList.add('theme-transition')
  appStore.setIsDark(!isDark.value)
  try {
    localStorage.setItem('xinhuo-theme', isDark.value ? 'dark' : 'light') // 给 index.html 的防闪烁脚本用
  } catch {
    /* 隐私模式下可能不可写，忽略 */
  }
  window.setTimeout(() => root.classList.remove('theme-transition'), 400)
}
</script>

<template>
  <ElTooltip :content="label" placement="bottom" :show-after="300">
    <button
      type="button"
      class="theme-toggle custom-hover"
      :aria-label="label"
      :aria-pressed="isDark"
      @click="toggle"
    >
      <ElIcon :size="18" :color="color || undefined">
        <Sunny v-if="isDark" />
        <Moon v-else />
      </ElIcon>
    </button>
  </ElTooltip>
</template>

<style scoped>
.theme-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 0 12px;
  color: inherit;
  cursor: pointer;
  background: transparent;
  border: 0;
  outline: none;
}
.theme-toggle:focus-visible {
  outline: 2px solid var(--el-color-primary);
  outline-offset: -2px;
}
</style>
