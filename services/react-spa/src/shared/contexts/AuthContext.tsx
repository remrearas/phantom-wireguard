import React, { createContext, useContext, useState, useCallback, useMemo, useEffect, ReactNode } from 'react';
import { apiClient } from '@shared/api/client';
import { useUser } from '@shared/contexts/UserContext';

interface LoginResponse {
  token: string;
  expires_in: number;
}

interface MFARequiredResponse {
  mfa_required: true;
  mfa_token: string;
  expires_in: number;
}

type LoginResult =
  | { status: 'ok' }
  | { status: 'mfa_required'; mfa_token: string; expires_in: number }
  | { status: 'error'; error: string };

interface AuthContextValue {
  token: string | null;
  isAuthenticated: boolean;
  initializing: boolean;
  login: (username: string, password: string) => Promise<LoginResult>;
  verifyTotp: (mfaToken: string, code: string) => Promise<LoginResult>;
  verifyBackupCode: (mfaToken: string, code: string) => Promise<LoginResult>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'));
  // Snapshot: was there a token on mount? SWR will be loading the initial fetch.
  const [hadTokenOnMount] = useState(() => !!localStorage.getItem('token'));
  const { isLoading: userLoading, mutateUser, clearUser } = useUser();

  // initializing = token existed on mount AND SWR hasn't resolved yet
  const initializing = hadTokenOnMount && userLoading;

  const clearSession = useCallback(() => {
    localStorage.removeItem('token');
    sessionStorage.setItem('auth_warning', 'session_expired');
    setToken(null);
    clearUser();
  }, [clearUser]);

  useEffect(() => {
    apiClient.setSessionExpiredHandler(clearSession);
  }, [clearSession]);

  // Sync token state with localStorage on cross-tab storage events and same-tab removals
  useEffect(() => {
    const syncToken = () => {
      const stored = localStorage.getItem('token');
      if (!stored && token) {
        setToken(null);
        clearUser();
      }
    };
    window.addEventListener('storage', syncToken);
    window.addEventListener('popstate', syncToken);
    const originalPushState = history.pushState.bind(history);
    history.pushState = (...args) => {
      originalPushState(...args);
      syncToken();
    };
    return () => {
      window.removeEventListener('storage', syncToken);
      window.removeEventListener('popstate', syncToken);
      history.pushState = originalPushState;
    };
  }, [token, clearUser]);

  const storeToken = useCallback(async (newToken: string) => {
    localStorage.setItem('token', newToken);
    setToken(newToken);
    await mutateUser();
  }, [mutateUser]);

  const login = useCallback(
    async (username: string, password: string): Promise<LoginResult> => {
      const res = await apiClient.post<LoginResponse | MFARequiredResponse>('/auth/login', {
        username,
        password,
      });

      if (!res.ok) {
        return { status: 'error', error: res.error_code ?? '' };
      }

      if ('mfa_required' in res.data) {
        return { status: 'mfa_required', mfa_token: res.data.mfa_token, expires_in: res.data.expires_in };
      }

      await storeToken(res.data.token);
      return { status: 'ok' };
    },
    [storeToken]
  );

  const verifyTotp = useCallback(
    async (mfaToken: string, code: string): Promise<LoginResult> => {
      const res = await apiClient.post<LoginResponse>('/auth/mfa/verify', {
        mfa_token: mfaToken,
        code,
      });

      if (!res.ok) {
        return { status: 'error', error: res.error_code ?? '' };
      }

      await storeToken(res.data.token);
      return { status: 'ok' };
    },
    [storeToken]
  );

  const verifyBackupCode = useCallback(
    async (mfaToken: string, code: string): Promise<LoginResult> => {
      const res = await apiClient.post<LoginResponse>('/auth/totp/backup', {
        mfa_token: mfaToken,
        code,
      });

      if (!res.ok) {
        return { status: 'error', error: res.error_code ?? '' };
      }

      await storeToken(res.data.token);
      return { status: 'ok' };
    },
    [storeToken]
  );

  const logout = useCallback(async () => {
    await apiClient.post('/auth/logout');
    localStorage.removeItem('token');
    setToken(null);
    clearUser();
  }, [clearUser]);

  const value = useMemo(
    () => ({
      token,
      isAuthenticated: !!token,
      initializing,
      login,
      verifyTotp,
      verifyBackupCode,
      logout,
    }),
    [token, initializing, login, verifyTotp, verifyBackupCode, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextValue => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
