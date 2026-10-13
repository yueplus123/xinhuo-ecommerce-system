<script setup lang="ts">
import PoolCrud, { type PoolField } from './PoolCrud.vue'

defineOptions({ name: 'ManagePhrasePool' })

const fields: PoolField[] = [
  { prop: 'name', label: '名称', required: true, width: 220 },
  { prop: 'content', label: '话术内容', type: 'textarea', required: true }
]
</script>

<template>
  <PoolCrud
    pool-key="phrase-pool"
    title="话术池"
    :fields="fields"
    hint="拖动左侧手柄调整顺序，机器人按此顺序读取"
  />
</template>
