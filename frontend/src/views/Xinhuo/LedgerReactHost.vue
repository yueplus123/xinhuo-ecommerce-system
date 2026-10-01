<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref } from 'vue'
import { ContentWrap } from '@/components/ContentWrap'

defineOptions({ name: 'LedgerAccounting' })

const rootEl = ref<HTMLElement | null>(null)
const status = ref('准备加载…')
const mountError = ref('')
let reactMounted = false

async function ensureMounted(attempt = 0) {
  await nextTick()
  const el = rootEl.value
  if (!el) {
    if (attempt < 20) {
      status.value = `等待挂载点…(${attempt + 1})`
      window.setTimeout(() => void ensureMounted(attempt + 1), 50)
    } else {
      mountError.value = '找不到记账挂载节点，请刷新页面'
      status.value = ''
    }
    return
  }
  if (reactMounted) {
    status.value = ''
    return
  }
  status.value = '正在加载记账模块…'
  try {
    const { mountLedgerApp } = await import('@/ledger-app/mount.tsx')
    mountLedgerApp(el)
    reactMounted = true
    mountError.value = ''
    status.value = ''
  } catch (e: any) {
    mountError.value = e?.message || String(e) || '记账模块加载失败'
    status.value = ''
    console.error('[LedgerReactHost] mount failed', e)
  }
}

async function ensureUnmounted() {
  if (!reactMounted) return
  try {
    const { unmountLedgerApp } = await import('@/ledger-app/mount.tsx')
    unmountLedgerApp()
  } catch (e) {
    console.error('[LedgerReactHost] unmount failed', e)
  } finally {
    reactMounted = false
  }
}

onMounted(() => {
  void ensureMounted()
})
onUnmounted(() => {
  void ensureUnmounted()
})
</script>

<template>
  <ContentWrap title="记账系统">
    <p v-if="mountError" class="ledger-mount-error">{{ mountError }}</p>
    <p v-else-if="status" class="ledger-mounting">{{ status }}</p>
    <div ref="rootEl" class="ledger-react-root" />
  </ContentWrap>
</template>

<style scoped>
.ledger-react-root {
  width: 100%;
  min-height: 480px;
}
.ledger-mount-error {
  margin: 0 0 12px;
  color: #dc2626;
  font-size: 14px;
}
.ledger-mounting {
  margin: 0 0 12px;
  color: #64748b;
  font-size: 14px;
}
</style>
