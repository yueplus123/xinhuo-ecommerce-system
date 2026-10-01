import { onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api/xinhuo/client'
import { formatRequestError } from '@/utils/format'

interface CrudPageOptions<TForm extends Recordable> {
  /** 资源路径，如 '/common-cards/'（相对 API 基址，须以 / 结尾） */
  endpoint: string
  pageSize: number
  emptyForm: () => TForm
  /** 表单 -> 提交体（含 trim/截断） */
  payloadFrom: (src: Recordable) => TForm
  /** 校验失败时自行提示并返回 false */
  validate: (payload: TForm) => boolean
  /** 行数据 -> 编辑表单 */
  rowToForm: (row: any) => TForm
  /** 删除确认文案 */
  deleteMessage: (row: any) => string
  deleteSuccessText?: string
  /** 额外的列表查询参数（如搜索关键字） */
  extraParams?: () => Recordable
  /** 新增成功后是否回到第 1 页 */
  resetPageOnCreate?: boolean
}

export function useCrudPage<TForm extends Recordable>(opts: CrudPageOptions<TForm>) {
  const rows = ref<any[]>([])
  const loading = ref(false)
  const saving = ref(false)
  const page = ref(1)
  const pageSize = ref(opts.pageSize)
  const totalCount = ref(0)
  const form = ref<TForm>(opts.emptyForm())
  const editOpen = ref(false)
  const editId = ref<number | null>(null)
  const editForm = ref<TForm>(opts.emptyForm())

  async function loadRows() {
    loading.value = true
    try {
      const params: Recordable = {
        page: page.value,
        page_size: pageSize.value,
        ...(opts.extraParams?.() ?? {})
      }
      const { data } = await api.get(opts.endpoint, { params })
      if (Array.isArray(data)) {
        rows.value = data
        totalCount.value = data.length
        return
      }
      rows.value = data.results || []
      totalCount.value = data.count ?? rows.value.length
    } catch (e: any) {
      ElMessage.error(formatRequestError(e, '加载失败'))
      rows.value = []
      totalCount.value = 0
    } finally {
      loading.value = false
    }
  }

  watch(page, (next, prev) => {
    if (next !== prev) loadRows()
  })

  async function onCreate() {
    const body = opts.payloadFrom(form.value)
    if (!opts.validate(body)) return
    saving.value = true
    try {
      await api.post(opts.endpoint, body)
      form.value = opts.emptyForm()
      ElMessage.success('添加成功')
      if (opts.resetPageOnCreate) page.value = 1
      await loadRows()
    } catch (e: any) {
      ElMessage.error(formatRequestError(e, '保存失败'))
    } finally {
      saving.value = false
    }
  }

  function openEdit(row: any) {
    editId.value = row.id
    editForm.value = opts.rowToForm(row)
    editOpen.value = true
  }

  async function saveEdit() {
    if (!editId.value) return
    const body = opts.payloadFrom(editForm.value)
    if (!opts.validate(body)) return
    saving.value = true
    try {
      await api.patch(`${opts.endpoint}${editId.value}/`, body)
      editOpen.value = false
      ElMessage.success('更新成功')
      await loadRows()
    } catch (e: any) {
      ElMessage.error(formatRequestError(e, '更新失败'))
    } finally {
      saving.value = false
    }
  }

  async function onDelete(row: any) {
    try {
      await ElMessageBox.confirm(opts.deleteMessage(row), '删除确认', {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消'
      })
      await api.delete(`${opts.endpoint}${row.id}/`)
      ElMessage.success(opts.deleteSuccessText ?? '删除成功')
      await loadRows()
    } catch (e: any) {
      if (e !== 'cancel' && e?.action !== 'cancel') {
        ElMessage.error(formatRequestError(e, '删除失败'))
      }
    }
  }

  onMounted(loadRows)

  return {
    rows,
    loading,
    saving,
    page,
    pageSize,
    totalCount,
    form,
    editOpen,
    editId,
    editForm,
    loadRows,
    onCreate,
    openEdit,
    saveEdit,
    onDelete
  }
}
