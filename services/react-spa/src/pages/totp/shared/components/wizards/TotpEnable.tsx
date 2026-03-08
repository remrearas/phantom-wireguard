import React, { useState } from 'react';
import {
  Grid, Column, Button, PasswordInput, TextInput,
  InlineNotification, CopyButton, CodeSnippet,
} from '@carbon/react';
import { ArrowLeft, CheckmarkFilled } from '@carbon/icons-react';
import { QRCodeSVG } from 'qrcode.react';
import { useNavigate, Navigate } from 'react-router-dom';
import { useUser } from '@shared/contexts/UserContext';
import { useLocale } from '@shared/hooks';
import { translate } from '@shared/translations';
import { apiClient } from '@shared/api/client';
import '../common.scss';

interface SetupData {
  setup_token: string;
  secret: string;
  uri: string;
  backup_codes: string[];
  expires_in: number;
}

type WizardStep = 'password' | 'setup' | 'verify' | 'done' | 'failed';

const TotpEnable: React.FC = () => {
  const { user, mutateUser } = useUser();
  const { locale } = useLocale();
  const t = translate(locale);
  const navigate = useNavigate();

  const [step, setStep] = useState<WizardStep>('password');
  const [password, setPassword] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [setupData, setSetupData] = useState<SetupData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (user?.totp_enabled) return <Navigate to="/totp" replace />;

  const totalSteps = 4;
  const currentStep = step === 'password' ? 1 : step === 'setup' ? 2 : step === 'verify' ? 3 : 4;
  const canGoNext = step === 'setup';
  const canGoBack = step === 'verify';

  const handleSetup = async () => {
    setLoading(true);
    setError(null);
    const res = await apiClient.post<SetupData>('/auth/totp/setup', { password });
    setLoading(false);
    if (res.ok) {
      setSetupData(res.data);
      setStep('setup');
    } else {
      const msg = res.error === 'Invalid password' ? t.settings.account.totp.invalidPassword
        : res.error === 'TOTP already enabled' ? t.settings.account.totp.alreadyEnabled
        : res.error;
      setError(msg);
    }
  };

  const handleConfirm = async () => {
    if (!setupData) return;
    setLoading(true);
    setError(null);
    const res = await apiClient.post<{ message: string }>('/auth/totp/confirm', {
      setup_token: setupData.setup_token,
      code: totpCode,
    });
    setLoading(false);
    if (res.ok) {
      await mutateUser();
      setStep('done');
    } else {
      if (res.error === 'Token expired') {
        setError(t.settings.account.totp.setupExpired);
        setStep('failed');
      } else {
        const msg = res.error === 'Invalid TOTP code' ? t.settings.account.totp.invalidPassword : res.error;
        setError(msg);
      }
    }
  };

  const handleRestart = () => {
    setStep('password');
    setPassword('');
    setTotpCode('');
    setSetupData(null);
    setError(null);
  };

  // ── Result states ──

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
              <p className="totp-wizard__done-text">
                {t.settings.account.totp.enableSuccess}
              </p>
              <Button kind="primary" renderIcon={ArrowLeft} onClick={() => navigate('/totp')}
                className="totp-wizard__done-btn">
                {t.settings.account.totp.goBack}
              </Button>
            </div>
          </Column>
        </Grid>
      </div>
    );
  }

  if (step === 'failed') {
    return (
      <div className="totp-wizard">
        <Grid>
          <Column xlg={16} lg={16} md={8} sm={4}>
            <div className="totp-wizard__result">
              <InlineNotification kind="error" title={error || t.settings.account.totp.setupExpired}
                lowContrast hideCloseButton />
              <div className="totp-wizard__restart">
                <Button kind="primary" onClick={handleRestart} className="totp-wizard__restart-btn">
                  {t.settings.account.totp.confirm}
                </Button>
                <Button kind="ghost" renderIcon={ArrowLeft} onClick={() => navigate('/totp')}
                  className="totp-wizard__restart-btn">
                  {t.settings.account.totp.cancel}
                </Button>
              </div>
            </div>
          </Column>
        </Grid>
      </div>
    );
  }

  // ── Wizard ──

  return (
    <div className="totp-wizard">
      <Grid>
        <Column xlg={16} lg={16} md={8} sm={4}>
          {/* Progress */}
          <div className="totp-wizard__progress">
            <span className="totp-wizard__progress-text">
              {currentStep} / {totalSteps}
            </span>
          </div>

          {/* Error */}
          {error && (
            <InlineNotification kind="error" title={error} lowContrast hideCloseButton
              className="totp-wizard__error" />
          )}

          {/* Step 1: Password */}
          {step === 'password' && (
            <div className="totp-wizard__question">
              <p className="totp-wizard__question-text">
                {t.settings.account.totp.enterPassword}
              </p>
              <div className="totp-wizard__input">
                <PasswordInput
                  id="totp-enable-password"
                  labelText={t.settings.account.totp.confirmPassword}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoFocus
                />
              </div>
            </div>
          )}

          {/* Step 2: QR + Secret + Backup Codes */}
          {step === 'setup' && setupData && (
            <div className="totp-wizard__question">
              <p className="totp-wizard__question-text">
                {t.settings.account.totp.scanQR}
              </p>

              <div className="totp-wizard__qr-container">
                <div className="totp-wizard__qr-wrapper">
                  <QRCodeSVG value={setupData.uri} size={200} />
                </div>
              </div>

              <div className="totp-wizard__secret">
                <span className="totp-wizard__secret-label">{t.settings.account.totp.secret}:</span>
                <code className="totp-wizard__secret-value">{setupData.secret}</code>
                <CopyButton
                  onClick={() => navigator.clipboard.writeText(setupData.secret)}
                  iconDescription={t.settings.account.totp.copied}
                />
              </div>

              <div className="totp-wizard__backup">
                <h4>{t.settings.account.totp.backupCodes}</h4>
                <CodeSnippet type="multi" feedback={t.settings.account.totp.copied}>
                  {setupData.backup_codes.join('\n')}
                </CodeSnippet>
                <InlineNotification kind="warning" title={t.settings.account.totp.backupCodesWarning}
                  lowContrast hideCloseButton />
              </div>
            </div>
          )}

          {/* Step 3: Verify TOTP Code */}
          {step === 'verify' && (
            <div className="totp-wizard__question">
              <p className="totp-wizard__question-text">
                {t.settings.account.totp.verifyCode}
              </p>
              <div className="totp-wizard__input">
                <TextInput
                  id="totp-enable-code"
                  type="text"
                  labelText={t.login.totpCode}
                  placeholder={t.login.totpPlaceholder}
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value)}
                  maxLength={6}
                  pattern="[0-9]{6}"
                  autoFocus
                />
              </div>
            </div>
          )}

          {/* Navigation */}
          <div className="totp-wizard__navigation">
            {canGoBack && (
              <Button kind="secondary" onClick={handleRestart}
                className="totp-wizard__nav-btn">
                {t.settings.account.totp.cancel}
              </Button>
            )}

            {step === 'password' && (
              <>
                <Button kind="secondary" onClick={() => navigate('/totp')}
                  className="totp-wizard__nav-btn">
                  {t.settings.account.totp.goBack}
                </Button>
                <Button kind="primary" onClick={handleSetup}
                  disabled={loading || !password} className="totp-wizard__nav-btn">
                  {loading ? t.loadingSpinner.loading : t.settings.account.totp.confirm}
                </Button>
              </>
            )}

            {canGoNext && (
              <Button kind="primary" onClick={() => { setStep('verify'); setTotpCode(''); setError(null); }}
                className="totp-wizard__nav-btn">
                {t.settings.account.totp.confirm}
              </Button>
            )}

            {step === 'verify' && (
              <Button kind="primary" onClick={handleConfirm}
                disabled={loading || totpCode.length < 6} className="totp-wizard__nav-btn">
                {loading ? t.loadingSpinner.loading : t.login.totpSubmit}
              </Button>
            )}
          </div>
        </Column>
      </Grid>
    </div>
  );
};

export default TotpEnable;
