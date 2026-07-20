<script setup lang="ts">
import { uploadImage } from '@/api/images';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useMutation, useQueryClient } from '@tanstack/vue-query';
import { ref } from 'vue';

const files = ref<FileList | null>(null);
const queryClient = useQueryClient();

const uploadMutation = useMutation({
  mutationFn: uploadImage,
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ['images'] }),
});

async function onSubmit() {
  if (!files.value) return;
  for (const file of Array.from(files.value)) {
    await uploadMutation.mutateAsync(file);
  }
  files.value = null;
}
</script>

<template>
  <div class="mx-auto max-w-sm">
    <h1 class="text-xl font-bold">Upload</h1>
    <form class="mt-4 flex flex-col gap-4" @submit.prevent="onSubmit">
      <Input
        type="file"
        accept="image/*"
        multiple
        @change="files = ($event.target as HTMLInputElement).files"
      />
      <p v-if="uploadMutation.isError.value" class="text-destructive text-sm">Upload failed</p>
      <Button type="submit" :disabled="!files || uploadMutation.isPending.value">Upload</Button>
    </form>
  </div>
</template>
