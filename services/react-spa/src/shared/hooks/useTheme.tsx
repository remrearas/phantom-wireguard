import React, { createContext, useContext, useEffect, ReactNode } from 'react';

export type AppTheme = 'g100';

interface ThemeContextValue {
  theme: AppTheme;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

export const THEME: AppTheme = 'g100';

export const ThemeProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  useEffect(() => {
    document.documentElement.setAttribute('data-carbon-theme', THEME);
  }, []);

  return <ThemeContext.Provider value={{ theme: THEME }}>{children}</ThemeContext.Provider>;
};

export const useTheme = (): ThemeContextValue => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
};
