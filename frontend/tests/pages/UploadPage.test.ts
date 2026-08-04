import type { Image } from '@/types/image';
import UploadPage from '@/pages/UploadPage.vue';
import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query';
import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';

vi.mock('@/api/images', () => ({
  uploadImage: vi.fn(),
}));

const imagesApi = await import('@/api/images');

const fakeImage: Image = {
  id: 'img-1',
  filename: 'a.jpg',
  mime_type: 'image/jpeg',
  width: null,
  height: null,
  uploaded_at: '2026-01-01T00:00:00Z',
  taken_at: null,
  camera: null,
  lens: null,
  gps: null,
  status: 'pending',
  url: '/img-1',
  thumbnail_url: null,
};

function mountPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  const wrapper = mount(UploadPage, {
    global: { plugins: [[VueQueryPlugin, { queryClient }]] },
  });
  return { wrapper, queryClient };
}

function selectFiles(wrapper: ReturnType<typeof mount>, files: File[]) {
  const input = wrapper.find('input[type="file"]').element as HTMLInputElement;
  Object.defineProperty(input, 'files', { value: files, configurable: true });
  return wrapper.find('input[type="file"]').trigger('change');
}

beforeEach(() => {
  vi.mocked(imagesApi.uploadImage).mockReset();
});

describe('UploadPage', () => {
  it('does nothing on submit  when no files are selected', async () => {
    const { wrapper } = mountPage();
    await wrapper.find('form').trigger('submit');
    await flushPromises();
    expect(imagesApi.uploadImage).not.toHaveBeenCalled();
  });

  it('uploads each selected file sequentially', async () => {
    vi.mocked(imagesApi.uploadImage).mockResolvedValue(fakeImage);
    const { wrapper } = mountPage();
    const fileA = new File(['a'], 'a.jpg', { type: 'image/jpeg' });
    const fileB = new File(['b'], 'b.jpg', { type: 'image/jpeg' });

    await selectFiles(wrapper, [fileA, fileB]);
    await wrapper.find('form').trigger('submit');
    await flushPromises();

    expect(imagesApi.uploadImage).toHaveBeenCalledTimes(2);
    expect(vi.mocked(imagesApi.uploadImage).mock.calls[0][0]).toBe(fileA);
    expect(vi.mocked(imagesApi.uploadImage).mock.calls[1][0]).toBe(fileB);
  });

  it('invalidates the images query after a successful upload', async () => {
    vi.mocked(imagesApi.uploadImage).mockResolvedValue(fakeImage);
    const { wrapper, queryClient } = mountPage();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    await selectFiles(wrapper, [new File(['a'], 'a.jpg', { type: 'image/jpeg' })]);
    await wrapper.find('form').trigger('submit');
    await flushPromises();

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['images'] });
  });

  it('shows an error message when the upload fails', async () => {
    vi.mocked(imagesApi.uploadImage).mockRejectedValue(new Error('network error'));
    const { wrapper } = mountPage();

    await selectFiles(wrapper, [new File(['a'], 'a.jpg', { type: 'image/jpeg' })]);
    await wrapper.find('form').trigger('submit');
    await flushPromises();

    expect(wrapper.text()).toContain('Upload failed');
  });

  it('disables the submit button while uploading, then clears files and re-enables once new files are selected', async () => {
    let resolveUpload!: (v: Image) => void;
    vi.mocked(imagesApi.uploadImage).mockReturnValue(
      new Promise<Image>((resolve) => (resolveUpload = resolve)),
    );
    const { wrapper } = mountPage();

    await selectFiles(wrapper, [new File(['a'], 'a.jpg', { type: 'image/jpeg' })]);
    await wrapper.find('form').trigger('submit');
    await wrapper.vm.$nextTick();

    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined();

    resolveUpload(fakeImage);
    await flushPromises();
    await nextTick();

    // files.value is reset to null after a successful upload, so the button
    // stays disabled (no files selected), not because isPending is still true.
    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined();

    await selectFiles(wrapper, [new File(['b'], 'b.jpg', { type: 'image/jpeg' })]);

    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeUndefined();
  });

  it('disables the submit button when no files are selected', async () => {
    const { wrapper } = mountPage();
    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined();
  });
});
