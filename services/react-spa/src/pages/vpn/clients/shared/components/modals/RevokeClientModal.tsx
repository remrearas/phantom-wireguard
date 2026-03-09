import React, { useState } from 'react';
import { Modal, Grid, Column } from '@carbon/react';
import FormError from '@shared/components/forms/FormError';
import { apiClient } from '@shared/api/client';
import { translate } from '@shared/translations';

interface Props {
  open: boolean;
  clientName: string;
  t: ReturnType<typeof translate>;
  onClose: () => void;
  onSuccess: () => void;
}

const RevokeClientModal: React.FC<Props> = ({ open, clientName, t, onClose, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleClose = () => {
    setError(null);
    onClose();
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    const res = await apiClient.post<{ status: string }>('/api/core/clients/revoke', { name: clientName });
    setLoading(false);
    if (res.ok) {
      onSuccess();
    } else {
      setError((t.daemon_api_codes as Record<string, string>)[res.code ?? ''] ?? t.settings.error.generic);
    }
  };

  return (
    <Modal
      open={open}
      danger
      modalHeading={t.clients.revokeClient}
      primaryButtonText={loading ? t.loadingSpinner.loading : t.settings.users.confirm}
      secondaryButtonText={t.settings.users.cancel}
      primaryButtonDisabled={loading}
      onRequestClose={handleClose}
      onRequestSubmit={handleSubmit}
      className="clients__modal"
      size="sm"
    >
      <Grid>
        <Column lg={16} md={8} sm={4}>
          <FormError error={error} className="clients__modal-error" />
          <p className="clients__confirm-text">
            <strong>{clientName}</strong>{' '}
            {t.clients.confirmRevoke}
          </p>
        </Column>
      </Grid>
    </Modal>
  );
};

export default RevokeClientModal;
