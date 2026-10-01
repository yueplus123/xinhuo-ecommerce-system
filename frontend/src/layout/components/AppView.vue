<script setup lang="ts">
import { useAppStore } from '@/store/modules/app'
import { Footer } from '@/components/Footer'
import { computed } from 'vue'

const appStore = useAppStore()

const footer = computed(() => appStore.getFooter)
</script>

<template>
  <section
    :class="[
      'box-border p-[var(--app-content-padding)] w-full min-h-full bg-[var(--app-content-bg-color)] dark:bg-[var(--el-bg-color)]',
      {
        '!min-h-[calc(100vh-var(--top-tool-height)-var(--app-footer-height))] pb-0': footer
      }
    ]"
  >
    <router-view v-slot="{ Component, route }">
      <keep-alive :max="20">
        <component :is="Component" v-if="!route.meta?.noCache" :key="route.name" />
      </keep-alive>
      <component :is="Component" v-if="route.meta?.noCache" :key="route.fullPath" />
    </router-view>
  </section>
  <Footer v-if="footer" />
</template>
