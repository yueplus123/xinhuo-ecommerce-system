<script setup lang="ts">
// 钱包余额：新增表单 + 记录表 + 编辑弹窗（新增/编辑共用 WalletFields）
import { computed, onMounted, ref } from 'vue'
import {
  ElAlert,
  ElButton,
  ElCard,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElTable,
  ElTableColumn
} from 'element-plus'
import { api, type WalletRow } from '@/api/xinhuo/ledger'
import { formatBeijing, formatMoneyOnBlur, notifyWalletUpdated, parseMoney, sanitizeMoneyInput } from './ledgerUtils'

const FIELDS = [
  { key: 'wechat', label: '微信' },
  { key: 'alipay', label: '支付宝' },
  { key: 'card', label: '卡片' },
  { key: 'pocket', label: '小荷包' }
] as const
type Key = (typeof FIELDS)[number]['key']
type Money = Record<Key, string>

const emptyMoney = (): Money => ({ wechat: '', alipay: '', card: '', pocket: '' })
const total = (m: Money) => (Math.round(FIELDS.reduce((a, f) => a + parseMoney(m[f.key]), 0) * 100) / 100).toFixed(2)
const toBody = (m: Money) => ({
  wechat: parseMoney(m.wechat),
  alipay: parseMoney(m.alipay),
  card: parseMoney(m.card),
  pocket: parseMoney(m.pocket)
})

const rows = ref<WalletRow[]>([])
const loadError = ref('')
async function load() {
  try {
    rows.value = [...(await api.walletList())].reverse()
    loadError.value = ''
  } catch (e) {
    loadError.value = (e as Error).message
  }
}
onMounted(load)
async function afterMutation() {
  await load()
  notifyWalletUpdated()
}

// ---------- 新增 ----------
const form = ref<Money>(emptyMoney())
const saving = ref(false)
async function submit() {
  saving.value = true
  try {
    await api.walletCreate({ recordAt: formatBeijing(), ...toBody(form.value) })
    form.value = emptyMoney()
    ElMessage.success('已保存')
    await afterMutation()
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    saving.value = false
  }
}

// ---------- 编辑 ----------
const editOpen = ref(false)
const editRow = ref<WalletRow | null>(null)
const editAt = ref('')
const editForm = ref<Money>(emptyMoney())
const editSaving = ref(false)
const fmt = (v: unknown) => (Number.isFinite(Number(v)) ? Number(v) : 0).toFixed(2)

function openEdit(r: WalletRow) {
  editRow.value = r
  editAt.value = r.recordAt
  editForm.value = { wechat: fmt(r.wechat), alipay: fmt(r.alipay), card: fmt(r.card), pocket: fmt(r.pocket) }
  editOpen.value = true
}
async function saveEdit() {
  if (!editRow.value) return
  editSaving.value = true
  try {
    await api.walletUpdate(editRow.value.id, { recordAt: editAt.value, ...toBody(editForm.value) })
    editOpen.value = false
    await afterMutation()
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    editSaving.value = false
  }
}

async function remove(r: WalletRow) {
  try {
    await ElMessageBox.confirm(`确定删除 ${r.recordAt} 这条记录？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await api.walletDelete(r.id)
    await afterMutation()
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

const totalNew = computed(() => total(form.value))
const totalEdit = computed(() => total(editForm.value))
</script>

<template>
  <div>
    <ElAlert v-if="loadError" type="error" :closable="false" class="mb-12px" :title="loadError" />

    <ElCard shadow="never" class="mb-16px">
      <ElForm inline @submit.prevent="submit">
        <ElFormItem v-for="f in FIELDS" :key="f.key" :label="f.label">
          <ElInput
            v-model="form[f.key]"
            inputmode="decimal"
            autocomplete="off"
            style="width: 130px"
            @input="form[f.key] = sanitizeMoneyInput($event)"
            @blur="form[f.key] = formatMoneyOnBlur(form[f.key])"
          />
        </ElFormItem>
        <ElFormItem label="总计（自动）"><ElInput :model-value="totalNew" readonly style="width: 130px" /></ElFormItem>
        <ElFormItem><ElButton type="primary" :loading="saving" native-type="submit">保存本条</ElButton></ElFormItem>
      </ElForm>
    </ElCard>

    <ElCard shadow="never">
      <template #header>
        <div class="head">
          <span>钱包余额记录</span>
          <ElButton size="small" @click="load">刷新</ElButton>
        </div>
      </template>
      <ElTable :data="rows" border stripe empty-text="暂无记录">
        <ElTableColumn prop="recordAt" label="记录日期" min-width="160" />
        <ElTableColumn prop="wechat" label="微信" />
        <ElTableColumn prop="alipay" label="支付宝" />
        <ElTableColumn prop="card" label="卡片" />
        <ElTableColumn prop="pocket" label="小荷包" />
        <ElTableColumn prop="total" label="总计" />
        <ElTableColumn label="操作" width="120">
          <template #default="{ row }">
            <ElButton link type="primary" @click="openEdit(row)">修改</ElButton>
            <ElButton link type="danger" @click="remove(row)">删除</ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
    </ElCard>

    <ElDialog v-model="editOpen" title="编辑钱包余额" width="460px" destroy-on-close>
      <ElForm label-width="110px">
        <ElFormItem label="记录日期"><ElInput v-model="editAt" /></ElFormItem>
        <ElFormItem v-for="f in FIELDS" :key="f.key" :label="f.label">
          <ElInput
            v-model="editForm[f.key]"
            inputmode="decimal"
            autocomplete="off"
            @input="editForm[f.key] = sanitizeMoneyInput($event)"
            @blur="editForm[f.key] = formatMoneyOnBlur(editForm[f.key])"
          />
        </ElFormItem>
        <ElFormItem label="总计"><ElInput :model-value="totalEdit" readonly /></ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="editOpen = false">取消</ElButton>
        <ElButton type="primary" :loading="editSaving" @click="saveEdit">保存</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.mb-12px {
  margin-bottom: 12px;
}
.mb-16px {
  margin-bottom: 16px;
}
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
