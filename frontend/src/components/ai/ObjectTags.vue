<script setup lang="ts">
import { Badge } from '@/components/ui/badge';
import type { DetectedObject } from '@/types/image';
import { computed } from 'vue';

const props = defineProps<{
  objects: DetectedObject[];
}>();

const sorted = computed(() => [...props.objects].sort((a, b) => b.confidence - a.confidence));
</script>

<template>
  <p v-if="sorted.length === 0" class="text-muted-foreground text-sm">No objects detected</p>
  <div v-else class="flex flex-wrap gap-2">
    <Badge v-for="obj in sorted" :key="obj.id" variant="secondary">
      {{ obj.class_name }} {{ Math.round(obj.confidence * 100) }}%
    </Badge>
  </div>
</template>
