import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  register: vi.fn(),
  refreshTokenRequest: vi.fn(),
  fetchMe: vi.fn(),
}));

const authApi = await import('@/api/auth');
const { useAuthStore } = await import('@/stores/auth');

const tokens = { access_token: 'access-1', refresh_token: 'refresh-1', token_type: 'Bearer' };
const user = {
  id: 'u1',
  email: 'a@b.com',
  is_active: true,
  is_superuser: false,
  is_verified: true,
};

beforeEach(() => {
  localStorage.clear();
  setActivePinia(createPinia());
  vi.clearAllMocks();
});

describe('initial state', () => {
  it('starts unauthenticated with no tokens in localStorage', () => {
    const store = useAuthStore();
    expect(store.accessToken).toBeNull();
    expect(store.refreshToken).toBeNull();
    expect(store.isAuthenticated).toBe(false);
  });

  it('hydrates tokens from localStorage on creation', () => {
    localStorage.setItem('access_token', 'existing-access');
    localStorage.setItem('refresh_token', 'existing-refresh');

    const store = useAuthStore();
    expect(store.accessToken).toBe('existing-access');
    expect(store.refreshToken).toBe('existing-refresh');
    expect(store.isAuthenticated).toBe(true);
  });
});

describe('login', () => {
  it('sets tokens, persists to localStorage, and loads current user', async () => {
    vi.mocked(authApi.login).mockResolvedValue(tokens);
    vi.mocked(authApi.fetchMe).mockResolvedValue(user);

    const store = useAuthStore();
    await store.login('a@b.com', 'pw123456');

    expect(authApi.login).toHaveBeenCalledWith('a@b.com', 'pw123456');
    expect(store.accessToken).toBe('access-1');
    expect(store.refreshToken).toBe('refresh-1');
    expect(store.user).toEqual(user);
    expect(store.isAuthenticated).toBe(true);
    expect(localStorage.getItem('access_token')).toBe('access-1');
    expect(localStorage.getItem('refresh_token')).toBe('refresh-1');
  });

  it('propagates failure and leaves state untouched', async () => {
    vi.mocked(authApi.login).mockRejectedValue(new Error('bad credentials'));

    const store = useAuthStore();
    await expect(store.login('a@b.com', 'wrong')).rejects.toThrow('bad credentials');

    expect(store.accessToken).toBeNull();
    expect(store.user).toBeNull();
    expect(authApi.fetchMe).not.toHaveBeenCalled();
  });
});

describe('register', () => {
  it('registers then logs in', async () => {
    vi.mocked(authApi.register).mockResolvedValue(user);
    vi.mocked(authApi.login).mockResolvedValue(tokens);
    vi.mocked(authApi.fetchMe).mockResolvedValue(user);

    const store = useAuthStore();
    await store.register('a@b.com', 'pw123456');

    expect(authApi.register).toHaveBeenCalledWith('a@b.com', 'pw123456');
    expect(authApi.login).toHaveBeenCalledWith('a@b.com', 'pw123456');
    expect(store.user).toEqual(user);
    expect(store.isAuthenticated).toBe(true);
  });

  it('does not attempt login when registration fails', async () => {
    vi.mocked(authApi.register).mockRejectedValue(new Error('email taken'));

    const store = useAuthStore();
    await expect(store.register('a@b.com', 'pw123456')).rejects.toThrow('email taken');

    expect(authApi.login).not.toHaveBeenCalled();
  });
});

describe('refreshTokens', () => {
  it('throws when there is no refresh token', async () => {
    const store = useAuthStore();
    await expect(store.refreshTokens()).rejects.toThrow('No refresh token');
    expect(authApi.refreshTokenRequest).not.toHaveBeenCalled();
  });

  it('requests new tokens and persists them', async () => {
    localStorage.setItem('access_token', 'old-access');
    localStorage.setItem('refresh_token', 'old-refresh');
    vi.mocked(authApi.refreshTokenRequest).mockResolvedValue(tokens);

    const store = useAuthStore();
    await store.refreshTokens();

    expect(authApi.refreshTokenRequest).toHaveBeenCalledWith('old-refresh');
    expect(store.accessToken).toBe('access-1');
    expect(store.refreshToken).toBe('refresh-1');
    expect(localStorage.getItem('access_token')).toBe('access-1');
  });
});

describe('hydrate', () => {
  it('does nothing when there is no access token', async () => {
    const store = useAuthStore();
    await store.hydrate();

    expect(authApi.fetchMe).not.toHaveBeenCalled();
    expect(store.user).toBeNull();
  });

  it('loads the current user when an access token exists', async () => {
    localStorage.setItem('access_token', 'existing-access');
    vi.mocked(authApi.fetchMe).mockResolvedValue(user);

    const store = useAuthStore();
    await store.hydrate();

    expect(store.user).toEqual(user);
  });

  it('sets user to null instead of throwing when fetchMe fails', async () => {
    localStorage.setItem('access_token', 'stale-access');
    vi.mocked(authApi.fetchMe).mockRejectedValue(new Error('401'));

    const store = useAuthStore();
    await expect(store.hydrate()).resolves.toBeUndefined();
    expect(store.user).toBeNull();
  });
});

describe('logout', () => {
  it('clears tokens, user, and localStorage', async () => {
    vi.mocked(authApi.login).mockResolvedValue(tokens);
    vi.mocked(authApi.fetchMe).mockResolvedValue(user);

    const store = useAuthStore();
    await store.login('a@b.com', 'pw123456');
    store.logout();

    expect(store.accessToken).toBeNull();
    expect(store.refreshToken).toBeNull();
    expect(store.user).toBeNull();
    expect(store.isAuthenticated).toBe(false);
    expect(localStorage.getItem('access_token')).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
  });
});
