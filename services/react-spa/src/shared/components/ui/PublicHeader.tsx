import React from 'react';
import {
  Header,
  HeaderContainer,
  HeaderName,
  HeaderGlobalBar,
  HeaderGlobalAction,
  SkipToContent,
} from '@carbon/react';
import { useLocale, useTheme } from '@shared/hooks';
import { translate } from '@shared/translations';
import FlagIcon from './FlagIcon';
import { Asleep, Light, RotateClockwise } from '@carbon/icons-react';
import './styles/ThemeSwitcher.scss';

interface RenderProps {
  isSideNavExpanded: boolean;
  onClickSideNavExpand: () => void;
}

const PublicHeader: React.FC = () => {
  const { locale, changeLocale } = useLocale();
  const { theme, toggleTheme, isThemeTransitioning } = useTheme();
  const t = translate(locale);

  return (
    <HeaderContainer
      render={({ isSideNavExpanded: _s, onClickSideNavExpand: _e }: RenderProps) => (
        <Header aria-label={t.header.appName}>
          <SkipToContent href="#main-content" />
          <HeaderName href="/login" prefix="">
            Phantom-WG
          </HeaderName>
          <HeaderGlobalBar>
            <HeaderGlobalAction
              aria-label={theme === 'white' ? t.header.darkMode : t.header.lightMode}
              onClick={toggleTheme}
              className={`theme-switcher${isThemeTransitioning ? ' theme-transitioning' : ''}`}
              tooltipAlignment="end"
              data-testid="header-theme-toggle"
            >
              {isThemeTransitioning ? (
                <RotateClockwise size={20} className="spinner-icon" />
              ) : theme === 'white' ? (
                <Asleep size={20} />
              ) : (
                <Light size={20} />
              )}
            </HeaderGlobalAction>
            <HeaderGlobalAction
              aria-label={t.language.switchTo}
              onClick={() => changeLocale(locale === 'tr' ? 'en' : 'tr')}
              tooltipAlignment="end"
            >
              <FlagIcon locale={locale === 'tr' ? 'en' : 'tr'} size={20} />
            </HeaderGlobalAction>
          </HeaderGlobalBar>
        </Header>
      )}
    />
  );
};

export default PublicHeader;
