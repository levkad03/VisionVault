import { beforeEach, describe, expect, it, vi } from 'vitest';

const authMock = {
  isAuthenticated: false,
  hydrate: vi.fn(),
};

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => authMock,
}));

async function freshRouter() {
  vi.resetModules();
  const { default: router } = await import('@/router');
  return router;
}

beforeEach(() => {
  authMock.isAuthenticated = false;
  authMock.hydrate = vi.fn().mockResolvedValue(undefined);
});

describe('router guard', () => {
  it('redirects unauthenticated users off a protected route, preserving the target', async () => {
    authMock.isAuthenticated = false;
    const router = await freshRouter();

    await router.push('/gallery');
    expect(router.currentRoute.value.name).toBe('login');
    expect(router.currentRoute.value.query.redirect).toBe('/gallery');
  });

  it('lets an authenticated user through to a protected route', async () => {
    authMock.isAuthenticated = true;
    const router = await freshRouter();

    await router.push('/gallery');

    expect(router.currentRoute.value.name).toBe('gallery');
  });

  it('redirects an authenticated user off a public route to the dashboard', async () => {
    authMock.isAuthenticated = true;
    const router = await freshRouter();

    await router.push('/login');

    expect(router.currentRoute.value.name).toBe('dashboard');
  });

  it('lets an unauthenticated user stay on a public route', async () => {
    authMock.isAuthenticated = false;
    const router = await freshRouter();

    await router.push('/register');

    expect(router.currentRoute.value.name).toBe('register');
  });

  it('calls hydrate exactly once across multiple navigations', async () => {
    authMock.isAuthenticated = true;
    const router = await freshRouter();

    await router.push('/gallery');
    await router.push('/upload');
    await router.push('/search');

    expect(authMock.hydrate).toHaveBeenCalledTimes(1);
  });
});
