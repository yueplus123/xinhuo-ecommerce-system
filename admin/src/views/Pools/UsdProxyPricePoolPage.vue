<script setup lang="ts">
import PoolCrud, { type PoolField } from './PoolCrud.vue'

defineOptions({ name: 'ManageUsdProxyPricePool' })

const fields: PoolField[] = [
  { prop: 'usd_range', label: '美金区间', required: true, placeholder: '例如 1-50', width: 240 },
  {
    prop: 'rate_percent',
    label: '代付比例 (%)',
    type: 'number',
    required: true,
    precision: 2,
    min: 0,
    max: 999.99
  }
]
</script>

<template>
  <PoolCrud
    pool-key="usd-proxy-price-pool"
    title="美金代付价格池"
    :fields="fields"
    hint="拖动左侧手柄调整顺序，机器人按此顺序读取"
  />
</template>
