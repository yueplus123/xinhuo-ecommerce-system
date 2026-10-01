<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const open = ref(false);
const rootRef = ref(null);

const displayName = computed(() => auth.me?.username || "用户");

const isActive = computed(() => {
  const path = route.path.replace(/\/+$/, "") || "/";
  return path === "/profile" || path.startsWith("/profile/");
});

function toggleMenu() {
  open.value = !open.value;
}

function closeMenu() {
  open.value = false;
}

function onDocumentClick(e) {
  if (!rootRef.value?.contains(e.target)) closeMenu();
}

function onKeydown(e) {
  if (e.key === "Escape") closeMenu();
}

onMounted(() => {
  document.addEventListener("click", onDocumentClick);
  document.addEventListener("keydown", onKeydown);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", onDocumentClick);
  document.removeEventListener("keydown", onKeydown);
});

function logout() {
  closeMenu();
  auth.logout();
  router.replace({ path: "/login" });
}
</script>

<template>
  <div ref="rootRef" class="user-profile-nav-wrap">
    <button
      type="button"
      class="user-profile-nav"
      :class="{ 'user-profile-nav--open': open, 'user-profile-nav--active': isActive }"
      aria-haspopup="menu"
      :aria-expanded="open"
      @click.stop="toggleMenu"
    >
      <span class="user-profile-nav__name">{{ displayName }}</span>
    </button>

    <transition name="menu-fade">
      <div v-if="open" class="user-profile-menu" role="menu">
        <router-link
          to="/profile"
          class="user-profile-menu__item"
          role="menuitem"
          @click="closeMenu"
        >
          查看个人资料
        </router-link>
        <button
          type="button"
          class="user-profile-menu__item user-profile-menu__item--danger"
          role="menuitem"
          @click="logout"
        >
          退出登录
        </button>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.user-profile-nav-wrap {
  position: relative;
}

.user-profile-nav {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  max-width: 160px;
  min-height: 36px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid var(--gray-200);
  background: #fff;
  color: var(--gray-700);
  font-family: inherit;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  transition: border-color 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
}

.user-profile-nav:hover,
.user-profile-nav--open {
  border-color: var(--green-100);
  background: var(--green-50);
  color: var(--gray-900);
}

.user-profile-nav--active {
  border-color: var(--green-100);
  background: var(--green-50);
  box-shadow: 0 2px 8px rgba(5, 150, 105, 0.12);
}

.user-profile-nav__name {
  font-size: 14px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.user-profile-menu {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  z-index: 1200;
  min-width: 168px;
  padding: 6px;
  border-radius: 12px;
  border: 1px solid var(--gray-200);
  background: #fff;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.12);
}

.user-profile-menu__item {
  display: flex;
  align-items: center;
  width: 100%;
  min-height: 40px;
  padding: 0 12px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--gray-700);
  font-size: 14px;
  font-weight: 500;
  font-family: inherit;
  text-decoration: none;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.user-profile-menu__item:hover {
  background: var(--gray-100);
  color: var(--gray-900);
}

.user-profile-menu__item--danger {
  color: #dc2626;
}

.user-profile-menu__item--danger:hover {
  background: #fef2f2;
  color: #b91c1c;
}

.menu-fade-enter-active,
.menu-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.menu-fade-enter-from,
.menu-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

@media (max-width: 900px) {
  .user-profile-nav {
    max-width: 120px;
    min-height: 34px;
    padding: 0 10px;
  }
  .user-profile-nav__name {
    font-size: 13px;
  }
}
</style>
