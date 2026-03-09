import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Grid, Column, Button, PasswordInput, InlineNotification } from '@carbon/react';
import {
  CheckmarkFilled,
  Checkmark,
  Close,
  Renew,
  Logout as LogoutIcon,
} from '@carbon/icons-react';
import { useNavigate } from 'react-router-dom';
import { useLocale } from '@shared/hooks';
import { useAuth } from '@shared/contexts/AuthContext';
import { translate } from '@shared/translations';
import { apiClient } from '@shared/api/client';
import { generatePassword, getPolicyChecks } from '@shared/utils/passwordUtils';
import '@pages/account/totp/shared/components/common.scss';
import './styles/password-change.scss';

interface VerifyResponse {
  change_token: string;
  expires_in: number;
}

type WizardStep = 'verify' | 'newpass' | 'done';

const PasswordChangeWizard: React.FC = () => {
  const { locale } = useLocale();
  const { logout } = useAuth();
  const t = translate(locale);
  const navigate = useNavigate();

  const [step, setStep] = useState<WizardStep>('verify');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [changeToken, setChangeToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const totalSteps = 3;
  const currentStep = step === 'verify' ? 1 : step === 'newpass' ? 2 : 3;

  const policyChecks = useMemo(() => getPolicyChecks(t.passwordChange.policy), [t]);
  const allPassed = policyChecks.every((c) => c.test(newPassword));

  const handleVerify = async () => {
    setLoading(true);
    setError(null);
    const res = await apiClient.post<VerifyResponse>('/auth/password/verify', {
      password: currentPassword,
    });
    setLoading(false);
    if (res.ok) {
      setChangeToken(res.data.change_token);
      setStep('newpass');
    } else {
      setError(
        (t.auth_service_api_codes as Record<string, string>)[res.error_code ?? ''] ??
          t.settings.error.generic
      );
    }
  };

  const handleChange = async () => {
    if (!allPassed) return;
    setLoading(true);
    setError(null);
    const res = await apiClient.post<{ message: string }>('/auth/password/change', {
      change_token: changeToken,
      password: newPassword,
    });
    setLoading(false);
    if (res.ok) {
      localStorage.removeItem('token');
      sessionStorage.removeItem('auth_warning');
      setStep('done');
    } else {
      setError(
        (t.auth_service_api_codes as Record<string, string>)[res.error_code ?? ''] ??
          t.settings.error.generic
      );
    }
  };

  const handleRestart = () => {
    setStep('verify');
    setCurrentPassword('');
    setNewPassword('');
    setChangeToken('');
    setError(null);
  };

  // Logout countdown
  const [countdown, setCountdown] = useState(5);
  const countdownStarted = useRef(false);

  useEffect(() => {
    if (step !== 'done' || countdownStarted.current) return;
    countdownStarted.current = true;

    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          logout().then(() => {
            sessionStorage.removeItem('auth_warning');
            navigate('/login');
          });
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [step, logout, navigate]);

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
              <CheckmarkFilled size={64} className="totp-wizard__done-icon" data-testid="pwchange-done" />
              <p className="totp-wizard__done-text">{t.passwordChange.success}</p>
              <div className="pw-change__countdown">
                <LogoutIcon size={20} />
                <span className="pw-change__countdown-number">{countdown}</span>
              </div>
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
              data-testid="pwchange-error"
            />
          )}

          {/* Step 1: Verify current password */}
          {step === 'verify' && (
            <div className="totp-wizard__question">
              <p className="totp-wizard__question-text">{t.passwordChange.description}</p>
              <div className="totp-wizard__input">
                <PasswordInput
                  id="current-password"
                  labelText={t.passwordChange.currentPassword}
                  placeholder={t.passwordChange.currentPasswordPlaceholder}
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  data-testid="pwchange-current-password"
                  autoFocus
                />
              </div>
            </div>
          )}

          {/* Step 2: New password with policy checklist */}
          {step === 'newpass' && (
            <div className="totp-wizard__question">
              <p className="totp-wizard__question-text">{t.passwordChange.newPassword}</p>
              <div className="totp-wizard__input">
                <PasswordInput
                  id="new-password"
                  labelText={t.passwordChange.newPassword}
                  placeholder={t.passwordChange.newPasswordPlaceholder}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  data-testid="pwchange-new-password"
                  autoFocus
                />
              </div>
              <Button
                kind="ghost"
                size="sm"
                renderIcon={Renew}
                onClick={() => setNewPassword(generatePassword())}
                className="pw-change__generate"
              >
                {t.passwordChange.generate}
              </Button>
              <ul className="pw-change__checklist">
                {policyChecks.map((check) => {
                  const passed = check.test(newPassword);
                  return (
                    <li
                      key={check.key}
                      className={`pw-change__check ${passed ? 'pw-change__check--pass' : ''}`}
                    >
                      {passed ? (
                        <Checkmark
                          size={16}
                          className="pw-change__check-icon pw-change__check-icon--pass"
                        />
                      ) : (
                        <Close
                          size={16}
                          className="pw-change__check-icon pw-change__check-icon--fail"
                        />
                      )}
                      <span>{check.label}</span>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          {/* Navigation */}
          <div className="totp-wizard__navigation">
            {step === 'verify' && (
              <>
                <Button
                  kind="secondary"
                  onClick={() => navigate('/')}
                  className="totp-wizard__nav-btn"
                >
                  {t.passwordChange.goBack}
                </Button>
                <Button
                  kind="primary"
                  onClick={handleVerify}
                  disabled={loading || !currentPassword}
                  className="totp-wizard__nav-btn"
                  data-testid="pwchange-verify-confirm"
                >
                  {loading ? t.loadingSpinner.loading : t.passwordChange.confirm}
                </Button>
              </>
            )}

            {step === 'newpass' && (
              <>
                <Button kind="secondary" onClick={handleRestart} className="totp-wizard__nav-btn">
                  {t.passwordChange.goBack}
                </Button>
                <Button
                  kind="primary"
                  onClick={handleChange}
                  disabled={loading || !allPassed}
                  className="totp-wizard__nav-btn"
                  data-testid="pwchange-change-confirm"
                >
                  {loading ? t.loadingSpinner.loading : t.passwordChange.confirm}
                </Button>
              </>
            )}
          </div>
        </Column>
      </Grid>
    </div>
  );
};

export default PasswordChangeWizard;
