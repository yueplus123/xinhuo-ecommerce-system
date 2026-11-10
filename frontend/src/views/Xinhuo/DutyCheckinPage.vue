<script setup lang="ts">
/**
 * 备忘打卡（原值班打卡）：内嵌 public/duty.html，数据走 /api/duty/*。
 * 销卡、补库存 A/B 轮流；月底清理 + 通知充值；月初 1–3 号解绑。只能当天打卡，漏了不能补。
 */
defineOptions({ name: 'DutyCheckin' })

// 带时间戳，避免浏览器一直用缓存里的旧版 duty.html
const src = `/duty.html?v=${Date.now()}`
</script>

<template>
  <div class="duty-checkin">
    <iframe :src="src" title="备忘打卡" class="duty-checkin__frame"></iframe>
  </div>
</template>

<style scoped>
.duty-checkin {
  height: calc(100vh - 120px);
  min-height: 560px;
}
.duty-checkin__frame {
  display: block;
  width: 100%;
  height: 100%;
  border: 0;
  border-radius: 12px;
  background: transparent;
}
</style>
