import type { RouteMeta } from 'vue-router'
import { ElIcon } from 'element-plus'
import 'element-plus/es/components/icon/style/css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import { useI18n } from '@/hooks/web/useI18n'

function resolveEpIcon(icon?: string) {
  if (!icon) return null
  // 支持：Monitor / ep:Monitor / vi-ep:monitor
  let name = icon
  if (name.startsWith('vi-ep:')) name = name.slice(6)
  if (name.startsWith('ep:')) name = name.slice(3)
  // kebab-case -> PascalCase
  name = name
    .split(/[-_]/)
    .filter(Boolean)
    .map((s) => s.charAt(0).toUpperCase() + s.slice(1))
    .join('')
  return (ElementPlusIconsVue as Recordable)[name] || null
}

export const useRenderMenuTitle = () => {
  const renderMenuTitle = (meta: RouteMeta) => {
    const { t } = useI18n()
    const { title = 'Please set title', icon } = meta
    const EpIcon = resolveEpIcon(icon as string | undefined)

    return (
      <>
        {EpIcon ? (
          <ElIcon class="v-menu__icon" size={20}>
            <EpIcon />
          </ElIcon>
        ) : undefined}
        <span class="v-menu__title overflow-hidden overflow-ellipsis whitespace-nowrap">
          {t(title as string)}
        </span>
      </>
    )
  }

  return {
    renderMenuTitle
  }
}
