import { useState, useEffect, useCallback, useRef } from 'react';
import { apiClient, type ApiResponse } from '@shared/api/client';

interface UseApiResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useApi<T>(path: string | null): UseApiResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(!!path);
  const [error, setError] = useState<string | null>(null);
  const pathRef = useRef(path);
  pathRef.current = path;

  const fetch = useCallback(async () => {
    const current = pathRef.current;
    if (!current) return;
    setLoading(true);
    setError(null);
    const res = (await apiClient.get(current)) as ApiResponse<T>;
    if (pathRef.current !== current) return;
    if (res.ok) {
      setData(res.data);
    } else {
      setError(res.error);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    if (!path) {
      setData(null);
      setLoading(false);
      return;
    }
    void fetch();
  }, [path, fetch]);

  return { data, loading, error, refetch: fetch };
}
