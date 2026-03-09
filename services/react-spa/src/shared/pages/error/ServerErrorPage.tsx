import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@carbon/react';
import { ArrowRight, WarningAlt, Checkmark } from '@carbon/icons-react';
import { useLocale } from '@shared/hooks';
import { translate } from '@shared/translations';
import DinoGame from '@shared/components/games/DinoGame';
import './styles/server-error.scss';

// ── Constants ─────────────────────────────────────────────────────

const RETRY_INTERVAL = 15;
const RING_RADIUS = 54;
const CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;

type Phase = 'waiting' | 'checking' | 'restored';

// ── ErrorState — countdown ring + health check + dino game ──────

interface ErrorStateProps {
  phase: Phase;
  countdown: number;
  attempts: number;
  t: ReturnType<typeof translate>;
}

const ErrorState: React.FC<ErrorStateProps> = ({ phase, countdown, attempts, t }) => {
  const progress = countdown / RETRY_INTERVAL;
  const offset = CIRCUMFERENCE * (1 - progress);

  return (
    <>
      <div className="server-error__icon">
        <WarningAlt size={64} />
      </div>

      <h1 className="server-error__code">{t.errorPages.serverError.code}</h1>
      <h2 className="server-error__title">{t.errorPages.serverError.title}</h2>
      <p className="server-error__description">{t.errorPages.serverError.description}</p>

      {/* Timer ring */}
      <div className="server-error__timer">
        <div
          className={`server-error__ring-wrap${phase === 'checking' ? ' server-error__ring-wrap--spin' : ''}`}
        >
          <svg viewBox="0 0 120 120" className="server-error__ring">
            <circle cx="60" cy="60" r={RING_RADIUS} className="server-error__ring-bg" />
            {phase === 'waiting' && (
              <circle
                cx="60"
                cy="60"
                r={RING_RADIUS}
                className="server-error__ring-progress"
                strokeDasharray={CIRCUMFERENCE}
                strokeDashoffset={offset}
                transform="rotate(-90 60 60)"
              />
            )}
          </svg>
          <span className="server-error__ring-text">
            {phase === 'checking' ? '...' : countdown}
          </span>
        </div>
        <p className="server-error__timer-label">
          {phase === 'checking'
            ? t.errorPages.serverError.checking
            : `${t.errorPages.serverError.retryIn} ${countdown}${t.errorPages.serverError.secondsShort}`}
        </p>
        {attempts > 0 && (
          <p className="server-error__attempts">
            {t.errorPages.serverError.attempt}: {attempts}
          </p>
        )}
      </div>

      {/* DinoGame */}
      <div className="server-error__game">
        <DinoGame.Lazy theme="error" />
      </div>

      {/* Disabled button */}
      <div className="server-error__actions">
        <Button size="lg" disabled>
          {t.errorPages.serverError.goToDashboard}
        </Button>
      </div>
    </>
  );
};

// ── RestoredState — success icon + enabled button ───────────────

interface RestoredStateProps {
  t: ReturnType<typeof translate>;
  onNavigate: () => void;
}

const RestoredState: React.FC<RestoredStateProps> = ({ t, onNavigate }) => (
  <>
    <div className="server-error__icon server-error__icon--success">
      <Checkmark size={64} />
    </div>

    <h1 className="server-error__code">200</h1>
    <h2 className="server-error__title">{t.errorPages.serverError.restored}</h2>

    <div className="server-error__actions">
      <Button renderIcon={ArrowRight} onClick={onNavigate} size="lg">
        {t.errorPages.serverError.goToDashboard}
      </Button>
    </div>
  </>
);

// ── ServerErrorPage — orchestrator ──────────────────────────────

const ServerErrorPage: React.FC = () => {
  const navigate = useNavigate();
  const { locale } = useLocale();
  const t = translate(locale);

  const [countdown, setCountdown] = useState(RETRY_INTERVAL);
  const [phase, setPhase] = useState<Phase>('waiting');
  const [attempts, setAttempts] = useState(0);

  const checkHealth = useCallback(async () => {
    setPhase('checking');
    try {
      // Raw fetch — bypass apiClient to avoid redirect loop
      const res = await fetch('/auth/me');
      if (res.status < 500) {
        setPhase('restored');
        return;
      }
    } catch {
      // Network error — server still down
    }
    setAttempts((a) => a + 1);
    setCountdown(RETRY_INTERVAL);
    setPhase('waiting');
  }, []);

  useEffect(() => {
    if (phase !== 'waiting') return;
    if (countdown <= 0) {
      void checkHealth();
      return;
    }
    const timer = setTimeout(() => setCountdown((c) => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [countdown, phase, checkHealth]);

  return (
    <div className="server-error">
      <div className="server-error__content">
        {phase === 'restored' ? (
          <RestoredState t={t} onNavigate={() => navigate('/')} />
        ) : (
          <ErrorState phase={phase} countdown={countdown} attempts={attempts} t={t} />
        )}
      </div>
    </div>
  );
};

export default ServerErrorPage;
