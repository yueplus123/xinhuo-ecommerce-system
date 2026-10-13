<script setup lang="tsx">
import { onMounted, reactive, ref } from 'vue'
import { ElLink, ElMessage } from 'element-plus'
import { ContentWrap } from '@/components/ContentWrap'
import { Search } from '@/components/Search'
import { Table, TableColumn } from '@/components/Table'
import { BaseButton } from '@/components/Button'
import { FormSchema } from '@/components/Form'
import { listNannyTutorials } from '@/api/xinhuo/tutorials'

defineOptions({ name: 'NannyTutorials' })

const loading = ref(false)
const rows = ref<any[]>([])
const tagOptions = ref<{ label: string; value: string }[]>([])
const searchParams = reactive({ name: '', tag: '' })

const searchSchema = ref<FormSchema[]>([
  {
    field: 'name',
    label: '教程名',
    component: 'Input',
    componentProps: { placeholder: '搜索教程名' }
  },
  {
    field: 'tag',
    label: '平台标签',
    component: 'Select',
    componentProps: {
      placeholder: '全部平台标签',
      options: tagOptions,
      clearable: true
    }
  }
])

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

function tagText(item: any) {
  const tags = Array.isArray(item?.platform_tags) ? item.platform_tags : []
  return tags.length ? tags.join(' / ') : '—'
}

const columns: TableColumn[] = [
  { field: 'name', label: '教程名', minWidth: 160 },
  {
    field: 'detail_url',
    label: '教程链接',
    minWidth: 260,
    slots: {
      default: (data) =>
        data.row.detail_url ? (
          <ElLink href={data.row.detail_url} target="_blank" type="primary">
            {data.row.detail_url}
          </ElLink>
        ) : (
          <span>—</span>
        )
    }
  },
  {
    field: 'platform_tags',
    label: '平台标签',
    minWidth: 160,
    slots: {
      default: (data) => <span>{tagText(data.row)}</span>
    }
  },
  {
    field: 'action',
    label: '复制',
    width: 100,
    slots: {
      default: (data) => {
        const title = String(data.row?.name || '').trim()
        const url = String(data.row?.detail_url || '').trim()
        const text = title && url ? `${title}\n${url}` : title || url
        return (
          <BaseButton type="primary" onClick={() => copyText(text)}>
            复制
          </BaseButton>
        )
      }
    }
  }
]

async function load(params: Recordable = {}) {
  Object.assign(searchParams, {
    name: params.name || '',
    tag: params.tag || ''
  })
  loading.value = true
  try {
    const { data } = await listNannyTutorials({
      name: searchParams.name.trim() || undefined,
      tag: searchParams.tag.trim() || undefined
    })
    const list = Array.isArray(data)
      ? data.slice()
      : Array.isArray(data?.results)
        ? data.results.slice()
        : []
    list.sort((a, b) => {
      const ao = Number(a?.sort_order ?? 0)
      const bo = Number(b?.sort_order ?? 0)
      if (ao !== bo) return ao - bo
      return (Number(a?.id) || 0) - (Number(b?.id) || 0)
    })
    rows.value = list
    const opts = Array.isArray(data?.platform_tag_options)
      ? data.platform_tag_options.filter(Boolean)
      : []
    tagOptions.value = opts.map((t: string) => ({ label: t, value: t }))
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
  <ContentWrap title="教程合计(对客户)">
    <Search :schema="searchSchema" @search="load" @reset="load" />
    <Table :columns="columns" :data="rows" :loading="loading" />
  </ContentWrap>
</template>
