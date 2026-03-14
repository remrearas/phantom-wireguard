import React, { useEffect } from 'react';
import { Content } from '@carbon/react';
import { Outlet, useLocation } from 'react-router-dom';
import ProtectedHeader from '@shared/components/ui/ProtectedHeader';
import Footer from '@shared/components/layout/Footer';
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
      <Content id="main-content" className="protected-content">
        <Outlet />
      </Content>
      <Footer />
    </>
  );
};

export default ProtectedLayout;
