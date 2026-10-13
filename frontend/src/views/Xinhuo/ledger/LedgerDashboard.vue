<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElAlert, ElCard, ElCol, ElEmpty, ElRow, ElSkeleton, ElStatistic } from 'element-plus'
import { api, type LedgerRow, type WalletRow } from '@/api/xinhuo/ledger'
import LedgerChart from './LedgerChart.vue'
import {
  LEDGER_UPDATED_EVENT,
  WALLET_UPDATED_EVENT,
  computeDashboardStats,
  isLedgerUnsettled
} from './ledgerUtils'

const ledger = ref<LedgerRow[]>([])
const wallet = ref<WalletRow[]>([])
const loaded = ref(false)
const err = ref('')
const walletErr = ref('')

const stats = computed(() => computeDashboardStats(ledger.value))
const unsettledCount = computed(() => ledger.value.filter(isLedgerUnsettled).length)

async function loadLedger() {
  try {
    ledger.value = await api.ledgerList()
    err.value = ''
  } catch (e) {
    err.value = (e as Error).message
  } finally {
    loaded.value = true
  }
}
async function loadWallet() {
  try {
    wallet.value = await api.walletList()
    walletErr.value = ''
  } catch (e) {
    wallet.value = []
    walletErr.value = (e as Error).message
  }
}

const axisBase = { axisLabel: { fontSize: 12 }, splitLine: { lineStyle: { color: '#ebeef5' } } }
const grid = { top: 36, right: 16, bottom: 28, left: 56 }
const tip = { trigger: 'axis' as const }
const months = computed(() => stats.value.byMonth.map((r) => r.month))

const barOpt = (name: string, key: 'amount' | 'count', color: string) =>
  computed(() => ({
    tooltip: tip,
    grid,
    xAxis: { type: 'category' as const, data: months.value },
    yAxis: { type: 'value' as const, ...axisBase, minInterval: key === 'count' ? 1 : undefined },
    series: [
      {
        name,
        type: 'bar' as const,
        data: stats.value.byMonth.map((r) => r[key]),
        itemStyle: { color, borderRadius: [4, 4, 0, 0] },
        barMaxWidth: 48
      }
    ]
  }))
const amountOpt = barOpt('收款', 'amount', '#409eff')
const countOpt = barOpt('笔数', 'count', '#e6a23c')
const profitOpt = computed(() => ({
  tooltip: tip,
  grid,
  xAxis: { type: 'category' as const, data: months.value },
  yAxis: { type: 'value' as const, ...axisBase },
  series: [
    {
      name: '利润',
      type: 'line' as const,
      smooth: true,
      symbolSize: 8,
      data: stats.value.byMonth.map((r) => r.profit),
      itemStyle: { color: '#67c23a' },
      lineStyle: { width: 2 }
    }
  ]
}))

const WALLET_SERIES = [
  { key: 'wechat', name: '微信', color: '#67c23a' },
  { key: 'alipay', name: '支付宝', color: '#409eff' },
  { key: 'card', name: '卡片', color: '#e6a23c' },
  { key: 'pocket', name: '小荷包', color: '#f56c6c' },
  { key: 'total', name: '总计', color: '#606266' }
] as const
const walletSorted = computed(() =>
  [...wallet.value].sort((a, b) => {
    const ta = Date.parse(String(a.recordAt).replace(' ', 'T')) || 0
    const tb = Date.parse(String(b.recordAt).replace(' ', 'T')) || 0
    return ta - tb || a.id.localeCompare(b.id)
  })
)
const walletLatest = computed(() => walletSorted.value.at(-1))
const walletOpt = computed(() => ({
  tooltip: tip,
  legend: { data: WALLET_SERIES.map((s) => s.name) },
  grid: { ...grid, top: 44 },
  xAxis: {
    type: 'category' as const,
    data: walletSorted.value.map((r) => String(r.recordAt).slice(5, 16))
  },
  yAxis: { type: 'value' as const, ...axisBase },
  series: WALLET_SERIES.map((s) => ({
    name: s.name,
    type: 'line' as const,
    smooth: true,
    data: walletSorted.value.map((r) => Number(r[s.key]) || 0),
    itemStyle: { color: s.color },
    lineStyle: { width: s.key === 'total' ? 3 : 2 }
  }))
}))

const refreshLedger = () => void loadLedger()
const refreshWallet = () => void loadWallet()
let timer = 0
onMounted(() => {
  void loadLedger()
  void loadWallet()
  window.addEventListener(LEDGER_UPDATED_EVENT, refreshLedger)
  window.addEventListener(WALLET_UPDATED_EVENT, refreshWallet)
  timer = window.setInterval(refreshLedger, 30000)
})
onBeforeUnmount(() => {
  window.removeEventListener(LEDGER_UPDATED_EVENT, refreshLedger)
  window.removeEventListener(WALLET_UPDATED_EVENT, refreshWallet)
  window.clearInterval(timer)
})
</script>

<template>
  <ElAlert
    v-if="err"
    type="warning"
    :closable="false"
    :title="`无法连接后端 API：${err}`"
    description="请确认已登录 CEO 账号，且服务器 /api/ledger 可用。"
  />
  <ElSkeleton v-else-if="!loaded" :rows="6" animated />
  <div v-else>
    <ElRow :gutter="16" class="mb-16px">
      <ElCol :xs="12" :md="6">
        <ElCard shadow="never">
          <ElStatistic title="本月收款金额" :value="stats.thisMonthAmount" :precision="2" />
        </ElCard>
      </ElCol>
      <ElCol :xs="12" :md="6">
        <ElCard shadow="never">
          <ElStatistic title="本月利润" :value="stats.thisMonthProfit" :precision="2" />
        </ElCard>
      </ElCol>
      <ElCol :xs="12" :md="6">
        <ElCard shadow="never">
          <ElStatistic title="本月记账笔数" :value="stats.thisMonthCount" />
        </ElCard>
      </ElCol>
      <ElCol :xs="12" :md="6">
        <ElCard shadow="never">
          <ElStatistic title="未清账笔数" :value="unsettledCount" />
        </ElCard>
      </ElCol>
    </ElRow>

    <ElRow :gutter="16" class="mb-16px">
      <ElCol :xs="24" :md="12">
        <ElCard shadow="never" header="记录表 · 月度收款">
          <LedgerChart v-if="months.length" :option="amountOpt" />
          <ElEmpty v-else description="暂无数据" />
        </ElCard>
      </ElCol>
      <ElCol :xs="24" :md="12">
        <ElCard shadow="never" header="记录表 · 月度利润">
          <LedgerChart v-if="months.length" :option="profitOpt" />
          <ElEmpty v-else description="暂无数据" />
        </ElCard>
      </ElCol>
    </ElRow>

    <ElCard shadow="never" header="记录表 · 历史每月汇总" class="mb-16px">
      <ElRow v-if="months.length" :gutter="16">
        <ElCol :xs="24" :md="8">
          <div class="mini-title">月度笔数</div>
          <LedgerChart :option="countOpt" :height="240" />
        </ElCol>
        <ElCol :xs="24" :md="8">
          <div class="mini-title">月度收款</div>
          <LedgerChart :option="amountOpt" :height="240" />
        </ElCol>
        <ElCol :xs="24" :md="8">
          <div class="mini-title">月度利润</div>
          <LedgerChart :option="profitOpt" :height="240" />
        </ElCol>
      </ElRow>
      <ElEmpty v-else description="暂无数据" />
    </ElCard>

    <ElCard shadow="never" header="余额曲线">
      <ElAlert v-if="walletErr" type="error" :closable="false" :title="walletErr" />
      <ElEmpty v-else-if="!walletSorted.length" description="暂无记录，保存第一条后将在此显示曲线" />
      <template v-else>
        <ElRow :gutter="12" class="mb-12px">
          <ElCol v-for="s in WALLET_SERIES" :key="s.key" :xs="12" :md="4">
            <ElStatistic
              :title="s.name"
              :value="Number(walletLatest?.[s.key]) || 0"
              :precision="2"
              :value-style="{ color: s.color, fontSize: '18px' }"
            />
          </ElCol>
        </ElRow>
        <LedgerChart :option="walletOpt" :height="320" />
      </template>
    </ElCard>
  </div>
</template>

<style scoped>
.mini-title {
  margin-bottom: 4px;
  font-size: 13px;
  color: #909399;
}
.mb-12px {
  margin-bottom: 12px;
}
.mb-16px {
  margin-bottom: 16px;
}
</style>
