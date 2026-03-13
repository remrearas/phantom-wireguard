import React, { useState, useEffect } from 'react';
import { Modal, InlineNotification } from '@carbon/react';
import { useLocale } from '@shared/hooks';
import { translate } from '@shared/translations';
import { apiClient } from '@shared/api/client';

interface Props {
  open: boolean;
  onClose: () => void;
  onDisabled: () => void;
}

const DisableGhostModal: React.FC<Props> = ({ open, onClose, onDisabled }) => {
  const { locale } = useLocale();
  const t = translate(locale);
  const tg = t.ghost;

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      const timer = setTimeout(() => {
        setError(null);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [open]);

  const handleDisable = async () => {
    setLoading(true);
    setError(null);
    const res = await apiClient.post<Record<string, never>>('/api/ghost/disable', {});
    setLoading(false);
    if (res.ok) {
      onDisabled();
    } else {
      setError(
        (t.daemon_api_codes as Record<string, string>)[res.code ?? ''] ??
          t.settings.error.generic
      );
    }
  };

  return (
    <Modal
      open={open}
      size="sm"
      danger
      modalHeading={tg.disableTitle}
      primaryButtonText={loading ? t.loadingSpinner.loading : tg.confirm}
      secondaryButtonText={tg.cancel}
      primaryButtonDisabled={loading}
      onRequestSubmit={() => void handleDisable()}
      onRequestClose={onClose}
      onSecondarySubmit={onClose}
      data-testid="ghost-disable-modal"
    >
      {error && (
        <InlineNotification
          kind="error"
          title={error}
          lowContrast
          hideCloseButton
        />
      )}
      <p>{tg.disableConfirm}</p>
    </Modal>
  );
};

export default DisableGhostModal;
