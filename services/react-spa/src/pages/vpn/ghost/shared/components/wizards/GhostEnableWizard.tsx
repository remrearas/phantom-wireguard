import React, { useState } from 'react';
import {
  Grid,
  Column,
  Button,
  TextInput,
  TextArea,
  Select,
  SelectItem,
  InlineNotification,
} from '@carbon/react';
import { ArrowLeft, CheckmarkFilled } from '@carbon/icons-react';
import * as x509 from '@peculiar/x509';
import { useLocale } from '@shared/hooks';
import { translate } from '@shared/translations';
import { apiClient } from '@shared/api/client';
import '../styles/ghost.scss';
import '@pages/account/totp/shared/components/common.scss';

interface Props {
  onEnabled: () => Promise<void>;
}

type WizardStep = 'domain' | 'cert' | 'confirm' | 'done';

interface CertPreview {
  subject: string;
  notAfter: Date;
  fingerprint?: string;
  type: 'self-signed' | 'imported';
}

interface EnableResponse {
  status: string;
  domain: string;
  protocol: string;
  port: number;
  restrict_path_prefix: string;
}

const FQDN_REGEX =
  /^(?!-)(?:[a-zA-Z0-9-]{1,63}\.)+[a-zA-Z]{2,}$/;

const GhostEnableWizard: React.FC<Props> = ({ onEnabled }) => {
  const { locale } = useLocale();
  const t = translate(locale);
  const tg = t.ghost;
  const tw = tg.wizard;

  const totalSteps = 3;

  // ── Wizard state ────────────────────────────────────────────────
  const [step, setStep] = useState<WizardStep>('domain');

  // Step 1
  const [domain, setDomain] = useState('');
  const [domainError, setDomainError] = useState<string | null>(null);

  // Step 2 — cert inputs
  const [certPem, setCertPem] = useState('');
  const [keyPem, setKeyPem] = useState('');
  const [certError, setCertError] = useState<string | null>(null);
  const [certWarning, setCertWarning] = useState<string | null>(null);
  const [certPreview, setCertPreview] = useState<CertPreview | null>(null);

  // Step 2 — generate form
  const [showGenerate, setShowGenerate] = useState(false);
  const [genValidity, setGenValidity] = useState('365');
  const [generating, setGenerating] = useState(false);

  // Step 3 — enable
  const [loading, setLoading] = useState(false);
  const [enableError, setEnableError] = useState<string | null>(null);


  // ── Step helpers ────────────────────────────────────────────────

  const validateCertPem = (
    pem: string,
    domainName: string
  ): { preview: CertPreview | null; error: string | null; warning: string | null } => {
    if (!pem.trim()) return { preview: null, error: null, warning: null };
    try {
      const cert = new x509.X509Certificate(pem);
      if (new Date() > cert.notAfter) {
        return { preview: null, error: tw.certExpired, warning: null };
      }
      let warning: string | null = null;
      const sanExt = cert.getExtension(x509.SubjectAlternativeNameExtension);
      if (sanExt) {
        const dnsNames = sanExt.names
          .toJSON()
          .filter((n) => n.type === 'dns')
          .map((n) => String(n.value));
        const matches = dnsNames.some(
          (n) => n === domainName || (n.startsWith('*.') && domainName.endsWith(n.slice(1)))
        );
        if (!matches) warning = tw.certDomainWarning;
      } else {
        const cn = cert.subject.match(/CN=([^,]+)/)?.[1]?.trim();
        if (cn && cn !== domainName) warning = tw.certDomainWarning;
      }
      return {
        preview: { subject: cert.subject, notAfter: cert.notAfter, type: 'imported' },
        error: null,
        warning,
      };
    } catch {
      return { preview: null, error: tw.certInvalid, warning: null };
    }
  };

  // ── Step 1: Domain ───────────────────────────────────────────────

  const handleDomainNext = () => {
    if (!FQDN_REGEX.test(domain)) {
      setDomainError(tw.domainInvalid);
      return;
    }
    setDomainError(null);
    setStep('cert');
  };

  // ── Step 2: Certificate ──────────────────────────────────────────

  const handleCertChange = (pem: string) => {
    setCertPem(pem);
    const { preview, error, warning } = validateCertPem(pem, domain);
    setCertError(error);
    setCertWarning(warning);
    setCertPreview(preview);
  };

  const handleCertNext = () => {
    if (!certPem.trim() || !keyPem.trim()) {
      setCertError(tw.certRequired);
      return;
    }
    const { preview, error } = validateCertPem(certPem, domain);
    if (error) {
      setCertError(error);
      return;
    }
    setCertPreview(preview);
    setStep('confirm');
  };

  // ── Generate self-signed ─────────────────────────────────────────

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const keyGenAlg = { name: 'ECDSA', namedCurve: 'P-256' };
      const signAlg = { name: 'ECDSA', hash: 'SHA-256' };
      const keys = await crypto.subtle.generateKey(keyGenAlg, true, ['sign', 'verify']);

      const validDays = parseInt(genValidity, 10);

      const cert = await x509.X509CertificateGenerator.createSelfSigned({
        serialNumber: Array.from(crypto.getRandomValues(new Uint8Array(8)))
          .map((b) => b.toString(16).padStart(2, '0'))
          .join(''),
        name: `CN=${domain}`,
        notBefore: new Date(),
        notAfter: new Date(Date.now() + validDays * 24 * 60 * 60 * 1000),
        signingAlgorithm: signAlg,
        keys,
        extensions: [
          new x509.SubjectAlternativeNameExtension([{ type: 'dns' as const, value: domain }]),
          new x509.BasicConstraintsExtension(false),
        ],
      });

      const certPemStr = cert.toString('pem');

      const privKeyBuf = await crypto.subtle.exportKey('pkcs8', keys.privateKey);
      const privKeyB64 = new Uint8Array(privKeyBuf).reduce(
        (acc, b) => acc + String.fromCharCode(b),
        ''
      );
      const keyPemStr = [
        '-----BEGIN PRIVATE KEY-----',
        ...btoa(privKeyB64).match(/.{1,64}/g)!,
        '-----END PRIVATE KEY-----',
        '',
      ].join('\n');

      const thumbBuf = await cert.getThumbprint('SHA-256');
      const fingerprint = Array.from(new Uint8Array(thumbBuf))
        .map((b) => b.toString(16).padStart(2, '0').toUpperCase())
        .join(':');

      setCertPem(certPemStr);
      setKeyPem(keyPemStr);
      setCertError(null);
      setCertWarning(null);
      setCertPreview({ subject: cert.subject, notAfter: cert.notAfter, fingerprint, type: 'self-signed' });
      setShowGenerate(false);
    } catch {
      setCertError(tw.generateFailed);
    } finally {
      setGenerating(false);
    }
  };

  // ── Step 3: Enable ───────────────────────────────────────────────

  const handleEnable = async () => {
    setLoading(true);
    setEnableError(null);
    const res = await apiClient.post<EnableResponse>('/api/ghost/enable', {
      domain,
      tls_certificate: btoa(certPem),
      tls_private_key: btoa(keyPem),
    });
    setLoading(false);
    if (res.ok) {
      setStep('done');
    } else {
      setEnableError(
        (t.daemon_api_codes as Record<string, string>)[res.code ?? ''] ??
          t.settings.error.generic
      );
    }
  };

  // ── Validity options ─────────────────────────────────────────────

  const validityOptions = [
    { value: '90', label: tw.validity90d },
    { value: '180', label: tw.validity180d },
    { value: '365', label: tw.validity1y },
    { value: '730', label: tw.validity2y },
  ];

  const stepNum = step === 'domain' ? 1 : step === 'cert' ? 2 : 3;

  // ── Done ─────────────────────────────────────────────────────────

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
              <CheckmarkFilled
                size={64}
                className="totp-wizard__done-icon"
                data-testid="ghost-enable-done"
              />
              <p className="totp-wizard__done-text">{tw.doneDesc}</p>

              <Button
                kind="primary"
                renderIcon={ArrowLeft}
                onClick={() => void onEnabled()}
                className="totp-wizard__done-btn"
                data-testid="ghost-enable-view-status"
              >
                {tw.viewStatus}
              </Button>
            </div>
          </Column>
        </Grid>
      </div>
    );
  }

  // ── Wizard ────────────────────────────────────────────────────────

  return (
    <div className="totp-wizard">
      <Grid>
        <Column xlg={16} lg={16} md={8} sm={4}>
          {/* Progress */}
          <div className="totp-wizard__progress">
            <span className="totp-wizard__progress-text">
              {stepNum} / {totalSteps}
            </span>
          </div>

          {/* Step 1: Domain */}
          {step === 'domain' && (
            <div className="totp-wizard__question">
              <p className="totp-wizard__question-text">{tw.step1Desc}</p>
              <div className="totp-wizard__input">
                <TextInput
                  id="ghost-domain"
                  labelText={tw.domainLabel}
                  placeholder={tw.domainPlaceholder}
                  value={domain}
                  onChange={(e) => {
                    setDomain(e.target.value);
                    setDomainError(null);
                  }}
                  invalid={!!domainError}
                  invalidText={domainError ?? ''}
                  data-testid="ghost-enable-domain"
                  autoFocus
                />
              </div>
            </div>
          )}

          {/* Step 2: Certificate */}
          {step === 'cert' && (
            <div className="totp-wizard__question">
              <p className="totp-wizard__question-text">{tw.step2Desc}</p>

              {certError && (
                <InlineNotification
                  kind="error"
                  title={certError}
                  lowContrast
                  hideCloseButton
                  className="totp-wizard__error"
                />
              )}
              {certWarning && !certError && (
                <InlineNotification
                  kind="warning"
                  title={certWarning}
                  lowContrast
                  hideCloseButton
                  className="totp-wizard__error"
                />
              )}

              <div className="ghost-wizard__textarea">
                <TextArea
                  id="ghost-cert-pem"
                  labelText={tw.certLabel}
                  placeholder={tw.certPlaceholder}
                  value={certPem}
                  rows={6}
                  onChange={(e) => handleCertChange(e.target.value)}
                  data-testid="ghost-enable-cert"
                />
              </div>

              <div className="ghost-wizard__textarea">
                <TextArea
                  id="ghost-key-pem"
                  labelText={tw.keyLabel}
                  placeholder={tw.keyPlaceholder}
                  value={keyPem}
                  rows={6}
                  onChange={(e) => setKeyPem(e.target.value)}
                  data-testid="ghost-enable-key"
                />
              </div>

              {/* Cert preview */}
              {certPreview && (
                <div className="ghost-wizard__cert-preview">
                  <span>
                    {tw.certPreviewSubject}: <code>{certPreview.subject}</code>
                  </span>
                  <span>
                    {tw.certPreviewExpiry}: {certPreview.notAfter.toLocaleDateString()}
                  </span>
                  {certPreview.fingerprint && (
                    <span>
                      SHA-256: <code>{certPreview.fingerprint}</code>
                    </span>
                  )}
                </div>
              )}

              {/* Generate collapse */}
              <button
                type="button"
                className="ghost-wizard__generate-link"
                onClick={() => setShowGenerate(!showGenerate)}
                data-testid="ghost-enable-generate-toggle"
              >
                {tw.generateLink}
              </button>

              {showGenerate && (
                <div className="ghost-wizard__generate-form">
                  <div className="totp-wizard__input">
                    <Select
                      id="ghost-gen-validity"
                      labelText={tw.validityLabel}
                      value={genValidity}
                      onChange={(e) => setGenValidity(e.target.value)}
                      data-testid="ghost-gen-validity"
                    >
                      {validityOptions.map((o) => (
                        <SelectItem key={o.value} value={o.value} text={o.label} />
                      ))}
                    </Select>
                  </div>

                  <Button
                    kind="primary"
                    size="sm"
                    onClick={() => void handleGenerate()}
                    disabled={generating}
                    className="ghost-wizard__generate-btn"
                    data-testid="ghost-gen-submit"
                  >
                    {generating ? tw.generating : tw.generateBtn}
                  </Button>
                </div>
              )}
            </div>
          )}

          {/* Step 3: Confirm */}
          {step === 'confirm' && certPreview && (
            <div className="totp-wizard__question">
              <p className="totp-wizard__question-text">{tw.step3Desc}</p>

              {enableError && (
                <InlineNotification
                  kind="error"
                  title={enableError}
                  lowContrast
                  hideCloseButton
                  className="totp-wizard__error"
                />
              )}

              <dl className="ghost-wizard__summary">
                <div className="ghost-wizard__summary-row">
                  <dt>{tg.domain}</dt>
                  <dd>{domain}</dd>
                </div>
                <div className="ghost-wizard__summary-row">
                  <dt>{tw.certLabel}</dt>
                  <dd>
                    {certPreview.type === 'self-signed'
                      ? tw.certTypeSelfSigned
                      : tw.certTypeImported}
                  </dd>
                </div>
                <div className="ghost-wizard__summary-row">
                  <dt>{tw.certPreviewSubject}</dt>
                  <dd>
                    <code>{certPreview.subject}</code>
                  </dd>
                </div>
                <div className="ghost-wizard__summary-row">
                  <dt>{tw.certPreviewExpiry}</dt>
                  <dd>{certPreview.notAfter.toLocaleDateString()}</dd>
                </div>
              </dl>
            </div>
          )}

          {/* Navigation */}
          <div className="totp-wizard__navigation">
            {step === 'domain' && (
              <>
                <span />
                <Button
                  kind="primary"
                  onClick={handleDomainNext}
                  disabled={!domain.trim()}
                  className="totp-wizard__nav-btn"
                  data-testid="ghost-enable-domain-next"
                >
                  {tg.confirm}
                </Button>
              </>
            )}

            {step === 'cert' && (
              <>
                <Button
                  kind="secondary"
                  renderIcon={ArrowLeft}
                  onClick={() => setStep('domain')}
                  className="totp-wizard__nav-btn"
                >
                  {tg.goBack}
                </Button>
                <Button
                  kind="primary"
                  onClick={handleCertNext}
                  disabled={!certPem.trim() || !keyPem.trim()}
                  className="totp-wizard__nav-btn"
                  data-testid="ghost-enable-cert-next"
                >
                  {tg.confirm}
                </Button>
              </>
            )}

            {step === 'confirm' && (
              <>
                <Button
                  kind="secondary"
                  renderIcon={ArrowLeft}
                  onClick={() => {
                    setStep('cert');
                    setEnableError(null);
                  }}
                  className="totp-wizard__nav-btn"
                >
                  {tg.goBack}
                </Button>
                <Button
                  kind="primary"
                  onClick={() => void handleEnable()}
                  disabled={loading}
                  className="totp-wizard__nav-btn"
                  data-testid="ghost-enable-submit"
                >
                  {loading ? t.loadingSpinner.loading : tg.enable}
                </Button>
              </>
            )}
          </div>
        </Column>
      </Grid>
    </div>
  );
};

export default GhostEnableWizard;
