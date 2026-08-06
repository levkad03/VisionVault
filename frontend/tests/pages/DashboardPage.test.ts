import DashboardPage from '@/pages/DashboardPage.vue';
import type { ImageStats } from '@/types/image';
import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query';
import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const authMock = {
  user: { id: 'u1', email: 'a@b.com' } as { id: string; email: string } | null,
};

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => authMock,
}));

vi.mock('@/api/images', () => ({
  getImageStats: vi.fn(),
}));

const imagesApi = await import('@/api/images');

function mountPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });

  return mount(DashboardPage, {
    global: { plugins: [[VueQueryPlugin, { queryClient }]] },
  });
}

beforeEach(() => {
  authMock.user = { id: 'u1', email: 'a@b.com' };
  vi.mocked(imagesApi.getImageStats).mockReset();
});

describe('DashboardPage', () => {
  it('renders the logged-in user email', async () => {
    vi.mocked(imagesApi.getImageStats).mockResolvedValue({
      count: 0,
      storage_bytes: 0,
      by_status: {},
      by_mime_type: {},
      uploads_per_day: [],
    } as ImageStats);
    const wrapper = mountPage();
    expect(wrapper.text()).toContain('a@b.com');
  });

  it('shows a placeholder for count and storage while the query is loading', () => {
    vi.mocked(imagesApi.getImageStats).mockReturnValue(new Promise(() => {}));
    const wrapper = mountPage();
    const values = wrapper.findAll('.text-2xl');
    expect(values[0].text()).toBe('–');
    expect(values[1].text()).toBe('–');
  });

  it('renders the image count once loaded', async () => {
    vi.mocked(imagesApi.getImageStats).mockResolvedValue({
      count: 7,
      storage_bytes: 0,
      by_status: {},
      by_mime_type: {},
      uploads_per_day: [],
    } as ImageStats);
    const wrapper = mountPage();
    await flushPromises();
    expect(wrapper.findAll('.text-2xl')[0].text()).toBe('7');
  });

  it.each([
    [0, '0 B'],
    [512, '512.0 B'],
    [1536, '1.5 KB'],
    [3 * 1024 ** 2, '3.0 MB'],
    [2 * 1024 ** 3, '2.0 GB'],
  ] as [number, string][])('formats %i storage_bytes as %s', async (storage_bytes, expected) => {
    vi.mocked(imagesApi.getImageStats).mockResolvedValue({ count: 1, storage_bytes } as ImageStats);
    const wrapper = mountPage();
    await flushPromises();
    expect(wrapper.findAll('.text-2xl')[1].text()).toBe(expected);
  });
});
