import React from 'react';
import { Button, Tag } from '@carbon/react';
import { ArrowRight } from '@carbon/icons-react';
import { useNavigate } from 'react-router-dom';
import { useUser } from '@shared/contexts/UserContext';
import { useLocale } from '@shared/hooks';
import { translate } from '@shared/translations';
import './common.scss';

const TotpStatus: React.FC = () => {
  const { user } = useUser();
  const { locale } = useLocale();
  const t = translate(locale);
  const navigate = useNavigate();

  if (!user) return null;

  return (
    <div className="totp-status">
      <div className="totp-status__row">
        <span className="totp-status__label">{t.settings.account.totp.status}</span>
        <Tag type={user.totp_enabled ? 'green' : 'cool-gray'} size="sm">
          {user.totp_enabled ? t.settings.account.totp.enabled : t.settings.account.totp.disabled}
        </Tag>
      </div>

      {!user.totp_enabled && (
        <Button kind="primary" size="md" renderIcon={ArrowRight}
          onClick={() => navigate('/totp/enable')}>
          {t.settings.account.totp.enable}
        </Button>
      )}

      {user.totp_enabled && (
        <Button kind="danger--tertiary" size="md" renderIcon={ArrowRight}
          onClick={() => navigate('/totp/disable')}>
          {t.settings.account.totp.disable}
        </Button>
      )}
    </div>
  );
};

export default TotpStatus;
