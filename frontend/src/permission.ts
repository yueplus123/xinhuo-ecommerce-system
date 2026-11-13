import router from './router'
import { useAppStoreWithOut } from '@/store/modules/app'
import type { RouteRecordRaw } from 'vue-router'
import { useTitle } from '@/hooks/web/useTitle'
import { useNProgress } from '@/hooks/web/useNProgress'
import { usePermissionStoreWithOut } from '@/store/modules/permission'
import { usePageLoading } from '@/hooks/web/usePageLoading'
import { NO_REDIRECT_WHITE_LIST } from '@/constants'
import { useUserStoreWithOut } from '@/store/modules/user'
import { useXinhuoAuthStore } from '@/store/modules/xinhuoAuth'
import { isSessionExpired } from '@/auth/session'
import { cloneDeep } from 'lodash-es'
import { asyncRouterMap, constantRouterMap } from '@/router'

const { start, done } = useNProgress()
const { loadStart, loadDone } = usePageLoading()

/** 游客/访客仅可访问这些业务页（个人中心/404 等工具页单独放行） */
const GUEST_UTILITY_PATHS = new Set(['/profile', '/404', '/login'])

function isGuestPathAllowed(path: string) {
  const p = (path || '/').replace(/\/+$/, '') || '/'
  if (GUEST_UTILITY_PATHS.has(p) || p.startsWith('/redirect')) return true
  return (
    p === '/data-screen' ||
    p === '/hall' ||
    p === '/products' ||
    p.startsWith('/products/') ||
    p === '/fanbox-stats' ||
    p === '/common-cards' ||
    p.startsWith('/common-cards/')
  )
}

function filterByRole(routes: AppRouteRecordRaw[], auth: ReturnType<typeof useXinhuoAuthStore>) {
  return routes
    .map((r) => {
      const route = { ...r }
      if (route.children?.length) {
        route.children = filterByRole(route.children, auth)
      }
      return route
    })
    .filter((r) => {
      if (auth.isGuest) {
        if (r.children?.length) return true
        return !!r.meta?.guestAllowed
      }
      if (r.meta?.requiresCeo && !auth.isCeo) return false
      if (r.meta?.requiresSuperuser && !auth.isSuperuser) return false
      return true
    })
}

async function ensureRouters(auth: ReturnType<typeof useXinhuoAuthStore>) {
  const permissionStore = usePermissionStoreWithOut()
  const appStore = useAppStoreWithOut()
  if (permissionStore.getIsAddRouters) return

  appStore.setDynamicRouter(false)
  appStore.setServerDynamicRouter(false)

  const menuRoutes = filterByRole(cloneDeep(asyncRouterMap), auth)
  // 路由表始终完整注册（避免菜单能点但 404）；菜单与权限由 filterByRole / beforeEach 控制
  permissionStore.addRouters = cloneDeep(asyncRouterMap).concat([
    {
      path: '/:path(.*)*',
      redirect: '/404',
      name: '404Page',
      meta: { hidden: true, breadcrumb: false }
    }
  ])
  permissionStore.routers = cloneDeep(constantRouterMap).concat(menuRoutes)
  permissionStore.addRouters.forEach((route) => {
    router.addRoute(route as unknown as RouteRecordRaw)
  })
  permissionStore.setIsAddRouters(true)
}

router.beforeEach(async (to, _from, next) => {
  start()
  // 仅首屏/鉴权阶段显示全页 loading；侧栏切换不再遮罩，避免卡顿感
  const permissionStore = usePermissionStoreWithOut()
  if (!permissionStore.getIsAddRouters) {
    loadStart()
  }

  const pathNorm = (to.path || '/').replace(/\/+$/, '') || '/'
  if (pathNorm === '/data_screen') {
    next({ path: '/data-screen', query: to.query, hash: to.hash, replace: true })
    return
  }

  const userStore = useUserStoreWithOut()
  const auth = useXinhuoAuthStore()

  if (isSessionExpired()) {
    auth.logout()
    userStore.setToken('')
    userStore.setUserInfo(undefined)
    if (!to.meta?.public && NO_REDIRECT_WHITE_LIST.indexOf(to.path) === -1) {
      next({ path: '/login', query: { expired: '1', redirect: to.path } })
      return
    }
  }

  if (!auth.loaded) {
    await auth.fetchMe()
    if (auth.me) {
      userStore.setToken(localStorage.getItem('access_token') || 'xinhuo')
      userStore.setUserInfo({
        username: auth.me.username || '',
        password: ''
      } as any)
    }
  }

  const isPublic = !!to.meta?.public || NO_REDIRECT_WHITE_LIST.indexOf(to.path) !== -1

  if (auth.isAuthenticated) {
    if (to.path === '/login') {
      next({ path: '/data-screen' })
      return
    }

    if (!permissionStore.getIsAddRouters) {
      await ensureRouters(auth)
      next({ ...to, replace: true })
      return
    }

    // 外链菜单的占位路由：不进入站内页面，直接在新标签页打开外链
    if (to.meta?.externalUrl) {
      window.open(String(to.meta.externalUrl), '_blank', 'noopener,noreferrer')
      // 有来源页就留在原地；直接打开该地址（没有来源页）则回到数据大屏
      if (_from.name) next(false)
      else next('/data-screen')
      return
    }

    if (to.meta?.requiresCeo && !auth.isCeo) {
      next('/data-screen')
      return
    }
    if (to.meta?.requiresSuperuser && !auth.isSuperuser) {
      next('/data-screen')
      return
    }
    if (auth.isGuest && !isGuestPathAllowed(to.path)) {
      next('/data-screen')
      return
    }
    next()
  } else if (isPublic) {
    next()
  } else {
    next(`/login?redirect=${encodeURIComponent(to.fullPath)}`)
  }
})

router.afterEach(() => {
  useTitle()
  done()
  loadDone()
})
