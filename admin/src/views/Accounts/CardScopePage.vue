<script setup lang="ts">
// 卡管家权限：给每个职员设置「可看的备注关键词」。
// 汇通卡片的备注里包含其中任意一个关键词，这个职员就能在薪火卡管家插件里看到这张卡。
// 超级管理员 / 老板 / CEO 能看全部卡；他们也可以填关键词，只用来「认领」卡（插件里这些卡算他们的，不再算无人认领）。
import { onMounted, ref } from 'vue'
import { ElAlert, ElButton, ElInput, ElMessage, ElTable, ElTableColumn, ElTag } from 'element-plus'
import ContentWrap from '@/components/ContentWrap.vue'
import { listCardScopes, saveCardScope, type CardScopeRow } from '@/api/modules/cardManager'
import { formatDateTime, formatRequestError } from '@/utils/format'

defineOptions({ name: 'ManageCardScope' })

type Row = CardScopeRow & { draft: string; saving: boolean }

const rows = ref<Row[]>([])
const loading = ref(false)

const toText = (kws: string[]) => kws.join('，')
const parse = (s: string) => [...new Set(s.split(/[\n\r,，、;；]+/).map((x) => x.trim()).filter(Boolean))]

async function load() {
  loading.value = true
  try {
    const { data } = await listCardScopes()
    rows.value = data.results.map((r) => ({ ...r, draft: toText(r.keywords), saving: false }))
  } catch (e) {
    ElMessage.error(formatRequestError(e, '加载失败'))
  } finally {
    loading.value = false
  }
}

const changed = (r: Row) => toText(parse(r.draft)) !== toText(r.keywords)

async function save(r: Row) {
  r.saving = true
  try {
    const { data } = await saveCardScope(r.id, parse(r.draft))
    Object.assign(r, data, { draft: toText(data.keywords) })
    ElMessage.success(`已保存 ${r.username} 的关键词`)
  } catch (e) {
    ElMessage.error(formatRequestError(e, '保存失败'))
  } finally {
    r.saving = false
  }
}

onMounted(load)
</script>

<template>
  <ContentWrap title="卡管家权限">
    <ElAlert type="info" :closable="false" show-icon class="mb-12px">
      卡片备注里包含任意一个关键词，这个职员就能看到这张卡（比如填「冬」，备注是“冬卡7”“胡玮 冬”的卡都能看到）。
      多个关键词用逗号分开。没填关键词的职员在插件里看不到任何卡。超级管理员 / 老板 / CEO 能看全部卡；
      他们也可以填关键词（比如老板填 hazen），只用来认领：这些卡在插件数据大屏里算他们的，也不再算「无人认领」。
    </ElAlert>
    <ElTable :data="rows" v-loading="loading" border>
      <ElTableColumn label="职员" prop="username" width="200" />
      <ElTableColumn label="可看的备注关键词" min-width="360">
        <template #default="{ row }">
          <div class="flex items-center gap-8px">
            <ElTag v-if="row.is_admin" type="success" class="shrink-0">能看全部卡</ElTag>
            <ElInput
            v-model="row.draft"
            :placeholder="row.is_admin ? '认领用，可不填，例如：hazen' : '例如：冬，苏橘，薪卡'"
            clearable
            @keyup.enter="changed(row) && save(row)"
            />
          </div>
        </template>
      </ElTableColumn>
      <ElTableColumn label="最后修改" width="220">
        <template #default="{ row }">
          <span v-if="row.updated_at">{{ formatDateTime(row.updated_at) }} {{ row.updated_by }}</span>
          <span v-else class="text-[var(--el-text-color-placeholder)]">未设置</span>
        </template>
      </ElTableColumn>
      <ElTableColumn label="" width="110" align="center">
        <template #default="{ row }">
          <ElButton type="primary" size="small" :disabled="!changed(row)" :loading="row.saving" @click="save(row)">
            保存
          </ElButton>
        </template>
      </ElTableColumn>
    </ElTable>
  </ContentWrap>
</template>
