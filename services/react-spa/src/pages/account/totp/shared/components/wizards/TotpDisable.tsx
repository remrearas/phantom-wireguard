import React, { useState } from 'react';
import { Grid, Column, Button, PasswordInput, InlineNotification } from '@carbon/react';
import { ArrowLeft, CheckmarkFilled } from '@carbon/icons-react';
import { useNavigate, Navigate } from 'react-router-dom';
import { useUser } from '@shared/contexts/UserContext';
import { useLocale } from '@shared/hooks';
import { translate } from '@shared/translations';
import { apiClient } from '@shared/api/client';
import '../common.scss';

type DisableStep = 'password' | 'done';

const TotpDisable: React.FC = () => {
  const { user } = useUser();
  const { locale } = useLocale();
  const t = translate(locale);
  const navigate = useNavigate();

  const [step, setStep] = useState<DisableStep>('password');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!user?.totp_enabled && step !== 'done') return <Navigate to="/account/totp" replace />;

  const totalSteps = 2;
  const currentStep = step === 'password' ? 1 : 2;

  const handleDisable = async () => {
    setLoading(true);
    setError(null);
    const res = await apiClient.post<{ message: string }>('/auth/totp/disable', { password });
    setLoading(false);
    if (res.ok) {
      setStep('done');
    } else {
      setError(
        (t.auth_service_api_codes as Record<string, string>)[res.error_code ?? ''] ??
          t.settings.error.generic
      );
    }
  };

  if (step === 'done') {
    return (
      <div className="totp-wizard">
        <Grid>
          <Column xlg={16} lg={16} md={8} sm={4}>
            <div className="totp-wizard__progress">
              <span className="totp-wizard__progress-text">
                {totalSteps} / {totalSteps}
              </span>
            </div>
            <div className="totp-wizard__question totp-wizard__done">
              <CheckmarkFilled size={64} className="totp-wizard__done-icon" />
              <p className="totp-wizard__done-text">{t.settings.account.totp.disableSuccess}</p>
              <Button
                kind="primary"
                renderIcon={ArrowLeft}
                onClick={() => navigate('/account/totp')}
                className="totp-wizard__done-btn"
              >
                {t.settings.account.totp.goBack}
              </Button>
            </div>
          </Column>
        </Grid>
      </div>
    );
  }

  return (
    <div className="totp-wizard">
      <Grid>
        <Column xlg={16} lg={16} md={8} sm={4}>
          <div className="totp-wizard__progress">
            <span className="totp-wizard__progress-text">
              {currentStep} / {totalSteps}
            </span>
          </div>

          {error && (
            <InlineNotification
              kind="error"
              title={error}
              lowContrast
              hideCloseButton
              className="totp-wizard__error"
            />
          )}

          <div className="totp-wizard__question">
            <p className="totp-wizard__question-text">{t.settings.account.totp.passwordRequired}</p>
            <div className="totp-wizard__input">
              <PasswordInput
                id="totp-disable-password"
                labelText={t.settings.account.totp.confirmPassword}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoFocus
              />
            </div>
          </div>

          <div className="totp-wizard__navigation">
            <Button
              kind="secondary"
              onClick={() => navigate('/account/totp')}
              className="totp-wizard__nav-btn"
            >
              {t.settings.account.totp.goBack}
            </Button>
            <Button
              kind="danger"
              onClick={handleDisable}
              disabled={loading || !password}
              className="totp-wizard__nav-btn"
            >
              {loading ? t.loadingSpinner.loading : t.settings.account.totp.confirm}
            </Button>
          </div>
        </Column>
      </Grid>
    </div>
  );
};

export default TotpDisable;
