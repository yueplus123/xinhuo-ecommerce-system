<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue";

const todayLabel = ref("");
const beijingTime = ref("--:--:--");
const newYorkTime = ref("--:--:--");
const tokyoTime = ref("--:--:--");
const usdCny = ref("加载中");
let clockTimer = null;
let quoteTimer = null;

function formatDateCN(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const week = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"][d.getDay()];
  return `${y}年${m}月${day}日 ${week}`;
}

function formatTimeInZone(timeZone) {
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone,
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date());
}

function refreshClock() {
  const now = new Date();
  todayLabel.value = formatDateCN(now);
  beijingTime.value = formatTimeInZone("Asia/Shanghai");
  newYorkTime.value = formatTimeInZone("America/New_York");
  tokyoTime.value = formatTimeInZone("Asia/Tokyo");
}

async function loadUsdCny() {
  try {
    const resp = await fetch("https://open.er-api.com/v6/latest/USD");
    const data = await resp.json();
    const cny = data?.rates?.CNY;
    usdCny.value = Number.isFinite(cny) ? `${Number(cny).toFixed(4)}` : "获取失败";
  } catch (_) {
    usdCny.value = "获取失败";
  }
}

onMounted(async () => {
  refreshClock();
  clockTimer = setInterval(refreshClock, 1000);
  await loadUsdCny();
  quoteTimer = setInterval(loadUsdCny, 10 * 60 * 1000);
});

onBeforeUnmount(() => {
  if (clockTimer) clearInterval(clockTimer);
  if (quoteTimer) clearInterval(quoteTimer);
});
</script>

<template>
  <div class="status-strip">
    <span class="status-chip">📅 {{ todayLabel }}</span>
    <span class="status-chip">北京 {{ beijingTime }}</span>
    <span class="status-chip">东京 {{ tokyoTime }}</span>
    <span class="status-chip">纽约 {{ newYorkTime }}</span>
    <span class="status-chip status-chip--rate">USD/CNY {{ usdCny }}</span>
  </div>
</template>

<style scoped>
.status-strip {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 0;
  width: 100%;
}
.status-chip {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 4px 12px;
  border-radius: 10px;
  border: 1px solid var(--gray-200);
  background: #fff;
  font-size: 13px;
  color: var(--gray-700);
  font-family: var(--font-body);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.status-chip--rate {
  color: var(--green-600);
  font-weight: 600;
  background: var(--green-50);
  border-color: var(--green-100);
}

@media (max-width: 900px) {
  .status-strip {
    margin-bottom: 0;
  }
}
</style>
