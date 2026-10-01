<script setup lang="ts">
import { ElDropdown, ElDropdownMenu, ElDropdownItem, ElMessage } from 'element-plus'
import { useI18n } from '@/hooks/web/useI18n'
import { useDesign } from '@/hooks/web/useDesign'
import LockDialog from './components/LockDialog.vue'
import { ref, computed, nextTick } from 'vue'
import LockPage from './components/LockPage.vue'
import { useLockStore } from '@/store/modules/lock'
import { useUserStore } from '@/store/modules/user'
import { useXinhuoAuthStore } from '@/store/modules/xinhuoAuth'
import { getUserAvatarUrl } from '@/utils/avatar'
import defaultAvatar from '@/assets/imgs/avatar.jpg'
import { useRouter } from 'vue-router'

const { push } = useRouter()

const userStore = useUserStore()
const xinhuoAuth = useXinhuoAuthStore()

const lockStore = useLockStore()

const getIsLock = computed(() => lockStore.getLockInfo?.isLock ?? false)

const avatarUrl = computed(() =>
  getUserAvatarUrl(
    xinhuoAuth.me?.username || userStore.getUserInfo?.username || 'user',
    128,
    xinhuoAuth.me?.avatar_url,
    defaultAvatar
  )
)

const { getPrefixCls } = useDesign()

const prefixCls = getPrefixCls('user-info')

const { t } = useI18n()

const dialogVisible = ref<boolean>(false)

const lockScreen = () => {
  dialogVisible.value = true
}

const loginOut = () => {
  userStore.logoutConfirm()
}

async function goProfile() {
  // 等下拉菜单关闭后再跳转，避免 ElDropdown 吞掉点击
  await nextTick()
  try {
    await push({ name: 'Profile' })
  } catch {
    try {
      await push('/profile')
    } catch (e: any) {
      ElMessage.error(e?.message || '无法打开个人中心')
    }
  }
}

async function onCommand(cmd: string | number) {
  if (cmd === 'profile') {
    await goProfile()
    return
  }
  if (cmd === 'lock') {
    lockScreen()
    return
  }
  if (cmd === 'logout') {
    loginOut()
  }
}
</script>

<template>
  <ElDropdown class="custom-hover" :class="prefixCls" trigger="click" @command="onCommand">
    <div class="flex items-center">
      <img
        :src="avatarUrl"
        alt=""
        class="w-[calc(var(--logo-height)-25px)] rounded-[50%]"
      />
      <span class="<lg:hidden text-14px pl-[5px] text-[var(--top-header-text-color)]">{{
        userStore.getUserInfo?.username
      }}</span>
    </div>
    <template #dropdown>
      <ElDropdownMenu>
        <ElDropdownItem command="profile">
          {{ t('router.personalCenter') }}
        </ElDropdownItem>
        <ElDropdownItem divided command="lock">{{ t('lock.lockScreen') }}</ElDropdownItem>
        <ElDropdownItem divided command="logout">{{ t('common.loginOut') }}</ElDropdownItem>
      </ElDropdownMenu>
    </template>
  </ElDropdown>

  <LockDialog v-if="dialogVisible" v-model="dialogVisible" />
  <teleport to="body">
    <transition name="fade-bottom" mode="out-in">
      <LockPage v-if="getIsLock" />
    </transition>
  </teleport>
</template>

<style scoped lang="less">
.fade-bottom-enter-active,
.fade-bottom-leave-active {
  transition:
    opacity 0.25s,
    transform 0.3s;
}

.fade-bottom-enter-from {
  opacity: 0;
  transform: translateY(-10%);
}

.fade-bottom-leave-to {
  opacity: 0;
  transform: translateY(10%);
}
</style>
