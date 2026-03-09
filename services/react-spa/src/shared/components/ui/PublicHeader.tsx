import React from 'react';
import {
  Header,
  HeaderContainer,
  HeaderName,
  HeaderGlobalBar,
  HeaderGlobalAction,
  SkipToContent,
} from '@carbon/react';
import { useLocale } from '@shared/hooks';
import { translate } from '@shared/translations';
import FlagIcon from './FlagIcon';
import { GatewayVpn } from '@carbon/icons-react';

interface RenderProps {
  isSideNavExpanded: boolean;
  onClickSideNavExpand: () => void;
}

const PublicHeader: React.FC = () => {
  const { locale, changeLocale } = useLocale();
  const t = translate(locale);

  return (
    <HeaderContainer
      render={({ isSideNavExpanded: _s, onClickSideNavExpand: _e }: RenderProps) => (
        <Header aria-label={t.header.appName}>
          <SkipToContent href="#main-content" />
          <HeaderName href="/login" prefix="">
            <GatewayVpn size={20} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} />
            Phantom-WG
          </HeaderName>
          <HeaderGlobalBar>
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
