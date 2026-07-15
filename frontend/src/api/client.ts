import { useAuthStore } from '@/stores/auth';

const BASE_URL = import.meta.env.VITE_API_BASE_URL;

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new ApiError(response.status, detail?.detail ?? response.statusText);
  }

  if (response.status === 204) return undefined as T;

  return response.json();
}

let refreshPromise: Promise<void> | null = null;

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
  _retry = false,
): Promise<T> {
  const auth = useAuthStore();
  const headers = new Headers(init.headers);

  if (auth.accessToken) headers.set('Authorization', `Bearer ${auth.accessToken}`);
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');

  const response = await fetch(`${BASE_URL}${path}`, { ...init, headers });

  if (response.status === 401 && !_retry && auth.refreshToken) {
    refreshPromise ??= auth.refreshTokens().finally(() => {
      refreshPromise = null;
    });

    try {
      await refreshPromise;
    } catch {
      auth.logout();
      throw new ApiError(401, 'Session expired');
    }
    return apiFetch<T>(path, init, true);
  }

  return parseResponse<T>(response);
}
