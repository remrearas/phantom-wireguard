import React, { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import ProtectedHeader from '@shared/components/ui/ProtectedHeader';
import { useUser } from '@shared/contexts/UserContext';
import './styles/ProtectedLayout.scss';

const ProtectedLayout: React.FC = () => {
  const { mutateUser } = useUser();
  const { pathname } = useLocation();

  useEffect(() => {
    void mutateUser();
  }, [pathname]);

  return (
    <>
      <ProtectedHeader />
      <main id="main-content" className="app-content">
        <div className="app-content__box">
          <Outlet />
        </div>
      </main>
    </>
  );
};

export default ProtectedLayout;
