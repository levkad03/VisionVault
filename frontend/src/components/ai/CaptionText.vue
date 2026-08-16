<script setup lang="ts">
import type { Caption } from '@/types/image';

defineProps<{
  caption: Caption | null;
}>();
</script>

<template>
  <p v-if="!caption" class="text-muted-foreground text-sm">No caption generated</p>
  <p v-else class="text-sm">{{ caption.text }}</p>
</template>
