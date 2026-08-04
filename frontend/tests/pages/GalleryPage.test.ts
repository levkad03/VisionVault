import GalleryPage from '@/pages/GalleryPage.vue';
import type { Image, ImageList } from '@/types/image';
import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query';
import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/api/images', () => ({
  listImages: vi.fn(),
  deleteImage: vi.fn(),
}));

const imagesApi = await import('@/api/images');

function makeImage(overrides: Partial<Image> = {}): Image {
  return {
    id: 'img-1',
    filename: 'a.jpg',
    mime_type: 'image/jpeg',
    width: 100,
    height: 100,
    uploaded_at: '2026-01-01T00:00:00Z',
    taken_at: null,
    camera: null,
    lens: null,
    gps: null,
    status: 'completed',
    url: '/full/a.jpg',
    thumbnail_url: '/thumb/a.jpg',
    ...overrides,
  };
}

function makeList(items: Image[], total: number): ImageList {
  return { items, total, limit: 24, offset: 0 };
}

function mountPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  const wrapper = mount(GalleryPage, {
    global: { plugins: [[VueQueryPlugin, { queryClient }]] },
  });

  return { wrapper, queryClient };
}

beforeEach(() => {
  vi.mocked(imagesApi.listImages).mockReset();
  vi.mocked(imagesApi.deleteImage).mockReset();
});

describe('GalleryPage', () => {
  it('shows a loading state before data arrives', () => {
    vi.mocked(imagesApi.listImages).mockReturnValue(new Promise(() => {}));
    const wrapper = mountPage().wrapper;
    expect(wrapper.text()).toContain('Loading...');
  });

  it('renders images with their thumbnail, alt text, and no badge when completed', async () => {
    vi.mocked(imagesApi.listImages).mockResolvedValue(
      makeList([makeImage({ status: 'completed' })], 1),
    );
    const { wrapper } = mountPage();
    await flushPromises();

    const img = wrapper.find('img');
    expect(img.attributes('src')).toBe('/thumb/a.jpg');
    expect(img.attributes('alt')).toBe('a.jpg');
    expect(wrapper.findComponent({ name: 'Badge' }).exists()).toBe(false);
  });

  it('falls back to the full url when there is no thumbnail', async () => {
    vi.mocked(imagesApi.listImages).mockResolvedValue(
      makeList([makeImage({ thumbnail_url: null })], 1),
    );
    const { wrapper } = mountPage();
    await flushPromises();

    expect(wrapper.find('img').attributes('src')).toBe('/full/a.jpg');
  });

  it('shows a status badge for non-completed images', async () => {
    vi.mocked(imagesApi.listImages).mockResolvedValue(
      makeList([makeImage({ status: 'processing' })], 1),
    );
    const { wrapper } = mountPage();
    await flushPromises();

    expect(wrapper.text()).toContain('processing');
  });

  it('deletes an image and invalidates the images query', async () => {
    vi.mocked(imagesApi.listImages).mockResolvedValue(makeList([makeImage({ id: 'img-1' })], 1));
    vi.mocked(imagesApi.deleteImage).mockResolvedValue(undefined);
    const { wrapper, queryClient } = mountPage();
    await flushPromises();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    await wrapper.find('button').trigger('click');
    await flushPromises();

    expect(vi.mocked(imagesApi.deleteImage).mock.calls[0][0]).toBe('img-1');
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['images'] });
  });

  it('disables Prev on the first page and enables Next when more pages exist', async () => {
    vi.mocked(imagesApi.listImages).mockResolvedValue(makeList([makeImage()], 30));
    const { wrapper } = mountPage();
    await flushPromises();

    const buttons = wrapper.findAll('button').filter((b) => ['Prev', 'Next'].includes(b.text()));
    const prev = buttons.find((b) => b.text() === 'Prev')!;
    const next = buttons.find((b) => b.text() === 'Next')!;

    expect(prev.attributes('disabled')).toBeDefined();
    expect(next.attributes('disabled')).toBeUndefined();
  });

  it('disables Next on the last page', async () => {
    vi.mocked(imagesApi.listImages).mockResolvedValue(makeList([makeImage()], 10));
    const { wrapper } = mountPage();
    await flushPromises();

    const next = wrapper.findAll('button').find((b) => b.text() === 'Next')!;
    expect(next.attributes('disabled')).toBeDefined();
  });

  it('advances the offset and refetches when Next is clicked', async () => {
    vi.mocked(imagesApi.listImages).mockResolvedValue(makeList([makeImage()], 30));
    const { wrapper } = mountPage();
    await flushPromises();

    const next = wrapper.findAll('button').find((b) => b.text() === 'Next')!;
    await next.trigger('click');
    await flushPromises();

    expect(imagesApi.listImages).toHaveBeenLastCalledWith(24, 24);
  });

  it('moves back to the previous offset when Prev is clicked', async () => {
    vi.mocked(imagesApi.listImages).mockResolvedValue(makeList([makeImage()], 30));
    const { wrapper } = mountPage();
    await flushPromises();

    const next = wrapper.findAll('button').find((b) => b.text() === 'Next')!;
    await next.trigger('click');
    await flushPromises();
    const prev = wrapper.findAll('button').find((b) => b.text() === 'Prev')!;
    await prev.trigger('click');
    await flushPromises();

    expect(imagesApi.listImages).toHaveBeenLastCalledWith(24, 0);
  });
});
