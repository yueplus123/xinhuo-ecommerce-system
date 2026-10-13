import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/store/auth'

// 管理后台路由。history 的 base 为 /admin/，所以这里的路径都不带 /admin 前缀
const page = (title: string, path: string, component: () => Promise<any>, extra: Partial<RouteRecordRaw> = {}) =>
  ({ path, component, meta: { title }, ...extra }) as RouteRecordRaw

const routes: RouteRecordRaw[] = [
  { path: '/login', component: () => import('@/views/LoginPage.vue'), meta: { title: '登录', public: true } },
  {
    path: '/',
    component: () => import('@/layout/AdminLayout.vue'),
    children: [
      page('管理中心', '', () => import('@/views/HomePage.vue')),
      // 商品
      page('平台管理', 'platforms', () => import('@/views/Catalog/PlatformsPage.vue')),
      page('平台工作台', 'platforms/:id(\\d+)', () => import('@/views/Catalog/PlatformWorkbenchPage.vue')),
      page('新增 SKU', 'skus/new', () => import('@/views/Catalog/SkuEditorPage.vue')),
      page('编辑 SKU', 'skus/:id(\\d+)', () => import('@/views/Catalog/SkuEditorPage.vue')),
      page('大厅板块管理', 'hall-blocks', () => import('@/views/Content/HallBlocksPage.vue')),
      // 链接与资料
      page('链接页管理', 'link-pages', () => import('@/views/Content/LinkPagesPage.vue')),
      page('AAA图文远程', 'payment-tutorials', () => import('@/views/Content/PaymentTutorialsPage.vue')),
      page('平台账号管理', 'platform-accounts', () => import('@/views/Content/PlatformAccountsPage.vue')),
      // 资源池
      page('教程池', 'tutorial-pool', () => import('@/views/Pools/TutorialPoolPage.vue')),
      page('话术池', 'phrase-pool', () => import('@/views/Pools/PhrasePoolPage.vue')),
      page('SKU 快捷话术', 'quick-phrases', () => import('@/views/Pools/QuickPhrasePage.vue')),
      page('平台标签池', 'platform-tag-pool', () => import('@/views/Pools/PlatformTagPoolPage.vue')),
      page('渠道池', 'channel-tag-pool', () => import('@/views/Pools/ChannelTagPoolPage.vue')),
      page('美金代付价格池', 'usd-proxy-price-pool', () => import('@/views/Pools/UsdProxyPricePoolPage.vue')),
      // 账号与数据
      page('职员账号', 'users', () => import('@/views/Accounts/UsersPage.vue')),
      page('收款记录管理', 'payment-records', () => import('@/views/Accounts/PaymentRecordsPage.vue')),
      page('订阅提醒管理', 'subscription-reminders', () => import('@/views/Accounts/SubscriptionRemindersPage.vue'))
    ]
  },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHistory('/admin/'),
  routes,
  scrollBehavior: () => ({ left: 0, top: 0 })
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.loaded) await auth.fetchMe()
  if (to.meta.public) {
    // 已登录的超管访问登录页 → 直接进后台
    return auth.isSuperuser && to.path === '/login' ? '/' : true
  }
  if (!auth.isSuperuser) return { path: '/login', query: to.fullPath === '/' ? {} : { redirect: to.fullPath } }
  return true
})

router.afterEach((to) => {
  document.title = `${(to.meta.title as string) || '管理后台'} · 薪火电商管理后台`
})

export default router
