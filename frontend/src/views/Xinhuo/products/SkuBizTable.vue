<script setup>
import { ref } from "vue";
import { ElImage, ElTable, ElTableColumn, ElTag, ElTooltip } from "element-plus";
import { BaseButton } from "@/components/Button";

const props = defineProps({
  biz: { type: Object, required: true },
  matchedSkuId: { type: [String, Number, null], default: null },
  openPricePopoverSkuId: { type: [String, Number, null], default: null },
  platformTags: { type: Array, default: () => [] },
  tutorialUrlMap: { type: Object, default: () => new Map() },
  usdProxyPriceTiers: { type: Array, default: () => [] },
});

const emit = defineEmits([
  "set-row-ref",
  "open-lightbox",
  "toggle-price",
  "copy-text",
  "copy-tutorial",
  "tutorial-click",
]);

const TAG_PREVIEW = 4;
/** 超过该长度才折叠，约显示前 30% 时可点展开 */
const PHRASE_COLLAPSE_LEN = 72;

const expandedPhrases = ref(new Set());

function phraseKey(skuId, idx) {
  return `${skuId}-${idx}`;
}

function isPhraseLong(text) {
  return String(text || "").trim().length > PHRASE_COLLAPSE_LEN;
}

function isPhraseExpanded(skuId, idx) {
  return expandedPhrases.value.has(phraseKey(skuId, idx));
}

function togglePhrase(skuId, idx) {
  const key = phraseKey(skuId, idx);
  const next = new Set(expandedPhrases.value);
  if (next.has(key)) next.delete(key);
  else next.add(key);
  expandedPhrases.value = next;
}

const pillColorPairs = [
  { bg: "#ffe4e6", text: "#be123c" },
  { bg: "#ffedd5", text: "#c2410c" },
  { bg: "#fef3c7", text: "#b45309" },
  { bg: "#dcfce7", text: "#15803d" },
  { bg: "#cffafe", text: "#0f766e" },
  { bg: "#dbeafe", text: "#1d4ed8" },
  { bg: "#e0e7ff", text: "#4338ca" },
  { bg: "#f3e8ff", text: "#7e22ce" },
];

function statusLabel(status) {
  if (status === "on_sale") return "在售";
  if (status === "pending_test") return "待测试";
  if (status === "off_sale") return "禁售";
  return status || "—";
}

function statusTagType(status) {
  if (status === "on_sale") return "success";
  if (status === "pending_test") return "warning";
  if (status === "off_sale") return "danger";
  return "info";
}

function channelTagList(sku) {
  return (sku?.channel_tags || []).filter((t) => t?.name);
}

function tagPillStyle(tag) {
  const key = String(tag?.id ?? tag?.name ?? "");
  let hash = 0;
  for (let i = 0; i < key.length; i += 1) hash = (hash * 31 + key.charCodeAt(i)) >>> 0;
  const pair = pillColorPairs[hash % pillColorPairs.length];
  return { backgroundColor: pair.bg, color: pair.text, borderColor: pair.text + "33" };
}

function previewTags(list) {
  const all = list || [];
  return {
    shown: all.slice(0, TAG_PREVIEW),
    more: Math.max(0, all.length - TAG_PREVIEW),
    allNames: all.map((t) => t.name).join("、"),
  };
}

function quickPhraseTextList(sku) {
  return (sku?.quick_phrases || []).map((ph) => ph?.content).filter(Boolean);
}

function tutorialTitleList(sku) {
  return String(sku?.tutorial_text || "")
    .split("/")
    .map((x) => x.trim())
    .filter(Boolean);
}

function tutorialUrlByTitle(title) {
  const map = props.tutorialUrlMap;
  if (map instanceof Map) return map.get(title) || "";
  return map?.[title] || "";
}

function skuPrecaution(sku) {
  return String(sku?.precaution ?? "").trim();
}

function normalizeMediaUrl(url) {
  const raw = String(url || "").trim();
  if (!raw) return "";
  try {
    const parsed = new URL(raw, window.location.origin);
    if (parsed.pathname.startsWith("/media/")) return parsed.pathname;
    return parsed.href;
  } catch (_) {
    return raw;
  }
}

function skuImageList(sku) {
  const urls = sku?.image_urls;
  if (Array.isArray(urls) && urls.length) {
    return urls.map(normalizeMediaUrl).filter(Boolean);
  }
  const one = normalizeMediaUrl(sku?.image_url || sku?.image);
  return one ? [one] : [];
}

function skuPriceItemList(sku) {
  const items = sku?.price_items || [];
  if (items.length) return items;
  if (sku?.price != null && sku?.price !== "") {
    return [{ id: null, label: "", rmb_amount: sku.price, notice: "", sort_order: 0 }];
  }
  return [];
}

function isUsdProxyPriceSku(sku) {
  return sku?.price_type === "usd_proxy";
}

function skuHasPrice(sku) {
  if (isUsdProxyPriceSku(sku)) return props.usdProxyPriceTiers.length > 0;
  if (String(sku?.price_notice ?? "").trim()) return true;
  return skuPriceItemList(sku).length > 0;
}

function skuRowClassName({ row }) {
  if (props.matchedSkuId && String(props.matchedSkuId) === String(row.id)) {
    return "sku-row-match";
  }
  return "";
}
</script>

<template>
  <ElTable
    v-if="(biz.skus || []).length"
    :data="biz.skus || []"
    row-key="id"
    class="sku-table mb-12px"
    :row-class-name="skuRowClassName"
  >
    <ElTableColumn label="截图" width="128" align="center">
      <template #default="{ row }">
        <div
          :id="`sku-row-${row.id}`"
          :ref="(el) => emit('set-row-ref', row.id, el)"
          class="sku-media-cell"
        >
          <div
            v-if="skuImageList(row).length"
            class="sku-media-frame cursor-zoom-in"
            @click="emit('open-lightbox', skuImageList(row), 0)"
          >
            <ElImage :src="skuImageList(row)[0]" fit="cover" class="sku-media-img" />
            <span v-if="skuImageList(row).length > 1" class="sku-media-count">
              {{ skuImageList(row).length }}
            </span>
          </div>
          <div v-else class="sku-media-placeholder">
            <span>暂无截图</span>
          </div>
        </div>
      </template>
    </ElTableColumn>

    <ElTableColumn label="SKU" min-width="300">
      <template #default="{ row }">
        <div class="sku-card">
          <div class="sku-card__title-row">
            <h4 class="sku-card__name">{{ row.name || "—" }}</h4>
            <ElTag :type="statusTagType(row.status)" size="small" effect="plain" round>
              {{ row.status_label || statusLabel(row.status) }}
            </ElTag>
          </div>

          <p v-if="skuPrecaution(row)" class="sku-card__warn">{{ skuPrecaution(row) }}</p>

          <div v-if="channelTagList(row).length" class="sku-card__meta">
            <span class="sku-card__meta-label">渠道</span>
            <div class="sku-card__chips">
              <span
                v-for="tag in previewTags(channelTagList(row)).shown"
                :key="`${row.id}-ch-${tag.id || tag.name}`"
                class="tag-pill"
                :style="tagPillStyle(tag)"
              >
                {{ tag.name }}
              </span>
              <ElTooltip
                v-if="previewTags(channelTagList(row)).more"
                :content="previewTags(channelTagList(row)).allNames"
                placement="top"
              >
                <span class="tag-more">+{{ previewTags(channelTagList(row)).more }}</span>
              </ElTooltip>
            </div>
          </div>

          <div v-if="platformTags.length" class="sku-card__meta">
            <span class="sku-card__meta-label">标签</span>
            <div class="sku-card__chips">
              <span
                v-for="tag in previewTags(platformTags).shown"
                :key="`plat-${tag.id || tag.name}`"
                class="tag-pill"
                :style="tagPillStyle(tag)"
              >
                {{ tag.name }}
              </span>
              <ElTooltip
                v-if="previewTags(platformTags).more"
                :content="previewTags(platformTags).allNames"
                placement="top"
              >
                <span class="tag-more">+{{ previewTags(platformTags).more }}</span>
              </ElTooltip>
            </div>
          </div>

          <div class="sku-card__price">
            <BaseButton
              v-if="skuHasPrice(row)"
              link
              type="primary"
              :data-price-trigger="row.id"
              @click="emit('toggle-price', row.id, $event)"
            >
              {{ openPricePopoverSkuId === String(row.id) ? "收起价格" : "查看价格" }}
            </BaseButton>
            <span v-else class="text-muted">暂无价格</span>
          </div>
        </div>
      </template>
    </ElTableColumn>

    <ElTableColumn label="快捷语" min-width="280">
      <template #default="{ row }">
        <div v-if="quickPhraseTextList(row).length" class="res-list">
          <div
            v-for="(text, idx) in quickPhraseTextList(row)"
            :key="`${row.id}-p-${idx}`"
            class="res-item res-item--phrase"
          >
            <div class="res-item__phrase-wrap">
              <span
                class="res-item__phrase"
                :class="{ 'is-collapsed': isPhraseLong(text) && !isPhraseExpanded(row.id, idx) }"
              >{{ text }}</span>
              <button
                v-if="isPhraseLong(text)"
                type="button"
                class="phrase-toggle"
                @click="togglePhrase(row.id, idx)"
              >
                {{ isPhraseExpanded(row.id, idx) ? "收起" : "展开全文" }}
              </button>
            </div>
            <BaseButton link type="primary" size="small" @click="emit('copy-text', text)">
              复制
            </BaseButton>
          </div>
        </div>
        <span v-else class="text-muted">—</span>
      </template>
    </ElTableColumn>

    <ElTableColumn label="教程" min-width="240">
      <template #default="{ row }">
        <div v-if="tutorialTitleList(row).length" class="res-list">
          <div class="res-list__count">共 {{ tutorialTitleList(row).length }} 篇</div>
          <div
            v-for="(title, idx) in tutorialTitleList(row)"
            :key="`${row.id}-t-${idx}`"
            class="res-item"
          >
            <ElTooltip :content="title" placement="top" :show-after="400">
              <span class="res-item__title">{{ title }}</span>
            </ElTooltip>
            <div class="res-item__actions">
              <BaseButton
                link
                type="primary"
                size="small"
                tag="a"
                :href="tutorialUrlByTitle(title) || '#'"
                target="_blank"
                rel="noopener noreferrer"
                :disabled="!tutorialUrlByTitle(title)"
                @click="emit('tutorial-click', $event, title)"
              >
                打开
              </BaseButton>
              <BaseButton link size="small" @click="emit('copy-tutorial', title)">复制</BaseButton>
            </div>
          </div>
        </div>
        <span v-else class="text-muted">—</span>
      </template>
    </ElTableColumn>
  </ElTable>
  <div v-else class="detail-empty">暂无 SKU</div>
</template>

<style scoped>
.sku-table {
  --el-table-border-color: var(--el-border-color-extra-light);
  border-radius: 12px;
  overflow: hidden;
}
.sku-table :deep(.el-table__header th) {
  background: #f8fafc !important;
  color: #64748b;
  font-weight: 600;
  font-size: 13px;
}
.sku-table :deep(.el-table__cell) {
  vertical-align: top;
  padding: 14px 12px;
}
.sku-table :deep(.sku-row-match > td) {
  background: rgba(5, 150, 105, 0.06) !important;
}
.text-muted {
  font-size: 13px;
  color: var(--el-text-color-placeholder);
}
.sku-media-cell {
  position: relative;
}
.sku-media-frame {
  position: relative;
  width: 96px;
  height: 96px;
  margin: 0 auto;
  border-radius: 10px;
  overflow: hidden;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
}
.sku-media-img {
  width: 96px;
  height: 96px;
}
.sku-media-count {
  position: absolute;
  right: 6px;
  bottom: 6px;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.75);
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  line-height: 20px;
  text-align: center;
}
.sku-media-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 96px;
  height: 96px;
  margin: 0 auto;
  border-radius: 10px;
  border: 1px dashed #cbd5e1;
  background: #f8fafc;
  color: #94a3b8;
  font-size: 12px;
}
.sku-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}
.sku-card__title-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.sku-card__name {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  line-height: 1.35;
  color: #0f172a;
}
.sku-card__warn {
  margin: 0;
  padding: 6px 10px;
  border-radius: 8px;
  background: #fef2f2;
  color: #b91c1c;
  font-size: 12px;
  line-height: 1.4;
}
.sku-card__meta {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.sku-card__meta-label {
  flex-shrink: 0;
  width: 32px;
  margin-top: 2px;
  font-size: 12px;
  color: #94a3b8;
}
.sku-card__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-width: 0;
}
.tag-pill {
  display: inline-flex;
  align-items: center;
  max-width: 140px;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  border: 1px solid transparent;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tag-more {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
  cursor: default;
}
.sku-card__price {
  margin-top: 2px;
}
.res-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.res-list__count {
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 2px;
}
.res-item {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  padding: 8px 10px;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid #eef2f7;
}
.res-item__title {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  color: #334155;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.res-item--phrase {
  align-items: flex-start;
}
.res-item__phrase-wrap {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}
.res-item__phrase {
  width: 100%;
  font-size: 13px;
  line-height: 1.55;
  color: #334155;
  white-space: pre-wrap;
  word-break: break-word;
}
.res-item__phrase.is-collapsed {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  overflow: hidden;
  /* 约 3 行 ≈ 长文前 30% 预览 */
  max-height: 4.65em;
}
.phrase-toggle {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--el-color-primary);
  font-size: 12px;
  line-height: 1.2;
  cursor: pointer;
}
.phrase-toggle:hover {
  text-decoration: underline;
}
.res-item__actions {
  display: flex;
  flex-shrink: 0;
  gap: 2px;
}
.detail-empty {
  padding: 16px;
  border-radius: 10px;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-light);
}
</style>
