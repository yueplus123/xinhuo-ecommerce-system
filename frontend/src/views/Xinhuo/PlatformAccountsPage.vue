<script setup lang="tsx">
import { onMounted, ref } from 'vue'
import { ElLink, ElMessage } from 'element-plus'
import { ContentWrap } from '@/components/ContentWrap'
import { Table, TableColumn } from '@/components/Table'
import { BaseButton } from '@/components/Button'
import api from '@/api/xinhuo/client'

defineOptions({ name: 'PlatformAccounts' })

const loading = ref(false)
const rows = ref<any[]>([])

async function copyText(text: string) {
  const val = String(text || '').trim()
  if (!val || val === '—') return
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
  { field: 'name', label: '平台', minWidth: 120 },
  {
    field: 'account',
    label: '账号',
    minWidth: 140,
    slots: {
      default: (data) => (
        <ElLink type="primary" onClick={() => copyText(data.row.account)}>
          {data.row.account || '—'}
        </ElLink>
      )
    }
  },
  {
    field: 'password',
    label: '密码',
    minWidth: 140,
    slots: {
      default: (data) => (
        <ElLink type="primary" onClick={() => copyText(data.row.password)}>
          {data.row.password || '—'}
        </ElLink>
      )
    }
  },
  {
    field: 'url',
    label: '网址链接',
    minWidth: 200,
    slots: {
      default: (data) => (
        <ElLink type="primary" onClick={() => copyText(data.row.url)}>
          {data.row.url || '—'}
        </ElLink>
      )
    }
  },
  { field: 'note', label: '备注', minWidth: 160, formatter: (_r, _c, v) => v || '—' },
  {
    field: 'action',
    label: '操作',
    width: 100,
    slots: {
      default: (data) => (
        <BaseButton
          type="primary"
          onClick={() =>
            copyText(
              [data.row.account, data.row.password, data.row.url].filter(Boolean).join('\n')
            )
          }
        >
          复制
        </BaseButton>
      )
    }
  }
]

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/platform-accounts/')
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

onMounted(load)
</script>

<template>
  <ContentWrap title="平台账号密码">
    <Table :columns="columns" :data="rows" :loading="loading" />
  </ContentWrap>
</template>
