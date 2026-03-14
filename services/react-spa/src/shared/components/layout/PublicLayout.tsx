import React from 'react';
import { Content } from '@carbon/react';
import { Outlet } from 'react-router-dom';
import PublicHeader from '@shared/components/ui/PublicHeader';
import Footer from '@shared/components/layout/Footer';
import './styles/PublicLayout.scss';

const PublicLayout: React.FC = () => {
  return (
    <>
      <PublicHeader />
      <Content id="main-content" className="public-content">
        <Outlet />
      </Content>
      <Footer />
    </>
  );
};

export default PublicLayout;
