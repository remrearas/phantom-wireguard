import React from 'react';
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom';
import { useAuth } from '@shared/contexts/AuthContext';
import LoadingSpinner from '@shared/components/ui/LoadingSpinner';
import ProtectedLayout from '@shared/components/layout/ProtectedLayout';
import PublicLayout from '@shared/components/layout/PublicLayout';
import ErrorPage from '@shared/pages/error/ErrorPage';
import LoginPage from '@pages/login/LoginPage';
import DashboardPage from '@pages/dashboard/pages/index/DashboardPage';
import TotpPage from '@pages/totp/pages/index/TotpPage';
import TotpEnablePage from '@pages/totp/pages/enable/TotpEnablePage';
import TotpDisablePage from '@pages/totp/pages/disable/TotpDisablePage';
import PasswordChangePage from '@pages/password-change/pages/index/PasswordChangePage';
import UsersPage from '@pages/users/pages/index/UsersPage';
import AuditPage from '@pages/audit/pages/index/AuditPage';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, initializing } = useAuth();

  if (initializing) {
    return <LoadingSpinner fullscreen />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

const PublicRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, initializing } = useAuth();

  if (initializing) {
    return <LoadingSpinner fullscreen />;
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
};

const router = createBrowserRouter([
  {
    element: (
      <PublicRoute>
        <PublicLayout />
      </PublicRoute>
    ),
    children: [
      { path: '/login', element: <LoginPage /> },
    ],
  },
  {
    element: (
      <ProtectedRoute>
        <ProtectedLayout />
      </ProtectedRoute>
    ),
    children: [
      { path: '/', element: <DashboardPage /> },
      { path: '/totp', element: <TotpPage /> },
      { path: '/totp/enable', element: <TotpEnablePage /> },
      { path: '/totp/disable', element: <TotpDisablePage /> },
      { path: '/password-change', element: <PasswordChangePage /> },
      { path: '/users', element: <UsersPage /> },
      { path: '/audit', element: <AuditPage /> },
    ],
  },
  {
    path: '*',
    element: <ErrorPage />,
  },
]);

const AppRouter: React.FC = () => {
  return <RouterProvider router={router} />;
};

export default AppRouter;
