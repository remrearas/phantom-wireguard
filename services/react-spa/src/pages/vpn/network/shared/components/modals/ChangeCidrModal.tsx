import React, { useState, useEffect, useMemo } from 'react';
import { Modal, Slider, Tag } from '@carbon/react';
import { useLocale } from '@shared/hooks';
import { translate } from '@shared/translations';
import { apiClient } from '@shared/api/client';
import FormError from '@shared/components/forms/FormError';

// ── Types ─────────────────────────────────────────────────────────

interface PoolStats {
  total: number;
  assigned: number;
  free: number;
}

interface ChangeCidrResponse {
  ipv4_subnet: string;
  ipv6_subnet: string;
  pool: PoolStats;
}

interface ChangeCidrModalProps {
  open: boolean;
  currentPrefix: number;
  assignedCount: number;
  onClose: () => void;
  onSaved: (data: ChangeCidrResponse) => void;
}

// ── Helpers ───────────────────────────────────────────────────────

function capacityForPrefix(prefix: number): number {
  const hostBits = 32 - prefix;
  return Math.pow(2, hostBits) - 3; // network + broadcast + server
}

function ipv6PrefixForV4(prefix: number): number {
  return 128 - (32 - prefix);
}

// ── Component ─────────────────────────────────────────────────────

const ChangeCidrModal: React.FC<ChangeCidrModalProps> = ({
  open,
  currentPrefix,
  assignedCount,
  onClose,
  onSaved,
}) => {
  const { locale } = useLocale();
  const t = translate(locale);

  const [prefix, setPrefix] = useState(currentPrefix);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setPrefix(currentPrefix);
      setError(null);
    }
  }, [open, currentPrefix]);

  const preview = useMemo(() => {
    const capacity = capacityForPrefix(prefix);
    const v6Prefix = ipv6PrefixForV4(prefix);
    const fits = capacity >= assignedCount;
    return { capacity, v6Prefix, fits };
  }, [prefix, assignedCount]);

  const handleSubmit = async () => {
    setError(null);
    setSaving(true);

    const res = await apiClient.post<ChangeCidrResponse>('/api/core/network/cidr', {
      prefix,
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

  const noChange = prefix === currentPrefix;

  return (
    <Modal
      open={open}
      modalHeading={t.network.changeCidr}
      primaryButtonText={saving ? t.network.saving : t.network.apply}
      secondaryButtonText={t.network.cancel}
      onRequestClose={onClose}
      onSecondarySubmit={onClose}
      onRequestSubmit={() => void handleSubmit()}
      primaryButtonDisabled={saving || noChange || !preview.fits}
      danger={!noChange && preview.fits}
      size="sm"
      className="network__modal"
      data-testid="vpn-net-cidr-modal"
    >
      <div className="network__modal-form">
        <FormError error={error} />

        <Slider
          id="cidr-prefix"
          labelText={t.network.prefix}
          min={16}
          max={30}
          step={1}
          value={prefix}
          onChange={({ value }: { value: number }) => setPrefix(value)}
          data-testid="vpn-net-cidr-slider"
        />

        <div className="network__preview" data-testid="vpn-net-cidr-preview">
          <div className="network__preview-row">
            <span className="network__preview-label">IPv4</span>
            <span className="network__preview-value">/{prefix}</span>
          </div>
          <div className="network__preview-row">
            <span className="network__preview-label">IPv6</span>
            <span className="network__preview-value">/{preview.v6Prefix}</span>
          </div>
          <div className="network__preview-row">
            <span className="network__preview-label">{t.network.capacity}</span>
            <span className="network__preview-value">
              {preview.capacity.toLocaleString()}
            </span>
          </div>
          <div className="network__preview-row">
            <span className="network__preview-label">{t.network.assigned}</span>
            <span className="network__preview-value">{assignedCount}</span>
          </div>

          {!preview.fits && (
            <Tag type="red" size="sm" className="network__preview-warning">
              {t.network.capacityExceeded}
            </Tag>
          )}
        </div>

        {!noChange && preview.fits && (
          <p className="network__destructive-note" data-testid="vpn-net-cidr-warning">
            {t.network.cidrWarning}
          </p>
        )}
      </div>
    </Modal>
  );
};

export default ChangeCidrModal;
