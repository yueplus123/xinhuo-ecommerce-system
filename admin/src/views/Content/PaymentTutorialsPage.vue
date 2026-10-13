<script setup lang="ts">
import ContentWrap from '@/components/ContentWrap.vue'
import ContentCrud, { type ContentField } from './ContentCrud.vue'

defineOptions({ name: 'ManagePaymentTutorials' })

const fields: ContentField[] = [
  { prop: 'name', label: '名称', required: true, width: 240 },
  {
    prop: 'detail_url',
    label: '详情链接',
    required: true,
    placeholder: '例如 https://example.com/tutorial（可省略 https://）'
  }
]
</script>

<template>
  <ContentWrap title="AAA图文远程">
    <ContentCrud
      content-key="payment-tutorials"
      noun="教程"
      :fields="fields"
      hint="与「教程池」互相独立；拖动左侧手柄调整顺序"
    />
  </ContentWrap>
</template>
