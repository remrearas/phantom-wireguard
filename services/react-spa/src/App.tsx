import React from 'react';
import { Theme } from '@carbon/react';
import { LocaleProvider, THEME } from '@shared/hooks';
import { ThemeProvider } from '@shared/hooks';
import { UserProvider } from '@shared/contexts/UserContext';
import { AuthProvider } from '@shared/contexts/AuthContext';
import AppRouter from './router';

const App: React.FC = () => {
  return (
    <LocaleProvider>
      <ThemeProvider>
        <Theme theme={THEME}>
          <UserProvider>
            <AuthProvider>
              <AppRouter />
            </AuthProvider>
          </UserProvider>
        </Theme>
      </ThemeProvider>
    </LocaleProvider>
  );
};

export default App;
