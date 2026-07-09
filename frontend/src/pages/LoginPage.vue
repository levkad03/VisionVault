<script setup lang="ts">
import { useAuthStore } from '@/stores/auth';
import { ref } from 'vue';
import { useRouter } from 'vue-router';

const email = ref('');
const password = ref('');
const loading = ref(false);
const error = ref('');
const auth = useAuthStore();
const router = useRouter();

async function onSubmit() {
  error.value = '';
  loading.value = true;

  try {
    await auth.login(email.value, password.value);
    router.push({ name: 'dashboard' });
  } catch {
    error.value = 'Invalid credentials';
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <form class="mx-auto mt-24 flex max-w-sm flex-col gap-4" @submit.prevent="onSubmit">
    <h1 class="text-xl font-bold">Log in</h1>
    <input v-model="email" type="email" placeholder="Email" required class="border p-2" />
    <input v-model="password" type="password" placeholder="Password" required class="border p-2" />
    <p v-if="error" class="text-red-500">{{ error }}</p>
    <button type="submit" :disabled="loading" class="bg-black p-2 text-white">Log in</button>
    <RouterLink to="/register" class="text-sm underline">Need an account?</RouterLink>
  </form>
</template>
