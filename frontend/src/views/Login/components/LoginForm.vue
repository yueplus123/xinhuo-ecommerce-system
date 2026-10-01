<script setup lang="tsx">
import { reactive, ref, watch, onMounted, unref } from 'vue'
import { Form, FormSchema } from '@/components/Form'
import { useI18n } from '@/hooks/web/useI18n'
import { ElCheckbox, ElAlert } from 'element-plus'
import { useForm } from '@/hooks/web/useForm'
import { useAppStore } from '@/store/modules/app'
import { usePermissionStore } from '@/store/modules/permission'
import { useRouter } from 'vue-router'
import type { RouteLocationNormalizedLoaded, RouteRecordRaw } from 'vue-router'
import type { UserType } from '@/api/login/types'
import { useValidator } from '@/hooks/web/useValidator'
import { useUserStore } from '@/store/modules/user'
import { BaseButton } from '@/components/Button'
import { useXinhuoAuthStore } from '@/store/modules/xinhuoAuth'
import { cloneDeep } from 'lodash-es'
import { asyncRouterMap, constantRouterMap } from '@/router'

const { required } = useValidator()

const appStore = useAppStore()

const userStore = useUserStore()

const permissionStore = usePermissionStore()

const { currentRoute, addRoute, push } = useRouter()

const { t } = useI18n()

const rules = {
  username: [required()],
  password: [required()]
}

const schema = reactive<FormSchema[]>([
  {
    field: 'title',
    colProps: {
      span: 24
    },
    formItemProps: {
      slots: {
        default: () => {
          return <h2 class="text-2xl font-bold text-center w-[100%]">{t('login.login')}</h2>
        }
      }
    }
  },
  {
    field: 'username',
    label: t('login.username'),
    component: 'Input',
    colProps: {
      span: 24
    },
    componentProps: {
      placeholder: '用户名'
    }
  },
  {
    field: 'password',
    label: t('login.password'),
    component: 'InputPassword',
    colProps: {
      span: 24
    },
    componentProps: {
      style: {
        width: '100%'
      },
      placeholder: '密码',
      onKeydown: (_e: any) => {
        if (_e.key === 'Enter') {
          _e.stopPropagation()
          signIn()
        }
      }
    }
  },
  {
    field: 'error',
    colProps: {
      span: 24
    },
    formItemProps: {
      slots: {
        default: () => {
          if (!unref(errorMessage)) return null
          return (
            <ElAlert
              title={unref(errorMessage)}
              type="error"
              show-icon
              closable
              onClose={() => {
                errorMessage.value = ''
              }}
            />
          )
        }
      }
    }
  },
  {
    field: 'tool',
    colProps: {
      span: 24
    },
    formItemProps: {
      slots: {
        default: () => {
          return (
            <div class="flex items-center w-[100%]">
              <ElCheckbox v-model={remember.value} label={t('login.remember')} size="small" />
            </div>
          )
        }
      }
    }
  },
  {
    field: 'login',
    colProps: {
      span: 24
    },
    formItemProps: {
      slots: {
        default: () => {
          return (
            <div class="w-[100%]">
              <BaseButton
                loading={loading.value}
                type="primary"
                class="w-[100%]"
                onClick={signIn}
              >
                {t('login.login')}
              </BaseButton>
            </div>
          )
        }
      }
    }
  }
])

const remember = ref(userStore.getRememberMe)

const errorMessage = ref('')

const loading = ref(false)

/** 防止回车 + 按钮重复触发把第一次登录的 token 清掉 */
let signingIn = false

const initLoginInfo = () => {
  const savedUsername = userStore.getLoginInfo
  if (savedUsername && unref(remember)) {
    setValues({ username: savedUsername })
  }
}
onMounted(() => {
  initLoginInfo()
  if (currentRoute.value.query.expired === '1') {
    errorMessage.value = '登录已过期（超过 12 小时），请重新登录。'
  }
})

const { formRegister, formMethods } = useForm()
const { getFormData, getElFormExpose, setValues } = formMethods

const redirect = ref<string>('')

watch(
  () => currentRoute.value,
  (route: RouteLocationNormalizedLoaded) => {
    redirect.value = route?.query?.redirect as string
  },
  {
    immediate: true
  }
)

watch(
  () => remember.value,
  (newVal) => {
    userStore.setRememberMe(newVal)
    if (!newVal) {
      userStore.setLoginInfo(undefined)
    }
  }
)

function applyLoginSession(auth: ReturnType<typeof useXinhuoAuthStore>, username: string) {
  if (unref(remember)) {
    userStore.setLoginInfo(username)
  } else {
    userStore.setLoginInfo(undefined)
  }
  userStore.setRememberMe(unref(remember))
  userStore.setToken(localStorage.getItem('access_token') || 'xinhuo')
  userStore.setUserInfo({
    username: auth.me?.username || username,
    password: ''
  } as any)

  appStore.setDynamicRouter(false)
  appStore.setServerDynamicRouter(false)

  const filterByRole = (routes: AppRouteRecordRaw[]): AppRouteRecordRaw[] =>
    routes
      .map((r) => {
        const route = { ...r }
        if (route.children?.length) route.children = filterByRole(route.children)
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

  const menuRoutes = filterByRole(cloneDeep(asyncRouterMap))
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
    addRoute(route as RouteRecordRaw)
  })
  permissionStore.setIsAddRouters(true)
}

// 登录（对接 Django JWT）
const signIn = async () => {
  if (signingIn || loading.value) return
  const formRef = await getElFormExpose()
  if (!formRef) return

  // 不要用 async callback 形式的 validate，Element Plus 下会丢异常 / 重复触发
  try {
    await formRef.validate()
  } catch {
    return
  }

  signingIn = true
  loading.value = true
  errorMessage.value = ''
  const formData = await getFormData<UserType>()
  const auth = useXinhuoAuthStore()

  try {
    await auth.login(formData.username, formData.password)
    applyLoginSession(auth, formData.username)
    await push({ path: redirect.value || '/data-screen' })
  } catch (error: any) {
    // 已有 token 则视为登录成功（兼容 /me 偶发失败）
    if (localStorage.getItem('access_token')) {
      if (!auth.me) {
        await auth.fetchMe()
        if (!auth.me) {
          auth.$patch({ me: { username: formData.username }, loaded: true })
        }
      }
      applyLoginSession(auth, formData.username)
      await push({ path: redirect.value || '/data-screen' })
      return
    }

    const status = error?.response?.status
    const detail =
      error?.response?.data?.detail || error?.response?.data?.non_field_errors?.[0]
    const msg = String(error?.message || '')
    const code = String(error?.code || '')
    if (msg === 'SESSION_EXPIRED') {
      errorMessage.value = '登录已过期，请重新输入密码登录'
    } else if (status === 401) {
      errorMessage.value = detail || '用户名或密码错误'
    } else if (status === 500) {
      errorMessage.value = detail || '服务器内部错误，请确认后端正常运行'
    } else if (
      !error?.response ||
      status === 502 ||
      status === 503 ||
      status === 504 ||
      code === 'ERR_NETWORK' ||
      msg.toLowerCase().includes('network')
    ) {
      errorMessage.value = '无法连接服务器，请确认后端已启动后重试'
    } else {
      errorMessage.value = detail || msg || '登录失败，请检查用户名和密码'
    }
  } finally {
    loading.value = false
    signingIn = false
  }
}
</script>

<template>
  <Form
    :schema="schema"
    :rules="rules"
    label-position="top"
    hide-required-asterisk
    size="large"
    class="dark:(border-1 border-[var(--el-border-color)] border-solid)"
    @register="formRegister"
  />
</template>
