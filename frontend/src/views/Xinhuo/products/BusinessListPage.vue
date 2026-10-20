<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  ElAlert,
  ElImageViewer,
  ElTag,
} from "element-plus";
import { ContentWrap } from "@/components/ContentWrap";
import { BaseButton } from "@/components/Button";
import SkuBizTable from "./SkuBizTable.vue";
import { getPlatform, listUsdProxyPriceTiers } from '@/api/xinhuo/platforms';
import { listPaymentTutorials, listNannyTutorials } from "@/api/xinhuo/tutorials";
import { showCopySuccess } from '@/copyFeedback';

defineOptions({ name: "PlatformBusinesses" });

const route = useRoute();
const router = useRouter();

const platform = ref(null);
const loadError = ref("");
const loading = ref(true);
const tutorialUrlMap = ref(new Map());
const usdProxyPriceTiers = ref([]);
const matchedSkuId = ref(null);
const skuRowRefMap = new Map();
const locateTip = ref("");
const selectedBizId = ref("");
const openPricePopoverSkuId = ref(null);
const priceNoteStyle = ref({});
const priceNotePlacement = ref("right");
const mediaLightbox = ref({ open: false, urls: [], index: 0 });
let locateTipTimer = null;
let priceNoteRelayoutHandler = null;
let mediaLightboxKeyHandler = null;

function statusLabel(status) {
  if (status === "on_sale") return "在售";
  if (status === "pending_test") return "待测试";
  if (status === "off_sale") return "禁售";
  return status || "—";
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

function channelTagList(sku) {
  return (sku?.channel_tags || []).filter((t) => t?.name);
}

function platformTagList() {
  return (platform.value?.platform_tags || []).filter((t) => t?.name);
}

function tagPillStyle(tag) {
  const key = String(tag?.id ?? tag?.name ?? "");
  let hash = 0;
  for (let i = 0; i < key.length; i += 1) hash = (hash * 31 + key.charCodeAt(i)) >>> 0;
  const pair = pillColorPairs[hash % pillColorPairs.length];
  return { backgroundColor: pair.bg, color: pair.text, borderColor: pair.text + "33" };
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
  return tutorialUrlMap.value.get(title) || "";
}

const businesses = computed(() => platform.value?.businesses || []);

const openPricePopoverSku = computed(() => {
  const id = openPricePopoverSkuId.value;
  if (!id) return null;
  for (const biz of businesses.value) {
    const sku = (biz.skus || []).find((s) => String(s.id) === id);
    if (sku) return sku;
  }
  return null;
});
const platformId = computed(() => String(route.params.platformId || ""));
const searchKeyword = computed(() => String(route.query.q || "").trim().toLowerCase());

const selectedBusiness = computed(() => {
  const list = businesses.value;
  if (!list.length) return null;
  const id = selectedBizId.value;
  return list.find((b) => String(b.id) === id) || list[0] || null;
});

function statusTagType(status) {
  if (status === "on_sale") return "success";
  if (status === "pending_test") return "warning";
  if (status === "off_sale") return "danger";
  return "info";
}

function skuRowClassName({ row }) {
  if (matchedSkuId.value && String(matchedSkuId.value) === String(row.id)) {
    return "sku-row-match";
  }
  return "";
}

function setSkuRowRef(skuId, el) {
  const key = String(skuId);
  if (el) skuRowRefMap.set(key, el);
  else skuRowRefMap.delete(key);
}

function skuTextMatched(sku, kw) {
  if (!kw) return false;
  const channels = (sku?.channel_tags || []).map((t) => t?.name).filter(Boolean).join(" ");
  const phrases = quickPhraseTextList(sku).join(" ");
  const text = [sku?.name, sku?.precaution, sku?.tutorial_text, channels, phrases]
    .map((x) => String(x || "").toLowerCase())
    .join(" ");
  return text.includes(kw);
}

function syncSelectedBiz() {
  const list = businesses.value;
  if (!list.length) {
    selectedBizId.value = "";
    return;
  }
  if (!list.some((b) => String(b.id) === selectedBizId.value)) {
    selectedBizId.value = String(list[0].id);
  }
}

function isBizSelected(bizId) {
  return String(selectedBizId.value || selectedBusiness.value?.id || "") === String(bizId);
}

function selectBiz(bizId) {
  selectedBizId.value = String(bizId);
}

function skuCount(biz) {
  return (biz?.skus || []).length;
}

function skuOnSaleCount(biz) {
  return (biz?.skus || []).filter((s) => s?.status === "on_sale").length;
}

function togglePricePopover(skuId, ev) {
  ev?.stopPropagation();
  const id = String(skuId);
  openPricePopoverSkuId.value = openPricePopoverSkuId.value === id ? null : id;
}

function getPriceTriggerEl(skuId) {
  const id = String(skuId || openPricePopoverSkuId.value || "");
  if (!id) return null;
  return document.querySelector(`[data-price-trigger="${id}"]`);
}

function positionPriceNote(triggerEl, attempt = 0) {
  const skuId = openPricePopoverSkuId.value;
  if (!skuId) return;
  const btn = triggerEl || getPriceTriggerEl(skuId);
  if (!btn) {
    if (attempt < 8) {
      nextTick(() => requestAnimationFrame(() => positionPriceNote(null, attempt + 1)));
    }
    return;
  }

  const noteEl = document.querySelector(".sku-price-note--floating");
  if (!noteEl) {
    if (attempt < 8) {
      nextTick(() => requestAnimationFrame(() => positionPriceNote(btn, attempt + 1)));
    }
    return;
  }

  const triggerRect = btn.getBoundingClientRect();
  const noteW = noteEl.offsetWidth || 240;
  const noteH = noteEl.offsetHeight || 120;
  const gap = 10;
  const pad = 12;
  const vw = window.innerWidth;
  const vh = window.innerHeight;

  let left = triggerRect.right + gap;
  let top = triggerRect.top + (triggerRect.height - noteH) / 2;
  let placement = "right";

  if (left + noteW > vw - pad) {
    left = Math.max(pad, triggerRect.left);
    top = triggerRect.bottom + gap;
    placement = "bottom";
    if (left + noteW > vw - pad) {
      left = Math.max(pad, vw - noteW - pad);
    }
  }

  if (top < pad) top = pad;
  if (top + noteH > vh - pad) top = Math.max(pad, vh - noteH - pad);

  priceNotePlacement.value = placement;
  priceNoteStyle.value = {
    position: "fixed",
    left: `${Math.round(left)}px`,
    top: `${Math.round(top)}px`,
    zIndex: "5000",
    maxWidth: `${Math.round(Math.min(320, vw - pad * 2))}px`,
    visibility: "visible",
  };

  if (attempt === 0) {
    nextTick(() => requestAnimationFrame(() => positionPriceNote(btn, 1)));
  }
}

function onPriceNoteRelayout() {
  if (!openPricePopoverSkuId.value) return;
  positionPriceNote(getPriceTriggerEl());
}

function onDocumentClick(ev) {
  if (!openPricePopoverSkuId.value) return;
  if (ev.target.closest("[data-price-trigger]") || ev.target.closest(".sku-price-note--floating")) return;
  closePricePopover();
}

function closePricePopover() {
  openPricePopoverSkuId.value = null;
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

function skuImageUrl(sku) {
  const list = skuImageList(sku);
  return list[0] || "";
}

function openMediaLightbox(urls, index = 0) {
  if (!urls?.length) return;
  mediaLightbox.value = {
    open: true,
    urls,
    index: Math.max(0, Math.min(index, urls.length - 1)),
  };
}

function closeMediaLightbox() {
  mediaLightbox.value.open = false;
}

function showPrevMediaLightbox() {
  const lb = mediaLightbox.value;
  if (!lb.open || lb.urls.length <= 1) return;
  lb.index = (lb.index - 1 + lb.urls.length) % lb.urls.length;
}

function showNextMediaLightbox() {
  const lb = mediaLightbox.value;
  if (!lb.open || lb.urls.length <= 1) return;
  lb.index = (lb.index + 1) % lb.urls.length;
}

function onMediaLightboxKeydown(ev) {
  if (!mediaLightbox.value.open) return;
  if (ev.key === "Escape") closeMediaLightbox();
  else if (ev.key === "ArrowLeft") showPrevMediaLightbox();
  else if (ev.key === "ArrowRight") showNextMediaLightbox();
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

function skuPriceCount(sku) {
  if (isUsdProxyPriceSku(sku)) return usdProxyPriceTiers.value.length;
  return skuPriceItemList(sku).length;
}

function skuHasPrice(sku) {
  if (isUsdProxyPriceSku(sku)) return usdProxyPriceTiers.value.length > 0;
  if (String(sku?.price_notice ?? "").trim()) return true;
  return skuPriceCount(sku) > 0;
}

function formatRatePercent(rate) {
  if (rate == null || rate === "") return "—";
  const n = Number(rate);
  if (Number.isNaN(n)) return `${rate}%`;
  return `${n % 1 === 0 ? n.toFixed(0) : n}%`;
}

function formatRmb(amount) {
  if (amount == null || amount === "") return "—";
  const n = Number(amount);
  if (Number.isNaN(n)) return `¥${amount}`;
  return `¥${n.toFixed(2)}`;
}

async function locateFromQuery() {
  const kw = searchKeyword.value;
  matchedSkuId.value = null;
  if (!kw || !platform.value) return;

  let targetBiz = null;
  let targetSku = null;
  for (const biz of businesses.value) {
    const bizMatched = String(biz?.name || "").toLowerCase().includes(kw);
    const skus = biz?.skus || [];
    const skuMatched = skus.find((sku) => skuTextMatched(sku, kw));
    if (skuMatched || bizMatched) {
      targetBiz = biz;
      targetSku = skuMatched || null;
      break;
    }
  }
  if (!targetBiz) return;

  selectedBizId.value = String(targetBiz.id);

  matchedSkuId.value = targetSku?.id || null;
  await nextTick();
  if (targetSku?.name) {
    locateTip.value = `已定位到 SKU：${targetSku.name}`;
    if (locateTipTimer) clearTimeout(locateTipTimer);
    locateTipTimer = setTimeout(() => {
      locateTip.value = "";
    }, 2500);
  } else if (targetBiz?.name) {
    locateTip.value = `已定位到业务：${targetBiz.name}`;
    if (locateTipTimer) clearTimeout(locateTipTimer);
    locateTipTimer = setTimeout(() => {
      locateTip.value = "";
    }, 2500);
  }
  if (!matchedSkuId.value) return;
  const rowEl =
    skuRowRefMap.get(String(matchedSkuId.value)) ||
    document.getElementById(`sku-row-${matchedSkuId.value}`);
  if (rowEl) {
    rowEl.scrollIntoView({ behavior: "smooth", block: "center" });
  }
}

async function loadPlatform() {
  const id = platformId.value;
  if (!id) return;
  loadError.value = "";
  loading.value = true;
  platform.value = null;
  matchedSkuId.value = null;
  openPricePopoverSkuId.value = null;
  locateTip.value = "";
  try {
    const { data } = await getPlatform(id);
    platform.value = data;
    syncSelectedBiz();
    await locateFromQuery();
  } catch (e) {
    platform.value = null;
    loadError.value =
      e?.response?.data?.detail || e?.response?.data?.message || e?.message || "加载失败";
  } finally {
    loading.value = false;
  }
}

watch(platformId, loadPlatform, { immediate: true });
watch(searchKeyword, async () => {
  if (!loading.value && platform.value) {
    await locateFromQuery();
  }
});

watch(openPricePopoverSkuId, (id) => {
  if (priceNoteRelayoutHandler) {
    window.removeEventListener("resize", priceNoteRelayoutHandler);
    window.removeEventListener("scroll", priceNoteRelayoutHandler, true);
    priceNoteRelayoutHandler = null;
  }
  if (!id) {
    priceNoteStyle.value = {};
    return;
  }
  priceNoteStyle.value = { visibility: "hidden" };
  nextTick(() => requestAnimationFrame(() => positionPriceNote()));
  priceNoteRelayoutHandler = () => onPriceNoteRelayout();
  window.addEventListener("resize", priceNoteRelayoutHandler);
  window.addEventListener("scroll", priceNoteRelayoutHandler, true);
});

async function loadTutorialMap() {
  const m = new Map();
  try {
    const { data } = await listPaymentTutorials();
    const rows = data?.results || data || [];
    rows.forEach((r) => {
      const name = String(r?.name || "").trim();
      const url = String(r?.detail_url || "").trim();
      if (name && url) m.set(name, url);
    });
  } catch (_) {
    /* 远程电脑图文等旧表拉取失败时仍尝试保姆级/部署模板 */
  }
  try {
    const { data } = await listNannyTutorials();
    const rows = data?.results || [];
    rows.forEach((r) => {
      const name = String(r?.name || "").trim();
      const url = String(r?.detail_url || "").trim();
      if (name && url) m.set(name, url);
    });
  } catch (_) {
    /* 忽略 */
  }
  tutorialUrlMap.value = m;
}

async function loadUsdProxyPriceTiers() {
  try {
    const { data } = await listUsdProxyPriceTiers();
    usdProxyPriceTiers.value = data?.results || data || [];
  } catch (_) {
    usdProxyPriceTiers.value = [];
  }
}

function onTutorialLinkClick(ev, title) {
  if (!tutorialUrlByTitle(title)) ev.preventDefault();
}

function statusPillClass(status) {
  if (status === "on_sale") return "sku-status--on";
  if (status === "pending_test") return "sku-status--pending";
  if (status === "off_sale") return "sku-status--off";
  return "";
}

function closeBusinessPage() {
  router.push({ name: "ProductPlatformsClassic" });
}

async function copyText(text) {
  const val = (text || "").trim();
  if (!val) return;
  try {
    await navigator.clipboard.writeText(val);
  } catch (_) {
    const ta = document.createElement("textarea");
    ta.value = val;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
  }
  showCopySuccess();
}

function copyTutorialTitleAndLink(title) {
  const name = String(title || "").trim();
  const url = (tutorialUrlByTitle(title) || "").trim();
  if (name && url) {
    copyText(`${name}\n${url}`);
  } else if (url) {
    copyText(url);
  } else if (name) {
    copyText(name);
  }
}

onMounted(() => {
  loadTutorialMap();
  loadUsdProxyPriceTiers();
  document.addEventListener("click", onDocumentClick);
  mediaLightboxKeyHandler = (ev) => onMediaLightboxKeydown(ev);
  window.addEventListener("keydown", mediaLightboxKeyHandler);
});

onUnmounted(() => {
  document.removeEventListener("click", onDocumentClick);
  if (mediaLightboxKeyHandler) {
    window.removeEventListener("keydown", mediaLightboxKeyHandler);
  }
  if (priceNoteRelayoutHandler) {
    window.removeEventListener("resize", priceNoteRelayoutHandler);
    window.removeEventListener("scroll", priceNoteRelayoutHandler, true);
  }
});
</script>

<template>
  <ContentWrap title="商品详情">
    <template #header>
      <BaseButton @click="closeBusinessPage">关闭</BaseButton>
    </template>

    <ElAlert v-if="loadError" type="error" :closable="false" class="mb-12px" :title="loadError" />
    <div v-else-if="loading" v-loading="loading" class="min-h-200px" />
    <ElAlert v-else-if="!businesses.length" type="info" :closable="false" title="该平台下暂无业务" />

    <template v-else>
      <div class="mb-16px flex items-center gap-8px flex-wrap">
        <span class="text-18px font-700">{{ platform?.name || "—" }}</span>
        <ElTag v-if="platform?.status" :type="statusTagType(platform.status)" size="small">
          {{ platform.status_label || statusLabel(platform.status) }}
        </ElTag>
        <span class="text-13px text-[var(--el-text-color-secondary)]">
          {{ businesses.length }} 个业务
        </span>
      </div>

      <ElAlert v-if="locateTip" :title="locateTip" type="success" show-icon :closable="false" class="mb-12px" />

      <div class="biz-workspace biz-workspace--framed">
        <div class="biz-grid mb-0">
          <button
            v-for="biz in businesses"
            :key="biz.id"
            type="button"
            class="biz-card"
            :class="{ 'is-active': isBizSelected(biz.id) }"
            @click="selectBiz(biz.id)"
          >
            <div class="biz-card__head">
              <span class="biz-card__name">{{ biz.name }}</span>
              <ElTag :type="statusTagType(biz.status)" size="small">
                {{ biz.status_label || statusLabel(biz.status) }}
              </ElTag>
            </div>
            <div class="biz-card__stats">
              <div class="biz-card__stat">
                <span class="biz-card__num">{{ skuCount(biz) }}</span>
                <span>SKU</span>
              </div>
              <div class="biz-card__stat">
                <span class="biz-card__num">{{ skuOnSaleCount(biz) }}</span>
                <span>在售</span>
              </div>
            </div>
            <div class="biz-card__foot">
              <span>{{ isBizSelected(biz.id) ? "当前查看" : "点击切换" }}</span>
              <span class="biz-card__action">查看商品 ›</span>
            </div>
          </button>
        </div>

        <section v-if="selectedBusiness" class="biz-panel">
          <div class="biz-panel__head">
            <span class="biz-panel__dot" />
            <span>
              当前业务：
              <strong>{{ selectedBusiness.name }}</strong>
            </span>
            <ElTag :type="statusTagType(selectedBusiness.status)" size="small">
              {{ selectedBusiness.status_label || statusLabel(selectedBusiness.status) }}
            </ElTag>
          </div>
          <SkuBizTable
            :key="selectedBusiness.id"
            :biz="selectedBusiness"
            :matched-sku-id="matchedSkuId"
            :open-price-popover-sku-id="openPricePopoverSkuId"
            :platform-tags="platformTagList()"
            :tutorial-url-map="tutorialUrlMap"
            :usd-proxy-price-tiers="usdProxyPriceTiers"
            @set-row-ref="setSkuRowRef"
            @open-lightbox="openMediaLightbox"
            @toggle-price="togglePricePopover"
            @copy-text="copyText"
            @copy-tutorial="copyTutorialTitleAndLink"
            @tutorial-click="onTutorialLinkClick"
          />
        </section>
      </div>
    </template>

    <Teleport to="body">
      <div
        v-if="openPricePopoverSku"
        class="sku-price-note sku-price-note--floating"
        :class="`sku-price-note--${priceNotePlacement}`"
        :style="priceNoteStyle"
        @click.stop
      >
        <p v-if="openPricePopoverSku.price_type_label" class="sku-price-note-type">
          {{ openPricePopoverSku.price_type_label }}
        </p>
        <table v-if="isUsdProxyPriceSku(openPricePopoverSku)" class="usd-proxy-price-table">
          <thead>
            <tr>
              <th>美金</th>
              <th>费率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="tier in usdProxyPriceTiers" :key="tier.id">
              <td>{{ tier.usd_range }}</td>
              <td>{{ formatRatePercent(tier.rate_percent) }}</td>
            </tr>
          </tbody>
        </table>
        <ul v-else class="sku-price-list">
          <li
            v-for="(item, idx) in skuPriceItemList(openPricePopoverSku)"
            :key="`${openPricePopoverSku.id}-price-${item.id || idx}`"
            class="sku-price-item"
          >
            <div class="sku-price-row">
              <span v-if="item.label?.trim()" class="sku-price-label">{{ item.label }}</span>
              <span v-if="item.label?.trim()" class="sku-price-arrow">→</span>
              <span class="sku-price-rmb">{{ formatRmb(item.rmb_amount) }}</span>
            </div>
            <div v-if="item.notice?.trim()" class="sku-price-item-notice">{{ item.notice }}</div>
          </li>
        </ul>
        <div v-if="openPricePopoverSku.price_notice?.trim()" class="sku-price-group-notice">
          {{ openPricePopoverSku.price_notice }}
        </div>
      </div>
    </Teleport>

    <ElImageViewer
      v-if="mediaLightbox.open"
      :url-list="mediaLightbox.urls"
      :initial-index="mediaLightbox.index"
      @close="closeMediaLightbox"
      @switch="(idx) => { mediaLightbox.index = idx }"
    />
  </ContentWrap>
</template>

<style scoped>
/* 参考 shadcn Card/Shadow Tabs：选中卡抬起 + 下方内容同框归属 */
.biz-workspace--framed {
  margin-bottom: 16px;
  padding: 14px;
  border: 1px solid #dbe4f0;
  border-radius: 14px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 48px);
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
}
.biz-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
  margin-bottom: 14px;
}
.biz-card {
  display: flex;
  flex-direction: column;
  min-height: 148px;
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #fff;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    transform 0.18s ease;
}
.biz-card:hover {
  border-color: #93c5fd;
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.12);
}
.biz-card.is-active {
  position: relative;
  z-index: 1;
  border-color: #2563eb;
  border-width: 2px;
  background: #fff;
  box-shadow:
    0 0 0 4px rgba(37, 99, 235, 0.12),
    0 14px 32px rgba(37, 99, 235, 0.28);
  transform: translateY(-2px);
}
.biz-card.is-active .biz-card__foot {
  border-top-color: #bfdbfe;
  color: #1d4ed8;
}
.biz-card.is-active .biz-card__action {
  color: #1d4ed8;
}
.biz-panel {
  border: 1px solid #dbe4f0;
  border-radius: 12px;
  background: #fff;
  padding: 12px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
}
.biz-workspace--framed .biz-panel {
  border-color: #bfdbfe;
  box-shadow: 0 8px 22px rgba(37, 99, 235, 0.08);
}
.biz-panel__head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #eff6ff;
  color: #1e3a8a;
  font-size: 13px;
}
.biz-panel__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #2563eb;
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.18);
}
.biz-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 12px;
}
.biz-card__name {
  font-size: 16px;
  font-weight: 700;
  line-height: 1.35;
  color: var(--el-text-color-primary);
  word-break: break-word;
}
.biz-card__stats {
  flex: 1 1 auto;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 12px;
}
.biz-card__stat {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--el-fill-color-light);
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.biz-card__num {
  font-size: 22px;
  font-weight: 700;
  line-height: 1.1;
  color: var(--el-text-color-primary);
}
.biz-card__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding-top: 10px;
  border-top: 1px solid var(--el-border-color-lighter);
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.biz-card__action {
  color: var(--el-color-primary);
  font-weight: 600;
}
.sku-price-note--floating {
  position: relative;
  box-sizing: border-box;
  width: max-content;
  max-width: min(320px, calc(100vw - 24px));
  padding: 10px 12px;
  border-radius: 6px;
  background: #10b981;
  border: 1px solid #6ee7b7;
  box-shadow: 0 10px 28px rgba(5, 150, 105, 0.32);
  pointer-events: auto;
  color: #fff;
}
.sku-price-note--floating.sku-price-note--right::before {
  content: "";
  position: absolute;
  left: -7px;
  top: 50%;
  width: 12px;
  height: 12px;
  background: #10b981;
  border-left: 1px solid #6ee7b7;
  border-bottom: 1px solid #6ee7b7;
  transform: translateY(-50%) rotate(45deg);
}
.sku-price-note--floating.sku-price-note--bottom::before {
  content: "";
  position: absolute;
  left: 24px;
  top: -7px;
  width: 12px;
  height: 12px;
  background: #10b981;
  border-left: 1px solid #6ee7b7;
  border-top: 1px solid #6ee7b7;
  transform: rotate(45deg);
}
.sku-price-note--floating .sku-price-note-type {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 700;
  color: #fcd34d;
}
.sku-price-note--floating .sku-price-label {
  color: #fff;
  font-weight: 500;
}
.sku-price-note--floating .sku-price-arrow {
  color: rgba(255, 255, 255, 0.78);
}
.sku-price-note--floating .sku-price-rmb {
  color: #fcd34d;
  font-weight: 700;
}
.sku-price-note--floating .sku-price-group-notice,
.sku-price-note--floating .sku-price-item-notice {
  margin-top: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.22);
  color: #fff;
  font-size: 12px;
  line-height: 1.45;
  white-space: pre-wrap;
  word-break: break-word;
}
.sku-price-note--floating .sku-price-item-notice {
  margin-top: 4px;
  width: fit-content;
  max-width: 100%;
}
.sku-price-note--floating .usd-proxy-price-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  margin-top: 4px;
  color: #fff;
}
.sku-price-note--floating .usd-proxy-price-table th,
.sku-price-note--floating .usd-proxy-price-table td {
  border: 1px solid rgba(255, 255, 255, 0.22);
  padding: 6px 10px;
  text-align: left;
}
.sku-price-note--floating .usd-proxy-price-table th {
  background: rgba(255, 255, 255, 0.12);
  font-weight: 600;
}
.sku-price-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.sku-price-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.sku-price-row {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px 10px;
  font-size: 15px;
  line-height: 1.4;
}
</style>
