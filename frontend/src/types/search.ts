import type { Image } from '@/types/image';

export interface SearchResultItem extends Image {
  score: number;
}

export interface SearchResponse {
  items: SearchResultItem[];
  limit: number;
  offset: number;
}
