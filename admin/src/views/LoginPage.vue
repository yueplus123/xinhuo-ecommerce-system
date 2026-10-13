<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElButton, ElForm, ElFormItem, ElInput, ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { formatRequestError } from '@/utils/format'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const form = reactive({ username: '', password: '' })
const loading = ref(false)

async function submit() {
  if (!form.username.trim() || !form.password) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    const redirect = String(route.query.redirect || '/')
    await router.replace(redirect.startsWith('/') ? redirect : '/')
  } catch (e: any) {
    ElMessage.error(e?.response?.status === 401 ? '账号或密码错误' : formatRequestError(e, '登录失败'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login">
    <div class="box">
      <div class="brand">薪火电商</div>
      <div class="sub">管理后台</div>
      <ElForm label-position="top" @submit.prevent="submit">
        <ElFormItem label="账号">
          <ElInput v-model="form.username" autocomplete="username" autofocus />
        </ElFormItem>
        <ElFormItem label="密码">
          <ElInput v-model="form.password" type="password" show-password autocomplete="current-password" @keyup.enter="submit" />
        </ElFormItem>
        <ElButton type="primary" :loading="loading" style="width: 100%" @click="submit">登录</ElButton>
      </ElForm>
      <div class="tip">仅超级管理员可登录。职员请使用职员端入口。</div>
    </div>
  </div>
</template>

<style scoped>
.login {
  display: flex;
  min-height: 100vh;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #eef3fb 0%, #f7f9fc 100%);
}
.box {
  width: 360px;
  padding: 36px 32px 28px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 30px rgb(0 0 0 / 8%);
}
.brand {
  font-size: 24px;
  font-weight: 700;
  color: var(--el-color-primary);
  text-align: center;
}
.sub {
  margin: 4px 0 24px;
  color: var(--el-text-color-secondary);
  text-align: center;
}
.tip {
  margin-top: 16px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  text-align: center;
}
</style>
