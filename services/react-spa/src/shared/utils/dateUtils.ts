export function formatDateTime(iso: string, options?: { seconds?: boolean }): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      ...(options?.seconds ? { second: '2-digit' } : {}),
    });
  } catch {
    return iso;
  }
}
