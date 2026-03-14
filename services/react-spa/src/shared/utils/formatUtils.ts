/**
 * Format a byte count into a human-readable string (e.g. "1.2 MB").
 */
export const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
};

/**
 * Format a unix timestamp into a relative time string (e.g. "30s", "5m", "2h", "3d").
 * Returns "—" if timestamp is 0 (never).
 */
export const formatHandshake = (ts: number): string => {
  if (ts === 0) return '—';
  const secs = Math.floor(Date.now() / 1000 - ts);
  if (secs < 60) return `${secs}s`;
  if (secs < 3600) return `${Math.floor(secs / 60)}m`;
  if (secs < 86400) return `${Math.floor(secs / 3600)}h`;
  return `${Math.floor(secs / 86400)}d`;
};
