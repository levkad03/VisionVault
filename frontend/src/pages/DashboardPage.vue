<script setup lang="ts">
import { getImageStats } from '@/api/images';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuthStore } from '@/stores/auth';
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

    <div class="mt-4 grid grid-cols-2 gap-4 sm:max-w-md">
      <Card>
        <CardHeader>
          <CardTitle class="text-muted-foreground text-sm">Images</CardTitle>
        </CardHeader>
        <CardContent class="text-2xl font-bold">{{ data?.count ?? '–' }}</CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle class="text-muted-foreground text-sm">Storage used</CardTitle>
        </CardHeader>
        <CardContent class="text-2xl font-bold">
          {{ data ? formatBytes(data.storage_bytes) : '–' }}
        </CardContent>
      </Card>
    </div>
  </div>
</template>
