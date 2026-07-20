import { apiFetch } from '@/api/client';
import type { SearchResponse } from '@/types/search';

export function searchImages(query: string, limit: number, offset: number) {
  return apiFetch<SearchResponse>('/search', {
    method: 'POST',
    body: JSON.stringify({ query, limit, offset }),
  });
}
