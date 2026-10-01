<script setup lang="tsx">
import axios from 'axios'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  ElAlert,
  ElCard,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElTable,
  ElTableColumn
} from 'element-plus'
import { BaseButton } from '@/components/Button'

defineOptions({ name: 'SalarySlipPublic' })

const route = useRoute()
const apiBase = import.meta.env.VITE_API_BASE_URL || '/api'

const loading = ref(true)
const saving = ref(false)
const error = ref('')
const payload = ref<any>(null)

const edits = reactive({
  shilei_sales_amount: '',
  tier2_sales_amount: '',
  yinli_sales_amount: '',
  refund_amount: ''
})

const COMPANY_NAME = '薪火电商'

const isReadOnly = computed(() => !!payload.value?.read_only || !!payload.value?.submitted)

function fmtMoney(v: unknown) {
  const n = Number(v || 0)
  return Number.isFinite(n)
    ? n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    : '0.00'
}

function parseMoneyInput(s: unknown) {
  const v = parseFloat(String(s ?? '').replace(/,/g, ''))
  return Number.isFinite(v) && v >= 0 ? v : 0
}

function round2(n: number) {
  return Math.round(n * 100) / 100
}

const showYinli = computed(() => !!payload.value?.yinli_separate)

const calc = computed(() => {
  const p = payload.value
  if (!p) return null
  const base = parseMoneyInput(p.base_salary)
  const shilei = parseMoneyInput(edits.shilei_sales_amount || p.shilei_sales_amount)
  const tier2 = parseMoneyInput(edits.tier2_sales_amount || p.tier2_sales_amount)
  const refund = parseMoneyInput(edits.refund_amount ?? p.refund_amount ?? 0)
  const yinli = showYinli.value
    ? parseMoneyInput(edits.yinli_sales_amount || p.yinli_sales_amount)
    : 0
  const social = parseMoneyInput(p.social_insurance_amount)

  const tier2Net = round2(Math.max(0, tier2 - refund))
  const commShilei = round2(shilei * 0.1)
  const commTier2 = round2(tier2Net * 0.02)
  const commYinli = round2(yinli * 0.005)
  const netPay = round2(base + commShilei + commTier2 + commYinli - social)

  const steps = [
    {
      key: 'base',
      operator: '',
      expression: fmtMoney(base),
      amount: base,
      caption: '基本工资（底薪）'
    },
    {
      key: 'shilei',
      operator: '+',
      expression: `${fmtMoney(shilei)} × 10%`,
      amount: commShilei,
      caption: '十类销售额 × 10%'
    },
    {
      key: 'tier2',
      operator: '+',
      expression: `(${fmtMoney(tier2)} − ${fmtMoney(refund)}) × 2%`,
      amount: commTier2,
      caption: '（二类销售额 − 退款项）× 2%'
    },
    {
      key: 'yinli',
      operator: '+',
      expression: `${fmtMoney(yinli)} × 0.5%`,
      amount: commYinli,
      caption: '引力币销售额 × 0.5%'
    },
    {
      key: 'social',
      operator: '−',
      expression: fmtMoney(social),
      amount: social,
      caption: '社保金额扣款'
    }
  ]

  return { steps, netPay }
})

const tableRow = computed(() => {
  if (!payload.value) return null
  return {
    username: payload.value.username,
    base_salary: payload.value.base_salary,
    total_sales_amount: payload.value.total_sales_amount,
    social_insurance_amount: payload.value.social_insurance_amount,
    net_pay: calc.value?.netPay
  }
})

function syncEditsFromPayload() {
  const p = payload.value
  if (!p) return
  edits.shilei_sales_amount = p.shilei_sales_amount != null ? String(p.shilei_sales_amount) : ''
  edits.tier2_sales_amount = p.tier2_sales_amount != null ? String(p.tier2_sales_amount) : ''
  edits.refund_amount = p.refund_amount != null ? String(p.refund_amount) : ''
  edits.yinli_sales_amount =
    p.yinli_separate && p.yinli_sales_amount != null ? String(p.yinli_sales_amount) : ''
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const token = route.params.token
    const { data } = await axios.get(`${apiBase}/salary-slip/${token}/`, {
      timeout: Number(import.meta.env.VITE_API_TIMEOUT_MS) || 60000
    })
    payload.value = data
    syncEditsFromPayload()
  } catch (e: any) {
    payload.value = null
    const d = e?.response?.data
    error.value =
      (typeof d === 'string' && d) || d?.detail || e?.message || '加载失败，请确认链接是否正确'
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (isReadOnly.value) return
  saving.value = true
  error.value = ''
  try {
    const token = route.params.token
    const body: Record<string, number> = {
      shilei_sales_amount: parseMoneyInput(edits.shilei_sales_amount),
      tier2_sales_amount: parseMoneyInput(edits.tier2_sales_amount),
      refund_amount: parseMoneyInput(edits.refund_amount)
    }
    if (showYinli.value) {
      body.yinli_sales_amount = parseMoneyInput(edits.yinli_sales_amount)
    }
    const { data } = await axios.post(`${apiBase}/salary-slip/${token}/`, body, {
      timeout: Number(import.meta.env.VITE_API_TIMEOUT_MS) || 60000
    })
    payload.value = data
    syncEditsFromPayload()
    ElMessage.success('填写成功')
  } catch (e: any) {
    const d = e?.response?.data
    error.value =
      (typeof d === 'string' && d) || d?.detail || e?.message || '提交失败'
    ElMessage.error(error.value)
  } finally {
    saving.value = false
  }
}

function onEditInput(field: keyof typeof edits, val: string) {
  if (isReadOnly.value) return
  edits[field] = val
}

onMounted(load)
</script>

<template>
  <div class="share-page">
    <div class="share-inner">
      <header class="share-header">
        <h1>工资条填报</h1>
        <ElAlert
          v-if="isReadOnly && payload"
          type="warning"
          :closable="false"
          show-icon
          title="本链接已提交，仅可查看，不可再次修改。"
          class="share-alert"
        />
        <p v-else-if="payload" class="share-sub">
          请填写本人当月十类、二类{{ showYinli ? '、引力币' : '' }}、退款项后提交（链接仅可提交一次）。
        </p>
      </header>

      <ElCard v-if="loading" shadow="never" v-loading="true" class="share-card">
        <div class="h-120px"></div>
      </ElCard>

      <ElAlert
        v-else-if="error && !payload"
        type="error"
        :closable="false"
        show-icon
        :title="error"
        class="share-alert"
      />

      <template v-else-if="payload">
        <ElAlert
          v-if="error"
          type="error"
          :closable="false"
          show-icon
          :title="error"
          class="share-alert mb-12px"
        />

        <ElCard shadow="never" class="share-card">
          <template #header>
            <div class="card-head">
              <span class="card-title">工资条</span>
              <span class="card-meta">
                编制单位：{{ COMPANY_NAME }} · 工资月份：{{ payload.period?.year }} 年
                {{ payload.period?.month }} 月
              </span>
            </div>
          </template>

          <ElTable :data="tableRow ? [tableRow] : []" border stripe class="share-table">
            <ElTableColumn prop="username" label="姓名" min-width="80" align="center" fixed />
            <ElTableColumn label="基本工资" min-width="100" align="right">
              <template #default="{ row }">
                <span class="tabular-nums">{{ fmtMoney(row.base_salary) }}</span>
              </template>
            </ElTableColumn>
            <ElTableColumn label="总销售额" min-width="100" align="right">
              <template #default="{ row }">
                <span class="tabular-nums">{{ fmtMoney(row.total_sales_amount) }}</span>
              </template>
            </ElTableColumn>
            <ElTableColumn label="十类销售额" min-width="120" align="center">
              <template #default>
                <ElInput
                  v-if="!isReadOnly"
                  :model-value="edits.shilei_sales_amount"
                  placeholder="0.00"
                  size="small"
                  @update:model-value="(v) => onEditInput('shilei_sales_amount', v)"
                />
                <span v-else class="tabular-nums">{{
                  fmtMoney(edits.shilei_sales_amount || payload.shilei_sales_amount)
                }}</span>
              </template>
            </ElTableColumn>
            <ElTableColumn label="二类销售额" min-width="120" align="center">
              <template #default>
                <ElInput
                  v-if="!isReadOnly"
                  :model-value="edits.tier2_sales_amount"
                  placeholder="0.00"
                  size="small"
                  @update:model-value="(v) => onEditInput('tier2_sales_amount', v)"
                />
                <span v-else class="tabular-nums">{{
                  fmtMoney(edits.tier2_sales_amount || payload.tier2_sales_amount)
                }}</span>
              </template>
            </ElTableColumn>
            <ElTableColumn label="引力币销售额" min-width="120" align="center">
              <template #default>
                <ElInput
                  v-if="showYinli && !isReadOnly"
                  :model-value="edits.yinli_sales_amount"
                  placeholder="0.00"
                  size="small"
                  @update:model-value="(v) => onEditInput('yinli_sales_amount', v)"
                />
                <span v-else-if="showYinli" class="tabular-nums">{{
                  fmtMoney(edits.yinli_sales_amount || payload.yinli_sales_amount)
                }}</span>
                <span v-else>—</span>
              </template>
            </ElTableColumn>
            <ElTableColumn label="退款项" min-width="110" align="center">
              <template #default>
                <ElInput
                  v-if="!isReadOnly"
                  :model-value="edits.refund_amount"
                  placeholder="0.00"
                  size="small"
                  @update:model-value="(v) => onEditInput('refund_amount', v)"
                />
                <span v-else class="tabular-nums">{{
                  fmtMoney(edits.refund_amount ?? payload.refund_amount)
                }}</span>
              </template>
            </ElTableColumn>
            <ElTableColumn label="社保金额" min-width="100" align="right">
              <template #default="{ row }">
                <span class="tabular-nums">{{ fmtMoney(row.social_insurance_amount) }}</span>
              </template>
            </ElTableColumn>
            <ElTableColumn label="实发工资" min-width="100" align="right" fixed="right">
              <template #default="{ row }">
                <span class="tabular-nums font-600 text-[var(--el-color-primary)]">{{
                  fmtMoney(row.net_pay)
                }}</span>
              </template>
            </ElTableColumn>
          </ElTable>

          <div v-if="calc" class="calc-section">
            <div class="calc-label">实发工资 =</div>
            <div class="calc-flow">
              <template v-for="step in calc.steps" :key="step.key">
                <span v-if="step.operator" class="calc-op">{{ step.operator }}</span>
                <div class="calc-block">
                  <div class="calc-expr">{{ step.expression }}</div>
                  <div class="calc-result">= {{ fmtMoney(step.amount) }}</div>
                  <div class="calc-caption">{{ step.caption }}</div>
                </div>
              </template>
              <span class="calc-op">=</span>
              <div class="calc-block calc-block--total">
                <div class="calc-expr">合计</div>
                <div class="calc-result calc-result--total">{{ fmtMoney(calc.netPay) }}</div>
                <div class="calc-caption">实发工资</div>
              </div>
            </div>
          </div>

          <p class="share-note">
            总销售额来自数据大屏；基本工资与社保由公司配置。请核对后提交，提交后链接不可再次修改。
          </p>
        </ElCard>

        <ElForm v-if="!isReadOnly" class="share-actions" @submit.prevent="submit">
          <ElFormItem>
            <BaseButton type="primary" :loading="saving" @click="submit">提交</BaseButton>
          </ElFormItem>
        </ElForm>
      </template>
    </div>
  </div>
</template>

<style scoped>
.share-page {
  min-height: 100vh;
  background: var(--el-bg-color-page);
  padding: 24px 16px;
  box-sizing: border-box;
}

.share-inner {
  max-width: 1100px;
  margin: 0 auto;
}

.share-header {
  text-align: center;
  margin-bottom: 20px;
}

.share-header h1 {
  margin: 0 0 10px;
  font-size: 22px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.share-sub {
  margin: 0;
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.share-alert {
  max-width: 640px;
  margin: 0 auto;
}

.share-card {
  margin-bottom: 16px;
}

.card-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
}

.card-meta {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.share-table {
  width: 100%;
}

.calc-section {
  margin-top: 16px;
  padding: 14px;
  border: 1px dashed var(--el-border-color);
  border-radius: var(--el-border-radius-base);
  background: var(--el-fill-color-lighter);
  overflow-x: auto;
}

.calc-label {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 10px;
  color: var(--el-text-color-primary);
}

.calc-flow {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 8px 6px;
}

.calc-op {
  align-self: center;
  font-weight: 700;
  color: var(--el-text-color-secondary);
}

.calc-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 88px;
  padding: 6px 8px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: var(--el-border-radius-base);
  background: var(--el-bg-color);
}

.calc-block--total {
  border-color: var(--el-color-primary-light-5);
  background: var(--el-color-primary-light-9);
}

.calc-expr {
  font-size: 12px;
  color: var(--el-text-color-regular);
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.calc-result {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  font-variant-numeric: tabular-nums;
}

.calc-result--total {
  font-size: 15px;
  color: var(--el-color-primary);
}

.calc-caption {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  text-align: center;
}

.share-note {
  margin: 14px 0 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
}

.share-actions {
  display: flex;
  justify-content: center;
  margin-top: 8px;
}

.share-actions :deep(.el-form-item) {
  margin-bottom: 0;
}

.tabular-nums {
  font-variant-numeric: tabular-nums;
}
</style>
