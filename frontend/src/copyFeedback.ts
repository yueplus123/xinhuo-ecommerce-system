import { ref } from 'vue'

export const copyToastVisible = ref(false)
export const copyToastMessage = ref('复制成功')

let hideTimer: ReturnType<typeof setTimeout> | null = null

/** 顶部飘窗提示，默认「复制成功」，约 2 秒自动消失 */
export function showCopySuccess(message = '复制成功') {
  copyToastMessage.value = message
  copyToastVisible.value = true
  if (hideTimer) clearTimeout(hideTimer)
  hideTimer = setTimeout(() => {
    copyToastVisible.value = false
    hideTimer = null
  }, 2000)
}
