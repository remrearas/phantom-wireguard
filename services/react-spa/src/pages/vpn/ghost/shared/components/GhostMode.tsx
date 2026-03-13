import React, { useState, useCallback, useEffect } from 'react';
import { InlineNotification } from '@carbon/react';
import { useLocale } from '@shared/hooks';
import { translate } from '@shared/translations';
import { apiClient } from '@shared/api/client';
import LoadingSpinner from '@shared/components/ui/LoadingSpinner';
import GhostStatus, { type GhostStatusData } from './GhostStatus';
import GhostEnableWizard from './wizards/GhostEnableWizard';

const GhostMode: React.FC = () => {
  const { locale } = useLocale();
  const t = translate(locale);

  const [status, setStatus] = useState<GhostStatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await apiClient.get<GhostStatusData>('/api/ghost/status');
    if (res.ok) {
      setStatus(res.data);
    } else {
      setError(
        (t.daemon_api_codes as Record<string, string>)[res.code ?? ''] ??
          t.settings.error.generic
      );
    }
    setLoading(false);
  }, [t]);

  useEffect(() => {
    void fetchStatus();
  }, [fetchStatus]);

  if (loading) return <LoadingSpinner />;

  if (error) {
    return (
      <InlineNotification
        kind="error"
        title={error}
        lowContrast
        hideCloseButton
      />
    );
  }

  if (!status) return null;

  return status.enabled ? (
    <GhostStatus status={status} onDisabled={fetchStatus} />
  ) : (
    <GhostEnableWizard onEnabled={fetchStatus} />
  );
};

export default GhostMode;
