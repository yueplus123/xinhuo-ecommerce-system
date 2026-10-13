<script setup lang="ts">
// CEO 记账系统：数据大屏 / 记账填写 / 钱包余额（Vue 3 + Element Plus，与全站统一）
import { ref } from 'vue'
import { ElTabPane, ElTabs } from 'element-plus'
import { ContentWrap } from '@/components/ContentWrap'
import LedgerDashboard from './ledger/LedgerDashboard.vue'
import LedgerRecords from './ledger/LedgerRecords.vue'
import LedgerWallet from './ledger/LedgerWallet.vue'

defineOptions({ name: 'LedgerAccounting' })

const tab = ref<'dashboard' | 'ledger' | 'wallet'>('dashboard')
</script>

<template>
  <ContentWrap title="记账系统">
    <ElTabs v-model="tab">
      <ElTabPane label="数据大屏" name="dashboard" lazy>
        <LedgerDashboard v-if="tab === 'dashboard'" />
      </ElTabPane>
      <ElTabPane label="记账填写" name="ledger" lazy>
        <LedgerRecords v-if="tab === 'ledger'" />
      </ElTabPane>
      <ElTabPane label="钱包余额" name="wallet" lazy>
        <LedgerWallet v-if="tab === 'wallet'" />
      </ElTabPane>
    </ElTabs>
  </ContentWrap>
</template>
