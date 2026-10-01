<script setup lang="tsx">
import html2canvas from 'html2canvas'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElDatePicker, ElMessage } from 'element-plus'
import { ContentWrap } from '@/components/ContentWrap'
import { BaseButton } from '@/components/Button'
import api from '@/api/xinhuo/client'

defineOptions({ name: 'SalarySlips' })

const loading = ref(false)
const saving = ref(false)
const exportingId = ref<number | null>(null)
const copyingId = ref<number | null>(null)
const copyOkId = ref<number | null>(null)
const error = ref('')
const saveOk = ref('')
const periodMonth = ref('')
const payload = ref<any>(null)
/** @type {Record<number, { shilei_sales_amount: string, tier2_sales_amount: string, yinli_sales_amount: string, social_insurance_amount: string, refund_amount: string }>} */
const edits = reactive<Record<number, any>>({})

const YINLI_USERNAME = '冬梅'
const COMPANY_NAME = '薪火电商'

function hasYinliField(emp: any) {
  if (emp?.yinli_separate != null) return !!emp.yinli_separate
  return String(emp?.username || '').trim() === YINLI_USERNAME
}

function currentMonthKey() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

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

function slipAmounts(emp: any, editRow: any) {
  const shilei = parseMoneyInput(editRow?.shilei_sales_amount ?? emp.shilei_sales_amount)
  const tier2 = parseMoneyInput(editRow?.tier2_sales_amount ?? emp.tier2_sales_amount)
  const total = Number(emp.member_gmv ?? emp.total_sales_amount ?? emp.summary?.gmv ?? 0)
  return {
    total_sales: round2(total),
    shilei_sales: round2(shilei),
    tier2_sales: round2(tier2)
  }
}

function buildCalcBreakdown(emp: any, editRow: any) {
  const base = parseMoneyInput(emp.base_salary)
  const shilei = parseMoneyInput(editRow?.shilei_sales_amount ?? emp.shilei_sales_amount)
  const tier2 = parseMoneyInput(editRow?.tier2_sales_amount ?? emp.tier2_sales_amount)
  const refund = parseMoneyInput(editRow?.refund_amount ?? emp.refund_amount ?? emp.summary?.refund ?? 0)
  const yinliSeparate = hasYinliField(emp)
  const yinli = yinliSeparate
    ? parseMoneyInput(editRow?.yinli_sales_amount ?? emp.yinli_sales_amount)
    : 0
  const social = parseMoneyInput(editRow?.social_insurance_amount ?? emp.social_insurance_amount)

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

  const formulaLine = `实发工资 = ${fmtMoney(base)} + ${steps[1].expression} + ${steps[2].expression} + ${steps[3].expression} − ${steps[4].expression} = ${fmtMoney(netPay)}`

  return {
    steps,
    formulaLine,
    netPay,
    base,
    shilei,
    tier2,
    refund,
    tier2Net,
    yinli,
    social,
    commShilei,
    commTier2,
    commYinli
  }
}

function syncEditsFromPayload() {
  Object.keys(edits).forEach((k) => delete edits[Number(k)])
  for (const emp of payload.value?.employees || []) {
    edits[emp.id] = {
      shilei_sales_amount:
        emp.shilei_sales_amount != null ? String(emp.shilei_sales_amount) : '',
      tier2_sales_amount:
        emp.tier2_sales_amount != null ? String(emp.tier2_sales_amount) : '',
      yinli_sales_amount:
        hasYinliField(emp) && emp.yinli_sales_amount != null
          ? String(emp.yinli_sales_amount)
          : '',
      social_insurance_amount:
        emp.social_insurance_amount != null ? String(emp.social_insurance_amount) : '',
      refund_amount: emp.refund_amount != null ? String(emp.refund_amount) : ''
    }
  }
}

const periodYear = computed(() => payload.value?.period?.year ?? '—')
const periodMonthNum = computed(() => payload.value?.period?.month ?? '—')

const displayEmployees = computed(() => {
  return (payload.value?.employees || []).map((emp: any) => {
    const editRow = edits[emp.id]
    const amounts = slipAmounts(emp, editRow)
    const calc = buildCalcBreakdown(emp, editRow)
    return {
      ...emp,
      amounts,
      calc,
      show_yinli: hasYinliField(emp)
    }
  })
})

async function load() {
  loading.value = true
  error.value = ''
  saveOk.value = ''
  try {
    const { data } = await api.get('/salary-payroll/', {
      params: { month: periodMonth.value }
    })
    payload.value = data
    if (data?.period?.month_key) {
      periodMonth.value = data.period.month_key
    }
    syncEditsFromPayload()
  } catch (e: any) {
    payload.value = null
    const d = e?.response?.data
    error.value =
      (typeof d === 'string' && d) || d?.detail || e?.message || '加载工资条失败'
    ElMessage.error(error.value)
  } finally {
    loading.value = false
  }
}

async function saveAll() {
  saving.value = true
  error.value = ''
  saveOk.value = ''
  try {
    const items = (payload.value?.employees || []).map((emp: any) => {
      const e = edits[emp.id] || {}
      return {
        user_id: emp.id,
        base_salary: parseMoneyInput(emp.base_salary),
        shilei_sales_amount: parseMoneyInput(e.shilei_sales_amount),
        tier2_sales_amount: parseMoneyInput(e.tier2_sales_amount),
        social_insurance_amount: parseMoneyInput(e.social_insurance_amount),
        refund_amount: parseMoneyInput(e.refund_amount),
        yinli_sales_amount: hasYinliField(emp) ? parseMoneyInput(e.yinli_sales_amount) : 0
      }
    })
    const { data } = await api.post('/salary-payroll/', {
      month: periodMonth.value,
      items
    })
    payload.value = data
    syncEditsFromPayload()
    saveOk.value = '已保存。'
    ElMessage.success(saveOk.value)
  } catch (e: any) {
    const d = e?.response?.data
    error.value =
      (typeof d === 'string' && d) || d?.detail || e?.message || '保存失败'
    ElMessage.error(error.value)
  } finally {
    saving.value = false
  }
}

function onEditInput(empId: number, field: string, event: Event) {
  if (!edits[empId]) {
    edits[empId] = {
      shilei_sales_amount: '',
      tier2_sales_amount: '',
      yinli_sales_amount: '',
      social_insurance_amount: '',
      refund_amount: ''
    }
  }
  edits[empId][field] = (event.target as HTMLInputElement).value
}

function slipFileName(emp: any) {
  const month = periodMonth.value || 'month'
  const name = String(emp.username || 'user').replace(/[\\/:*?"<>|]/g, '_')
  return `工资条_${name}_${month}.png`
}

function shareUrlFromToken(token: string) {
  const origin = window.location.origin.replace(/\/+$/, '')
  return `${origin}/salary-slip/${token}`
}

async function copyTextToClipboard(text: string) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      /* HTTP 非 localhost 时 clipboard API 常被禁用，走下方降级方案 */
    }
  }
  const ta = document.createElement('textarea')
  ta.value = text
  ta.setAttribute('readonly', '')
  ta.style.position = 'fixed'
  ta.style.left = '-9999px'
  ta.style.top = '0'
  document.body.appendChild(ta)
  ta.focus()
  ta.select()
  ta.setSelectionRange(0, text.length)
  let ok = false
  try {
    ok = document.execCommand('copy')
  } catch {
    ok = false
  }
  document.body.removeChild(ta)
  return ok
}

async function copyShareLink(emp: any) {
  if (emp?.is_ceo) return
  copyingId.value = emp.id
  copyOkId.value = null
  error.value = ''
  try {
    const { data } = await api.post('/salary-payroll/share-link/', {
      month: periodMonth.value,
      user_id: emp.id
    })
    const url = shareUrlFromToken(data.share_token)
    const ok = await copyTextToClipboard(url)
    if (ok) {
      copyOkId.value = emp.id
      ElMessage.success('已复制员工填报链接')
      setTimeout(() => {
        if (copyOkId.value === emp.id) copyOkId.value = null
      }, 2000)
    } else {
      error.value = '复制失败，请手动复制链接：' + url
      ElMessage.error(error.value)
    }
  } catch (e: any) {
    const d = e?.response?.data
    error.value =
      (typeof d === 'string' && d) || d?.detail || e?.message || '生成分享链接失败'
    ElMessage.error(error.value)
  } finally {
    copyingId.value = null
  }
}

async function exportSlip(emp: any) {
  const el = document.getElementById(`slip-card-${emp.id}`)
  if (!el) {
    error.value = '未找到工资条节点，请刷新后重试。'
    ElMessage.error(error.value)
    return
  }
  exportingId.value = emp.id
  error.value = ''
  try {
    const canvas = await html2canvas(el, {
      backgroundColor: '#ffffff',
      scale: 2,
      useCORS: true,
      logging: false,
      onclone: (doc) => {
        const root = doc.getElementById(`slip-card-${emp.id}`)
        if (!root) return
        root.style.background = '#fff'
        root.style.color = '#111'
        root.style.border = 'none'
        root.style.boxShadow = 'none'
        root
          .querySelectorAll(
            '.slip-title, .slip-meta, .slip-note, .slip-calc-eq-label, .slip-calc-expr, .slip-calc-result, .slip-calc-caption, .slip-calc-op'
          )
          .forEach((node) => {
            ;(node as HTMLElement).style.color = '#111'
          })
        root.querySelectorAll('.slip-calc-result--total').forEach((node) => {
          ;(node as HTMLElement).style.color = '#111'
          ;(node as HTMLElement).style.fontWeight = '700'
        })
        root.querySelectorAll('.slip-calc').forEach((node) => {
          ;(node as HTMLElement).style.borderColor = '#ccc'
          ;(node as HTMLElement).style.background = '#fafafa'
        })
        root.querySelectorAll('.slip-table th, .slip-table td').forEach((node) => {
          ;(node as HTMLElement).style.borderColor = '#111'
          ;(node as HTMLElement).style.color = '#111'
          ;(node as HTMLElement).style.background = '#fff'
        })
        root.querySelectorAll('.slip-cut').forEach((node) => {
          ;(node as HTMLElement).style.backgroundImage =
            'repeating-linear-gradient(90deg, #111 0, #111 6px, transparent 6px, transparent 12px)'
        })
        root.querySelectorAll('.pay-input').forEach((input) => {
          const span = doc.createElement('span')
          span.textContent = (input as HTMLInputElement).value || '0.00'
          span.className = 'cell-num'
          span.style.color = '#111'
          input.replaceWith(span)
        })
      }
    })
    const url = canvas.toDataURL('image/png')
    const a = document.createElement('a')
    a.href = url
    a.download = slipFileName(emp)
    document.body.appendChild(a)
    a.click()
    a.remove()
  } catch (e: any) {
    error.value = e?.message || '导出工资条图片失败'
    ElMessage.error(error.value)
  } finally {
    exportingId.value = null
  }
}

onMounted(() => {
  periodMonth.value = currentMonthKey()
  load()
})

watch(periodMonth, (val, oldVal) => {
  if (val && oldVal && val !== oldVal) load()
})
</script>

<template>
  <ContentWrap>
    <div class="flex flex-wrap items-end justify-between gap-12px mb-16px">
      <p class="text-13px text-[var(--el-text-color-secondary)] m-0 max-w-520px leading-relaxed">
        总销售额自动取自数据大屏；点击「复制员工填报链接」每次生成新链接（仅可提交一次），填错可重新复制再发。
      </p>
      <div class="flex flex-wrap items-center gap-8px">
        <span class="text-13px text-[var(--el-text-color-secondary)]">核算月份</span>
        <ElDatePicker
          v-model="periodMonth"
          type="month"
          value-format="YYYY-MM"
          format="YYYY-MM"
          placeholder="选择月份"
          :disabled="loading"
          style="width: 150px"
        />
        <BaseButton :loading="loading" @click="load">刷新</BaseButton>
        <BaseButton type="primary" :loading="saving" :disabled="loading" @click="saveAll">
          保存全部
        </BaseButton>
      </div>
    </div>

    <p v-if="loading && !displayEmployees.length" class="text-[var(--el-text-color-secondary)] m-0">
      加载中…
    </p>
    <p
      v-else-if="!loading && !displayEmployees.length"
      class="text-[var(--el-text-color-secondary)] m-0"
    >
      暂无员工账号
    </p>

    <div v-else class="payslip-list">
      <article v-for="emp in displayEmployees" :key="emp.id" class="payslip-doc">
        <div :id="`slip-card-${emp.id}`" class="slip-strip">
          <div class="slip-cut slip-cut--top" aria-hidden="true"></div>

          <div class="slip-body">
            <h3 class="slip-title">工资条</h3>

            <div class="slip-meta">
              <span class="slip-meta-left">编制单位：{{ COMPANY_NAME }}</span>
              <span class="slip-meta-right">
                工资月份：<strong>{{ periodYear }}</strong> 年 <strong>{{ periodMonthNum }}</strong>
                月
              </span>
            </div>

            <div class="slip-table-wrap">
              <table class="slip-table">
                <thead>
                  <tr>
                    <th rowspan="2" class="col-name">姓名</th>
                    <th rowspan="2" class="col-base">基本工资</th>
                    <th rowspan="2" class="col-total">总销售额</th>
                    <th colspan="4" class="group-head">应发工资</th>
                    <th colspan="1" class="group-head">社保</th>
                    <th rowspan="2" class="col-net">实发工资</th>
                  </tr>
                  <tr>
                    <th class="sub-head">十类销售额</th>
                    <th class="sub-head">二类销售额</th>
                    <th class="sub-head">引力币销售额</th>
                    <th class="sub-head">退款项金额</th>
                    <th class="sub-head">社保金额</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td class="cell-name">{{ emp.username }}</td>
                    <td class="cell-num">{{ fmtMoney(emp.base_salary) }}</td>
                    <td class="cell-num">{{ fmtMoney(emp.amounts.total_sales) }}</td>
                    <td class="cell-money">
                      <input
                        type="text"
                        inputmode="decimal"
                        class="pay-input"
                        :value="edits[emp.id]?.shilei_sales_amount ?? ''"
                        placeholder="0.00"
                        @input="onEditInput(emp.id, 'shilei_sales_amount', $event)"
                      />
                    </td>
                    <td class="cell-money">
                      <input
                        type="text"
                        inputmode="decimal"
                        class="pay-input"
                        :value="edits[emp.id]?.tier2_sales_amount ?? ''"
                        placeholder="0.00"
                        @input="onEditInput(emp.id, 'tier2_sales_amount', $event)"
                      />
                    </td>
                    <td class="cell-money">
                      <template v-if="emp.show_yinli">
                        <input
                          type="text"
                          inputmode="decimal"
                          class="pay-input"
                          :value="edits[emp.id]?.yinli_sales_amount ?? ''"
                          placeholder="0.00"
                          @input="onEditInput(emp.id, 'yinli_sales_amount', $event)"
                        />
                      </template>
                      <span v-else class="cell-dash">—</span>
                    </td>
                    <td class="cell-money">
                      <input
                        type="text"
                        inputmode="decimal"
                        class="pay-input"
                        :value="edits[emp.id]?.refund_amount ?? ''"
                        placeholder="0.00"
                        @input="onEditInput(emp.id, 'refund_amount', $event)"
                      />
                    </td>
                    <td class="cell-money">
                      <input
                        type="text"
                        inputmode="decimal"
                        class="pay-input"
                        :value="edits[emp.id]?.social_insurance_amount ?? ''"
                        placeholder="0.00"
                        @input="onEditInput(emp.id, 'social_insurance_amount', $event)"
                      />
                    </td>
                    <td class="cell-num cell-net-pay">{{ fmtMoney(emp.calc.netPay) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div class="slip-calc">
              <div class="slip-calc-flow">
                <span class="slip-calc-eq-label">实发工资 =</span>
                <template v-for="step in emp.calc.steps" :key="step.key">
                  <span v-if="step.operator" class="slip-calc-op">{{ step.operator }}</span>
                  <div class="slip-calc-block">
                    <span class="slip-calc-expr">{{ step.expression }}</span>
                    <span class="slip-calc-result">= {{ fmtMoney(step.amount) }}</span>
                    <span class="slip-calc-caption">{{ step.caption }}</span>
                  </div>
                </template>
                <span class="slip-calc-op">=</span>
                <div class="slip-calc-block slip-calc-block--total">
                  <span class="slip-calc-expr">合计</span>
                  <span class="slip-calc-result slip-calc-result--total">{{
                    fmtMoney(emp.calc.netPay)
                  }}</span>
                  <span class="slip-calc-caption">实发工资</span>
                </div>
              </div>
            </div>

            <p v-if="emp.is_ceo" class="slip-note">注：销售额为当月全员合计。</p>
          </div>

          <div class="slip-cut slip-cut--bottom" aria-hidden="true"></div>
        </div>

        <div class="payslip-actions">
          <BaseButton
            v-if="!emp.is_ceo"
            :loading="copyingId === emp.id"
            @click="copyShareLink(emp)"
          >
            {{
              copyingId === emp.id
                ? '复制中…'
                : copyOkId === emp.id
                  ? '已复制链接'
                  : '复制员工填报链接'
            }}
          </BaseButton>
          <BaseButton type="primary" :loading="exportingId === emp.id" @click="exportSlip(emp)">
            {{ exportingId === emp.id ? '生成中…' : '导出工资条图片' }}
          </BaseButton>
        </div>
      </article>
    </div>
  </ContentWrap>
</template>

<style scoped>
.payslip-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.payslip-doc {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* 传统横条工资条 — 深绿护眼 */
.slip-strip {
  background: linear-gradient(180deg, #163d31 0%, #122f26 100%);
  color: #e8f7f0;
  font-family: 'SimSun', 'Songti SC', 'STSong', serif;
  border: 1px solid rgba(110, 231, 183, 0.2);
  border-radius: 8px;
  box-shadow: 0 4px 18px rgba(8, 28, 22, 0.28);
}

.slip-cut {
  height: 10px;
  background-image: repeating-linear-gradient(
    90deg,
    rgba(167, 243, 208, 0.75) 0,
    rgba(167, 243, 208, 0.75) 6px,
    transparent 6px,
    transparent 12px
  );
  background-size: 12px 2px;
  background-position: center;
  background-repeat: repeat-x;
}

.slip-cut--top {
  margin-bottom: 6px;
}

.slip-cut--bottom {
  margin-top: 6px;
}

.slip-body {
  padding: 4px 8px 8px;
}

.slip-title {
  margin: 0 0 10px;
  text-align: center;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0.35em;
  padding-left: 0.35em;
  color: #f0fdf8;
}

.slip-meta {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 16px;
  margin-bottom: 8px;
  font-size: 13px;
}

.slip-meta-right strong {
  font-weight: 700;
  min-width: 1.5em;
  display: inline-block;
  text-align: center;
}

.slip-table-wrap {
  overflow-x: auto;
}

.slip-table {
  width: 100%;
  min-width: 900px;
  border-collapse: collapse;
  table-layout: fixed;
  font-size: 13px;
}

.slip-table th,
.slip-table td {
  border: 1px solid rgba(110, 231, 183, 0.32);
  padding: 6px 4px;
  text-align: center;
  vertical-align: middle;
  line-height: 1.35;
  word-break: break-all;
  color: #e8f7f0;
}

.slip-table th {
  font-weight: 700;
  background: rgba(8, 28, 22, 0.45);
  color: #d1fae5;
}

.group-head {
  font-size: 13px;
}

.sub-head {
  font-size: 12px;
  font-weight: 600;
}

.col-name {
  width: 72px;
}

.col-base {
  width: 88px;
}

.col-total {
  width: 92px;
}

.col-net {
  width: 80px;
}

.cell-name {
  font-weight: 700;
}

.cell-num,
.cell-num :deep(*) {
  font-variant-numeric: tabular-nums;
  font-size: 12px;
}

.cell-money {
  padding: 4px 2px;
}

.cell-empty,
.cell-dash {
  color: #7fb89f;
}

.pay-input {
  width: 100%;
  max-width: 76px;
  min-height: 24px;
  border: none;
  border-bottom: 1px solid rgba(110, 231, 183, 0.45);
  background: transparent;
  text-align: center;
  font-size: 12px;
  font-family: inherit;
  font-variant-numeric: tabular-nums;
  padding: 0 2px;
  color: #f0fdf8;
}

.pay-input::placeholder {
  color: #6b9f88;
}

.pay-input:focus {
  outline: none;
  border-bottom-color: #6ee7b7;
  background: rgba(8, 28, 22, 0.35);
}

.slip-note {
  margin: 6px 0 0;
  font-size: 11px;
  color: #9fd4bf;
  font-family: inherit;
}

.slip-calc {
  margin-top: 10px;
  padding: 10px 12px;
  border: 1px dashed rgba(110, 231, 183, 0.35);
  border-radius: 6px;
  background: rgba(8, 28, 22, 0.28);
  overflow-x: auto;
}

.slip-calc-flow {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 6px 4px;
  min-width: min-content;
  font-family: inherit;
}

.slip-calc-eq-label {
  align-self: center;
  font-size: 12px;
  font-weight: 700;
  color: #ecfdf5;
  white-space: nowrap;
  padding-top: 2px;
}

.slip-calc-op {
  align-self: flex-start;
  padding-top: 2px;
  font-size: 13px;
  font-weight: 700;
  color: #a7f3d0;
  line-height: 1.4;
}

.slip-calc-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  min-width: 88px;
  max-width: 140px;
  padding: 4px 6px;
  border-radius: 4px;
  background: rgba(8, 28, 22, 0.22);
}

.slip-calc-block--total {
  background: rgba(110, 231, 183, 0.12);
  border: 1px solid rgba(110, 231, 183, 0.25);
}

.slip-calc-expr {
  font-size: 11px;
  line-height: 1.35;
  color: #ecfdf5;
  text-align: center;
  font-variant-numeric: tabular-nums;
  word-break: break-word;
}

.slip-calc-result {
  font-size: 12px;
  font-weight: 700;
  color: #d1fae5;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.slip-calc-result--total {
  font-size: 13px;
  color: #6ee7b7;
}

.slip-calc-caption {
  font-size: 10px;
  line-height: 1.3;
  color: #9fd4bf;
  text-align: center;
}

.cell-net-pay {
  font-weight: 700;
  color: #6ee7b7;
}

.payslip-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
  padding: 0 2px;
}

@media (max-width: 640px) {
  .slip-meta {
    flex-direction: column;
    gap: 4px;
  }

  .slip-title {
    font-size: 18px;
  }
}
</style>
