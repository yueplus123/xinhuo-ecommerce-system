<script setup lang="ts">
import { computed } from 'vue'

defineOptions({ name: 'SalaryPayroll' })
import { useRoute, useRouter } from 'vue-router'
import { ContentWrap } from '@/components/ContentWrap'
import { ElTabs, ElTabPane } from 'element-plus'

const route = useRoute()
const router = useRouter()

const tabs = [
  { name: '/salary-payroll/slips', label: '工资条' },
  { name: '/salary-payroll/base-salary', label: '基本工资' }
]

const active = computed(() => {
  const path = route.path.replace(/\/+$/, '')
  if (path.includes('base-salary')) return '/salary-payroll/base-salary'
  return '/salary-payroll/slips'
})

function onTab(name: string | number) {
  router.push(String(name))
}
</script>

<template>
  <ContentWrap title="工资核算">
    <ElTabs :model-value="active" @tab-change="onTab">
      <ElTabPane v-for="tab in tabs" :key="tab.name" :label="tab.label" :name="tab.name" />
    </ElTabs>
    <router-view v-slot="{ Component }">
      <keep-alive :max="8">
        <component :is="Component" />
      </keep-alive>
    </router-view>
  </ContentWrap>
</template>
