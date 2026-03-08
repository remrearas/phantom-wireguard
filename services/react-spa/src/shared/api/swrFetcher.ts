import { apiClient } from './client';

export const USER_KEY = '/auth/me' as const;

export async function swrFetcher<T>(path: string): Promise<T | null> {
  if (!localStorage.getItem('token')) return null;
  const res = await apiClient.get<T>(path);
  return res.ok ? res.data : null;
}
