<script setup lang="ts">
// SKU 详细编辑：基本信息 / 价格档 / 渠道标签 / 对应教程 / 快捷话术 / 会员截图
// 路由：/manage/skus/new?business=<id> 新建；/manage/skus/<id> 编辑
import { computed, onMounted, reactive, ref } from 'vue'
import {
  ElAlert,
  ElButton,
  ElCard,
  ElCheckbox,
  ElCheckboxGroup,
  ElForm,
  ElFormItem,
  ElImage,
  ElInput,
  ElInputNumber,
  ElMessage,
  ElOption,
  ElSelect,
  ElUpload,
  type UploadFile
} from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import ContentWrap from '@/components/ContentWrap.vue'
import { formatRequestError } from '@/utils/format'
import {
  createSkuEditor,
  getSkuEditor,
  getSkuEditorOptions,
  saveSkuEditor,
  type SkuDetail,
  type SkuEditorOptions,
  type SkuImageItem
} from '@/api/modules/catalog'

defineOptions({ name: 'ManageSkuEditor' })

const MAX_IMAGE_MB = 5
const route = useRoute()
const router = useRouter()
const skuId = computed(() => (route.params.id ? Number(route.params.id) : null))
const isCreate = computed(() => skuId.value === null)

const loading = ref(false)
const saving = ref(false)
const options = ref<SkuEditorOptions | null>(null)
const ctx = reactive({ business: 0, business_name: '', platform: 0, platform_name: '' })

const form = reactive({
  name: '',
  status: 'on_sale',
  price_type: '',
  price_notice: '',
  precaution: '',
  warranty: '',
  warranty_note: '',
  channel_tag_ids: [] as number[]
})
const prices = ref<Array<{ label: string; rmb_amount: number | undefined; notice: string }>>([])
const images = ref<SkuImageItem[]>([]) // 已有截图
const removeImageIds = ref<number[]>([])
const newFiles = ref<UploadFile[]>([])

function fill(d: SkuDetail) {
  options.value = d.options
  Object.assign(ctx, {
    business: d.business,
    business_name: d.business_name,
    platform: d.platform,
    platform_name: d.platform_name
  })
  form.name = d.name
  form.status = d.status
  form.price_type = d.price_type
  form.price_notice = d.price_notice
  form.precaution = d.precaution
  form.warranty = d.warranty || ''
  form.warranty_note = d.warranty_note || ''
  form.channel_tag_ids = [...d.channel_tag_ids]
  prices.value = d.price_items.map((p) => ({ label: p.label, rmb_amount: Number(p.rmb_amount), notice: p.notice }))
  images.value = [...d.images]
  removeImageIds.value = []
  newFiles.value = []
}

async function load() {
  loading.value = true
  try {
    if (isCreate.value) {
      const bid = Number(route.query.business)
      if (!bid) throw new Error('缺少业务参数，请从平台工作台进入')
      options.value = await getSkuEditorOptions()
      ctx.business = bid
    } else {
      fill(await getSkuEditor(skuId.value as number))
    }
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '加载失败'))
  } finally {
    loading.value = false
  }
}
onMounted(load)

const backToWorkbench = () =>
  router.push(ctx.platform ? `/platforms/${ctx.platform}` : '/platforms')

// ---- 价格档 ----
// 不同价格类型的填写方式（与旧版后台一致）：single 只填一档；multi 可多档；none 不填价格档
type PriceMode = 'none' | 'single' | 'multi'
const PRICE_UI: Record<string, { hint: string; mode: PriceMode; label: string; amount: string; showLabel: boolean }> = {
  '': { hint: '请先选择价格类型，下面会显示对应的填写方式。', mode: 'none', label: '档位名称', amount: '人民币（元）', showLabel: true },
  cny_single: { hint: '单一人民币：只填一个人民币金额，不需要档位名称。', mode: 'single', label: '档位名称', amount: '人民币（元）', showLabel: false },
  usd_single: { hint: '美金（单一）：填一档。左边写美金金额（如 9.99），右边写折算人民币。', mode: 'single', label: '美金（USD）', amount: '折算人民币（元）', showLabel: true },
  usd_tier: { hint: '美金（多档）：每行一档。左边写美金档位，右边写对应人民币，可以加多行。', mode: 'multi', label: '美金档位', amount: '折算人民币（元）', showLabel: true },
  package: { hint: '套餐：每行一个套餐。左边写套餐名称，右边写人民币价格，可以加多行。', mode: 'multi', label: '套餐名称', amount: '人民币（元）', showLabel: true },
  jpy_recharge: { hint: '日元充值：每行一档。左边写日元数量（如 1000），右边写人民币，可以加多行。', mode: 'multi', label: '日元档位', amount: '人民币（元）', showLabel: true },
  usd_proxy: { hint: '按美金代付收费：费率用资源池「美金代付价格池」，这里不用填价格档。', mode: 'none', label: '档位名称', amount: '人民币（元）', showLabel: false }
}
const priceUi = computed(() => PRICE_UI[form.price_type || ''] || PRICE_UI[''])
// 切换类型时不删已有价格档：不该有的档位会标出来，由你决定删不删
const priceRowExtra = (i: number) =>
  priceUi.value.mode === 'none' || (priceUi.value.mode === 'single' && i > 0)
const canAddPrice = computed(
  () => priceUi.value.mode === 'multi' || (priceUi.value.mode === 'single' && prices.value.length === 0)
)
const addPrice = () => prices.value.push({ label: '', rmb_amount: undefined, notice: '' })
const removePrice = (i: number) => prices.value.splice(i, 1)
const movePrice = (i: number, d: -1 | 1) => {
  const j = i + d
  if (j < 0 || j >= prices.value.length) return
  ;[prices.value[i], prices.value[j]] = [prices.value[j], prices.value[i]]
}

// 话术、教程已移到「教程+话术」（管理后台左侧「教程+话术」），这里不再编辑

// 质保说明预览：和职员端同样的判断规则
const W_NO = /(不(?:另外|再|提供|予|给|做)?(?:质保|保修|保|包换|包补|包|退款|退|负责)|无法质保|概不)/
const W_OK = /(包换|包补|免费补|补发|补卡|换新|可以找回|找回|退款|保修)/
const warrantyLines = computed(() =>
  String(form.warranty_note || '')
    .split(/[；;\n]+/)
    .map((t) => t.trim())
    .filter(Boolean)
    .map((text) => ({ text, kind: W_NO.test(text) ? 'no' : W_OK.test(text) ? 'ok' : 'tx' }))
)

// ---- 截图 ----
function beforeUpload(file: File) {
  if (!file.type.startsWith('image/')) {
    ElMessage.warning('仅支持图片文件')
    return false
  }
  if (file.size > MAX_IMAGE_MB * 1024 * 1024) {
    ElMessage.warning(`单张图片不能超过 ${MAX_IMAGE_MB}MB`)
    return false
  }
  return true
}
const toggleRemoveImage = (id: number) => {
  const i = removeImageIds.value.indexOf(id)
  if (i >= 0) removeImageIds.value.splice(i, 1)
  else removeImageIds.value.push(id)
}

// ---- 保存 ----
async function submit() {
  if (!form.name.trim()) return void ElMessage.warning('请填写 SKU 名称')
  for (const [i, p] of prices.value.entries()) {
    if (p.rmb_amount === undefined || p.rmb_amount === null) {
      return void ElMessage.warning(`第 ${i + 1} 个价格档请填写人民币金额（不需要的档位请删除）`)
    }
  }
  const fd = new FormData()
  fd.append('business', String(ctx.business))
  fd.append('name', form.name.trim())
  fd.append('status', form.status)
  fd.append('price_type', form.price_type)
  fd.append('price_notice', form.price_notice)
  fd.append('precaution', form.precaution)
  fd.append('warranty', form.warranty || '')
  fd.append('warranty_note', form.warranty_note || '')
  fd.append('channel_tag_ids', JSON.stringify(form.channel_tag_ids))
  fd.append(
    'price_items',
    JSON.stringify(prices.value.map((p) => ({ label: p.label, rmb_amount: String(p.rmb_amount), notice: p.notice })))
  )
  fd.append('delete_image_ids', JSON.stringify(removeImageIds.value))
  for (const f of newFiles.value) if (f.raw) fd.append('images', f.raw)

  saving.value = true
  try {
    const d = isCreate.value ? await createSkuEditor(fd) : await saveSkuEditor(skuId.value as number, fd)
    ElMessage.success('SKU 已保存')
    if (isCreate.value) await router.replace(`/skus/${d.id}`)
    fill(d)
  } catch (e: any) {
    ElMessage.error(formatRequestError(e, '保存失败'))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <ContentWrap :title="isCreate ? '新增 SKU' : `编辑 SKU · ${form.name || ''}`">
    <div class="toolbar">
      <ElButton @click="backToWorkbench">← 返回平台工作台</ElButton>
      <ElButton type="primary" :loading="saving" @click="submit">保存</ElButton>
      <span v-if="ctx.platform_name" class="muted">{{ ctx.platform_name }} / {{ ctx.business_name }}</span>
    </div>

    <div v-loading="loading">
      <ElForm v-if="options" label-width="100px" @submit.prevent="submit">
        <ElCard shadow="never" header="基本信息" class="mb">
          <ElFormItem label="SKU 名称" required><ElInput v-model="form.name" maxlength="200" /></ElFormItem>
          <ElFormItem label="状态">
            <ElSelect v-model="form.status" style="width: 200px">
              <ElOption v-for="o in options.statuses" :key="o.value" :label="o.label" :value="o.value" />
            </ElSelect>
          </ElFormItem>
          <ElFormItem label="注意事项">
            <ElInput v-model="form.precaution" type="textarea" :rows="4" placeholder="职员端 SKU 卡片上显示的注意事项" />
          </ElFormItem>
        </ElCard>

        <ElCard shadow="never" header="质保条件" class="mb">
          <ElFormItem label="质保期">
            <ElSelect
              v-model="form.warranty"
              filterable
              allow-create
              default-first-option
              clearable
              placeholder="未填写（可以选，也可以直接输入，比如 15 天）"
              style="width: 320px"
            >
              <ElOption v-for="o in options.warranty_presets || []" :key="o" :label="o" :value="o" />
            </ElSelect>
          </ElFormItem>
          <ElFormItem label="质保说明">
            <ElInput
              v-model="form.warranty_note"
              type="textarea"
              :rows="4"
              :placeholder="'一条一行（或用；隔开），例如：\n登录不上、被封号包换一次\n自己改密码、改邮箱后出问题不保'"
            />
            <div class="muted wty-hint">
              职员端「业务+价格」详情右上角显示为「质保条件：」。写了「包换 / 补 / 找回」的一行显示 ✓，写了「不保 / 不包 / 不另外质保」的显示 ✕。
            </div>
            <ul v-if="warrantyLines.length" class="wty-preview">
              <li v-for="(l, i) in warrantyLines" :key="i" :class="l.kind">
                <span class="m">{{ l.kind === 'ok' ? '✓' : l.kind === 'no' ? '✕' : '•' }}</span>{{ l.text }}
              </li>
            </ul>
          </ElFormItem>
        </ElCard>

        <ElCard shadow="never" header="价格" class="mb">
          <ElFormItem label="价格类型">
            <ElSelect v-model="form.price_type" clearable placeholder="未设置" style="width: 240px">
              <ElOption v-for="o in options.price_types" :key="o.value" :label="o.label" :value="o.value" />
            </ElSelect>
            <span v-if="form.price_type === 'usd_proxy'" class="muted ml">
              将引用「美金代付价格池」（当前 {{ options.usd_tiers.length }} 档）
            </span>
          </ElFormItem>
          <ElFormItem label="整组说明">
            <ElInput v-model="form.price_notice" type="textarea" :rows="3" placeholder="价格弹层内整组说明（可选）" />
          </ElFormItem>
          <ElFormItem label="价格档">
            <div class="rows">
              <div class="price-hint">{{ priceUi.hint }}</div>
              <div v-if="prices.length" class="price-row price-head">
                <span v-if="priceUi.showLabel" style="width: 160px">{{ priceUi.label }}</span>
                <span style="width: 150px">{{ priceUi.amount }}</span>
                <span style="flex: 1; min-width: 160px">单条注意事项</span>
              </div>
              <div v-for="(p, i) in prices" :key="i" class="price-row" :class="{ extra: priceRowExtra(i) }">
                <ElInput
                  v-if="priceUi.showLabel || p.label"
                  v-model="p.label"
                  :placeholder="priceUi.label + '（可选）'"
                  style="width: 160px"
                  maxlength="100"
                />
                <ElInputNumber v-model="p.rmb_amount" :min="0" :precision="2" :step="1" :placeholder="priceUi.amount" controls-position="right" style="width: 150px" />
                <ElInput v-model="p.notice" placeholder="单条注意事项（可选）" style="flex: 1; min-width: 160px" />
                <ElButton link :disabled="i === 0" @click="movePrice(i, -1)">↑</ElButton>
                <ElButton link :disabled="i === prices.length - 1" @click="movePrice(i, 1)">↓</ElButton>
                <ElButton link type="danger" @click="removePrice(i)">删除</ElButton>
                <span v-if="priceRowExtra(i)" class="extra-tip">
                  {{ priceUi.mode === 'none' ? '这个类型不用价格档，可以删除' : '单一价格只用第一档，这档可以删除' }}
                </span>
              </div>
              <template v-if="canAddPrice">
                <ElButton size="small" @click="addPrice">+ {{ priceUi.mode === 'single' ? '填写价格' : '添加' + priceUi.label }}</ElButton>
                <span class="muted ml">第一档会同步为 SKU 的「默认价格」</span>
              </template>
            </div>
          </ElFormItem>
        </ElCard>

        <ElCard shadow="never" header="渠道" class="mb">
          <ElFormItem label="渠道标签">
            <ElCheckboxGroup v-model="form.channel_tag_ids">
              <ElCheckbox v-for="t in options.channel_tags" :key="t.id" :value="t.id">{{ t.name }}</ElCheckbox>
            </ElCheckboxGroup>
            <span v-if="!options.channel_tags.length" class="muted">渠道池为空，请先到「渠道池」添加</span>
          </ElFormItem>
        </ElCard>


        <ElCard shadow="never" header="会员截图" class="mb">
          <div v-if="images.length" class="imgs">
            <div v-for="im in images" :key="im.id" class="img-item" :class="{ removed: removeImageIds.includes(im.id) }">
              <ElImage :src="im.url" fit="cover" class="thumb" :preview-src-list="[im.url]" preview-teleported />
              <ElButton size="small" link :type="removeImageIds.includes(im.id) ? 'primary' : 'danger'" @click="toggleRemoveImage(im.id)">
                {{ removeImageIds.includes(im.id) ? '撤销删除' : '删除' }}
              </ElButton>
            </div>
          </div>
          <ElUpload v-model:file-list="newFiles" list-type="picture-card" multiple accept="image/*" :auto-upload="false" :before-upload="beforeUpload">+</ElUpload>
          <div class="muted">单张不超过 {{ MAX_IMAGE_MB }}MB，每个 SKU 最多 20 张；第一张作为封面。</div>
        </ElCard>

        <div class="bottom">
          <ElButton @click="backToWorkbench">取消</ElButton>
          <ElButton type="primary" :loading="saving" @click="submit">保存</ElButton>
        </div>
      </ElForm>
      <ElAlert v-else-if="!loading" type="error" :closable="false" title="加载失败，请返回重试" />
    </div>
  </ContentWrap>
</template>

<style scoped>
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin-bottom: 14px;
}
.mb {
  margin-bottom: 14px;
}
.ml {
  margin-left: 10px;
}
.muted {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.price-hint {
  width: 100%;
  padding: 6px 10px;
  font-size: 13px;
  color: var(--el-color-primary-dark-2);
  background: var(--el-color-primary-light-9);
  border-radius: 6px;
}
.price-head {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.price-row.extra :deep(.el-input__wrapper),
.price-row.extra :deep(.el-input-number) {
  opacity: 0.55;
}
.extra-tip {
  font-size: 12px;
  color: var(--el-color-warning-dark-2);
}
.rows {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: flex-start;
}
.price-row {
  width: 100%;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.imgs {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
}
.img-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.img-item.removed {
  opacity: 0.4;
}
.thumb {
  width: 96px;
  height: 96px;
  border-radius: 4px;
}
.bottom {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}
.wty-hint {
  font-size: 12px;
  line-height: 1.6;
  margin-top: 6px;
}
.wty-preview {
  list-style: none;
  margin: 8px 0 0;
  padding: 8px 10px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  width: 100%;
  font-size: 13px;
  line-height: 1.7;
}
.wty-preview .m {
  display: inline-block;
  width: 18px;
  font-weight: 800;
}
.wty-preview .ok .m {
  color: #15803d;
}
.wty-preview .no .m {
  color: #c24141;
}
.wty-preview .tx .m {
  color: var(--el-text-color-secondary);
}
</style>
