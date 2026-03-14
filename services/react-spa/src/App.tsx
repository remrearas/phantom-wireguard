import React from 'react';
import { Theme } from '@carbon/react';
import { LocaleProvider, ThemeProvider, useTheme } from '@shared/hooks';
import { UserProvider } from '@shared/contexts/UserContext';
import { AuthProvider } from '@shared/contexts/AuthContext';
import AppRouter from './router';

const AppContent: React.FC = () => {
  const { theme } = useTheme();

  return (
    <Theme theme={theme}>
      <div className="app">
        <UserProvider>
          <AuthProvider>
            <AppRouter />
          </AuthProvider>
        </UserProvider>
      </div>
    </Theme>
  );
};

const App: React.FC = () => {
  return (
    <LocaleProvider>
      <ThemeProvider>
        <AppContent />
      </ThemeProvider>
    </LocaleProvider>
  );
};

export default App;