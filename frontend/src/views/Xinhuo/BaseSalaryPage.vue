<script setup lang="tsx">
import { computed, onMounted, ref, watch } from 'vue'
import { ElForm, ElFormItem, ElInput, ElOption, ElSelect, ElMessage } from 'element-plus'
import { ContentWrap } from '@/components/ContentWrap'
import { Table, TableColumn } from '@/components/Table'
import { BaseButton } from '@/components/Button'
import api from '@/api/xinhuo/client'

defineOptions({ name: 'BaseSalary' })

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const saveOk = ref('')
const payload = ref<any>(null)

const formUserId = ref('')
const formSalary = ref('')
const formYinliSeparate = ref('no')
const formYinliRate = ref('')
const formHasSocial = ref('no')
const formSocialAmount = ref('')

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

function parseRateInput(s: unknown) {
  const v = parseFloat(String(s ?? '').replace(/,/g, ''))
  return Number.isFinite(v) && v > 0 && v <= 100 ? v : null
}

const personnel = computed(() => payload.value?.personnel || [])
const records = computed(() => payload.value?.records || [])
const currentByUserId = computed(() => {
  const map: Record<number, any> = {}
  for (const row of payload.value?.current || []) {
    map[row.user_id] = row
  }
  return map
})

const showYinliRate = computed(() => formYinliSeparate.value === 'yes')
const showSocialAmount = computed(() => formHasSocial.value === 'yes')

function applyCurrentForUser(userId: string) {
  const row = currentByUserId.value[Number(userId)]
  if (!row) {
    formSalary.value = ''
    formYinliSeparate.value = 'no'
    formYinliRate.value = ''
    formHasSocial.value = 'no'
    formSocialAmount.value = ''
    return
  }
  formSalary.value = row.base_salary != null ? String(row.base_salary) : ''
  formYinliSeparate.value = row.yinli_separate ? 'yes' : 'no'
  formYinliRate.value =
    row.yinli_separate && row.yinli_commission_rate_percent != null
      ? String(row.yinli_commission_rate_percent)
      : ''
  formHasSocial.value = row.has_social_insurance ? 'yes' : 'no'
  formSocialAmount.value =
    row.has_social_insurance && row.social_insurance_amount != null
      ? String(row.social_insurance_amount)
      : ''
}

watch(formUserId, (id) => {
  if (id) applyCurrentForUser(id)
})

async function load() {
  loading.value = true
  error.value = ''
  saveOk.value = ''
  try {
    const { data } = await api.get('/base-salary/')
    payload.value = data
    if (formUserId.value) {
      applyCurrentForUser(formUserId.value)
    }
  } catch (e: any) {
    payload.value = null
    const d = e?.response?.data
    error.value =
      (typeof d === 'string' && d) || d?.detail || e?.message || '加载失败'
    ElMessage.error(error.value)
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (!formUserId.value) {
    error.value = '请选择人员'
    ElMessage.warning(error.value)
    return
  }
  if (formYinliSeparate.value === 'yes' && parseRateInput(formYinliRate.value) == null) {
    error.value = '请填写引力币提成比例（0～100）'
    ElMessage.warning(error.value)
    return
  }
  if (formHasSocial.value === 'yes' && parseMoneyInput(formSocialAmount.value) <= 0) {
    error.value = '请填写社保金额'
    ElMessage.warning(error.value)
    return
  }
  saving.value = true
  error.value = ''
  saveOk.value = ''
  try {
    const body: Record<string, unknown> = {
      user_id: Number(formUserId.value),
      base_salary: parseMoneyInput(formSalary.value),
      yinli_separate: formYinliSeparate.value === 'yes',
      has_social_insurance: formHasSocial.value === 'yes'
    }
    if (formYinliSeparate.value === 'yes') {
      body.yinli_commission_rate_percent = parseRateInput(formYinliRate.value)
    }
    if (formHasSocial.value === 'yes') {
      body.social_insurance_amount = parseMoneyInput(formSocialAmount.value)
    }
    const { data } = await api.post('/base-salary/', body)
    payload.value = data
    applyCurrentForUser(formUserId.value)
    saveOk.value = '已保存，记录已更新。'
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

const columns: TableColumn[] = [
  { field: 'created_at', label: '录入时间', minWidth: 168 },
  { field: 'username', label: '人员', minWidth: 100 },
  {
    field: 'base_salary',
    label: '工资（元）',
    minWidth: 120,
    align: 'right',
    slots: {
      default: (data) => <span class="tabular-nums font-600">{fmtMoney(data.row.base_salary)}</span>
    }
  },
  {
    field: 'yinli_separate_label',
    label: '引力币单独算',
    minWidth: 120,
    formatter: (_r, _c, v) => v || '否'
  },
  {
    field: 'social_insurance_label',
    label: '是否有社保',
    minWidth: 110,
    formatter: (_r, _c, v) => v || '否'
  },
  {
    field: 'created_by',
    label: '录入人',
    minWidth: 100,
    formatter: (_r, _c, v) => v || '—'
  }
]

onMounted(load)
</script>

<template>
  <ContentWrap>
    <div class="mb-16px">
      <p class="text-14px text-[var(--el-text-color-secondary)] m-0 leading-relaxed">
        选择人员并填写基本工资；引力币、社保如需单独配置请选择「是」并填写对应金额或比例。保存后会在下方列表中显示记录。
      </p>
    </div>

    <ElForm inline label-width="auto" @submit.prevent="submit">
      <ElFormItem label="人员" required>
        <ElSelect
          v-model="formUserId"
          placeholder="请选择"
          clearable
          style="width: 160px"
          :disabled="loading || saving"
        >
          <ElOption v-for="p in personnel" :key="p.id" :label="p.username" :value="String(p.id)" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem label="工资（元）">
        <ElInput
          v-model="formSalary"
          placeholder="0.00"
          style="width: 140px"
          :disabled="loading || saving"
        />
      </ElFormItem>
      <ElFormItem label="引力币单独算">
        <ElSelect
          v-model="formYinliSeparate"
          style="width: 100px"
          :disabled="loading || saving"
        >
          <ElOption label="否" value="no" />
          <ElOption label="是" value="yes" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem v-if="showYinliRate" label="引力币提成（%）">
        <ElInput
          v-model="formYinliRate"
          placeholder="如 10"
          style="width: 120px"
          :disabled="loading || saving"
        >
          <template #suffix>%</template>
        </ElInput>
      </ElFormItem>
      <ElFormItem label="是否有社保">
        <ElSelect v-model="formHasSocial" style="width: 100px" :disabled="loading || saving">
          <ElOption label="否" value="no" />
          <ElOption label="是" value="yes" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem v-if="showSocialAmount" label="社保金额（元）">
        <ElInput
          v-model="formSocialAmount"
          placeholder="0.00"
          style="width: 140px"
          :disabled="loading || saving"
        />
      </ElFormItem>
      <ElFormItem>
        <BaseButton type="primary" :loading="saving" :disabled="loading" @click="submit">
          保存
        </BaseButton>
      </ElFormItem>
    </ElForm>

    <div class="flex items-center justify-between mb-12px mt-20px">
      <span class="text-16px font-600">录入记录</span>
      <BaseButton :loading="loading" @click="load">刷新</BaseButton>
    </div>

    <Table :columns="columns" :data="records" :loading="loading" empty-text="暂无记录，填写保存后将显示在这里。" />
  </ContentWrap>
</template>
