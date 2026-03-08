import React, { useState } from 'react';
import { Modal, Grid, Column, TextInput } from '@carbon/react';
import FormError from '@shared/components/forms/FormError';
import { apiClient } from '@shared/api/client';
import { translate } from '@shared/translations';

const NAME_PATTERN = /^[a-zA-Z0-9_-]{1,64}$/;

interface ClientRecord {
  id: string;
  name: string;
}

interface Props {
  open: boolean;
  t: ReturnType<typeof translate>;
  onClose: () => void;
  onSuccess: () => void;
}

const CreateClientModal: React.FC<Props> = ({ open, t, onClose, onSuccess }) => {
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isValid = NAME_PATTERN.test(name);

  const reset = () => {
    setName('');
    setError(null);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleSubmit = async () => {
    if (!isValid) return;
    setLoading(true);
    setError(null);
    const res = await apiClient.post<ClientRecord>('/api/core/clients/assign', { name });
    setLoading(false);
    if (res.ok) {
      reset();
      onSuccess();
    } else {
      setError(res.error);
    }
  };

  return (
    <Modal
      open={open}
      modalHeading={t.clients.createTitle}
      primaryButtonText={loading ? t.loadingSpinner.loading : t.settings.users.confirm}
      secondaryButtonText={t.settings.users.cancel}
      primaryButtonDisabled={loading || !isValid}
      onRequestClose={handleClose}
      onRequestSubmit={handleSubmit}
      className="clients__modal"
      size="sm"
    >
      <Grid>
        <Column lg={16} md={8} sm={4}>
          <FormError error={error} className="clients__modal-error" />
          <TextInput
            id="create-client-name"
            labelText={t.clients.name}
            placeholder={t.clients.namePlaceholder}
            helperText={t.clients.nameHelperText}
            value={name}
            onChange={(e) => setName(e.target.value)}
            invalid={name.length > 0 && !isValid}
            invalidText={t.clients.nameInvalid}
            autoFocus
          />
        </Column>
      </Grid>
    </Modal>
  );
};

export default CreateClientModal;
