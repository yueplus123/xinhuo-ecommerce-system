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
  channel_tag_ids: [] as number[],
  tutorial_ids: [] as number[]
})
const prices = ref<Array<{ label: string; rmb_amount: number | undefined; notice: string }>>([])
const phrases = ref<string[]>([])
const images = ref<SkuImageItem[]>([]) // 已有截图
const removeImageIds = ref<number[]>([])
const newFiles = ref<UploadFile[]>([])
const phrasePick = ref<number | undefined>(undefined)

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
  form.channel_tag_ids = [...d.channel_tag_ids]
  form.tutorial_ids = [...d.tutorial_ids]
  prices.value = d.price_items.map((p) => ({ label: p.label, rmb_amount: Number(p.rmb_amount), notice: p.notice }))
  phrases.value = d.quick_phrases.map((q) => q.content)
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
const addPrice = () => prices.value.push({ label: '', rmb_amount: undefined, notice: '' })
const removePrice = (i: number) => prices.value.splice(i, 1)
const movePrice = (i: number, d: -1 | 1) => {
  const j = i + d
  if (j < 0 || j >= prices.value.length) return
  ;[prices.value[i], prices.value[j]] = [prices.value[j], prices.value[i]]
}

// ---- 快捷话术 ----
const addPhrase = () => phrases.value.push('')
const removePhrase = (i: number) => phrases.value.splice(i, 1)
function addFromPool() {
  const p = options.value?.phrases.find((x) => x.id === phrasePick.value)
  if (!p) return
  phrases.value.push(p.content)
  phrasePick.value = undefined
}

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
  fd.append('channel_tag_ids', JSON.stringify(form.channel_tag_ids))
  fd.append('tutorial_ids', JSON.stringify(form.tutorial_ids))
  fd.append(
    'price_items',
    JSON.stringify(prices.value.map((p) => ({ label: p.label, rmb_amount: String(p.rmb_amount), notice: p.notice })))
  )
  fd.append('quick_phrases', JSON.stringify(phrases.value.map((content) => ({ content }))))
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
              <div v-for="(p, i) in prices" :key="i" class="price-row">
                <ElInput v-model="p.label" placeholder="档位名称（可选）" style="width: 160px" maxlength="100" />
                <ElInputNumber v-model="p.rmb_amount" :min="0" :precision="2" :step="1" placeholder="人民币" controls-position="right" style="width: 150px" />
                <ElInput v-model="p.notice" placeholder="单条注意事项（可选）" style="flex: 1; min-width: 160px" />
                <ElButton link :disabled="i === 0" @click="movePrice(i, -1)">↑</ElButton>
                <ElButton link :disabled="i === prices.length - 1" @click="movePrice(i, 1)">↓</ElButton>
                <ElButton link type="danger" @click="removePrice(i)">删除</ElButton>
              </div>
              <ElButton size="small" @click="addPrice">+ 添加价格档</ElButton>
              <span class="muted ml">第一档会同步为 SKU 的「默认价格」</span>
            </div>
          </ElFormItem>
        </ElCard>

        <ElCard shadow="never" header="渠道与教程" class="mb">
          <ElFormItem label="渠道标签">
            <ElCheckboxGroup v-model="form.channel_tag_ids">
              <ElCheckbox v-for="t in options.channel_tags" :key="t.id" :value="t.id">{{ t.name }}</ElCheckbox>
            </ElCheckboxGroup>
            <span v-if="!options.channel_tags.length" class="muted">渠道池为空，请先到「渠道池」添加</span>
          </ElFormItem>
          <ElFormItem label="对应教程">
            <ElSelect v-model="form.tutorial_ids" multiple filterable placeholder="从教程池选择（按选择顺序展示）" style="width: 100%">
              <ElOption v-for="t in options.tutorials" :key="t.id" :label="t.name" :value="t.id" />
            </ElSelect>
          </ElFormItem>
        </ElCard>

        <ElCard shadow="never" header="快捷话术" class="mb">
          <div class="rows">
            <div v-for="(_, i) in phrases" :key="i" class="phrase-row">
              <ElInput v-model="phrases[i]" type="textarea" :rows="2" />
              <ElButton link type="danger" @click="removePhrase(i)">删除</ElButton>
            </div>
            <div class="phrase-add">
              <ElButton size="small" @click="addPhrase">+ 添加话术</ElButton>
              <ElSelect v-model="phrasePick" filterable clearable placeholder="从话术池导入一条" style="width: 280px" @change="addFromPool">
                <ElOption v-for="p in options.phrases" :key="p.id" :label="p.name" :value="p.id" />
              </ElSelect>
            </div>
          </div>
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
.rows {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: flex-start;
}
.price-row,
.phrase-row {
  width: 100%;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.phrase-row :deep(.el-textarea) {
  flex: 1;
  min-width: 240px;
}
.phrase-add {
  display: flex;
  gap: 10px;
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
</style>
