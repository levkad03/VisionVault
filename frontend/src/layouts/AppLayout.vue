<script setup lang="ts">
import { Button } from '@/components/ui/button';
import { useTheme } from '@/composables/useTheme';
import { useAuthStore } from '@/stores/auth';
import { Moon, Sun } from '@lucide/vue';
import { useRouter } from 'vue-router';

const auth = useAuthStore();
const router = useRouter();
const { isDark, toggleTheme } = useTheme();

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
        <Button variant="ghost" size="icon" @click="toggleTheme()">
          <Sun v-if="isDark" class="size-4" />
          <Moon v-else class="size-4" />
        </Button>
        <span class="text-sm">{{ auth.user?.email }}</span>
        <Button variant="link" size="sm" class="p-0" @click="onLogout">Logout</Button>
      </div>
    </header>
    <main class="p-4">
      <RouterView />
    </main>
  </div>
</template>
