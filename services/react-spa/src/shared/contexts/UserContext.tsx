import React, { createContext, useContext, useState, useCallback, useMemo, ReactNode } from 'react';
import { apiClient, type ApiResponse } from '@shared/api/client';

export interface UserInfo {
  id: string;
  username: string;
  role: string;
  totp_enabled: boolean;
  created_at: string;
  updated_at: string;
}

interface UserContextValue {
  user: UserInfo | null;
  isSuperadmin: boolean;
  fetchUser: () => Promise<void>;
  clearUser: () => void;
  setUser: (user: UserInfo) => void;
}

const UserContext = createContext<UserContextValue | undefined>(undefined);

export const UserProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserInfo | null>(null);

  const fetchUser = useCallback(async () => {
    const res = (await apiClient.get('/auth/me')) as ApiResponse<UserInfo>;
    if (res.ok) {
      setUser(res.data);
    }
  }, []);

  const clearUser = useCallback(() => {
    setUser(null);
  }, []);

  const isSuperadmin = user?.role === 'superadmin';

  const value = useMemo(
    () => ({ user, isSuperadmin, fetchUser, clearUser, setUser }),
    [user, isSuperadmin, fetchUser, clearUser]
  );

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
};

export const useUser = (): UserContextValue => {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error('useUser must be used within UserProvider');
  }
  return context;
};
