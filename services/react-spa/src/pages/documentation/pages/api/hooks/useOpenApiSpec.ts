import { useState, useEffect, useCallback } from 'react';
import type { OpenApiSpec, TagGroup } from '../types/openapi';
import { groupByTag } from '../utils/specParser';

interface UseOpenApiSpecResult {
  spec: OpenApiSpec | null;
  tagGroups: TagGroup[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useOpenApiSpec(): UseOpenApiSpecResult {
  const [spec, setSpec] = useState<OpenApiSpec | null>(null);
  const [tagGroups, setTagGroups] = useState<TagGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSpec = useCallback(() => {
    setLoading(true);
    setError(null);

    const token = localStorage.getItem('token');
    fetch('/api/core/hello/openapi', {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((res) => {
        if (!res.ok) throw new Error(`${res.status}`);
        return res.json();
      })
      .then((data: OpenApiSpec) => {
        if (!data.paths || !data.info) {
          throw new Error('Invalid OpenAPI spec');
        }
        setSpec(data);
        setTagGroups(groupByTag(data));
      })
      .catch((err: Error) => {
        setError(err.message);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    fetchSpec();
  }, [fetchSpec]);

  return { spec, tagGroups, loading, error, refetch: fetchSpec };
}
