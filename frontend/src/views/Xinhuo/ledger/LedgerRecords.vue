<script setup lang="ts">
// 记账填写：手动补记表单 + 员工分页 + 记录表（多选批量清账/撤销/恢复/删除）+ 编辑 + 清账小票
import { computed, onMounted, ref, watch } from 'vue'
import {
  ElAlert,
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElTabPane,
  ElTabs,
  ElTable,
  ElTableColumn,
  ElTag,
  ElPagination,
  ElAutocomplete
} from 'element-plus'
import { api, type LedgerMeta, type LedgerRow } from '@/api/xinhuo/ledger'
import {
  buildReceiptText,
  digit,
  formatBeijing,
  formatLedgerBusinessLine,
  isLedgerUnsettled,
  ledgerStatusTagType,
  notifyLedgerUpdated,
  type ReceiptLine
} from './ledgerUtils'

const ALL = '__all__'

// ---------- 数据 ----------
const rows = ref<LedgerRow[]>([])
const meta = ref<LedgerMeta>({ employees: [], chats: [] })
const loadError = ref('')
const search = ref('')
const employeeFilter = ref(ALL)
const page = ref(1)
const pageSize = ref(50)
const selected = ref<LedgerRow[]>([])
const tableRef = ref<InstanceType<typeof ElTable>>()
const busy = ref(false)

async function load() {
  try {
    rows.value = await api.ledgerList()
    loadError.value = ''
  } catch (e) {
    loadError.value = (e as Error).message
  }
}
onMounted(() => {
  void load()
  api.ledgerMeta().then((m) => (meta.value = m)).catch(() => {})
})

async function afterMutation() {
  await load()
  notifyLedgerUpdated()
}

// ---------- 筛选 / 分页 ----------
const employeeTabs = computed(() => {
  const names = new Set(rows.value.map((r) => (r.employeeName || '').trim()).filter(Boolean))
  return [...names].sort((a, b) => a.localeCompare(b, 'zh-CN'))
})
const filtered = computed(() => {
  let list = rows.value
  if (employeeFilter.value !== ALL) {
    list = list.filter((r) => (r.employeeName || '').trim() === employeeFilter.value)
  }
  const q = search.value.trim().toLowerCase()
  if (!q) return list
  return list.filter((r) =>
    [
      formatLedgerBusinessLine(r),
      r.amount,
      r.giveAmount,
      r.takeAmount,
      r.profit,
      r.employeeName,
      r.chatName,
      r.statusLabel,
      r.recordNo,
      r.recordAt
    ]
      .join(' ')
      .toLowerCase()
      .includes(q)
  )
})
const paged = computed(() => filtered.value.slice((page.value - 1) * pageSize.value, page.value * pageSize.value))
watch([search, employeeFilter, pageSize], () => (page.value = 1))

const sums = computed(() => {
  const s = { amount: 0, give: 0, take: 0, profit: 0 }
  for (const r of filtered.value) {
    if (!isLedgerUnsettled(r)) continue
    s.amount += Number(r.amount) || 0
    s.give += Number(r.giveAmount) || 0
    s.take += Number(r.takeAmount) || 0
    s.profit += Number(r.profit) || 0
  }
  return s
})

// ---------- 表格选择：仅未清账行可选 ----------
const selectable = (r: LedgerRow) => isLedgerUnsettled(r)
const selectedIds = computed(() => selected.value.map((r) => r.id))
function onRowClick(r: LedgerRow) {
  if (selectable(r)) tableRef.value?.toggleRowSelection(r)
}
watch(rows, () => {
  // 数据刷新后清空选择，避免引用到旧行
  tableRef.value?.clearSelection()
})

// ---------- 手动补记 ----------
const emptyForm = () => ({ project: '', amount: '', give: '', take: '', profit: '', employee: '', chat: '' })
const form = ref(emptyForm())
const submitting = ref(false)
const suggest = (list: string[]) => (q: string, cb: (r: { value: string }[]) => void) =>
  cb(list.filter((x) => x.toLowerCase().includes(q.toLowerCase())).map((value) => ({ value })))

async function submit() {
  if (submitting.value) return
  const f = form.value
  const biz = f.project.trim()
  if (!biz) return void ElMessage.warning('请填写项目名')
  if (!f.employee.trim() || !f.chat.trim()) return void ElMessage.warning('请选择提交人与群')
  const [a, g, t, p] = [f.amount, f.give, f.take, f.profit].map((x) => Number(x) || 0)
  if (!a && !g && !t && !p) return void ElMessage.warning('金额、给你、给我、利润至少填一项')
  submitting.value = true
  try {
    const ts = formatBeijing()
    await api.ledgerCreate({
      recordAt: ts,
      recordNo: ts,
      businessName: biz,
      amount: a,
      giveAmount: g,
      takeAmount: t,
      profit: p,
      employeeName: f.employee.trim(),
      chatName: f.chat.trim()
    })
    form.value = { ...emptyForm(), employee: f.employee, chat: f.chat }
    ElMessage.success('添加成功')
    await afterMutation()
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    submitting.value = false
  }
}

// ---------- 批量操作 ----------
const receipt = ref<{ settledAt: string; lines: ReceiptLine[] } | null>(null)

async function bulkSetStatus(status: LedgerRow['status']) {
  if (!selectedIds.value.length) return
  busy.value = true
  try {
    const snapshot = [...selected.value]
    await api.ledgerBulkStatus(selectedIds.value, status)
    if (status === 'PROCESSED') {
      receipt.value = {
        settledAt: formatBeijing(),
        lines: snapshot.map((r) => ({
          recordAt: r.recordAt,
          business: formatLedgerBusinessLine(r),
          amount: Number(r.amount) || 0,
          give: Number(r.giveAmount) || 0,
          take: Number(r.takeAmount) || 0,
          profit: Number(r.profit) || 0
        }))
      }
    }
    await afterMutation()
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    busy.value = false
  }
}

async function removeRows(targets: LedgerRow[]) {
  if (!targets.length) return
  const label = targets.length === 1 ? `「${formatLedgerBusinessLine(targets[0])}」这条记录` : `选中的 ${targets.length} 条记录`
  try {
    await ElMessageBox.confirm(`确定删除${label}？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  busy.value = true
  try {
    await Promise.all(targets.map((r) => api.ledgerDelete(r.id)))
    await afterMutation()
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    busy.value = false
  }
}

// ---------- 编辑 ----------
const editOpen = ref(false)
const editRow = ref<LedgerRow | null>(null)
const editForm = ref({ project: '', recordAt: '', recordNo: '', amount: '', give: '', take: '', profit: '', employee: '', chat: '' })
const editSaving = ref(false)

function openEdit(r: LedgerRow) {
  editRow.value = r
  editForm.value = {
    project: formatLedgerBusinessLine(r),
    recordAt: r.recordAt,
    recordNo: r.recordNo || r.recordAt,
    amount: String(r.amount ?? 0),
    give: String(r.giveAmount),
    take: String(r.takeAmount),
    profit: String(r.profit),
    employee: r.employeeName || '',
    chat: r.chatName || ''
  }
  editOpen.value = true
}
async function saveEdit() {
  const r = editRow.value
  const f = editForm.value
  if (!r) return
  if (!f.project.trim()) return void ElMessage.warning('请填写项目名')
  editSaving.value = true
  try {
    await api.ledgerUpdate(r.id, {
      recordAt: f.recordAt,
      recordNo: f.recordNo,
      businessName: f.project.trim(),
      amount: Number(f.amount) || 0,
      giveAmount: Number(f.give) || 0,
      takeAmount: Number(f.take) || 0,
      profit: Number(f.profit) || 0,
      employeeName: f.employee.trim(),
      chatName: f.chat.trim()
    })
    editOpen.value = false
    await afterMutation()
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    editSaving.value = false
  }
}

// ---------- 清账小票 ----------
const receiptOpen = computed({
  get: () => receipt.value != null,
  set: (v) => {
    if (!v) receipt.value = null
  }
})
const receiptText = computed(() => (receipt.value ? buildReceiptText(receipt.value.settledAt, receipt.value.lines) : ''))
const receiptSum = (k: keyof ReceiptLine) =>
  (receipt.value?.lines ?? []).reduce((a, r) => a + (Number(r[k]) || 0), 0)
async function copyReceipt() {
  try {
    await navigator.clipboard.writeText(receiptText.value)
    ElMessage.success('已复制')
  } catch {
    ElMessage.warning('复制失败，请手动选择文本')
  }
}
</script>

<template>
  <div>
    <ElAlert v-if="loadError" type="error" :closable="false" class="mb-12px" :title="loadError" />

    <ElInput v-model="search" clearable placeholder="搜索项目 / 提交人 / 群 / 单号…" class="mb-12px search-input" />

    <ElForm inline class="manual-row" @submit.prevent="submit">
      <span class="manual-label">手动补记</span>
      <ElFormItem><ElInput v-model="form.project" placeholder="项目" style="width: 140px" /></ElFormItem>
      <ElFormItem><ElInput v-model="form.amount" inputmode="decimal" placeholder="金额" style="width: 90px" /></ElFormItem>
      <ElFormItem><ElInput v-model="form.give" inputmode="decimal" placeholder="给你" style="width: 90px" /></ElFormItem>
      <ElFormItem><ElInput v-model="form.take" inputmode="decimal" placeholder="给我" style="width: 90px" /></ElFormItem>
      <ElFormItem><ElInput v-model="form.profit" inputmode="decimal" placeholder="利润" style="width: 90px" /></ElFormItem>
      <ElFormItem>
        <ElAutocomplete v-model="form.employee" :fetch-suggestions="suggest(meta.employees)" placeholder="提交人" style="width: 120px" />
      </ElFormItem>
      <ElFormItem>
        <ElAutocomplete v-model="form.chat" :fetch-suggestions="suggest(meta.chats)" placeholder="群" style="width: 140px" />
      </ElFormItem>
      <ElFormItem><ElButton type="primary" :loading="submitting" native-type="submit">添加</ElButton></ElFormItem>
    </ElForm>

    <ElTabs v-model="employeeFilter">
      <ElTabPane label="全部员工" :name="ALL" />
      <ElTabPane v-for="n in employeeTabs" :key="n" :label="n" :name="n" />
    </ElTabs>

    <div class="sum-bar">
      未清账合计：金额 <b>{{ digit(sums.amount) }}</b> · 给你 <b>{{ digit(sums.give) }}</b> · 给我
      <b>{{ digit(sums.take) }}</b> · 利润
      <b :class="sums.profit >= 0 ? 'pos' : 'neg'">{{ digit(sums.profit) }}</b>
    </div>

    <ElTable
      ref="tableRef"
      :data="paged"
      border
      stripe
      empty-text="暂无"
      row-key="id"
      @selection-change="(v: LedgerRow[]) => (selected = v)"
      @row-click="onRowClick"
    >
      <ElTableColumn type="selection" width="46" :selectable="selectable" />
      <ElTableColumn prop="employeeName" label="提交人" width="100">
        <template #default="{ row }">{{ row.employeeName || '—' }}</template>
      </ElTableColumn>
      <ElTableColumn label="项目" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">{{ formatLedgerBusinessLine(row) }}</template>
      </ElTableColumn>
      <ElTableColumn prop="amount" label="金额" width="90" />
      <ElTableColumn prop="giveAmount" label="给你" width="90" />
      <ElTableColumn prop="takeAmount" label="给我" width="90" />
      <ElTableColumn label="利润" width="90">
        <template #default="{ row }"><span :class="row.profit >= 0 ? 'pos' : 'neg'">{{ row.profit }}</span></template>
      </ElTableColumn>
      <ElTableColumn label="群" min-width="120" show-overflow-tooltip>
        <template #default="{ row }">{{ row.chatName || '—' }}</template>
      </ElTableColumn>
      <ElTableColumn label="状态" width="90">
        <template #default="{ row }"><ElTag :type="ledgerStatusTagType(row)" size="small">{{ row.statusLabel }}</ElTag></template>
      </ElTableColumn>
      <ElTableColumn label="时间/单号" min-width="160">
        <template #default="{ row }">{{ row.recordNo || row.recordAt }}</template>
      </ElTableColumn>
      <ElTableColumn label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <ElButton link type="primary" @click.stop="openEdit(row)">编辑</ElButton>
          <ElButton link type="danger" @click.stop="removeRows([row])">删除</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>

    <div class="pager">
      <span class="muted">共 {{ filtered.length }} 条</span>
      <ElPagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="filtered.length"
        :page-sizes="[20, 50, 100, 500]"
        layout="sizes, prev, pager, next"
        background
      />
    </div>

    <div class="actions">
      <ElButton :disabled="!selectedIds.length || busy" @click="bulkSetStatus('REVERSED')">撤销选中</ElButton>
      <ElButton type="primary" :disabled="!selectedIds.length || busy" @click="bulkSetStatus('PROCESSED')">标记已处理</ElButton>
      <ElButton :disabled="!selectedIds.length || busy" @click="bulkSetStatus('ACTIVE')">恢复有效</ElButton>
      <ElButton :disabled="selected.length !== 1" @click="openEdit(selected[0])">编辑记录</ElButton>
      <ElButton type="danger" plain :disabled="!selectedIds.length || busy" @click="removeRows(selected)">删除选中</ElButton>
      <ElButton @click="load">刷新</ElButton>
    </div>

    <ElDialog v-model="editOpen" title="编辑记录" width="560px" destroy-on-close>
      <p class="muted mb-12px">修改仅保存在薪火系统，不会回传机器人；保存后「数据大屏」会自动更新。</p>
      <ElForm label-width="84px">
        <ElFormItem label="项目"><ElInput v-model="editForm.project" /></ElFormItem>
        <ElFormItem label="记录时间"><ElInput v-model="editForm.recordAt" /></ElFormItem>
        <ElFormItem label="时间/单号"><ElInput v-model="editForm.recordNo" /></ElFormItem>
        <ElFormItem label="金额"><ElInput v-model="editForm.amount" inputmode="decimal" /></ElFormItem>
        <ElFormItem label="给你"><ElInput v-model="editForm.give" inputmode="decimal" /></ElFormItem>
        <ElFormItem label="给我"><ElInput v-model="editForm.take" inputmode="decimal" /></ElFormItem>
        <ElFormItem label="利润"><ElInput v-model="editForm.profit" inputmode="decimal" /></ElFormItem>
        <ElFormItem label="提交人"><ElInput v-model="editForm.employee" /></ElFormItem>
        <ElFormItem label="群"><ElInput v-model="editForm.chat" /></ElFormItem>
        <ElFormItem label="状态"><ElInput :model-value="editRow?.statusLabel" readonly /></ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="editOpen = false">取消</ElButton>
        <ElButton type="primary" :loading="editSaving" @click="saveEdit">保存</ElButton>
      </template>
    </ElDialog>

    <ElDialog v-model="receiptOpen" title="记账 · 清账凭证" width="520px">
      <div v-if="receipt" class="receipt">
        <div class="receipt-row"><span>清账时间</span><b>{{ receipt.settledAt }}</b></div>
        <div class="receipt-row"><span>本次笔数</span><b>{{ receipt.lines.length }} 笔</b></div>
        <hr />
        <div v-for="(r, i) in receipt.lines" :key="`${r.recordAt}-${i}`" class="receipt-item">
          <div class="receipt-head"><span>#{{ i + 1 }}</span><span>{{ r.recordAt }}</span></div>
          <div>{{ r.business }}</div>
          <div class="receipt-nums">
            <span>金额 {{ digit(r.amount, 4) }}</span><span>给你 {{ digit(r.give, 4) }}</span>
            <span>给我 {{ digit(r.take, 4) }}</span>
            <span :class="r.profit >= 0 ? 'pos' : 'neg'">利润 {{ digit(r.profit, 4) }}</span>
          </div>
        </div>
        <hr />
        <div class="receipt-row"><span>合计 金额</span><b>{{ digit(receiptSum('amount'), 4) }}</b></div>
        <div class="receipt-row"><span>合计 给你</span><b>{{ digit(receiptSum('give'), 4) }}</b></div>
        <div class="receipt-row"><span>合计 给我</span><b>{{ digit(receiptSum('take'), 4) }}</b></div>
        <div class="receipt-row">
          <span>合计 利润</span>
          <b :class="receiptSum('profit') >= 0 ? 'pos' : 'neg'">{{ digit(receiptSum('profit'), 4) }}</b>
        </div>
      </div>
      <template #footer>
        <ElButton @click="copyReceipt">复制小票文本</ElButton>
        <ElButton type="primary" @click="receiptOpen = false">关闭</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.mb-12px {
  margin-bottom: 12px;
}
.search-input {
  max-width: 360px;
}
.manual-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0 8px;
  padding: 12px 12px 0;
  margin-bottom: 8px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
}
.manual-label {
  margin: 0 8px 18px 0;
  font-weight: 600;
}
.sum-bar {
  padding: 8px 12px;
  margin-bottom: 8px;
  font-size: 13px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
}
.pos {
  color: var(--el-color-success);
}
.neg {
  color: var(--el-color-danger);
}
.muted {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.pager {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin: 12px 0;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.receipt {
  font-size: 14px;
}
.receipt hr {
  margin: 10px 0;
  border: 0;
  border-top: 1px dashed var(--el-border-color);
}
.receipt-row {
  display: flex;
  justify-content: space-between;
  padding: 2px 0;
}
.receipt-item {
  padding: 6px 0;
}
.receipt-head {
  display: flex;
  justify-content: space-between;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.receipt-nums {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 14px;
  font-size: 13px;
}
</style>
