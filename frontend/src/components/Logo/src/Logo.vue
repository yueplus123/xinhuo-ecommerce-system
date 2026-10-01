<script setup lang="ts">
import { computed, onMounted, ref, unref, watch } from 'vue'
import { useAppStore } from '@/store/modules/app'
import { useDesign } from '@/hooks/web/useDesign'

const { getPrefixCls } = useDesign()

const prefixCls = getPrefixCls('logo')

const appStore = useAppStore()

const showFull = ref(true)

const title = computed(() => appStore.getTitle)

/** 折叠时用简称，避免去掉图标后侧栏顶栏空白 */
const shortTitle = computed(() => {
  const t = String(title.value || '薪火')
  return t.slice(0, 2)
})

const layout = computed(() => appStore.getLayout)

const collapse = computed(() => appStore.getCollapse)

onMounted(() => {
  if (unref(collapse) && unref(layout) === 'classic') showFull.value = false
})

watch(
  () => collapse.value,
  (collapsed: boolean) => {
    if (unref(layout) === 'topLeft' || unref(layout) === 'cutMenu') {
      showFull.value = true
      return
    }
    showFull.value = !collapsed
  }
)

watch(
  () => layout.value,
  (layoutMode) => {
    if (layoutMode === 'top' || layoutMode === 'cutMenu' || layoutMode === 'topLeft') {
      showFull.value = true
    } else {
      showFull.value = !unref(collapse)
    }
  }
)
</script>

<template>
  <!-- 对齐 vue-element-admin：侧栏 Logo 区 width:100% + 居中占满顶栏 -->
  <div :class="[prefixCls, 'xinhuo-logo-wrap']">
    <router-link
      :class="[
        `${prefixCls}__link`,
        layout !== 'classic' ? `${prefixCls}__Top` : '',
        'xinhuo-logo-link'
      ]"
      to="/"
      :title="title"
    >
      <h1
        :class="[
          'xinhuo-logo-title',
          showFull ? 'is-full' : 'is-collapsed',
          {
            'is-classic': layout === 'classic',
            'is-top': layout === 'topLeft' || layout === 'top' || layout === 'cutMenu'
          }
        ]"
      >
        {{ showFull ? title : shortTitle }}
      </h1>
    </router-link>
  </div>
</template>

<style lang="less" scoped>
.xinhuo-logo-wrap {
  width: 100%;
  height: var(--logo-height);
  overflow: hidden;
}

.xinhuo-logo-link {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  padding: 0 8px;
  text-decoration: none;
  box-sizing: border-box;
}

.xinhuo-logo-title {
  margin: 0;
  width: 100%;
  text-align: center;
  font-weight: 700;
  letter-spacing: 0.12em;
  line-height: var(--logo-height);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  user-select: none;
  font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', Avenir, Helvetica, Arial, sans-serif;

  &.is-full {
    font-size: 20px;
  }

  &.is-collapsed {
    font-size: 16px;
    letter-spacing: 0;
  }

  &.is-classic {
    color: #059669;
  }

  &.is-top {
    color: #059669;
  }
}
</style>
