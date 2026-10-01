<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  ElButton,
  ElDescriptions,
  ElDescriptionsItem,
  ElDialog,
  ElDivider,
  ElImage,
  ElMessage,
  ElTabPane,
  ElTable,
  ElTableColumn,
  ElTabs,
  ElTag,
  ElUpload,
  type UploadFile,
  type UploadRawFile
} from 'element-plus'
import { ContentWrap } from '@/components/ContentWrap'
import { useXinhuoAuthStore } from '@/store/modules/xinhuoAuth'
import api from '@/api/xinhuo/client'
import { getUserAvatarUrl } from '@/utils/avatar'
import defaultAvatar from '@/assets/imgs/avatar.jpg'

defineOptions({ name: 'Profile' })

const auth = useXinhuoAuthStore()
const loginLogs = ref<any[]>([])
const logsLoading = ref(false)
const activeTab = ref('info')
const dialogVisible = ref(false)
const avatarLoading = ref(false)
const previewUrl = ref('')
const pendingBase64 = ref('')

const role = computed(() => {
  if (auth.me?.is_superuser) return '管理员'
  if (auth.me?.is_boss) return '老板'
  if (auth.me?.is_ceo) return 'CEO'
  if (auth.me?.is_guest) return '游客/访客'
  return '员工'
})

const roleTags = computed(() => {
  const tags: string[] = []
  if (auth.me?.is_superuser) tags.push('超级管理员')
  if (auth.me?.is_boss) tags.push('老板')
  if (auth.me?.is_ceo) tags.push('CEO')
  if (auth.me?.is_guest) tags.push('游客/访客')
  if (!tags.length) tags.push('员工')
  return tags
})

const avatarUrl = computed(() =>
  getUserAvatarUrl(
    auth.me?.username || auth.me?.id || 'user',
    150,
    auth.me?.avatar_url,
    defaultAvatar
  )
)

function formatLogTime(value: string) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
}

async function loadLoginLogs() {
  logsLoading.value = true
  try {
    const { data } = await api.get('/auth/me/login-logs/')
    loginLogs.value = Array.isArray(data) ? data : []
  } catch (e: any) {
    loginLogs.value = []
    ElMessage.error(e?.response?.data?.detail || e?.message || '加载登录日志失败')
  } finally {
    logsLoading.value = false
  }
}

async function refreshMe() {
  try {
    await auth.fetchMe()
    ElMessage.success('已刷新账号信息')
  } catch (e: any) {
    ElMessage.error(e?.message || '刷新失败')
  }
}

function openAvatarDialog() {
  previewUrl.value = avatarUrl.value
  pendingBase64.value = ''
  dialogVisible.value = true
}

function fileToDataUrl(file: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(new Error('读取图片失败'))
    reader.readAsDataURL(file)
  })
}

async function onAvatarChange(uploadFile: UploadFile) {
  const raw = uploadFile.raw as UploadRawFile | undefined
  if (!raw) return
  if (!raw.type.startsWith('image/')) {
    ElMessage.error('请选择图片文件')
    return
  }
  if (raw.size > 2 * 1024 * 1024) {
    ElMessage.error('头像不能超过 2MB')
    return
  }
  try {
    const dataUrl = await fileToDataUrl(raw)
    pendingBase64.value = dataUrl
    previewUrl.value = dataUrl
  } catch (e: any) {
    ElMessage.error(e?.message || '读取图片失败')
  }
}

async function saveAvatar() {
  if (!pendingBase64.value) {
    ElMessage.warning('请先选择一张图片')
    return
  }
  try {
    avatarLoading.value = true
    const { data } = await api.post('/auth/me/avatar/', { avatar: pendingBase64.value })
    auth.me = data
    dialogVisible.value = false
    ElMessage.success('头像已更新')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '上传失败')
  } finally {
    avatarLoading.value = false
  }
}

async function clearAvatar() {
  try {
    avatarLoading.value = true
    const { data } = await api.delete('/auth/me/avatar/')
    auth.me = data
    dialogVisible.value = false
    ElMessage.success('已恢复默认头像')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '清除失败')
  } finally {
    avatarLoading.value = false
  }
}

onMounted(loadLoginLogs)
</script>

<template>
  <div class="flex flex-wrap gap-16px w-full">
    <ContentWrap title="个人信息" class="w-full max-w-400px">
      <div class="flex justify-center items-center py-8px">
        <div class="profile-avatar" @click="openAvatarDialog">
          <ElImage class="w-150px h-150px rounded-full" :src="avatarUrl" fit="cover" />
          <div class="profile-avatar__mask">更换头像</div>
        </div>
      </div>
      <ElDivider />
      <div class="flex justify-between items-center py-6px">
        <span class="text-[var(--el-text-color-secondary)]">账号</span>
        <span>{{ auth.me?.username || '—' }}</span>
      </div>
      <ElDivider />
      <div class="flex justify-between items-center py-6px">
        <span class="text-[var(--el-text-color-secondary)]">角色</span>
        <div class="flex flex-wrap gap-6px justify-end">
          <ElTag v-for="t in roleTags" :key="t" type="success" size="small">{{ t }}</ElTag>
        </div>
      </div>
      <ElDivider />
      <div class="flex justify-between items-center py-6px">
        <span class="text-[var(--el-text-color-secondary)]">身份</span>
        <span>{{ role }}</span>
      </div>
      <ElDivider />
      <ElButton type="primary" class="w-full mt-8px" @click="refreshMe">刷新信息</ElButton>
    </ContentWrap>

    <ContentWrap title="账号详情" class="flex-1 min-w-320px">
      <ElTabs v-model="activeTab">
        <ElTabPane label="基本资料" name="info">
          <ElDescriptions :column="1" border class="mt-8px">
            <ElDescriptionsItem label="用户名">{{ auth.me?.username || '—' }}</ElDescriptionsItem>
            <ElDescriptionsItem label="角色">{{ role }}</ElDescriptionsItem>
            <ElDescriptionsItem label="超级管理员">
              {{ auth.me?.is_superuser ? '是' : '否' }}
            </ElDescriptionsItem>
            <ElDescriptionsItem label="老板权限">
              {{ auth.me?.is_boss ? '是' : '否' }}
            </ElDescriptionsItem>
            <ElDescriptionsItem label="CEO 权限">
              {{ auth.me?.is_ceo ? '是' : '否' }}
            </ElDescriptionsItem>
            <ElDescriptionsItem label="游客/访客">
              {{ auth.me?.is_guest ? '是' : '否' }}
            </ElDescriptionsItem>
          </ElDescriptions>
        </ElTabPane>
        <ElTabPane label="登录日志" name="logs">
          <ElTable class="mt-8px" :data="loginLogs" v-loading="logsLoading" stripe>
            <ElTableColumn label="登录时间" min-width="180">
              <template #default="{ row }">{{ formatLogTime(row.logged_at) }}</template>
            </ElTableColumn>
            <ElTableColumn label="IP 地址" min-width="140">
              <template #default="{ row }">{{ row.ip || '—' }}</template>
            </ElTableColumn>
          </ElTable>
        </ElTabPane>
      </ElTabs>
    </ContentWrap>
  </div>

  <ElDialog v-model="dialogVisible" title="修改头像" width="480px" destroy-on-close>
    <div class="flex flex-col items-center gap-16px py-8px">
      <ElImage class="w-140px h-140px rounded-full" :src="previewUrl || avatarUrl" fit="cover" />
      <ElUpload
        :auto-upload="false"
        :show-file-list="false"
        accept="image/png,image/jpeg,image/jpg,image/webp"
        :limit="1"
        @change="onAvatarChange"
      >
        <ElButton type="primary" plain>选择图片</ElButton>
      </ElUpload>
      <div class="text-12px text-[var(--el-text-color-secondary)]">支持 jpg / png / webp，不超过 2MB</div>
    </div>
    <template #footer>
      <ElButton type="primary" :loading="avatarLoading" @click="saveAvatar">保存</ElButton>
      <ElButton :loading="avatarLoading" @click="clearAvatar">恢复默认</ElButton>
      <ElButton @click="dialogVisible = false">关闭</ElButton>
    </template>
  </ElDialog>
</template>

<style scoped lang="less">
.profile-avatar {
  position: relative;
  cursor: pointer;
  border-radius: 50%;
  overflow: hidden;

  &__mask {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 14px;
    background: rgb(0 0 0 / 45%);
    opacity: 0;
    transition: opacity 0.2s;
  }

  &:hover .profile-avatar__mask {
    opacity: 1;
  }
}
</style>
