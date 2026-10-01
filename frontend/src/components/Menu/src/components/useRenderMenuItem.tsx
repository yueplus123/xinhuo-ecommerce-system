import { ElSubMenu, ElMenuItem } from 'element-plus'
import { unref } from 'vue'
import { hasOneShowingChild } from '../helper'
import { isUrl } from '@/utils/is'
import { useRenderMenuTitle } from './useRenderMenuTitle'
import { pathResolve } from '@/utils/routerHelper'
import { useDesign } from '@/hooks/web/useDesign'

const { getPrefixCls } = useDesign()
const prefixCls = getPrefixCls('submenu')

const { renderMenuTitle } = useRenderMenuTitle()

export const useRenderMenuItem = (menuMode) =>
  // allRouters: AppRouteRecordRaw[] = [],
  {
    const renderMenuItem = (routers: AppRouteRecordRaw[], parentPath = '/') => {
      return routers
        .filter((v) => !v.meta?.hidden)
        .map((v) => {
          const meta = v.meta ?? {}
          const { oneShowingChild, onlyOneChild } = hasOneShowingChild(v.children, v)
          const fullPath = isUrl(v.path) ? v.path : pathResolve(parentPath, v.path)

          const itemMeta = (oneShowingChild ? onlyOneChild?.meta : meta) || meta
          const groupClass = [
            itemMeta.navGroup ? `nav-group-${itemMeta.navGroup}` : '',
            itemMeta.navGroupStart ? 'nav-group-start' : ''
          ]
            .filter(Boolean)
            .join(' ')

          if (
            oneShowingChild &&
            (!onlyOneChild?.children || onlyOneChild?.noShowingChildren) &&
            !meta?.alwaysShow
          ) {
            return (
              <ElMenuItem
                index={onlyOneChild ? pathResolve(fullPath, onlyOneChild.path) : fullPath}
                class={groupClass}
              >
                {{
                  default: () => renderMenuTitle(itemMeta)
                }}
              </ElMenuItem>
            )
          } else {
            return (
              <ElSubMenu
                index={fullPath}
                teleported
                class={groupClass}
                popperClass={unref(menuMode) === 'vertical' ? `${prefixCls}-popper--vertical` : ''}
              >
                {{
                  title: () => renderMenuTitle(meta),
                  default: () => renderMenuItem(v.children!, fullPath)
                }}
              </ElSubMenu>
            )
          }
        })
    }

    return {
      renderMenuItem
    }
  }
