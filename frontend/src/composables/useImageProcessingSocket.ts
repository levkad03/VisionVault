import { useAuthStore } from '@/stores/auth';
import { useQueryClient } from '@tanstack/vue-query';
import { createSharedComposable, useWebSocket } from '@vueuse/core';
import { computed, watch } from 'vue';

const BASE_URL = import.meta.env.VITE_API_BASE_URL;
const WS_BASE_URL = BASE_URL.replace(/^http/, 'ws');

export interface ProcessingImage {
  image_id: string;
  stage: string;
  status: string;
}

function parseMessage(raw: string | null): ProcessingImage | null {
  if (!raw) return null;

  try {
    return JSON.parse(raw) as ProcessingImage;
  } catch {
    console.warn('Ignoring malformed processing message:', raw);
    return null;
  }
}

function useImageProcessingSocketImpl() {
  const auth = useAuthStore();
  const queryClient = useQueryClient();
  const url = computed(() =>
    auth.accessToken ? `${WS_BASE_URL}/ws/images?token=${auth.accessToken}` : undefined,
  );

  const { data, status } = useWebSocket<string>(url, {
    autoReconnect: true,
  });

  const lastMessage = computed(() => parseMessage(data.value));

  watch(lastMessage, (message) => {
    if (message) queryClient.invalidateQueries({ queryKey: ['images'] });
  });

  return { lastMessage, status };
}

export const useImageProcessingSocket = createSharedComposable(useImageProcessingSocketImpl);
