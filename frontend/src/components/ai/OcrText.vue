<script setup lang="ts">
import { Badge } from '@/components/ui/badge';
import type { OCRResult } from '@/types/image';

defineProps<{
  results: OCRResult[];
}>();
</script>

<template>
  <p v-if="results.length === 0" class="text-muted-foreground text-sm">No text detected</p>
  <ul v-else class="space-y-2">
    <li
      v-for="result in results"
      :key="result.id"
      class="flex items-start justify-between gap-2 text-sm"
    >
      <span>{{ result.text }}</span>
      <Badge variant="outline">{{ Math.round(result.confidence * 100) }}%</Badge>
    </li>
  </ul>
</template>
