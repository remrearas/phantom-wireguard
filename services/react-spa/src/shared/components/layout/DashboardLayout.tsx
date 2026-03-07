import React from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  Header,
  HeaderContainer,
  HeaderName,
  HeaderMenuButton,
  HeaderNavigation,
  HeaderMenu,
  HeaderMenuItem,
  HeaderGlobalBar,
  HeaderGlobalAction,
  SkipToContent,
  SideNav,
  SideNavItems,
  SideNavMenu,
  SideNavMenuItem,
  SideNavLink,
} from '@carbon/react';
import { Logout } from '@carbon/icons-react';
import { useLocale } from '@shared/hooks';
import { useAuth } from '@shared/contexts/AuthContext';
import { useUser } from '@shared/contexts/UserContext';
import { translate } from '@shared/translations';
import FlagIcon from '@shared/components/ui/FlagIcon';
import './styles/DashboardLayout.scss';

interface RenderProps {
  isSideNavExpanded: boolean;
  onClickSideNavExpand: () => void;
}

const DashboardLayout: React.FC = () => {
  const { locale, changeLocale } = useLocale();
  const { logout } = useAuth();
  const { user } = useUser();
  const navigate = useNavigate();
  const location = useLocation();
  const t = translate(locale);

  const isSuperadmin = user?.role === 'superadmin';

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleLocaleToggle = () => {
    changeLocale(locale === 'tr' ? 'en' : 'tr');
  };

  const isActive = (href: string) =>
    location.pathname === href || (href !== '/' && location.pathname.startsWith(href));

  const userOpsActive = isActive('/totp') || isActive('/password-change');
  const usersActive = isActive('/users');

  const nav = (e: React.MouseEvent, href: string, closeSideNav?: () => void) => {
    e.preventDefault();
    navigate(href);
    closeSideNav?.();
  };

  return (
    <HeaderContainer
      render={({ isSideNavExpanded, onClickSideNavExpand }: RenderProps) => (
        <>
          <Header aria-label={t.header.appName}>
            <SkipToContent />
            <HeaderMenuButton
              aria-label={isSideNavExpanded ? 'Close menu' : 'Open menu'}
              onClick={onClickSideNavExpand}
              isActive={isSideNavExpanded}
            />
            <HeaderName href="/" prefix="" onClick={(e: React.MouseEvent) => nav(e, '/')}>
              {t.header.appName}
            </HeaderName>

            {/* Desktop navigation */}
            <HeaderNavigation aria-label={t.header.appName}>
              <HeaderMenuItem href="/" isCurrentPage={isActive('/')}
                onClick={(e: React.MouseEvent) => nav(e, '/')}>
                {t.nav.dashboard}
              </HeaderMenuItem>
              <HeaderMenu aria-label={t.nav.userOps} menuLinkName={t.nav.userOps}
                isCurrentPage={userOpsActive || usersActive}>
                <HeaderMenuItem href="/password-change" isCurrentPage={isActive('/password-change')}
                  onClick={(e: React.MouseEvent) => nav(e, '/password-change')}>
                  {t.nav.passwordChange}
                </HeaderMenuItem>
                <HeaderMenuItem href="/totp" isCurrentPage={isActive('/totp')}
                  onClick={(e: React.MouseEvent) => nav(e, '/totp')}>
                  {t.nav.totp}
                </HeaderMenuItem>
                {isSuperadmin && (
                  <HeaderMenuItem href="/users" isCurrentPage={usersActive}
                    onClick={(e: React.MouseEvent) => nav(e, '/users')}>
                    {t.nav.users}
                  </HeaderMenuItem>
                )}
              </HeaderMenu>
            </HeaderNavigation>

            <HeaderGlobalBar>
              <HeaderGlobalAction
                aria-label={t.language.switchTo}
                onClick={handleLocaleToggle}
                tooltipAlignment="end"
              >
                <FlagIcon locale={locale === 'tr' ? 'en' : 'tr'} size={20} />
              </HeaderGlobalAction>
              <HeaderGlobalAction
                aria-label={t.header.logout}
                onClick={handleLogout}
                tooltipAlignment="end"
              >
                <Logout size={20} />
              </HeaderGlobalAction>
            </HeaderGlobalBar>

            {/* Mobile overlay navigation */}
            <SideNav
              aria-label="Navigation"
              expanded={isSideNavExpanded}
              isPersistent={false}
              onOverlayClick={onClickSideNavExpand}
            >
              <SideNavItems>
                <SideNavLink href="/" isActive={isActive('/')}
                  onClick={(e: React.MouseEvent) => nav(e, '/', onClickSideNavExpand)}>
                  {t.nav.dashboard}
                </SideNavLink>
                <SideNavMenu title={t.nav.userOps} isActive={userOpsActive || usersActive}>
                  <SideNavMenuItem href="/password-change" isActive={isActive('/password-change')}
                    onClick={(e: React.MouseEvent) => nav(e, '/password-change', onClickSideNavExpand)}>
                    {t.nav.passwordChange}
                  </SideNavMenuItem>
                  <SideNavMenuItem href="/totp" isActive={isActive('/totp')}
                    onClick={(e: React.MouseEvent) => nav(e, '/totp', onClickSideNavExpand)}>
                    {t.nav.totp}
                  </SideNavMenuItem>
                  {isSuperadmin && (
                    <SideNavMenuItem href="/users" isActive={usersActive}
                      onClick={(e: React.MouseEvent) => nav(e, '/users', onClickSideNavExpand)}>
                      {t.nav.users}
                    </SideNavMenuItem>
                  )}
                </SideNavMenu>
              </SideNavItems>
            </SideNav>
          </Header>

          <main id="main-content" className="app-content">
            <div className="app-content__box">
              <Outlet />
            </div>
          </main>
        </>
      )}
    />
  );
};

export default DashboardLayout;
