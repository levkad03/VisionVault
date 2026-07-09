import type { User } from '@/types/auth';
import { defineStore } from 'pinia';
import { computed, ref } from 'vue';

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(localStorage.getItem('access_token'));
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'));
  const user = ref<User | null>(null);

  const isAuthenticated = computed(() => !!accessToken.value);

  function setTokens(tokens: { access_token: string; refresh_token: string }) {
    accessToken.value = tokens.access_token;
    refreshToken.value = tokens.refresh_token;

    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);
  }

  async function login(email: string, password: string) {
    setTokens(await authApi.login(email, password));
    user.value = await authApi.fetchMe();
  }

  async function register(email: string, password: string) {
    await authApi.register(email, password);
    await login(email, password);
  }

  async function refreshTokens() {
    if (!refreshToken.value) throw new Error('No refresh token');
    setTokens(await authApi.refreshTokenRequest(refreshToken.value));
  }

  async function hydrate() {
    if (accessToken.value) {
      user.value = await authApi.fetchMe().catch(() => null);
    }
  }

  function logout() {
    accessToken.value = null;
    refreshToken.value = null;
    user.value = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }

  return {
    accessToken,
    refreshToken,
    user,
    isAuthenticated,
    login,
    register,
    refreshTokens,
    hydrate,
    logout,
  };
});
