<script lang="tsx">
import { computed, defineComponent, unref, PropType } from 'vue'
import { ElMenu, ElScrollbar } from 'element-plus'
import { useAppStore } from '@/store/modules/app'
import { usePermissionStore } from '@/store/modules/permission'
import { useRenderMenuItem } from './components/useRenderMenuItem'
import { useRouter } from 'vue-router'
import { isUrl } from '@/utils/is'
import { useDesign } from '@/hooks/web/useDesign'

const { getPrefixCls } = useDesign()

const prefixCls = getPrefixCls('menu')

export default defineComponent({
  name: 'Menu',
  props: {
    menuSelect: {
      type: Function as PropType<(index: string) => void>,
      default: undefined
    }
  },
  setup(props) {
    const appStore = useAppStore()

    const layout = computed(() => appStore.getLayout)

    const { push, currentRoute } = useRouter()

    const permissionStore = usePermissionStore()

    const menuMode = computed((): 'vertical' | 'horizontal' => {
      // 竖
      const vertical: LayoutType[] = ['classic', 'topLeft', 'cutMenu']

      if (vertical.includes(unref(layout))) {
        return 'vertical'
      } else {
        return 'horizontal'
      }
    })

    /** 扁平化根路由子菜单，去掉「薪火电商」折叠父级 */
    const routers = computed(() => {
      const raw =
        unref(layout) === 'cutMenu' ? permissionStore.getMenuTabRouters : permissionStore.getRouters
      const flat: AppRouteRecordRaw[] = []
      for (const r of raw || []) {
        const isRootWrap =
          r.name === 'XinhuoRoot' ||
          (r.path === '/' && Array.isArray(r.children) && r.children.length > 0)
        if (isRootWrap && r.children?.length) {
          for (const child of r.children) {
            if (child?.meta?.hidden) continue
            const childPath = child.path?.startsWith('/') ? child.path : `/${child.path || ''}`
            flat.push({
              ...child,
              path: childPath
            })
          }
          continue
        }
        if (r?.meta?.hidden) continue
        flat.push(r)
      }
      return flat
    })

    const collapse = computed(() => appStore.getCollapse)

    const uniqueOpened = computed(() => appStore.getUniqueOpened)

    const activeMenu = computed(() => {
      const { meta, path } = unref(currentRoute)
      // if set path, the sidebar will highlight the path you set
      if (meta.activeMenu) {
        return meta.activeMenu as string
      }
      return path
    })

    const menuSelect = (index: string) => {
      if (props.menuSelect) {
        props.menuSelect(index)
      }
      // 自定义事件
      if (isUrl(index)) {
        window.open(index)
      } else {
        push(index)
      }
    }

    const renderMenuWrap = () => {
      if (unref(layout) === 'top') {
        return renderMenu()
      } else {
        return <ElScrollbar>{renderMenu()}</ElScrollbar>
      }
    }

    const renderMenu = () => {
      return (
        <ElMenu
          defaultActive={unref(activeMenu)}
          mode={unref(menuMode)}
          collapse={
            unref(layout) === 'top' || unref(layout) === 'cutMenu' ? false : unref(collapse)
          }
          uniqueOpened={unref(layout) === 'top' ? false : unref(uniqueOpened)}
          backgroundColor="var(--left-menu-bg-color)"
          textColor="var(--left-menu-text-color)"
          activeTextColor="var(--left-menu-text-active-color)"
          popperClass={
            unref(menuMode) === 'vertical'
              ? `${prefixCls}-popper--vertical`
              : `${prefixCls}-popper--horizontal`
          }
          onSelect={menuSelect}
        >
          {{
            default: () => {
              const { renderMenuItem } = useRenderMenuItem(menuMode)
              return renderMenuItem(unref(routers))
            }
          }}
        </ElMenu>
      )
    }

    return () => (
      <div
        id={prefixCls}
        class={[
          `${prefixCls} ${prefixCls}__${unref(menuMode)}`,
          'h-[100%] overflow-hidden flex-col bg-[var(--left-menu-bg-color)]',
          {
            'w-[var(--left-menu-min-width)]': unref(collapse) && unref(layout) !== 'cutMenu',
            'w-[var(--left-menu-max-width)]': !unref(collapse) && unref(layout) !== 'cutMenu'
          }
        ]}
      >
        {renderMenuWrap()}
      </div>
    )
  }
})
</script>

<style lang="less" scoped>
@prefix-cls: ~'@{adminNamespace}-menu';

.@{prefix-cls} {
  position: relative;
  transition: width var(--transition-time-02);
  background-color: var(--left-menu-bg-color);
  padding-top: 6px;

  :deep(.@{elNamespace}-menu) {
    width: 100% !important;
    border-right: none;
    background-color: transparent !important;
    padding: 0 0 12px;

    .v-menu__icon {
      margin-right: 12px;
      vertical-align: middle;
      color: #5c7cfa;
      transition: color 0.15s ease;
      width: 20px !important;
      height: 20px !important;
      font-size: 20px !important;
      flex-shrink: 0;

      svg {
        width: 1em !important;
        height: 1em !important;
      }
    }

    .@{elNamespace}-menu-item,
    .@{elNamespace}-sub-menu__title {
      border-radius: 10px;
      margin: 4px 12px;
      width: calc(100% - 24px);
      height: 44px !important;
      line-height: 44px !important;
      padding: 0 14px !important;
      box-sizing: border-box;
      color: var(--left-menu-text-color) !important;
      background-color: transparent !important;
      font-size: 14px;
      font-weight: 700;
      transition:
        background-color 0.15s ease,
        color 0.15s ease;
    }

    // 侧栏分组：浅色底 + 同组文字色，组间留白
    // 选中态参考 Gutenberg / shadcn：加深同色背景 + 加粗，不改字色以免混淆分组
    .@{elNamespace}-menu-item.nav-group-start,
    .@{elNamespace}-sub-menu.nav-group-start > .@{elNamespace}-sub-menu__title {
      margin-top: 14px !important;
    }

    .@{elNamespace}-menu-item.nav-group-1,
    .@{elNamespace}-sub-menu.nav-group-1 > .@{elNamespace}-sub-menu__title {
      background-color: #eef5ff !important;
      color: #3b5bdb !important;
      .v-menu__icon {
        color: #3b5bdb !important;
      }
    }
    .@{elNamespace}-menu-item.nav-group-1.is-active,
    .@{elNamespace}-menu-item.nav-group-1:hover,
    .@{elNamespace}-sub-menu.nav-group-1.is-active > .@{elNamespace}-sub-menu__title,
    .@{elNamespace}-sub-menu.nav-group-1 > .@{elNamespace}-sub-menu__title:hover {
      background-color: #d0e2ff !important;
      color: #3b5bdb !important;
      box-shadow: inset 3px 0 0 #3b5bdb, inset -3px 0 0 #3b5bdb;
      .v-menu__icon {
        color: #3b5bdb !important;
      }
    }

    .@{elNamespace}-menu-item.nav-group-2,
    .@{elNamespace}-sub-menu.nav-group-2 > .@{elNamespace}-sub-menu__title {
      background-color: #eefbf3 !important;
      color: #2f9e44 !important;
      .v-menu__icon {
        color: #2f9e44 !important;
      }
    }
    .@{elNamespace}-menu-item.nav-group-2.is-active,
    .@{elNamespace}-menu-item.nav-group-2:hover,
    .@{elNamespace}-sub-menu.nav-group-2.is-active > .@{elNamespace}-sub-menu__title,
    .@{elNamespace}-sub-menu.nav-group-2 > .@{elNamespace}-sub-menu__title:hover {
      background-color: #d3f9d8 !important;
      color: #2f9e44 !important;
      box-shadow: inset 3px 0 0 #2f9e44, inset -3px 0 0 #2f9e44;
      .v-menu__icon {
        color: #2f9e44 !important;
      }
    }

    .@{elNamespace}-menu-item.nav-group-3,
    .@{elNamespace}-sub-menu.nav-group-3 > .@{elNamespace}-sub-menu__title {
      background-color: #fff8e8 !important;
      color: #b98900 !important;
      .v-menu__icon {
        color: #b98900 !important;
      }
    }
    .@{elNamespace}-menu-item.nav-group-3.is-active,
    .@{elNamespace}-menu-item.nav-group-3:hover,
    .@{elNamespace}-sub-menu.nav-group-3.is-active > .@{elNamespace}-sub-menu__title,
    .@{elNamespace}-sub-menu.nav-group-3 > .@{elNamespace}-sub-menu__title:hover {
      background-color: #ffe8a3 !important;
      color: #b98900 !important;
      box-shadow: inset 3px 0 0 #b98900, inset -3px 0 0 #b98900;
      .v-menu__icon {
        color: #b98900 !important;
      }
    }

    .@{elNamespace}-menu-item.nav-group-4,
    .@{elNamespace}-sub-menu.nav-group-4 > .@{elNamespace}-sub-menu__title {
      background-color: #e8f7fb !important;
      color: #0c8599 !important;
      .v-menu__icon {
        color: #0c8599 !important;
      }
    }
    .@{elNamespace}-menu-item.nav-group-4.is-active,
    .@{elNamespace}-menu-item.nav-group-4:hover,
    .@{elNamespace}-sub-menu.nav-group-4.is-active > .@{elNamespace}-sub-menu__title,
    .@{elNamespace}-sub-menu.nav-group-4 > .@{elNamespace}-sub-menu__title:hover {
      background-color: #c5f6fa !important;
      color: #0c8599 !important;
      box-shadow: inset 3px 0 0 #0c8599, inset -3px 0 0 #0c8599;
      .v-menu__icon {
        color: #0c8599 !important;
      }
    }

    .@{elNamespace}-menu-item.nav-group-5,
    .@{elNamespace}-sub-menu.nav-group-5 > .@{elNamespace}-sub-menu__title {
      background-color: #f4f6f8 !important;
      color: #495057 !important;
      .v-menu__icon {
        color: #495057 !important;
      }
    }
    .@{elNamespace}-menu-item.nav-group-5.is-active,
    .@{elNamespace}-menu-item.nav-group-5:hover,
    .@{elNamespace}-sub-menu.nav-group-5.is-active > .@{elNamespace}-sub-menu__title,
    .@{elNamespace}-sub-menu.nav-group-5 > .@{elNamespace}-sub-menu__title:hover {
      background-color: #dee2e6 !important;
      color: #495057 !important;
      box-shadow: inset 3px 0 0 #495057, inset -3px 0 0 #495057;
      .v-menu__icon {
        color: #495057 !important;
      }
    }

    .@{elNamespace}-menu-item.nav-group-6,
    .@{elNamespace}-sub-menu.nav-group-6 > .@{elNamespace}-sub-menu__title {
      background-color: #f8f0fc !important;
      color: #9c36b5 !important;
      .v-menu__icon {
        color: #9c36b5 !important;
      }
    }
    .@{elNamespace}-menu-item.nav-group-6.is-active,
    .@{elNamespace}-menu-item.nav-group-6:hover,
    .@{elNamespace}-sub-menu.nav-group-6.is-active > .@{elNamespace}-sub-menu__title,
    .@{elNamespace}-sub-menu.nav-group-6 > .@{elNamespace}-sub-menu__title:hover {
      background-color: #eebefa !important;
      color: #9c36b5 !important;
      box-shadow: inset 3px 0 0 #9c36b5, inset -3px 0 0 #9c36b5;
      .v-menu__icon {
        color: #9c36b5 !important;
      }
    }

    .@{elNamespace}-menu-item.nav-group-1.is-active,
    .@{elNamespace}-menu-item.nav-group-2.is-active,
    .@{elNamespace}-menu-item.nav-group-3.is-active,
    .@{elNamespace}-menu-item.nav-group-4.is-active,
    .@{elNamespace}-menu-item.nav-group-5.is-active,
    .@{elNamespace}-menu-item.nav-group-6.is-active {
      font-weight: 700;
    }

    .@{elNamespace}-sub-menu__icon-arrow {
      color: #adb5bd !important;
      font-size: 12px;
      margin-top: -6px;
      right: 14px;
    }

    // 未分组项：沿用原选中/悬停
    .is-active:not([class*='nav-group-']) {
      & > .@{elNamespace}-sub-menu__title {
        color: var(--left-menu-text-active-color) !important;
        background-color: var(--left-menu-bg-active-color) !important;

        .v-menu__icon {
          color: var(--left-menu-text-active-color);
        }
      }
    }

    .@{elNamespace}-sub-menu:not([class*='nav-group-']) > .@{elNamespace}-sub-menu__title,
    .@{elNamespace}-menu-item:not([class*='nav-group-']) {
      &:hover {
        color: var(--left-menu-text-active-color) !important;
        background-color: var(--left-menu-bg-active-color) !important;

        .v-menu__icon {
          color: var(--left-menu-text-active-color);
        }
      }
    }

    .@{elNamespace}-menu-item.is-active:not([class*='nav-group-']) {
      position: relative;
      color: var(--left-menu-text-active-color) !important;
      background-color: var(--left-menu-bg-active-color) !important;
      font-weight: 600;

      .v-menu__icon {
        color: var(--left-menu-text-active-color);
      }

      &:hover {
        background-color: var(--left-menu-bg-active-color) !important;
      }
    }

    // 子菜单展开区保持透明，子项同样用内嵌圆角
    .@{elNamespace}-menu {
      background-color: transparent !important;

      .@{elNamespace}-sub-menu__title,
      .@{elNamespace}-menu-item:not(.is-active) {
        background-color: transparent !important;
      }

      .@{elNamespace}-menu-item {
        padding-left: 46px !important;
      }
    }
  }

  // 折叠时的最小宽度
  :deep(.@{elNamespace}-menu--collapse) {
    width: var(--left-menu-min-width);

    & > .is-active,
    & > .is-active > .@{elNamespace}-sub-menu__title {
      position: relative;
      background-color: var(--left-menu-collapse-bg-active-color) !important;
    }
  }

  // 折叠动画的时候，就需要把文字给隐藏掉
  :deep(.horizontal-collapse-transition) {
    .@{prefix-cls}__title {
      display: none;
    }
  }

  // 水平菜单
  &__horizontal {
    height: calc(~'var(--top-tool-height)') !important;
    padding-top: 0;

    :deep(.@{elNamespace}-menu--horizontal) {
      height: calc(~'var(--top-tool-height)');
      border-bottom: none;
      padding: 0;
      // 重新设置底部高亮颜色
      & > .@{elNamespace}-sub-menu.is-active {
        .@{elNamespace}-sub-menu__title {
          border-bottom-color: var(--el-color-primary) !important;
        }
      }

      .@{elNamespace}-menu-item,
      .@{elNamespace}-sub-menu__title {
        margin: 0;
        width: auto;
        border-radius: 0;
        height: calc(~'var(--top-tool-height)') !important;
        line-height: calc(~'var(--top-tool-height)') !important;
      }

      .@{elNamespace}-menu-item.is-active {
        position: relative;

        &::after {
          display: none !important;
        }
      }

      .@{prefix-cls}__title {
        /* stylelint-disable-next-line */
        max-height: calc(~'var(--top-tool-height) - 2px') !important;
        /* stylelint-disable-next-line */
        line-height: calc(~'var(--top-tool-height) - 2px');
      }
    }
  }
}
</style>

<style lang="less">
@prefix-cls: ~'@{adminNamespace}-menu-popper';

.@{prefix-cls}--vertical,
.@{prefix-cls}--horizontal {
  // 设置选中时子标题的颜色
  .is-active {
    & > .el-sub-menu__title {
      color: var(--left-menu-text-active-color) !important;
    }
  }

  // 设置子菜单悬停的高亮和背景色
  .el-sub-menu__title,
  .el-menu-item {
    border-radius: 10px;

    &:hover {
      color: var(--left-menu-text-active-color) !important;
      background-color: var(--left-menu-bg-active-color) !important;
    }
  }

  // 设置选中时的高亮背景
  .el-menu-item.is-active {
    position: relative;
    color: var(--left-menu-text-active-color) !important;
    background-color: var(--left-menu-bg-active-color) !important;

    &:hover {
      background-color: var(--left-menu-bg-active-color) !important;
    }
  }
}

@submenu-prefix-cls: ~'@{adminNamespace}-submenu-popper';

// 设置子菜单溢出时滚动样式
.@{submenu-prefix-cls}--vertical {
  max-height: 100%;
  overflow-y: auto;

  &::-webkit-scrollbar {
    width: 6px;
    background-color: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background-color: rgb(144 147 153 / 30%);
    border-radius: 4px;
  }
}
</style>
