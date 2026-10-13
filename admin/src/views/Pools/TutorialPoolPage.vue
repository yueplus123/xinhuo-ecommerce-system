<script setup lang="ts">
import PoolCrud, { type PoolField } from './PoolCrud.vue'

defineOptions({ name: 'ManageTutorialPool' })

const fields: PoolField[] = [
  { prop: 'name', label: '教程名称', required: true, width: 240 },
  {
    prop: 'detail_url',
    label: '详情链接',
    required: true,
    placeholder: '例如 https://example.com/tutorial（可省略 https://）'
  }
]
</script>

<template>
  <PoolCrud
    pool-key="tutorial-pool"
    title="教程池"
    :fields="fields"
    hint="拖动左侧手柄调整顺序，机器人按此顺序读取"
  />
</template>
