import { useAuthStore } from '@/stores/auth';
import { useQueryClient } from '@tanstack/vue-query';
import { createSharedComposable, useWebSocket } from '@vueuse/core';
import { computed, reactive, ref } from 'vue';

const BASE_URL = import.meta.env.VITE_API_BASE_URL;
const WS_BASE_URL = BASE_URL.replace(/^http/, 'ws');

export interface ProcessingImage {
  image_id: string;
  stage: string;
  status: string;
}

// Backend publishes a stage after it finishes, so each label names the stage running next.
const NEXT_STAGE_LABELS: Record<string, string> = {
  thumbnail: 'reading metadata...',
  metadata: 'embedding...',
  embedding: 'extracting colors...',
  color: 'detecting objects...',
  object_detection: 'reading text...',
  ocr: 'captioning...',
  caption: 'finishing...',
};

// Only these stages change fields the list/stats queries show (status, thumbnail_url).
const STATUS_CHANGING_STAGES = new Set(['thumbnail', 'done', 'failed']);

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

  const lastMessage = ref<ProcessingImage | null>(null);
  const stages = reactive(new Map<string, string>());

  function handleMessage(message: ProcessingImage) {
    lastMessage.value = message;

    if (message.stage === 'done' || message.stage === 'failed') {
      stages.delete(message.image_id);
    } else {
      stages.set(message.image_id, NEXT_STAGE_LABELS[message.stage] ?? message.stage);
    }

    if (STATUS_CHANGING_STAGES.has(message.stage)) {
      queryClient.invalidateQueries({ queryKey: ['images'] });
    }
  }

  const { status } = useWebSocket<string>(url, {
    autoReconnect: true,
    // Events published while disconnected are lost, so resync on (re)connect.
    onConnected: () => queryClient.invalidateQueries({ queryKey: ['images'] }),
    onMessage: (_ws, event) => {
      const message = parseMessage(event.data);
      if (message) handleMessage(message);
    },
  });

  return { lastMessage, status, stages };
}

export const useImageProcessingSocket = createSharedComposable(useImageProcessingSocketImpl);
