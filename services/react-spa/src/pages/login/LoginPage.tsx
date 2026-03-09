import React, { useState, useEffect } from 'react';
import {
  Form,
  TextInput,
  PasswordInput,
  Button,
  InlineNotification,
  Stack,
  Grid,
  Column,
} from '@carbon/react';
import { ArrowRight } from '@carbon/icons-react';
import { useAuth } from '@shared/contexts/AuthContext';
import { useLocale } from '@shared/hooks';
import { translate } from '@shared/translations';
import PhantomIcon from '@shared/components/ui/PhantomIcon';
import './styles/LoginPage.scss';

const LoginPage: React.FC = () => {
  const { login, verifyTotp, verifyBackupCode } = useAuth();
  const { locale } = useLocale();
  const t = translate(locale);

  const localizeError = (code: string): string =>
    (t.auth_service_api_codes as Record<string, string>)[code] ??
    (t.client_side_api_codes as Record<string, string>)[code] ??
    code;

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [backupCode, setBackupCode] = useState('');
  const [useBackup, setUseBackup] = useState(false);
  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [mfaCountdown, setMfaCountdown] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // MFA countdown timer
  useEffect(() => {
    if (mfaCountdown <= 0) return;
    const timer = setInterval(() => {
      setMfaCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          setMfaToken(null);
          setError(t.login.error.tokenExpired);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [mfaCountdown > 0]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const authWarning = sessionStorage.getItem('auth_warning');
    if (authWarning === 'session_expired') {
      sessionStorage.removeItem('auth_warning');
      setWarning(t.login.warning.sessionExpired);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleLogin = async (e: React.SyntheticEvent) => {
    e.preventDefault();
    setError(null);
    setWarning(null);
    setLoading(true);

    const result = await login(username, password);
    setLoading(false);

    switch (result.status) {
      case 'ok':
        break;
      case 'mfa_required':
        setMfaToken(result.mfa_token);
        setMfaCountdown(result.expires_in);
        setTotpCode('');
        setBackupCode('');
        setUseBackup(false);
        break;
      case 'error':
        setError(localizeError(result.error));
        break;
    }
  };

  const handleTotp = async (e: React.SyntheticEvent) => {
    e.preventDefault();
    if (!mfaToken) return;
    setError(null);
    setLoading(true);

    const result = useBackup
      ? await verifyBackupCode(mfaToken, backupCode)
      : await verifyTotp(mfaToken, totpCode);
    setLoading(false);

    if (result.status === 'error') {
      setError(localizeError(result.error));
    }
  };

  return (
    <div className="login-page__card">
      <PhantomIcon className="login-page__icon" />

      <h1 className="login-page__heading">
        {mfaToken ? (useBackup ? t.login.backupCodeTitle : t.login.totpTitle) : t.login.title}
      </h1>

      <Grid className="login-page__grid" narrow>
        {warning && (
          <Column lg={16} md={8} sm={4}>
            <InlineNotification
              kind="warning"
              title={warning}
              onCloseButtonClick={() => setWarning(null)}
              lowContrast
              className="login-page__notification"
            />
          </Column>
        )}

        {error && (
          <Column lg={16} md={8} sm={4}>
            <InlineNotification
              kind="error"
              title={error}
              onCloseButtonClick={() => setError(null)}
              lowContrast
              className="login-page__notification"
            />
          </Column>
        )}

        <Column lg={16} md={8} sm={4}>
          {!mfaToken ? (
            <Form onSubmit={handleLogin}>
              <Stack gap={6}>
                <TextInput
                  id="username"
                  type="text"
                  labelText={t.login.username}
                  placeholder={t.login.usernamePlaceholder}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  required
                />
                <PasswordInput
                  id="password"
                  labelText={t.login.password}
                  placeholder={t.login.passwordPlaceholder}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />
                <Button
                  type="submit"
                  renderIcon={ArrowRight}
                  disabled={loading || !username || !password}
                  className="login-page__submit"
                >
                  {loading ? t.login.submitting : t.login.submit}
                </Button>
              </Stack>
            </Form>
          ) : (
            <Form onSubmit={handleTotp}>
              <Stack gap={6}>
                {!useBackup ? (
                  <TextInput
                    id="totp-code"
                    type="text"
                    labelText={t.login.totpCode}
                    placeholder={t.login.totpPlaceholder}
                    value={totpCode}
                    onChange={(e) => setTotpCode(e.target.value)}
                    maxLength={6}
                    pattern="[0-9]{6}"
                    autoComplete="one-time-code"
                    autoFocus
                    required
                  />
                ) : (
                  <TextInput
                    id="backup-code"
                    type="text"
                    labelText={t.login.backupCode}
                    placeholder={t.login.backupCodePlaceholder}
                    value={backupCode}
                    onChange={(e) => setBackupCode(e.target.value)}
                    maxLength={8}
                    autoFocus
                    required
                  />
                )}
                {mfaCountdown > 0 && (
                  <p className="login-page__countdown">
                    {t.login.countdown}: {Math.floor(mfaCountdown / 60)}:
                    {String(mfaCountdown % 60).padStart(2, '0')}
                  </p>
                )}
                <Button
                  type="submit"
                  renderIcon={ArrowRight}
                  disabled={
                    loading ||
                    mfaCountdown <= 0 ||
                    (useBackup ? backupCode.length < 6 : totpCode.length < 6)
                  }
                  className="login-page__submit"
                >
                  {loading ? t.login.submitting : t.login.totpSubmit}
                </Button>
                <button
                  type="button"
                  className="login-page__toggle-link"
                  onClick={() => {
                    setUseBackup(!useBackup);
                    setError(null);
                  }}
                >
                  {useBackup ? t.login.useTotpCode : t.login.useBackupCode}
                </button>
              </Stack>
            </Form>
          )}
        </Column>
      </Grid>
    </div>
  );
};

export default LoginPage;
