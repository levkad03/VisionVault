<script setup lang="ts">
defineProps<{
  colors: string[] | null;
}>();
</script>

<template>
  <p v-if="!colors || colors.length === 0" class="text-muted-foreground text-sm">
    No colors extracted
  </p>
  <div v-else class="flex flex-wrap gap-3">
    <div v-for="color in colors" :key="color" class="flex flex-col items-center gap-1">
      <div class="size-8 rounded border" :style="{ backgroundColor: color }" />
      <span class="text-muted-foreground text-xs">{{ color }}</span>
    </div>
  </div>
</template>
