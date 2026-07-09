import { apiFetch, parseResponse } from '@/api/client';
import type { TokenPair, User } from '@/types/auth';

const BASE_URL = import.meta.env.VITE_API_BASE_URL;

export function login(email: string, password: string) {
  const body = new URLSearchParams({ username: email, password });
  return fetch(`${BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  }).then((r) => parseResponse<TokenPair>(r));
}

export function register(email: string, password: string) {
  return fetch(`${BASE_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  }).then((r) => parseResponse<User>(r));
}

export function refreshTokenRequest(refresh_token: string) {
  return fetch(`${BASE_URL}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token }),
  }).then((r) => parseResponse<TokenPair>(r));
}

export function fetchMe() {
  return apiFetch<User>('/auth/me');
}
