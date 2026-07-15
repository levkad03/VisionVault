<script setup lang="ts">
import { useAuthStore } from '@/stores/auth';

const auth = useAuthStore();
</script>

<template>
  <div>
    <h1 class="text-xl font-bold">Dashboard</h1>
    <p>Logged in as {{ auth.user?.email }}</p>
  </div>
</template>
