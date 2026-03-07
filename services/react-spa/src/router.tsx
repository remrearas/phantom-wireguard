import React, { lazy, Suspense } from 'react';
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom';
import { useAuth } from '@shared/contexts/AuthContext';
import LoadingSpinner from '@shared/components/ui/LoadingSpinner';
import DashboardLayout from '@shared/components/layout/DashboardLayout';
import ErrorPage from '@shared/pages/error/ErrorPage';

const LoginPage = lazy(() => import('@pages/login/LoginPage'));
const DashboardPage = lazy(() => import('@pages/dashboard/pages/index/DashboardPage'));
const TotpPage = lazy(() => import('@pages/totp/pages/index/TotpPage'));
const TotpEnablePage = lazy(() => import('@pages/totp/pages/enable/TotpEnablePage'));
const TotpDisablePage = lazy(() => import('@pages/totp/pages/disable/TotpDisablePage'));
const PasswordChangePage = lazy(() => import('@pages/password-change/pages/index/PasswordChangePage'));
const UsersPage = lazy(() => import('@pages/users/pages/index/UsersPage'));

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
    path: '/login',
    element: (
      <PublicRoute>
        <LoginPage />
      </PublicRoute>
    ),
  },
  {
    element: (
      <ProtectedRoute>
        <DashboardLayout />
      </ProtectedRoute>
    ),
    children: [
      { path: '/', element: <DashboardPage /> },
      { path: '/totp', element: <TotpPage /> },
      { path: '/totp/enable', element: <TotpEnablePage /> },
      { path: '/totp/disable', element: <TotpDisablePage /> },
      { path: '/password-change', element: <PasswordChangePage /> },
      { path: '/users', element: <UsersPage /> },
    ],
  },
  {
    path: '*',
    element: <ErrorPage />,
  },
]);

const AppRouter: React.FC = () => {
  return (
    <Suspense fallback={<LoadingSpinner fullscreen />}>
      <RouterProvider router={router} />
    </Suspense>
  );
};

export default AppRouter;
