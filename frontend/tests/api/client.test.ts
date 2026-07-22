import { beforeEach, describe, expect, it, vi } from 'vitest';

const authState = {
  accessToken: null as string | null,
  refreshToken: null as string | null,
  refreshTokens: vi.fn(),
  logout: vi.fn(),
};

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => authState,
}));

const { apiFetch, parseResponse, ApiError } = await import('@/api/client');

function fakeResponse(status: number, body: unknown = null, statusText = 'Error') {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText,
    json: vi.fn(async () => {
      if (body === null) throw new Error('invalid json');
      return body;
    }),
  } as unknown as Response;
}

function queueFetch(...responses: Response[]) {
  const fetchMock = vi.fn();
  responses.forEach((r) => fetchMock.mockImplementationOnce(() => Promise.resolve(r)));
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

beforeEach(() => {
  authState.accessToken = null;
  authState.refreshToken = null;
  authState.refreshTokens = vi.fn().mockResolvedValue(undefined);
  authState.logout = vi.fn();
  vi.unstubAllGlobals();
});

describe('parseResponse', () => {
  it('returns parsed json on ok response', async () => {
    const result = await parseResponse(fakeResponse(200, { id: 1 }));
    expect(result).toEqual({ id: 1 });
  });

  it('returns undefined for 204', async () => {
    const res = fakeResponse(204);
    const result = await parseResponse(res);
    expect(result).toBeUndefined();
    expect(res.json).not.toHaveBeenCalled();
  });

  it('throws ApiError with detail message on non-ok response', async () => {
    await expect(parseResponse(fakeResponse(400, { detail: 'Bad input' }))).rejects.toMatchObject({
      status: 400,
      message: 'Bad input',
    });
  });

  it('falls back to statusText when body has no detail', async () => {
    await expect(
      parseResponse(fakeResponse(500, { other: 'x' }, 'Internal Server Error')),
    ).rejects.toMatchObject({ status: 500, message: 'Internal Server Error' });
  });

  it('falls back to statusText when body is not valid json', async () => {
    await expect(
      parseResponse(fakeResponse(500, null, 'Internal Server Error')),
    ).rejects.toMatchObject({ status: 500, message: 'Internal Server Error' });
  });

  it('thrown error is an instance of ApiError', async () => {
    await expect(parseResponse(fakeResponse(404, { detail: 'not found' }))).rejects.toBeInstanceOf(
      ApiError,
    );
  });
});

describe('apiFetch', () => {
  it('omits Authorization header when no access token', async () => {
    const fetchMock = queueFetch(fakeResponse(200, {}));
    await apiFetch('/images');
    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.has('Authorization')).toBe(false);
  });

  it('attaches Authorization header when access token present', async () => {
    authState.accessToken = 'token123';
    const fetchMock = queueFetch(fakeResponse(200, {}));
    await apiFetch('/images');
    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer token123');
  });

  it('sets JSON content-type for plain body', async () => {
    const fetchMock = queueFetch(fakeResponse(200, {}));
    await apiFetch('/images', { method: 'POST', body: JSON.stringify({ a: 1 }) });
    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get('Content-Type')).toBe('application/json');
  });

  it('does not set content-type for FormData body', async () => {
    const fetchMock = queueFetch(fakeResponse(200, {}));
    const body = new FormData();
    body.append('file', new Blob(['x']), 'a.jpg');
    await apiFetch('/images', { method: 'POST', body });
    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.has('Content-Type')).toBe(false);
  });

  it('does not override an explicitly-set content-type', async () => {
    const fetchMock = queueFetch(fakeResponse(200, {}));
    await apiFetch('/images', {
      method: 'POST',
      body: 'raw',
      headers: { 'Content-Type': 'text/plain' },
    });
    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get('Content-Type')).toBe('text/plain');
  });

  it('returns parsed data on success', async () => {
    queueFetch(fakeResponse(200, { id: 42 }));
    const result = await apiFetch('/images/42');
    expect(result).toEqual({ id: 42 });
  });

  it('401 with no refresh token throws without attempting refresh', async () => {
    queueFetch(fakeResponse(401, { detail: 'unauthorized' }));
    await expect(apiFetch('/images')).rejects.toMatchObject({ status: 401 });
    expect(authState.refreshTokens).not.toHaveBeenCalled();
  });

  it('401 with refresh token refreshes once and retries the request', async () => {
    authState.refreshToken = 'refresh123';
    const fetchMock = queueFetch(
      fakeResponse(401, { detail: 'expired' }),
      fakeResponse(200, { id: 1 }),
    );
    const result = await apiFetch('/images');
    expect(result).toEqual({ id: 1 });
    expect(authState.refreshTokens).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('concurrent 401s share a single refresh call (single-flight)', async () => {
    authState.refreshToken = 'refresh123';
    const fetchMock = queueFetch(
      fakeResponse(401, {}),
      fakeResponse(401, {}),
      fakeResponse(200, { id: 'a' }),
      fakeResponse(200, { id: 'b' }),
    );

    const [a, b] = await Promise.all([apiFetch('/a'), apiFetch('/b')]);
    expect(a).toEqual({ id: 'a' });
    expect(b).toEqual({ id: 'b' });
    expect(authState.refreshTokens).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledTimes(4);
  });

  it('logs out and throws when refresh fails', async () => {
    authState.refreshToken = 'refresh123';
    authState.refreshTokens = vi.fn().mockRejectedValue(new Error('refresh failed'));
    const fetchMock = queueFetch(fakeResponse(401, {}));
    await expect(apiFetch('/images')).rejects.toMatchObject({
      status: 401,
      message: 'Session expired',
    });
    expect(authState.logout).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('does not attempt refresh again on a retried request', async () => {
    authState.refreshToken = 'refresh123';
    queueFetch(fakeResponse(401, { detail: 'still unauthorized' }));
    await expect(apiFetch('/images', {}, true)).rejects.toMatchObject({ status: 401 });
    expect(authState.refreshTokens).not.toHaveBeenCalled();
  });
});
