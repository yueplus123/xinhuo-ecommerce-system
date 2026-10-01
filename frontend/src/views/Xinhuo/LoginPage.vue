<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

/** Legacy entry — router uses @/views/Login/Login.vue; redirect if imported directly. */
defineOptions({ name: 'LoginPageRedirect' })

const route = useRoute()
const router = useRouter()

onMounted(() => {
  router.replace({ path: '/login', query: route.query })
})
</script>

<template>
  <div />
</template>
