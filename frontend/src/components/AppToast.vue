<script setup>
import { onBeforeUnmount, watch } from "vue";

const props = defineProps({
  message: { type: String, default: "" },
  type: { type: String, default: "success" },
  durationMs: { type: Number, default: 4000 },
});

const emit = defineEmits(["hide"]);

let hideTimer = null;

function clearHideTimer() {
  if (hideTimer != null) {
    clearTimeout(hideTimer);
    hideTimer = null;
  }
}

function scheduleHide() {
  clearHideTimer();
  if (!props.message) return;
  hideTimer = window.setTimeout(() => {
    emit("hide");
  }, props.durationMs);
}

watch(
  () => props.message,
  (msg) => {
    clearHideTimer();
    if (msg) scheduleHide();
  },
  { immediate: true }
);

onBeforeUnmount(clearHideTimer);
</script>

<template>
  <Teleport to="body">
    <div
      v-if="message"
      class="app-toast"
      :class="`app-toast--${type}`"
      :style="{ animationDuration: `${durationMs}ms` }"
      role="status"
      aria-live="polite"
    >
      {{ message }}
    </div>
  </Teleport>
</template>

<style scoped>
.app-toast {
  position: fixed;
  top: max(20px, env(safe-area-inset-top, 0px));
  left: 50%;
  z-index: 3000;
  transform: translateX(-50%);
  max-width: min(92vw, 520px);
  padding: 12px 20px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.45;
  text-align: center;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.14);
  pointer-events: none;
  animation-name: app-toast-life;
  animation-timing-function: ease;
  animation-fill-mode: forwards;
}

.app-toast--success {
  background: #fff;
  color: var(--green-600, #059669);
  border: 1px solid var(--green-100, #d1fae5);
}

.app-toast--warning {
  background: #fffbeb;
  color: #b45309;
  border: 1px solid #fde68a;
}

.app-toast--error {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

@keyframes app-toast-life {
  0% {
    opacity: 0;
    transform: translateX(-50%) translateY(-10px);
  }
  10% {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
  55% {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
  100% {
    opacity: 0;
    transform: translateX(-50%) translateY(-6px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .app-toast {
    animation: none;
    opacity: 1;
  }
}
</style>
