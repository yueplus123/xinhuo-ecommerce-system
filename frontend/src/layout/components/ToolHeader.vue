<script lang="tsx">
import { defineComponent, computed } from 'vue'
import { Collapse } from '@/components/Collapse'
import { LocaleDropdown } from '@/components/LocaleDropdown'
import { SizeDropdown } from '@/components/SizeDropdown'
import { UserInfo } from '@/components/UserInfo'
import { ThemeToggle } from '@/components/ThemeToggle'
import { Screenfull } from '@/components/Screenfull'
import { Breadcrumb } from '@/components/Breadcrumb'
import { useAppStore } from '@/store/modules/app'
import { useDesign } from '@/hooks/web/useDesign'

const { getPrefixCls, variables } = useDesign()

const prefixCls = getPrefixCls('tool-header')

const appStore = useAppStore()

const breadcrumb = computed(() => appStore.getBreadcrumb)
const hamburger = computed(() => appStore.getHamburger)
const screenfull = computed(() => appStore.getScreenfull)
const size = computed(() => appStore.getSize)
const layout = computed(() => appStore.getLayout)
const locale = computed(() => appStore.getLocale)
const mobile = computed(() => appStore.getMobile)
const title = computed(() => appStore.getTitle)

export default defineComponent({
  name: 'ToolHeader',
  setup() {
    return () => {
      // 手机端必须始终显示菜单按钮（不受持久化 hamburger=false 影响）
      const showCollapse =
        (mobile.value || hamburger.value) && layout.value !== 'cutMenu' && layout.value !== 'top'

      return (
        <div
          id={`${variables.namespace}-tool-header`}
          class={[
            prefixCls,
            'h-[var(--top-tool-height)] relative px-[var(--top-tool-p-x)] flex items-center justify-between'
          ]}
        >
          <div class="h-full flex items-center min-w-0 flex-1">
            {showCollapse ? (
              <Collapse color="var(--top-header-text-color)"></Collapse>
            ) : undefined}
            {mobile.value ? (
              <span class="mobile-header-brand truncate">{title.value || '薪火电商'}</span>
            ) : breadcrumb.value ? (
              <Breadcrumb class="<md:hidden"></Breadcrumb>
            ) : undefined}
          </div>
          <div class="h-full flex items-center shrink-0">
            {screenfull.value ? (
              <Screenfull class="custom-hover" color="var(--top-header-text-color)"></Screenfull>
            ) : undefined}
            {size.value ? (
              <SizeDropdown class="custom-hover" color="var(--top-header-text-color)"></SizeDropdown>
            ) : undefined}
            {locale.value ? (
              <LocaleDropdown
                class="custom-hover"
                color="var(--top-header-text-color)"
              ></LocaleDropdown>
            ) : undefined}
            <ThemeToggle color="var(--top-header-text-color)"></ThemeToggle>
            <UserInfo></UserInfo>
          </div>
        </div>
      )
    }
  }
})
</script>

<style lang="less" scoped>
@prefix-cls: ~'@{adminNamespace}-tool-header';

.@{prefix-cls} {
  transition: left var(--transition-time-02);
}

.mobile-header-brand {
  margin-left: 4px;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #059669;
  line-height: 1;
}
</style>
