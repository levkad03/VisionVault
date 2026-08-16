<script setup lang="ts">
import { getImageDetail } from '@/api/images';
import CaptionText from '@/components/ai/CaptionText.vue';
import ColorPalette from '@/components/ai/ColorPalette.vue';
import ObjectTags from '@/components/ai/ObjectTags.vue';
import OcrText from '@/components/ai/OcrText.vue';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useImageProcessingSocket } from '@/composables/useImageProcessingSocket';
import { useQuery } from '@tanstack/vue-query';
import { computed, watch } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();
const id = computed(() => route.params.id as string);

const { data, isPending, refetch } = useQuery({
  queryKey: ['image', id],
  queryFn: () => getImageDetail(id.value),
  refetchInterval: (query) => {
    const status = query.state.data?.status;
    return status === 'pending' || status === 'processing' ? 2000 : false;
  },
});
const { lastMessage } = useImageProcessingSocket();

watch(lastMessage, (message) => {
  if (message?.image_id === id.value) refetch();
});
</script>

<template>
  <div>
    <RouterLink to="/gallery" class="text-sm">&larr; Back to gallery</RouterLink>

    <p v-if="isPending">Loading...</p>
    <div v-else-if="data" class="mt-4 grid gap-4 md:grid-cols-2">
      <img
        :src="data.url"
        :alt="data.filename"
        class="w-full rounded object-contain md:col-span-2"
      />
      <Card>
        <CardHeader>
          <CardTitle>Detaild</CardTitle>
        </CardHeader>
        <CardContent class="space-y-1 text-sm">
          <p>Status: {{ data.status }}</p>
          <p>Taken: {{ data.taken_at ?? 'Unknown' }}</p>
          <p>Camera: {{ data.camera ?? 'Unknown' }}</p>
          <p>Lens: {{ data.lens ?? 'Unknown' }}</p>
          <p>GPS: {{ data.gps ?? 'Unknown' }}</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Caption</CardTitle>
        </CardHeader>
        <CardContent>
          <CaptionText :caption="data.caption" />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Objects</CardTitle>
        </CardHeader>
        <CardContent>
          <ObjectTags :objects="data.objects" />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Text (OCR)</CardTitle>
        </CardHeader>
        <CardContent>
          <OcrText :results="data.ocr" />
        </CardContent>
      </Card>

      <Card class="md:col-span-2">
        <CardHeader>
          <CardTitle>Colors</CardTitle>
        </CardHeader>
        <CardContent>
          <ColorPalette :colors="data.dominant_colors" />
        </CardContent>
      </Card>
    </div>
  </div>
</template>
