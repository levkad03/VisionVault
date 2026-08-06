<script setup lang="ts">
import { deleteImage, listImages } from '@/api/images';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import type { Image } from '@/types/image';
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query';
import { computed, ref } from 'vue';

const limit = 24;
const offset = ref(0);
const queryClient = useQueryClient();
const selectedImage = ref<Image | null>(null);

const { data, isPending } = useQuery({
  queryKey: ['images', offset],
  queryFn: () => listImages(limit, offset.value),
  refetchInterval: (query) => {
    const items = query.state.data?.items ?? [];
    return items.some((i) => i.status === 'pending' || i.status === 'processing') ? 2000 : false;
  },
});

const hasNext = computed(() => (data.value ? offset.value + limit < data.value.total : false));

const deleteMutation = useMutation({
  mutationFn: deleteImage,
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ['images'] }),
});
</script>

<template>
  <div>
    <h1 class="text-xl font-bold">Gallery</h1>
    <p v-if="isPending">Loading...</p>
    <div v-else class="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
      <div v-for="image in data?.items" :key="image.id" class="relative">
        <img
          :src="image.thumbnail_url ?? image.url"
          :alt="image.filename"
          class="aspect-square w-full cursor-pointer rounded object-cover"
          @click="selectedImage = image"
        />
        <Badge v-if="image.status !== 'completed'" class="absolute top-2 left-2">
          {{ image.status }}
        </Badge>
        <Button
          size="sm"
          variant="destructive"
          class="absolute top-2 right-2"
          @click="deleteMutation.mutate(image.id)"
        >
          Delete
        </Button>
      </div>
    </div>
    <Dialog :open="!!selectedImage" @update:open="(v) => !v && (selectedImage = null)">
      <DialogContent class="max-w-3-xl border-none bg-transparent p-0 shadow-none">
        <DialogTitle class="sr-only">{{ selectedImage?.filename }}</DialogTitle>
        <img
          v-if="selectedImage"
          :src="selectedImage.url"
          :alt="selectedImage.filename"
          class="max-h-[85vh] w-full rounded object-contain"
        />
      </DialogContent>
    </Dialog>
    <div class="mt-4 flex gap-2">
      <Button variant="outline" :disabled="offset === 0" @click="offset -= limit">Prev</Button>
      <Button variant="outline" :disabled="!hasNext" @click="offset += limit">Next</Button>
    </div>
  </div>
</template>
