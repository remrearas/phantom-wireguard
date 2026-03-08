import React from 'react';
import { Outlet } from 'react-router-dom';
import PublicHeader from '@shared/components/ui/PublicHeader';
import './styles/PublicLayout.scss';

const PublicLayout: React.FC = () => {
  return (
    <>
      <PublicHeader />
      <main id="main-content" className="public-content">
        <Outlet />
      </main>
    </>
  );
};

export default PublicLayout;
