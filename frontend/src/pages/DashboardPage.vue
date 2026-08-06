<script setup lang="ts">
import { getImageStats } from '@/api/images';
import UploadActivityChart from '@/components/dashboard/UploadActivityChart.vue';
import { Card, CardAction, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuthStore } from '@/stores/auth';
import { Activity, FileImage, HardDrive, Images } from '@lucide/vue';
import { useQuery } from '@tanstack/vue-query';

const auth = useAuthStore();

const { data } = useQuery({
  queryKey: ['images', 'stats'],
  queryFn: getImageStats,
});

function formatBytes(bytes: number) {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / 1024 ** i).toFixed(1)} ${units[i]}`;
}
</script>

<template>
  <div>
    <h1 class="text-xl font-bold">Dashboard</h1>
    <p class="text-muted-foreground">Logged in as {{ auth.user?.email }}</p>

    <div class="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
      <Card>
        <CardHeader>
          <CardTitle class="text-muted-foreground text-sm">Images</CardTitle>
          <CardAction>
            <Images class="text-muted-foreground size-4" />
          </CardAction>
        </CardHeader>
        <CardContent class="text-2xl font-bold">{{ data?.count ?? '–' }}</CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle class="text-muted-foreground text-sm">Storage used</CardTitle>
          <CardAction>
            <HardDrive class="text-muted-foreground size-4" />
          </CardAction>
        </CardHeader>
        <CardContent class="text-2xl font-bold">
          {{ data ? formatBytes(data.storage_bytes) : '–' }}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle class="text-muted-foreground text-sm">By status</CardTitle>
          <CardAction>
            <Activity class="text-muted-foreground size-4" />
          </CardAction>
        </CardHeader>
        <CardContent class="flex flex-wrap gap-1.5">
          <Badge v-for="(count, status) in data?.by_status" :key="status" variant="secondary">
            {{ status }}: {{ count }}
          </Badge>
          <span
            v-if="!data?.by_status || !Object.keys(data.by_status).length"
            class="text-muted-foreground text-sm"
            >–</span
          >
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle class="text-muted-foreground text-sm">By file type</CardTitle>
          <CardAction>
            <FileImage class="text-muted-foreground size-4" />
          </CardAction>
        </CardHeader>
        <CardContent class="flex flex-wrap gap-1.5">
          <Badge v-for="(count, mime) in data?.by_mime_type" :key="mime" variant="secondary">
            {{ mime.replace('image/', '') }}: {{ count }}
          </Badge>
          <span
            v-if="!data?.by_mime_type || !Object.keys(data.by_mime_type).length"
            class="text-muted-foreground text-sm"
            >–</span
          >
        </CardContent>
      </Card>
    </div>

    <Card class="mt-4">
      <CardHeader>
        <CardTitle class="text-muted-foreground text-sm">Upload activity (last 30 days)</CardTitle>
      </CardHeader>
      <CardContent>
        <UploadActivityChart v-if="data" :data="data.uploads_per_day" />
      </CardContent>
    </Card>
  </div>
</template>
