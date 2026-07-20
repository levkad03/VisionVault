<script setup lang="ts">
import { searchImages } from '@/api/search';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useQuery } from '@tanstack/vue-query';
import { ref } from 'vue';

const limit = 24;
const query = ref('');
const submittedQuery = ref('');
const offset = ref(0);

const { data, isPending, isFetching } = useQuery({
  queryKey: ['search', submittedQuery, offset],
  queryFn: () => searchImages(submittedQuery.value, limit, offset.value),
  enabled: () => submittedQuery.value.length > 0,
});

function onSubmit() {
  submittedQuery.value = query.value;
  offset.value = 0;
}
</script>

<template>
  <div>
    <h1 class="text-xl font-bold">Search</h1>

    <form class="mt-4 flex gap-2" @submit.prevent="onSubmit">
      <Input v-model="query" placeholder="a dog on a beach..." />
      <Button type="submit" :disabled="!query">Search</Button>
    </form>

    <p v-if="isPending && submittedQuery">Searching...</p>
    <p v-else-if="submittedQuery && !isFetching && data?.items.length === 0">No results.</p>

    <div class="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
      <div v-for="image in data?.items" :key="image.id" class="relative">
        <img
          :src="image.thumbnail_url ?? image.url"
          :alt="image.filename"
          class="aspect-square w-full rounded object-cover"
        />
        <span
          class="absolute right-2 bottom-2 rounded bg-black/70 px-1.5 py-0.5 text-xs text-white"
        >
          {{ image.score.toFixed(2) }}
        </span>
      </div>
    </div>

    <div v-if="data?.items.length" class="mt-4 flex gap-2">
      <Button variant="outline" :disabled="offset === 0" @click="offset -= limit">Prev</Button>
      <Button variant="outline" :disabled="data.items.length < limit" @click="offset += limit">
        Next
      </Button>
    </div>
  </div>
</template>
