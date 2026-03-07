import React, { createContext, useContext, useState, useCallback, useMemo, useEffect, ReactNode } from 'react';
import { apiClient, type ApiResponse } from '@shared/api/client';
import { useUser, type UserInfo } from '@shared/contexts/UserContext';

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
  const [initializing, setInitializing] = useState(() => !!localStorage.getItem('token'));
  const { setUser, clearUser } = useUser();

  const clearSession = useCallback(() => {
    localStorage.removeItem('token');
    sessionStorage.setItem('auth_warning', 'session_expired');
    setToken(null);
    clearUser();
  }, [clearUser]);

  useEffect(() => {
    apiClient.setSessionExpiredHandler(clearSession);
  }, [clearSession]);

  const checkSession = useCallback(async () => {
    if (!localStorage.getItem('token')) return;
    const res = (await apiClient.get('/auth/me')) as ApiResponse<UserInfo>;
    if (res.ok) {
      setUser(res.data);
    }
  }, [setUser]);

  // Initial token validation
  useEffect(() => {
    if (!token) {
      setInitializing(false);
      return;
    }

    let cancelled = false;

    const validate = async () => {
      const res = (await apiClient.get('/auth/me')) as ApiResponse<UserInfo>;
      if (cancelled) return;

      if (res.ok) {
        setUser(res.data);
      } else {
        clearSession();
      }
      setInitializing(false);
    };

    void validate();
    return () => { cancelled = true; };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Visibility change — check session when tab becomes visible
  useEffect(() => {
    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        checkSession();
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, [checkSession]);

  // Sync token state with localStorage on route changes and same-tab removals
  useEffect(() => {
    const syncToken = () => {
      const stored = localStorage.getItem('token');
      if (!stored && token) {
        setToken(null);
        clearUser();
      }
    };
    // Listen for cross-tab storage events
    window.addEventListener('storage', syncToken);
    // Listen for same-tab pushState/popState (route changes)
    window.addEventListener('popstate', syncToken);
    // Patch pushState to detect SPA navigation
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

  const storeToken = useCallback((newToken: string) => {
    localStorage.setItem('token', newToken);
    setToken(newToken);
  }, []);

  const login = useCallback(
    async (username: string, password: string): Promise<LoginResult> => {
      const res = (await apiClient.post('/auth/login', {
        username,
        password,
      })) as ApiResponse<LoginResponse | MFARequiredResponse>;

      if (!res.ok) {
        return { status: 'error', error: res.error };
      }

      if ('mfa_required' in res.data) {
        return { status: 'mfa_required', mfa_token: res.data.mfa_token, expires_in: res.data.expires_in };
      }

      storeToken(res.data.token);
      return { status: 'ok' };
    },
    [storeToken]
  );

  const verifyTotp = useCallback(
    async (mfaToken: string, code: string): Promise<LoginResult> => {
      const res = (await apiClient.post('/auth/mfa/verify', {
        mfa_token: mfaToken,
        code,
      })) as ApiResponse<LoginResponse>;

      if (!res.ok) {
        return { status: 'error', error: res.error };
      }

      storeToken(res.data.token);
      return { status: 'ok' };
    },
    [storeToken]
  );

  const verifyBackupCode = useCallback(
    async (mfaToken: string, code: string): Promise<LoginResult> => {
      const res = (await apiClient.post('/auth/totp/backup', {
        mfa_token: mfaToken,
        code,
      })) as ApiResponse<LoginResponse>;

      if (!res.ok) {
        return { status: 'error', error: res.error };
      }

      storeToken(res.data.token);
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
