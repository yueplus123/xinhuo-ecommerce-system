import { watch, ref } from 'vue'
import { isString } from '@/utils/is'

/** 浏览器标签固定标题，不随路由变化 */
export const APP_DOCUMENT_TITLE = '薪火电商管理系统'

export const useTitle = (_newTitle?: string) => {
  const title = ref(APP_DOCUMENT_TITLE)

  watch(
    title,
    (n, o) => {
      if (isString(n) && n !== o && document) {
        document.title = n
      }
    },
    { immediate: true }
  )

  // 路由切换时仍强制写回固定标题
  if (document && document.title !== APP_DOCUMENT_TITLE) {
    document.title = APP_DOCUMENT_TITLE
  }

  return title
}
