import SearchPage from '@/pages/SearchPage.vue';
import type { SearchResponse, SearchResultItem } from '@/types/search';
import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query';
import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/api/search', () => ({
  searchImages: vi.fn(),
}));

const searchApi = await import('@/api/search');

function makeItem(overrides: Partial<SearchResultItem> = {}): SearchResultItem {
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
    score: 0.8734,
    ...overrides,
  };
}

function makeResponse(items: SearchResultItem[]): SearchResponse {
  return { items, limit: 24, offset: 0 };
}

function mountPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  const wrapper = mount(SearchPage, {
    global: { plugins: [[VueQueryPlugin, { queryClient }]] },
  });

  return wrapper;
}

async function submitQuery(wrapper: ReturnType<typeof mountPage>, text: string) {
  await wrapper.find('input').setValue(text);
  await wrapper.find('form').trigger('submit');
}

beforeEach(() => {
  vi.mocked(searchApi.searchImages).mockReset();
});

describe('SearchPage', () => {
  it('disables the Search button until text is entered', async () => {
    const wrapper = mountPage();
    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined();

    await wrapper.find('input').setValue('a dog');
    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeUndefined();
  });

  it('does not search on mount', () => {
    mountPage();
    expect(searchApi.searchImages).not.toHaveBeenCalled();
  });

  it('searches with the submitted query and resets the offset', async () => {
    vi.mocked(searchApi.searchImages).mockResolvedValue(makeResponse([]));
    const wrapper = mountPage();

    await submitQuery(wrapper, 'a dog on a beach');
    await flushPromises();

    expect(searchApi.searchImages).toHaveBeenCalledWith('a dog on a beach', 24, 0);
  });

  it('shows a searching indicator while the query is in flight', async () => {
    vi.mocked(searchApi.searchImages).mockReturnValue(new Promise(() => {}));
    const wrapper = mountPage();

    await submitQuery(wrapper, 'a dog');

    expect(wrapper.text()).toContain('Searching...');
  });

  it('shows "No results." when the search returns nothing', async () => {
    vi.mocked(searchApi.searchImages).mockResolvedValue(makeResponse([]));
    const wrapper = mountPage();

    await submitQuery(wrapper, 'a dog');
    await flushPromises();

    expect(wrapper.text()).toContain('No results.');
  });

  it('renders result thumbnails, alt text, and score', async () => {
    vi.mocked(searchApi.searchImages).mockResolvedValue(
      makeResponse([makeItem({ score: 0.8734 })]),
    );
    const wrapper = mountPage();

    await submitQuery(wrapper, 'a dog');
    await flushPromises();

    const img = wrapper.find('img');
    expect(img.attributes('src')).toBe('/thumb/a.jpg');
    expect(img.attributes('alt')).toBe('a.jpg');
    expect(wrapper.text()).toContain('0.87');
  });

  it('falls back to the full url when there is no thumbnail', async () => {
    vi.mocked(searchApi.searchImages).mockResolvedValue(
      makeResponse([makeItem({ thumbnail_url: null })]),
    );
    const wrapper = mountPage();

    await submitQuery(wrapper, 'a dog');
    await flushPromises();

    expect(wrapper.find('img').attributes('src')).toBe('/full/a.jpg');
  });

  it('hides pagination controls when there are no results', async () => {
    vi.mocked(searchApi.searchImages).mockResolvedValue(makeResponse([]));
    const wrapper = mountPage();

    await submitQuery(wrapper, 'a dog');
    await flushPromises();

    expect(wrapper.findAll('button').some((b) => b.text() === 'Prev')).toBe(false);
  });

  it('disables Prev on the first page and Next on a partial (last) page', async () => {
    vi.mocked(searchApi.searchImages).mockResolvedValue(makeResponse([makeItem()]));
    const wrapper = mountPage();

    await submitQuery(wrapper, 'a dog');
    await flushPromises();

    const prev = wrapper.findAll('button').find((b) => b.text() === 'Prev')!;
    const next = wrapper.findAll('button').find((b) => b.text() === 'Next')!;
    expect(prev.attributes('disabled')).toBeDefined();
    expect(next.attributes('disabled')).toBeDefined();
  });

  it('enables Next on a full page and advances the offset on click', async () => {
    const fullPage = Array.from({ length: 24 }, (_, i) => makeItem({ id: `img-${i}` }));
    vi.mocked(searchApi.searchImages).mockResolvedValue(makeResponse(fullPage));
    const wrapper = mountPage();

    await submitQuery(wrapper, 'a dog');
    await flushPromises();

    const next = wrapper.findAll('button').find((b) => b.text() === 'Next')!;
    expect(next.attributes('disabled')).toBeUndefined();

    await next.trigger('click');
    await flushPromises();

    expect(vi.mocked(searchApi.searchImages)).toHaveBeenLastCalledWith('a dog', 24, 24);
  });

  it('moves back to the previous offset when Prev is clicked', async () => {
    const fullPage = Array.from({ length: 24 }, (_, i) => makeItem({ id: `img-${i}` }));
    vi.mocked(searchApi.searchImages).mockResolvedValue(makeResponse(fullPage));
    const wrapper = mountPage();

    await submitQuery(wrapper, 'a dog');
    await flushPromises();

    const next = wrapper.findAll('button').find((b) => b.text() === 'Next')!;
    await next.trigger('click');
    await flushPromises();
    const prev = wrapper.findAll('button').find((b) => b.text() === 'Prev')!;
    await prev.trigger('click');
    await flushPromises();

    expect(vi.mocked(searchApi.searchImages)).toHaveBeenLastCalledWith('a dog', 24, 0);
  });

  it('resets the offset to 0 on a new search after paginating', async () => {
    const fullPage = Array.from({ length: 24 }, (_, i) => makeItem({ id: `img-${i}` }));
    vi.mocked(searchApi.searchImages).mockResolvedValue(makeResponse(fullPage));
    const wrapper = mountPage();

    await submitQuery(wrapper, 'a dog');
    await flushPromises();
    const next = wrapper.findAll('button').find((b) => b.text() === 'Next')!;
    await next.trigger('click');
    await flushPromises();

    await submitQuery(wrapper, 'a cat');
    await flushPromises();

    expect(vi.mocked(searchApi.searchImages)).toHaveBeenLastCalledWith('a cat', 24, 0);
  });
});
