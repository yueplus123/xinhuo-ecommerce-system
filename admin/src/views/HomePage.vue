<script setup lang="ts">
// 管理中心：所有后台管理功能的统一入口（仅超级管理员）。
// 功能清单与左侧导航共用 layout/nav.ts，新增功能只改那一处。
import { computed, ref } from 'vue'
import { ElEmpty, ElIcon, ElInput } from 'element-plus'
import { useRouter } from 'vue-router'
import ContentWrap from '@/components/ContentWrap.vue'
import * as Icons from '@element-plus/icons-vue'
import { NAV_GROUPS } from '@/layout/nav'

defineOptions({ name: 'ManageHome' })

const GROUPS = NAV_GROUPS

const router = useRouter()
const q = ref('')
const groups = computed(() => {
  const k = q.value.trim().toLowerCase()
  if (!k) return GROUPS
  return GROUPS.map((g) => ({
    ...g,
    items: g.items.filter((i) => `${i.title}${i.desc}`.toLowerCase().includes(k))
  })).filter((g) => g.items.length)
})
</script>

<template>
  <ContentWrap title="管理中心">
    <ElInput v-model="q" clearable placeholder="搜索管理功能，如「话术」「职员」「大厅」" style="max-width: 360px" class="search" />

    <div v-for="g in groups" :key="g.name" class="group">
      <div class="group-name">{{ g.name }}</div>
      <div class="cards">
        <div v-for="it in g.items" :key="it.path" class="card" tabindex="0" @click="router.push(it.path)" @keyup.enter="router.push(it.path)">
          <ElIcon :size="26" class="ico"><component :is="(Icons as any)[it.icon] || Icons.Menu" /></ElIcon>
          <div class="txt">
            <div class="title">{{ it.title }}</div>
            <div class="desc">{{ it.desc }}</div>
          </div>
        </div>
      </div>
    </div>
    <ElEmpty v-if="!groups.length" description="没有匹配的管理功能" />
  </ContentWrap>
</template>

<style scoped>
.search {
  margin-bottom: 8px;
}
.group {
  margin-top: 18px;
}
.group-name {
  margin-bottom: 10px;
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px;
}
.card {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 14px 16px;
  cursor: pointer;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  transition: all 0.15s;
}
.card:hover,
.card:focus-visible {
  border-color: var(--el-color-primary);
  box-shadow: 0 2px 10px rgb(64 158 255 / 15%);
  outline: none;
}
.ico {
  flex-shrink: 0;
  color: var(--el-color-primary);
}
.title {
  font-weight: 600;
}
.desc {
  margin-top: 2px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
