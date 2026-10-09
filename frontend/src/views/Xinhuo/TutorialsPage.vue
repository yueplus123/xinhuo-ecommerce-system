<script setup lang="tsx">
import { onMounted, reactive, ref } from 'vue'
import { ElLink, ElMessage } from 'element-plus'
import { ContentWrap } from '@/components/ContentWrap'
import { Search } from '@/components/Search'
import { Table, TableColumn } from '@/components/Table'
import { BaseButton } from '@/components/Button'
import { FormSchema } from '@/components/Form'
import { listPaymentTutorials } from '@/api/xinhuo/tutorials'

defineOptions({ name: 'PaymentTutorials' })

const loading = ref(false)
const rows = ref<any[]>([])
const searchParams = reactive({ name: '' })

const searchSchema: FormSchema[] = [
  {
    field: 'name',
    label: '模块名',
    component: 'Input',
    componentProps: { placeholder: '查询模块' }
  }
]

async function copyText(text: string) {
  const val = String(text || '').trim()
  if (!val) return
  try {
    await navigator.clipboard.writeText(val)
  } catch (_) {
    const ta = document.createElement('textarea')
    ta.value = val
    ta.setAttribute('readonly', '')
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
  }
  ElMessage.success('已复制')
}

const columns: TableColumn[] = [
  { field: 'name', label: '教程名字', minWidth: 160 },
  {
    field: 'detail_url',
    label: '教程链接',
    minWidth: 280,
    slots: {
      default: (data) =>
        data.row.detail_url ? (
          <ElLink href={data.row.detail_url} target="_blank" rel="noopener noreferrer" type="primary">
            {data.row.detail_url}
          </ElLink>
        ) : (
          <span>—</span>
        )
    }
  },
  {
    field: 'action',
    label: '复制链接',
    width: 120,
    slots: {
      default: (data) => (
        <BaseButton type="primary" onClick={() => copyText(data.row.detail_url)}>
          一键复制
        </BaseButton>
      )
    }
  }
]

async function load(params: Recordable = {}) {
  Object.assign(searchParams, { name: params.name || '' })
  loading.value = true
  try {
    const { data } = await listPaymentTutorials({ name: searchParams.name || undefined })
    const raw = data.results || data
    const list = (Array.isArray(raw) ? raw : []).slice()
    list.sort((a, b) => {
      const ao = Number(a?.sort_order ?? 0)
      const bo = Number(b?.sort_order ?? 0)
      if (ao !== bo) return ao - bo
      return (Number(a?.id) || 0) - (Number(b?.id) || 0)
    })
    rows.value = list
  } catch (e: any) {
    rows.value = []
    ElMessage.error(e?.response?.data?.detail || e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => load())
</script>

<template>
  <ContentWrap title="远程电脑图文">
    <Search :schema="searchSchema" @search="load" @reset="load" />
    <Table :columns="columns" :data="rows" :loading="loading" />
  </ContentWrap>
</template>
