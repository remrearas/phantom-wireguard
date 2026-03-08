import React from 'react';
import { Outlet } from 'react-router-dom';
import ProtectedHeader from '@shared/components/ui/ProtectedHeader';
import './styles/ProtectedLayout.scss';

const ProtectedLayout: React.FC = () => {
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
