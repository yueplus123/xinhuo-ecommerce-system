<script setup lang="ts">
import ContentWrap from '@/components/ContentWrap.vue'
import ContentCrud, { type ContentField } from './ContentCrud.vue'

defineOptions({ name: 'ManagePlatformAccounts' })

const fields: ContentField[] = [
  { prop: 'name', label: '平台', required: true, width: 160 },
  { prop: 'account', label: '账号', required: true, width: 200 },
  { prop: 'password', label: '密码', required: true, width: 140, masked: true },
  { prop: 'url', label: '网址链接', placeholder: '选填' },
  { prop: 'note', label: '备注', type: 'textarea', placeholder: '选填' }
]
</script>

<template>
  <ContentWrap title="平台账号密码管理">
    <ContentCrud
      content-key="platform-accounts"
      noun="平台账号"
      :fields="fields"
      hint="维护前端「平台账号密码」页的数据来源；密码在列表中打码，编辑时可见"
    />
  </ContentWrap>
</template>
