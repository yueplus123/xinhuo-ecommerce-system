<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import PoolCrud, { type PoolField } from './PoolCrud.vue'
import { listQuickPhraseSkuOptions } from '@/api/modules/pools'
import { formatRequestError } from '@/utils/format'

defineOptions({ name: 'ManageQuickPhrases' })

const skuOptions = ref<Array<{ id: number; label: string }>>([])
const fields = ref<PoolField[]>([
  {
    prop: 'sku',
    label: 'SKU',
    type: 'select',
    required: true,
    displayProp: 'sku_label',
    options: [],
    width: 320
  },
  { prop: 'content', label: '话术内容', type: 'textarea', required: true },
  { prop: 'order', label: '排序', type: 'number', min: 0, width: 100 }
])

onMounted(async () => {
  try {
    skuOptions.value = await listQuickPhraseSkuOptions()
    fields.value = fields.value.map((f) => (f.prop === 'sku' ? { ...f, options: skuOptions.value } : f))
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, 'SKU 列表加载失败'))
  }
})
</script>

<template>
  <PoolCrud
    pool-key="quick-phrases"
    title="SKU 快捷话术"
    :fields="fields"
    filter-prop="sku"
    filter-label="按 SKU 筛选"
    :filter-options="skuOptions"
    hint="数字越小越靠前"
  />
</template>
