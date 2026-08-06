<script setup lang="ts">
import type { UploadsPerDay } from '@/types/image';
import { VisAxis, VisCrosshair, VisGroupedBar, VisTooltip, VisXYContainer } from '@unovis/vue';
import { computed } from 'vue';
import {
  ChartContainer,
  ChartTooltipContent,
  componentToString,
  type ChartConfig,
} from '../ui/chart';

const props = defineProps<{ data: UploadsPerDay[] }>();
const config: ChartConfig = { count: { label: 'Uploads', color: 'var(--primary)' } };

const x = (_: UploadsPerDay, i: number) => i;
const y = (d: UploadsPerDay) => d.count;
const labels = computed(() => props.data.map((d) => d.date.slice(5)));

const template = componentToString(config, ChartTooltipContent, {
  labelKey: 'count',
  nameKey: 'count',
});
</script>

<template>
  <ChartContainer :config="config" class="h-80 w-full">
    <VisXYContainer :data="data">
      <VisGroupedBar :x="x" :y="[y]" color="var(--color-count)" :rounded-corners="2" />
      <VisAxis type="x" :tick-format="(i: number) => labels[i] ?? ''" :grid-line="false" />
      <VisCrosshair color="var(--color-count)" :template="template" />
      <VisTooltip :horizontal-placement="'center'" />
    </VisXYContainer>
  </ChartContainer>
</template>
