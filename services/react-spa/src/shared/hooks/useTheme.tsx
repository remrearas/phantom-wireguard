import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useMemo,
  useEffect,
  ReactNode,
} from 'react';

export type AppTheme = 'white' | 'g100';

interface ThemeContextValue {
  theme: AppTheme;
  toggleTheme: () => void;
  isThemeTransitioning: boolean;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

const VALID_THEMES: AppTheme[] = ['white', 'g100'];
const DEFAULT_THEME: AppTheme = 'white';

export const ThemeProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [theme, setTheme] = useState<AppTheme>(() => {
    try {
      const cookieTheme = document.cookie.match(/preferred_theme=(white|g100)/)?.[1];
      if (cookieTheme && VALID_THEMES.includes(cookieTheme as AppTheme)) {
        return cookieTheme as AppTheme;
      }

      const htmlTheme = document.documentElement.getAttribute('data-carbon-theme');
      if (htmlTheme && VALID_THEMES.includes(htmlTheme as AppTheme)) {
        return htmlTheme as AppTheme;
      }

      return DEFAULT_THEME;
    } catch {
      return DEFAULT_THEME;
    }
  });

  const [isThemeTransitioning, setIsThemeTransitioning] = useState(false);

  const applyTheme = useCallback((newTheme: AppTheme) => {
    setTheme(newTheme);
    try {
      document.cookie = `preferred_theme=${newTheme}; path=/; max-age=31536000; SameSite=Lax`;
      document.documentElement.setAttribute('data-carbon-theme', newTheme);
    } catch {
      // Silent fail
    }
  }, []);

  const toggleTheme = useCallback(() => {
    if (isThemeTransitioning) return;

    setIsThemeTransitioning(true);
    applyTheme(theme === 'white' ? 'g100' : 'white');

    setTimeout(() => {
      setIsThemeTransitioning(false);
    }, 800);
  }, [theme, isThemeTransitioning, applyTheme]);

  useEffect(() => {
    document.documentElement.setAttribute('data-carbon-theme', theme);
  }, [theme]);

  const value = useMemo(
    () => ({ theme, toggleTheme, isThemeTransitioning }),
    [theme, toggleTheme, isThemeTransitioning]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};

export const useTheme = (): ThemeContextValue => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
};
