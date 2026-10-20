import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import type { App } from 'vue'
import { Layout } from '@/utils/routerHelper'
import { NO_RESET_WHITE_LIST } from '@/constants'

export const constantRouterMap: AppRouteRecordRaw[] = [
  {
    path: '/redirect',
    component: Layout,
    name: 'RedirectWrap',
    children: [
      {
        path: '/redirect/:path(.*)',
        name: 'Redirect',
        component: () => import('@/views/Redirect/Redirect.vue'),
        meta: {}
      }
    ],
    meta: { hidden: true, noTagsView: true }
  },
  {
    path: '/login',
    component: () => import('@/views/Login/Login.vue'),
    name: 'Login',
    meta: { hidden: true, title: '登录', noTagsView: true, public: true }
  },
  {
    path: '/404',
    component: () => import('@/views/Error/404.vue'),
    name: 'NoFind',
    meta: { hidden: true, title: '404', noTagsView: true }
  },
  {
    path: '/profile',
    component: Layout,
    name: 'ProfileLayout',
    meta: { hidden: true },
    children: [
      {
        path: '',
        component: () => import('@/views/Xinhuo/ProfilePage.vue'),
        name: 'Profile',
        meta: { title: '个人中心', hidden: true, canTo: true }
      }
    ]
  },
  {
    path: '/data_screen',
    redirect: '/data-screen',
    name: 'DataScreenAlias',
    meta: { hidden: true }
  }
]

export const asyncRouterMap: AppRouteRecordRaw[] = [
  {
    path: '/',
    component: Layout,
    redirect: '/data-screen',
    name: 'XinhuoRoot',
    meta: { hidden: true },
    children: [
      {
        path: 'data-screen',
        component: () => import('@/views/Xinhuo/DataScreenPage.vue'),
        name: 'DataScreen',
        meta: {
          title: '数据大屏',
          icon: 'DataAnalysis',
          affix: true,
          guestAllowed: true,
          navGroup: 1,
          navGroupStart: true
        }
      },
      {
        path: 'hall',
        component: () => import('@/views/Xinhuo/HallPage.vue'),
        name: 'Hall',
        meta: { title: '大厅', icon: 'House', guestAllowed: true, navGroup: 1 }
      },
      {
        // 平台/商品（新版，淘宝样式）：内嵌 public/library.html
        path: 'products',
        component: () => import('@/views/Xinhuo/products/CatalogLibraryPage.vue'),
        name: 'ProductPlatforms',
        meta: { title: '平台/商品', icon: 'Goods', guestAllowed: true, navGroup: 1 }
      },
      {
        // 旧版平台列表，保留备用
        path: 'products/classic',
        component: () => import('@/views/Xinhuo/products/PlatformGridPage.vue'),
        name: 'ProductPlatformsClassic',
        meta: { title: '平台/商品（旧版）', hidden: true, canTo: true, activeMenu: '/products', guestAllowed: true }
      },
      {
        path: 'products/classic/:platformId',
        component: () => import('@/views/Xinhuo/products/BusinessListPage.vue'),
        name: 'PlatformBusinessesClassic',
        meta: { title: '业务商品（旧版）', hidden: true, canTo: true, activeMenu: '/products', guestAllowed: true }
      },
      {
        // 新版平台页：/products/平台ID
        path: 'products/:platformId',
        component: () => import('@/views/Xinhuo/products/CatalogLibraryPage.vue'),
        name: 'PlatformBusinesses',
        meta: {
          title: '业务商品',
          hidden: true,
          canTo: true,
          activeMenu: '/products',
          guestAllowed: true
        }
      },
      {
        path: 'payment-stats',
        component: () => import('@/views/Xinhuo/PaymentStatsPage.vue'),
        name: 'PaymentStats',
        meta: { title: '收款统计', icon: 'Money', navGroup: 1 }
      },
      {
        path: 'subscription-reminders',
        component: () => import('@/views/Xinhuo/SubscriptionRemindersPage.vue'),
        name: 'SubscriptionReminders',
        meta: {
          title: '订阅到期提醒',
          icon: 'Bell',
          navGroup: 2,
          navGroupStart: true
        }
      },
      {
        path: 'nanny-tutorials',
        component: () => import('@/views/Xinhuo/NannyTutorialsPage.vue'),
        name: 'NannyTutorials',
        meta: { title: '教程合计(对客户)', icon: 'Reading', navGroup: 2 }
      },
      {
        path: 'shared-apple-id',
        component: () => import('@/views/Xinhuo/SharedAppleIdPage.vue'),
        name: 'SharedAppleId',
        meta: {
          title: '共享苹果ID',
          icon: 'Iphone',
          navGroup: 3,
          navGroupStart: true
        }
      },
      {
        path: 'fanbox-stats',
        component: () => import('@/views/Xinhuo/FanboxStatsPage.vue'),
        name: 'FanboxStats',
        meta: {
          title: 'fanbox投稿作品统计',
          icon: 'Picture',
          guestAllowed: true,
          navGroup: 3
        }
      },
      {
        path: 'pict-cart',
        component: () => import('@/views/Xinhuo/PictCartPage.vue'),
        name: 'PictCart',
        meta: { title: 'pict加购物车', icon: 'ShoppingCart', navGroup: 3 }
      },
      {
        // 外链菜单：点击直接在新标签页打开 fanbox 账号管理，不进入站内页面
        path: 'fanbox-account-link',
        component: { render: () => null },
        name: 'FanboxAccountLink',
        meta: {
          title: 'fanbox账号管理',
          icon: 'User',
          navGroup: 3,
          noTagsView: true,
          externalUrl: 'https://fanbox.xinhuo.cloud/dashboard'
        }
      },
      {
        path: 'platform-accounts',
        component: () => import('@/views/Xinhuo/PlatformAccountsPage.vue'),
        name: 'PlatformAccounts',
        meta: {
          title: '平台账号密码',
          icon: 'Key',
          navGroup: 4,
          navGroupStart: true
        }
      },
      {
        path: 'common-cards',
        component: () => import('@/views/Xinhuo/CommonCardsShell.vue'),
        name: 'CommonCards',
        redirect: '/common-cards/cards',
        meta: { title: '常用卡', icon: 'Wallet', guestAllowed: true, navGroup: 4 },
        children: [
          {
            path: 'cards',
            component: () => import('@/views/Xinhuo/CommonCardsPage.vue'),
            name: 'CommonCardNumbers',
            meta: {
              title: '常用卡',
              hidden: true,
              canTo: true,
              guestAllowed: true,
              activeMenu: '/common-cards'
            }
          },
          {
            path: 'accounts',
            component: () => import('@/views/Xinhuo/CommonAccountsPage.vue'),
            name: 'CommonAccounts',
            meta: {
              title: '常用号',
              hidden: true,
              canTo: true,
              guestAllowed: true,
              activeMenu: '/common-cards'
            }
          }
        ]
      },
      {
        path: 'payment-tutorials',
        component: () => import('@/views/Xinhuo/TutorialsPage.vue'),
        name: 'PaymentTutorials',
        meta: { title: '远程电脑图文', icon: 'Document', navGroup: 4 }
      },
      {
        path: 'service-monitor',
        component: () => import('@/views/Xinhuo/ServiceMonitorPage.vue'),
        name: 'ServiceMonitor',
        meta: {
          title: '服务监控',
          icon: 'Monitor',
          navGroup: 5,
          navGroupStart: true
        }
      },
      {
        path: 'wechat-bot-data',
        component: () => import('@/views/Xinhuo/WechatBotDataShell.vue'),
        name: 'WechatBotData',
        redirect: '/wechat-bot-data/pixivcoban',
        meta: { title: '微信BOT数据', icon: 'ChatDotRound', navGroup: 5 },
        children: [
          {
            path: ':tableKey',
            component: () => import('@/views/Xinhuo/WechatBotBusinessPage.vue'),
            name: 'WechatBotBusiness',
            meta: {
              title: '微信BOT业务表',
              hidden: true,
              canTo: true,
              activeMenu: '/wechat-bot-data'
            }
          }
        ]
      },
      {
        path: 'material-renewal',
        component: () => import('@/views/Xinhuo/MaterialRenewalPage.vue'),
        name: 'MaterialRenewal',
        meta: { title: '物料续费提醒', icon: 'Calendar', navGroup: 5 }
      },
      {
        path: 'ledger-accounting',
        component: () => import('@/views/Xinhuo/LedgerPage.vue'),
        name: 'LedgerAccounting',
        meta: {
          title: '记账系统',
          icon: 'Notebook',
          requiresCeo: true,
          noCache: true,
          navGroup: 6,
          navGroupStart: true
        }
      },
      {
        path: 'personal/personal-center',
        redirect: '/profile',
        name: 'PersonalCenterRedirect',
        meta: { hidden: true }
      },
      {
        path: 'membership',
        redirect: '/data-screen',
        name: 'MembershipRedirect',
        meta: { hidden: true }
      },
      {
        path: 'renewal-reminders',
        redirect: '/subscription-reminders',
        name: 'RenewalRedirect',
        meta: { hidden: true }
      },
      {
        path: 'customer',
        redirect: '/subscription-reminders',
        name: 'CustomerRedirect',
        meta: { hidden: true }
      },
      {
        path: 'customer/subscription-reminders',
        redirect: '/subscription-reminders',
        name: 'CustomerSubRemindRedirect',
        meta: { hidden: true }
      },
      {
        path: 'customer/nanny-tutorials',
        redirect: '/nanny-tutorials',
        name: 'CustomerNannyRedirect',
        meta: { hidden: true }
      },
      {
        path: 'customer/shared-apple-id',
        redirect: '/shared-apple-id',
        name: 'CustomerAppleRedirect',
        meta: { hidden: true }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  strict: true,
  routes: constantRouterMap as RouteRecordRaw[],
  scrollBehavior: () => ({ left: 0, top: 0 })
})

export const resetRouter = (): void => {
  router.getRoutes().forEach((route) => {
    const { name } = route
    if (name && !NO_RESET_WHITE_LIST.includes(name as string)) {
      router.hasRoute(name) && router.removeRoute(name)
    }
  })
}

export const setupRouter = (app: App<Element>) => {
  app.use(router)
}

export default router
