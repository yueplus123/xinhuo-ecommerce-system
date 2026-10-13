<script setup lang="ts">
// 链接页管理：共享苹果ID / pict加购物车 / fanbox统计 / 服务监控——都只是「名称 + 链接 + 启用」，合并在一页用标签切换
import { ref } from 'vue'
import { ElTabPane, ElTabs } from 'element-plus'
import ContentWrap from '@/components/ContentWrap.vue'
import ContentCrud, { type ContentField } from './ContentCrud.vue'
import type { ContentKey } from '@/api/modules/content'

defineOptions({ name: 'ManageLinkPages' })

const fields = (linkLabel: string): ContentField[] => [
  { prop: 'name', label: '页面名称', required: true, width: 220 },
  {
    prop: 'share_url',
    label: linkLabel,
    required: true,
    placeholder: '例如 https://example.com/page（可省略 https://）'
  },
  { prop: 'is_active', label: '状态', type: 'switch', width: 90 }
]

const tabs: Array<{ name: ContentKey; label: string; noun: string; link: string; hint: string }> = [
  {
    name: 'shared-apple-id-pages',
    label: '共享苹果ID',
    noun: '分享页',
    link: '分享页链接',
    hint: '前端「共享苹果ID」页展示；可建多条并启用/停用'
  },
  {
    name: 'pict-cart-pages',
    label: 'pict加购物车',
    noun: '页面',
    link: '页面链接',
    hint: '前端「pict加购物车」页嵌入第一条已启用的链接'
  },
  {
    name: 'fanbox-stats-pages',
    label: 'fanbox投稿统计',
    noun: '页面',
    link: '页面链接',
    hint: '前端「fanbox投稿作品统计」页展示（游客可见）'
  },
  {
    name: 'service-monitor-pages',
    label: '服务监控',
    noun: '页面',
    link: '页面链接',
    hint: '前端「服务监控」页嵌入的 Uptime Kuma / 状态页链接'
  }
]

const active = ref<ContentKey>('shared-apple-id-pages')
</script>

<template>
  <ContentWrap title="链接页管理">
    <ElTabs v-model="active">
      <ElTabPane v-for="t in tabs" :key="t.name" :label="t.label" :name="t.name" lazy>
        <ContentCrud
          v-if="active === t.name"
          :content-key="t.name"
          :noun="t.noun"
          :fields="fields(t.link)"
          :hint="t.hint"
        />
      </ElTabPane>
    </ElTabs>
  </ContentWrap>
</template>
