<script lang="tsx">
import { computed, defineComponent, unref } from 'vue'
import { useAppStore } from '@/store/modules/app'
import { Backtop } from '@/components/Backtop'
import { useRenderLayout } from './components/useRenderLayout'
import { useDesign } from '@/hooks/web/useDesign'

const { getPrefixCls } = useDesign()

const prefixCls = getPrefixCls('layout')

const appStore = useAppStore()

// 是否是移动端
const mobile = computed(() => appStore.getMobile)

// 菜单折叠
const collapse = computed(() => appStore.getCollapse)

const layout = computed(() => appStore.getLayout)

const handleClickOutside = () => {
  appStore.setCollapse(true)
}

const renderLayout = () => {
  const { renderClassic, renderTopLeft, renderTop, renderCutMenu } = useRenderLayout()
  switch (unref(layout)) {
    case 'classic':
      return renderClassic()
    case 'topLeft':
      return renderTopLeft()
    case 'top':
      return renderTop()
    case 'cutMenu':
      return renderCutMenu()
    default:
      break
  }
}

export default defineComponent({
  name: 'Layout',
  setup() {
    // 覆盖本地持久化的旧配置，保证简洁布局生效
    appStore.setBreadcrumb(false)
    appStore.setBreadcrumbIcon(false)
    appStore.setTagsView(false)
    appStore.setTagsViewIcon(false)
    appStore.setScreenfull(false)
    appStore.setSize(false)
    appStore.setLocale(false)
    appStore.setHamburger(true) // 强制显示侧栏收缩按钮（覆盖旧持久化 false）
    appStore.setLogo(true)
    // 手机端默认收起侧栏，靠顶栏汉堡打开
    if (appStore.getMobile) {
      appStore.setCollapse(true)
      appStore.setLayout('classic')
    }

    // 强制应用截图风格：白底 + 浅蓝圆角内嵌选中
    appStore.setTheme({
      elColorPrimary: '#228be6',
      leftMenuBorderColor: '#f1f3f5',
      leftMenuBgColor: '#ffffff',
      leftMenuBgLightColor: '#ffffff',
      leftMenuBgActiveColor: '#eef2ff',
      leftMenuCollapseBgActiveColor: '#eef2ff',
      leftMenuTextColor: '#333333',
      leftMenuTextActiveColor: '#3b5bdb',
      logoTitleTextColor: '#228be6',
      logoBorderColor: '#f1f3f5',
      topHeaderBgColor: '#ffffff',
      topHeaderTextColor: '#333333',
      topHeaderHoverColor: '#f8f9fa',
      topToolBorderColor: '#f1f3f5'
    })
    appStore.setCssVarTheme()

    return () => (
      <section class={[prefixCls, `${prefixCls}__${layout.value}`, 'w-[100%] h-[100%] relative']}>
        {mobile.value && !collapse.value ? (
          <div
            class="absolute top-0 left-0 w-full h-full opacity-30 z-99 bg-[var(--el-color-black)]"
            onClick={handleClickOutside}
          ></div>
        ) : undefined}

        {renderLayout()}

        <Backtop></Backtop>
      </section>
    )
  }
})
</script>

<style lang="less" scoped>
@prefix-cls: ~'@{adminNamespace}-layout';

.@{prefix-cls} {
  background-color: var(--app-content-bg-color);
}
</style>
