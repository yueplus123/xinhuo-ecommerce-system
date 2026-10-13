<script setup lang="ts">
// 后台外壳：顶栏 + 左侧固定导航 + 内容区。导航清单来自 ./nav.ts（与管理中心首页共用）。
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElButton, ElIcon } from 'element-plus'
import * as Icons from '@element-plus/icons-vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { NAV_GROUPS, activeNavPath } from './nav'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const active = computed(() => (route.path === '/' ? '/' : activeNavPath(route.path)))
const icon = (name: string) => (Icons as any)[name] || Icons.Menu

// 窄屏：侧栏默认收起，点汉堡按钮滑出；选了菜单后自动收起
const NARROW = 900
const narrow = ref(window.innerWidth < NARROW)
const open = ref(false)
const onResize = () => {
  narrow.value = window.innerWidth < NARROW
  if (!narrow.value) open.value = false
}
onMounted(() => window.addEventListener('resize', onResize))
onUnmounted(() => window.removeEventListener('resize', onResize))
watch(() => route.path, () => (open.value = false))

function go(path: string) {
  if (route.path !== path) router.push(path)
}
function logout() {
  auth.logout()
  router.replace('/login')
}
</script>

<template>
  <div class="shell">
    <header class="bar">
      <div class="left">
        <ElButton v-if="narrow" link class="burger" @click="open = !open">
          <ElIcon :size="22"><Icons.Menu /></ElIcon>
        </ElButton>
        <span class="brand" @click="go('/')">薪火电商 · 管理后台</span>
      </div>
      <div class="right">
        <span class="user">{{ auth.me?.username }}</span>
        <ElButton size="small" @click="logout">退出</ElButton>
      </div>
    </header>

    <div class="body">
      <div v-if="narrow && open" class="mask" @click="open = false" />
      <aside class="side" :class="{ narrow, open }">
        <nav>
          <div class="item home" :class="{ on: active === '/' }" @click="go('/')">
            <ElIcon><Icons.HomeFilled /></ElIcon><span>管理中心</span>
          </div>
          <div v-for="g in NAV_GROUPS" :key="g.name" class="group">
            <div class="group-name">{{ g.name }}</div>
            <div
              v-for="it in g.items"
              :key="it.path"
              class="item"
              :class="{ on: active === it.path }"
              :title="it.desc"
              @click="go(it.path)"
            >
              <ElIcon><component :is="icon(it.icon)" /></ElIcon><span>{{ it.title }}</span>
            </div>
          </div>
        </nav>
      </aside>

      <main class="main">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
.shell {
  min-height: 100vh;
  background: #f4f6fa;
}
.bar {
  position: fixed;
  top: 0;
  right: 0;
  left: 0;
  z-index: 30;
  display: flex;
  height: 52px;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: #fff;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.left,
.right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.brand {
  font-weight: 700;
  color: var(--el-color-primary);
  cursor: pointer;
}
.user {
  font-size: 13px;
  color: var(--el-text-color-regular);
}
.body {
  padding-top: 52px;
}
.side {
  position: fixed;
  top: 52px;
  bottom: 0;
  left: 0;
  z-index: 20;
  width: 210px;
  padding: 10px 0 24px;
  overflow-y: auto;
  background: #fff;
  border-right: 1px solid var(--el-border-color-lighter);
}
.side.narrow {
  transform: translateX(-100%);
  transition: transform 0.2s;
  box-shadow: 2px 0 12px rgb(0 0 0 / 12%);
}
.side.narrow.open {
  transform: translateX(0);
}
.mask {
  position: fixed;
  inset: 52px 0 0;
  z-index: 15;
  background: rgb(0 0 0 / 30%);
}
.group {
  margin-top: 8px;
}
.group-name {
  padding: 10px 20px 4px;
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}
.item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 20px;
  font-size: 14px;
  color: var(--el-text-color-regular);
  cursor: pointer;
  border-left: 3px solid transparent;
  user-select: none;
}
.item:hover {
  background: var(--el-fill-color-light);
}
.item.on {
  font-weight: 600;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  border-left-color: var(--el-color-primary);
}
.main {
  padding: 20px 24px 40px 234px;
  max-width: 1500px;
}
@media (max-width: 899px) {
  .main {
    padding: 16px 14px 32px;
  }
}
</style>
