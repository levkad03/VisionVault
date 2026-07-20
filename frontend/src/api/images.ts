import { apiFetch } from '@/api/client';
import type { Image, ImageList, ImageStats } from '@/types/image';

export function listImages(limit: number, offset: number) {
  return apiFetch<ImageList>(`/images?limit=${limit}&offset=${offset}`);
}

export function uploadImage(file: File) {
  const body = new FormData();
  body.append('file', file);
  return apiFetch<Image>('/images', { method: 'POST', body });
}

export function deleteImage(id: string) {
  return apiFetch<void>(`/images/${id}`, { method: 'DELETE' });
}

export function getImageStats() {
  return apiFetch<ImageStats>('/images/stats');
}
