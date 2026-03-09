import React, { useState } from 'react';
import { Modal, Grid, Column } from '@carbon/react';
import FormError from '@shared/components/forms/FormError';
import { apiClient } from '@shared/api/client';
import { translate } from '@shared/translations';

interface Props {
  open: boolean;
  username: string;
  t: ReturnType<typeof translate>;
  onClose: () => void;
  onSuccess: () => void;
}

const DeleteUserModal: React.FC<Props> = ({ open, username, t, onClose, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleClose = () => {
    setError(null);
    onClose();
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    const res = await apiClient.delete<{ message: string }>(`/auth/users/${username}`);
    setLoading(false);
    if (res.ok) {
      setError(null);
      onSuccess();
    } else {
      setError(
        (t.auth_service_api_codes as Record<string, string>)[res.error_code ?? ''] ??
          t.settings.error.generic
      );
    }
  };

  return (
    <Modal
      open={open}
      danger
      modalHeading={t.settings.users.deleteUserTitle}
      primaryButtonText={loading ? t.loadingSpinner.loading : t.settings.users.confirm}
      secondaryButtonText={t.settings.users.cancel}
      primaryButtonDisabled={loading}
      onRequestClose={handleClose}
      onRequestSubmit={handleSubmit}
      className="um__modal"
      size="sm"
    >
      <Grid>
        <Column lg={16} md={8} sm={4}>
          <FormError error={error} className="um__modal-error" />
          <p className="um__confirm-text">
            <strong>{username}</strong> {t.settings.users.confirmDelete}
          </p>
        </Column>
      </Grid>
    </Modal>
  );
};

export default DeleteUserModal;
