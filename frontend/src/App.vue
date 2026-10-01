<script setup lang="ts">
import { computed } from 'vue'
import { useAppStore } from '@/store/modules/app'
import { ConfigGlobal } from '@/components/ConfigGlobal'
import { useDesign } from '@/hooks/web/useDesign'
import { copyToastMessage, copyToastVisible } from '@/copyFeedback'

const { getPrefixCls } = useDesign()

const prefixCls = getPrefixCls('app')

const appStore = useAppStore()

const currentSize = computed(() => appStore.getCurrentSize)

const greyMode = computed(() => appStore.getGreyMode)

appStore.initTheme()
</script>

<template>
  <ConfigGlobal :size="currentSize">
    <RouterView :class="greyMode ? `${prefixCls}-grey-mode` : ''" />
    <Teleport to="body">
      <div v-if="copyToastVisible" class="copy-success-toast" role="status" aria-live="polite">
        {{ copyToastMessage }}
      </div>
    </Teleport>
  </ConfigGlobal>
</template>

<style lang="less">
@prefix-cls: ~'@{adminNamespace}-app';

.size {
  width: 100%;
  height: 100%;
}

html,
body {
  padding: 0 !important;
  margin: 0;
  overflow: hidden;
  .size;

  #app {
    .size;
  }
}

.@{prefix-cls}-grey-mode {
  filter: grayscale(100%);
}

.copy-success-toast {
  position: fixed;
  left: 50%;
  top: max(16px, env(safe-area-inset-top, 0px));
  transform: translateX(-50%);
  z-index: 10050;
  padding: 10px 22px;
  border-radius: 12px;
  background: rgba(15, 118, 110, 0.94);
  color: #ecfdf5;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.02em;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.18);
  pointer-events: none;
}
</style>
