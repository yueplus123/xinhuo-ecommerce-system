<script setup lang="ts">
import PoolCrud, { type PoolField } from './PoolCrud.vue'

defineOptions({ name: 'ManagePlatformTagPool' })

const fields: PoolField[] = [
  { prop: 'name', label: '名称', required: true },
  { prop: 'order', label: '排序', type: 'number', min: 0, width: 100 }
]
</script>

<template>
  <PoolCrud
    pool-key="platform-tag-pool"
    title="平台标签池"
    :fields="fields"
    quick-add
    quick-add-placeholder="输入标签名称后回车快速添加"
    hint="平台编辑时可选的标签；拖动手柄调整顺序"
  />
</template>
