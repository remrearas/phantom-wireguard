import React, { ReactNode } from 'react';
import { Theme } from '@carbon/react';
import { LocaleProvider } from '@shared/hooks';
import { ThemeProvider, useTheme } from '@shared/hooks';
import { UserProvider } from '@shared/contexts/UserContext';
import { AuthProvider } from '@shared/contexts/AuthContext';
import AppRouter from './router';

const ThemeWrapper: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { theme } = useTheme();
  return <Theme theme={theme}>{children}</Theme>;
};

const App: React.FC = () => {
  return (
    <LocaleProvider>
      <ThemeProvider>
        <ThemeWrapper>
          <UserProvider>
            <AuthProvider>
              <AppRouter />
            </AuthProvider>
          </UserProvider>
        </ThemeWrapper>
      </ThemeProvider>
    </LocaleProvider>
  );
};

export default App;
