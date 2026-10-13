<script setup lang="ts">
import PoolCrud, { type PoolField } from './PoolCrud.vue'

defineOptions({ name: 'ManageChannelTagPool' })

const fields: PoolField[] = [
  { prop: 'name', label: '渠道名称', required: true },
  { prop: 'order', label: '排序', type: 'number', min: 0, width: 100 }
]
</script>

<template>
  <PoolCrud
    pool-key="channel-tag-pool"
    title="渠道池"
    :fields="fields"
    quick-add
    quick-add-placeholder="输入渠道名称后回车快速添加"
    hint="SKU 编辑时可选的渠道；拖动手柄调整顺序，机器人按此顺序读取"
  />
</template>
