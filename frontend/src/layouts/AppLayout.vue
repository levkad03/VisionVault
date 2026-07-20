<script setup lang="ts">
import { useAuthStore } from '@/stores/auth';
import { useRouter } from 'vue-router';

const auth = useAuthStore();
const router = useRouter();

function onLogout() {
  auth.logout();
  router.push({ name: 'login' });
}
</script>

<template>
  <div>
    <header class="flex items-center justify-between border-b p-4">
      <span>VisionVault</span>
      <nav class="flex gap-4 text-sm">
        <RouterLink to="/">Dashboard</RouterLink>
        <RouterLink to="/upload">Upload</RouterLink>
        <RouterLink to="/gallery">Gallery</RouterLink>
        <RouterLink to="/search">Search</RouterLink>
      </nav>
      <div class="flex items-center gap-4">
        <span class="text-sm">{{ auth.user?.email }}</span>
        <button class="text-sm underline" @click="onLogout">Logout</button>
      </div>
    </header>
    <main class="p-4">
      <RouterView />
    </main>
  </div>
</template>
