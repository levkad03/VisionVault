<script setup lang="ts">
import { uploadImage } from '@/api/images';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useMutation, useQueryClient } from '@tanstack/vue-query';
import { ref } from 'vue';

const files = ref<FileList | null>(null);
const uploadProgress = ref<{ current: number; total: number } | null>(null);
const queryClient = useQueryClient();

const uploadMutation = useMutation({
  mutationFn: uploadImage,
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ['images'] }),
});

async function onSubmit() {
  if (!files.value) return;
  const list = Array.from(files.value);
  uploadProgress.value = { current: 0, total: list.length };
  try {
    for (const file of Array.from(files.value)) {
      await uploadMutation.mutateAsync(file);
      uploadProgress.value = { current: uploadProgress.value.current + 1, total: list.length };
    }
  } catch {
    return;
  } finally {
    uploadProgress.value = null;
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
        :disabled="uploadMutation.isPending.value"
        @change="files = ($event.target as HTMLInputElement).files"
      />
      <p v-if="uploadMutation.isError.value" class="text-destructive text-sm">Upload failed</p>
      <p v-if="uploadProgress" class="text-muted-foreground text-sm">
        Uploading {{ uploadProgress.current + 1 }} of {{ uploadProgress.total }}…
      </p>
      <Button type="submit" :disabled="!files || uploadMutation.isPending.value">
        <Loader2 v-if="uploadMutation.isPending.value" class="size-4 animate-spin" />
        {{ uploadMutation.isPending.value ? 'Uploading…' : 'Upload' }}
      </Button>
    </form>
  </div>
</template>
