<script setup lang="ts">
// 月度目标：每个月一个全公司 GMV 目标，职员端数据大屏「本月目标」读这里（只有 admin 能改）
import { onMounted, reactive, ref } from 'vue'
import { ElAlert, ElButton, ElInput, ElMessage, ElTable, ElTableColumn, ElTag } from 'element-plus'
import ContentWrap from '@/components/ContentWrap.vue'
import { listGmvTargets, saveGmvTarget, type GmvTargetRow } from '@/api/modules/gmvTarget'
import { formatRequestError } from '@/utils/format'

defineOptions({ name: 'ManageGmvTarget' })

const rows = ref<GmvTargetRow[]>([])
const loading = ref(false)
const loadErr = ref('')
const drafts = reactive<Record<string, string>>({})
const saving = reactive<Record<string, boolean>>({})

const money = (v: number | null) =>
  v === null || v === undefined ? '—' : `¥${Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

function apply(list: GmvTargetRow[]) {
  rows.value = list
  for (const r of list) drafts[r.month] = r.target === null ? '' : String(r.target)
}

async function load() {
  loading.value = true
  loadErr.value = ''
  try {
    const { data } = await listGmvTargets()
    apply(data.rows)
  } catch (e) {
    loadErr.value = formatRequestError(e, '加载失败')
  } finally {
    loading.value = false
  }
}

const dirty = (r: GmvTargetRow) => (drafts[r.month] ?? '').trim().replace(/,/g, '') !== (r.target === null ? '' : String(r.target))

async function save(r: GmvTargetRow) {
  saving[r.month] = true
  try {
    const { data } = await saveGmvTarget(r.month, (drafts[r.month] ?? '').trim())
    apply(data.rows)
    ElMessage.success(drafts[r.month] ? `${r.month} 目标已保存` : `${r.month} 目标已清空`)
  } catch (e) {
    ElMessage.error(formatRequestError(e, '保存失败'))
  } finally {
    saving[r.month] = false
  }
}

onMounted(load)
</script>

<template>
  <ContentWrap title="月度目标">
    <p class="hint">
      每个月填一个全公司 GMV 目标（元）。职员端数据大屏选「本月」时，顶部会显示目标完成度、每天还需收多少和月底预测；不填目标的月份只显示月底预测。
    </p>
    <ElAlert v-if="loadErr" :title="loadErr" type="error" show-icon :closable="false" class="mb" />
    <ElTable v-loading="loading" :data="rows" stripe style="max-width: 760px">
      <ElTableColumn label="月份" width="130">
        <template #default="{ row }">
          {{ row.month }}
          <ElTag v-if="row.is_current" size="small" type="success" class="ml">本月</ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn label="GMV 目标（元）" min-width="230">
        <template #default="{ row }">
          <div class="edit">
            <ElInput v-model="drafts[row.month]" placeholder="不设目标就留空" clearable style="width: 150px" @keyup.enter="save(row)" />
            <ElButton size="small" type="primary" :disabled="!dirty(row)" :loading="saving[row.month]" @click="save(row)">保存</ElButton>
          </div>
        </template>
      </ElTableColumn>
      <ElTableColumn label="实际 GMV" min-width="130">
        <template #default="{ row }">
          <span class="mono">{{ row.is_future ? '—' : money(row.gmv) }}</span>
        </template>
      </ElTableColumn>
      <ElTableColumn label="完成度" width="110">
        <template #default="{ row }">
          <span v-if="row.done_pct === null" class="muted">—</span>
          <span v-else class="mono" :class="row.done_pct >= 100 ? 'ok' : row.is_current ? '' : 'bad'">{{ row.done_pct }}%</span>
        </template>
      </ElTableColumn>
      <ElTableColumn label="最后修改" prop="updated_by" width="110" />
    </ElTable>
  </ContentWrap>
</template>

<style scoped>
.hint {
  margin: 0 0 14px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.mb {
  margin-bottom: 12px;
}
.ml {
  margin-left: 6px;
}
.edit {
  display: flex;
  align-items: center;
  gap: 8px;
}
.mono {
  font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace;
  font-variant-numeric: tabular-nums;
}
.muted {
  color: var(--el-text-color-secondary);
}
.ok {
  color: #16a34a;
  font-weight: 700;
}
.bad {
  color: #dc2626;
  font-weight: 700;
}
</style>
