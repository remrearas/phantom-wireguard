import React, { useState, useEffect } from 'react';
import { Modal, TextInput } from '@carbon/react';
import { useLocale } from '@shared/hooks';
import { translate } from '@shared/translations';
import { apiClient } from '@shared/api/client';
import FormError from '@shared/components/forms/FormError';

interface DnsRecord {
  family: string;
  primary: string;
  secondary: string;
}

type DnsFamily = 'v4' | 'v6';

interface EditDnsModalProps {
  family: DnsFamily | null;
  record: DnsRecord | null;
  onClose: () => void;
  onSaved: (record: DnsRecord) => void;
}

const EditDnsModal: React.FC<EditDnsModalProps> = ({ family, record, onClose, onSaved }) => {
  const { locale } = useLocale();
  const t = translate(locale);

  const [primary, setPrimary] = useState('');
  const [secondary, setSecondary] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (record) {
      setPrimary(record.primary);
      setSecondary(record.secondary);
      setError(null);
    }
  }, [record]);

  const handleSubmit = async () => {
    if (!family) return;
    setError(null);
    setSaving(true);

    const res = await apiClient.post<DnsRecord>('/api/dns/change', {
      family,
      primary: primary.trim(),
      secondary: secondary.trim(),
    });

    setSaving(false);

    if (res.ok) {
      onSaved(res.data);
    } else {
      const errMsg =
        (t.daemon_api_codes as Record<string, string>)[res.code ?? ''] ??
        t.settings.error.generic;
      setError(errMsg);
    }
  };

  const label = family === 'v4' ? 'IPv4' : 'IPv6';

  return (
    <Modal
      open={!!family}
      modalHeading={`${t.dns.edit} — ${label}`}
      primaryButtonText={saving ? t.dns.saving : t.dns.save}
      secondaryButtonText={t.dns.cancel}
      onRequestClose={onClose}
      onSecondarySubmit={onClose}
      onRequestSubmit={() => void handleSubmit()}
      primaryButtonDisabled={saving || !primary.trim()}
      size="sm"
      className="dns__modal"
      data-testid="vpn-dns-edit-modal"
    >
      <div className="dns__modal-form">
        <FormError error={error} data-testid="vpn-dns-edit-error" />
        <TextInput
          id="dns-primary"
          labelText={t.dns.primary}
          value={primary}
          onChange={(e) => setPrimary(e.target.value)}
          placeholder={family === 'v4' ? '1.1.1.1' : '2606:4700:4700::1111'}
          data-testid="vpn-dns-edit-primary"
        />
        <TextInput
          id="dns-secondary"
          labelText={t.dns.secondary}
          value={secondary}
          onChange={(e) => setSecondary(e.target.value)}
          placeholder={family === 'v4' ? '8.8.8.8' : '2001:4860:4860::8888'}
          data-testid="vpn-dns-edit-secondary"
        />
      </div>
    </Modal>
  );
};

export default EditDnsModal;
