<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

const WEEKDAYS = ["日", "一", "二", "三", "四", "五", "六"];
const MONTHS = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"];

const props = defineProps({
  dateFrom: { type: String, default: "" },
  dateTo: { type: String, default: "" },
  label: { type: String, default: "订单时间" },
  placeholder: { type: String, default: "选择时间区间" },
});

const emit = defineEmits(["update:dateFrom", "update:dateTo"]);

const open = ref(false);
const rootEl = ref(null);
const committedFrom = ref("");
const committedTo = ref("");
const draftFrom = ref(null);
const draftTo = ref(null);
const viewMonth = ref(new Date(new Date().getFullYear(), new Date().getMonth(), 1));
const pickingEnd = ref(false);
const hoverDate = ref(null);

function parseYmd(s) {
  if (!s) return null;
  const m = String(s).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!m) return null;
  return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
}

function formatYmd(d) {
  if (!d) return "";
  const y = d.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, "0");
  const da = String(d.getDate()).padStart(2, "0");
  return `${y}-${mo}-${da}`;
}

function cloneDay(d) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

function sameDay(a, b) {
  return (
    a &&
    b &&
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

function compareDay(a, b) {
  return a.getFullYear() - b.getFullYear() || a.getMonth() - b.getMonth() || a.getDate() - b.getDate();
}

function addMonths(base, delta) {
  return new Date(base.getFullYear(), base.getMonth() + delta, 1);
}

function monthTitle(d) {
  return `${d.getFullYear()}年 ${MONTHS[d.getMonth()]}`;
}

function normalizeRange(a, b) {
  if (compareDay(a, b) <= 0) return [cloneDay(a), cloneDay(b)];
  return [cloneDay(b), cloneDay(a)];
}

function syncCommittedFromProps() {
  committedFrom.value = props.dateFrom || "";
  committedTo.value = props.dateTo || "";
}

watch(() => [props.dateFrom, props.dateTo], syncCommittedFromProps, { immediate: true });

const triggerLabel = computed(() => {
  const a = committedFrom.value;
  const b = committedTo.value;
  if (a && b) return `${a} 至 ${b}`;
  if (a) return `${a} 起`;
  if (b) return `至 ${b}`;
  return props.placeholder;
});

const leftTitle = computed(() => monthTitle(viewMonth.value));
const rightTitle = computed(() => monthTitle(addMonths(viewMonth.value, 1)));

function effectiveEnd() {
  if (draftTo.value) return draftTo.value;
  if (pickingEnd.value && hoverDate.value) return hoverDate.value;
  return null;
}

function rangeBounds() {
  if (!draftFrom.value) return null;
  const end = effectiveEnd();
  if (!end) return [draftFrom.value, draftFrom.value];
  return normalizeRange(draftFrom.value, end);
}

function buildPaneCells(monthStart) {
  const year = monthStart.getFullYear();
  const month = monthStart.getMonth();
  const firstWeekday = new Date(year, month, 1).getDay();
  const gridStart = new Date(year, month, 1 - firstWeekday);
  const bounds = rangeBounds();
  const today = new Date();
  const todayLocal = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const rows = [];

  for (let row = 0; row < 6; row += 1) {
    const cells = [];
    for (let col = 0; col < 7; col += 1) {
      const offset = row * 7 + col;
      const cellDate = new Date(gridStart.getFullYear(), gridStart.getMonth(), gridStart.getDate() + offset);
      const isOther = cellDate.getMonth() !== month;
      const classes = ["range-cal-day"];
      if (isOther) classes.push("is-other");
      if (sameDay(cellDate, todayLocal)) classes.push("is-today");

      let isStart = false;
      let isEnd = false;
      if (bounds) {
        const cmpStart = compareDay(cellDate, bounds[0]);
        const cmpEnd = compareDay(cellDate, bounds[1]);
        isStart = cmpStart === 0;
        isEnd = cmpEnd === 0;
        if (cmpStart >= 0 && cmpEnd <= 0) {
          classes.push("is-in-range");
          if (isStart) classes.push("is-range-start");
          if (isEnd) classes.push("is-range-end");
          if (!isStart && !isEnd) classes.push("is-range-middle");
        }
      }

      cells.push({
        key: formatYmd(cellDate),
        ymd: formatYmd(cellDate),
        day: cellDate.getDate(),
        classes,
        innerClass: isStart || isEnd ? "range-cal-day-inner is-edge" : "range-cal-day-inner",
      });
    }
    rows.push(cells);
  }
  return rows;
}

const leftPane = computed(() => buildPaneCells(viewMonth.value));
const rightPane = computed(() => buildPaneCells(addMonths(viewMonth.value, 1)));

function setDraftRange(from, to) {
  draftFrom.value = from ? cloneDay(from) : null;
  draftTo.value = to ? cloneDay(to) : null;
  pickingEnd.value = Boolean(draftFrom.value && !draftTo.value);
  hoverDate.value = null;
  if (draftFrom.value) {
    viewMonth.value = new Date(draftFrom.value.getFullYear(), draftFrom.value.getMonth(), 1);
  }
}

function openPanel() {
  setDraftRange(parseYmd(committedFrom.value), parseYmd(committedTo.value));
  open.value = true;
}

function closePanel(revert) {
  if (revert) {
    setDraftRange(parseYmd(committedFrom.value), parseYmd(committedTo.value));
  }
  open.value = false;
}

function applyPanel() {
  if (!draftFrom.value || !draftTo.value) return;
  committedFrom.value = formatYmd(draftFrom.value);
  committedTo.value = formatYmd(draftTo.value);
  emit("update:dateFrom", committedFrom.value);
  emit("update:dateTo", committedTo.value);
  open.value = false;
}

function clearPanel() {
  draftFrom.value = null;
  draftTo.value = null;
  pickingEnd.value = false;
  hoverDate.value = null;
}

function onDayClick(ymd) {
  const day = parseYmd(ymd);
  if (!day) return;
  if (!draftFrom.value || (draftFrom.value && draftTo.value)) {
    draftFrom.value = cloneDay(day);
    draftTo.value = null;
    pickingEnd.value = true;
    hoverDate.value = null;
  } else {
    const range = normalizeRange(draftFrom.value, day);
    draftFrom.value = range[0];
    draftTo.value = range[1];
    pickingEnd.value = false;
    hoverDate.value = null;
  }
}

function onDayHover(ymd) {
  if (!pickingEnd.value || !draftFrom.value) return;
  const day = parseYmd(ymd);
  if (day) hoverDate.value = cloneDay(day);
}

function onDayLeave() {
  hoverDate.value = null;
}

function shiftMonth(delta) {
  viewMonth.value = addMonths(viewMonth.value, delta);
}

function onDocumentClick(ev) {
  if (!open.value) return;
  if (rootEl.value && !rootEl.value.contains(ev.target)) closePanel(true);
}

onMounted(() => document.addEventListener("click", onDocumentClick));
onBeforeUnmount(() => document.removeEventListener("click", onDocumentClick));
</script>

<template>
  <div ref="rootEl" class="range-picker">
    <span v-if="label" class="range-picker__heading">{{ label }}</span>
    <button
      type="button"
      class="range-picker__trigger"
      :aria-expanded="open ? 'true' : 'false'"
      @click.stop="open ? closePanel(true) : openPanel()"
    >
      <span class="range-picker__trigger-text">{{ triggerLabel }}</span>
    </button>
    <div v-show="open" class="range-picker__panel" @click.stop>
      <div class="range-cal">
        <div class="range-cal__toolbar">
          <div class="range-cal__nav-group">
            <button type="button" class="range-cal__nav" aria-label="上一年" @click="shiftMonth(-12)">&laquo;</button>
            <button type="button" class="range-cal__nav" aria-label="上一月" @click="shiftMonth(-1)">&lsaquo;</button>
          </div>
          <div class="range-cal__titles">
            <span class="range-cal__title">{{ leftTitle }}</span>
            <span class="range-cal__title">{{ rightTitle }}</span>
          </div>
          <div class="range-cal__nav-group">
            <button type="button" class="range-cal__nav" aria-label="下一月" @click="shiftMonth(1)">&rsaquo;</button>
            <button type="button" class="range-cal__nav" aria-label="下一年" @click="shiftMonth(12)">&raquo;</button>
          </div>
        </div>
        <div class="range-cal__panes">
          <div v-for="(pane, pi) in [leftPane, rightPane]" :key="pi" class="range-cal__pane">
            <table class="range-cal__table">
              <thead>
                <tr>
                  <th v-for="w in WEEKDAYS" :key="`${pi}-${w}`">{{ w }}</th>
                </tr>
              </thead>
              <tbody @mouseleave="onDayLeave">
                <tr v-for="(row, ri) in pane" :key="`${pi}-r-${ri}`">
                  <td
                    v-for="cell in row"
                    :key="cell.key"
                    :class="cell.classes"
                    @click="onDayClick(cell.ymd)"
                    @mouseover="onDayHover(cell.ymd)"
                  >
                    <span :class="cell.innerClass">{{ cell.day }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <div class="range-picker__actions">
        <button type="button" class="btn-secondary" @click="clearPanel">清空</button>
        <button type="button" class="btn-primary" :disabled="!draftFrom || !draftTo" @click="applyPanel">确定</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.range-picker {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 240px;
  flex: 1 1 240px;
  max-width: 340px;
}

.range-picker__heading {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-soft);
  white-space: nowrap;
}

.range-picker__trigger {
  width: 100%;
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid rgba(148, 163, 184, 0.48);
  border-radius: 10px;
  background: #fff;
  text-align: left;
  cursor: pointer;
  font-size: 13px;
  color: var(--text);
}

.range-picker__trigger:hover {
  border-color: var(--green-500);
}

.range-picker__trigger-text {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.range-picker__panel {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  z-index: 120;
  width: 580px;
  max-width: calc(100vw - 32px);
  padding: 8px 12px 12px;
  border: 1px solid var(--gray-200);
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.12);
}

.range-cal__toolbar {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.range-cal__nav-group {
  display: inline-flex;
  gap: 2px;
}

.range-cal__nav {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--gray-600);
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
}

.range-cal__nav:hover {
  background: var(--gray-100);
  color: var(--gray-900);
}

.range-cal__titles {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  text-align: center;
}

.range-cal__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--gray-800);
}

.range-cal__panes {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.range-cal__table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.range-cal__table th {
  height: 32px;
  font-size: 12px;
  font-weight: 500;
  color: var(--gray-500);
  text-align: center;
}

.range-cal-day {
  padding: 2px 0;
  text-align: center;
  vertical-align: middle;
  cursor: pointer;
  user-select: none;
}

.range-cal-day-inner {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  font-size: 13px;
  color: var(--gray-800);
  border-radius: 50%;
  position: relative;
  z-index: 1;
}

.range-cal-day.is-other .range-cal-day-inner {
  color: var(--gray-400);
}

.range-cal-day.is-today:not(.is-range-start):not(.is-range-end) .range-cal-day-inner {
  border: 1px solid #1677ff;
}

.range-cal-day.is-in-range {
  background: #e6f4ff;
}

.range-cal-day.is-range-start {
  background: linear-gradient(to right, transparent 50%, #e6f4ff 50%);
}

.range-cal-day.is-range-end {
  background: linear-gradient(to left, transparent 50%, #e6f4ff 50%);
}

.range-cal-day.is-range-start.is-range-end {
  background: transparent;
}

.range-cal-day-inner.is-edge {
  background: #1677ff;
  color: #fff;
}

.range-cal-day:hover:not(.is-range-start):not(.is-range-end) .range-cal-day-inner {
  background: rgba(22, 119, 255, 0.12);
}

.range-picker__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--gray-100);
}

.btn-primary,
.btn-secondary {
  min-height: 32px;
  padding: 0 12px;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
}

.btn-primary {
  border: none;
  background: var(--green-600);
  color: #fff;
}

.btn-primary:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.btn-secondary {
  border: 1px solid var(--gray-200);
  background: #fff;
  color: var(--text);
}

@media (max-width: 720px) {
  .range-picker {
    max-width: none;
  }

  .range-picker__panel {
    width: min(320px, calc(100vw - 32px));
  }

  .range-cal__panes {
    grid-template-columns: 1fr;
  }

  .range-cal__titles {
    grid-template-columns: 1fr;
  }

  .range-cal__title:last-child {
    display: none;
  }
}
</style>
