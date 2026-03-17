import React, { lazy, Suspense } from 'react';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';

import LandingLayout from '@shared/components/layout/LandingLayout';
import DocumentationLayout from '@shared/components/layout/DocumentationLayout';
import ErrorPage from '@shared/pages/error/ErrorPage';
import LoadingSpinner from '@shared/components/ui/LoadingSpinner';

// ── Home (Landing) ────────────────────────────────────────────────
const HomePage = lazy(() => import('@pages/home/pages/index/LandingPage'));

// ── Documentation pages ───────────────────────────────────────────
const DocsHomePage      = lazy(() => import('@pages/docs/home/pages/index/HomePage'));
const ApiPage           = lazy(() => import('@pages/docs/api/pages/index/ApiPage'));
const ArchitecturePage  = lazy(() => import('@pages/docs/architecture/pages/index/ArchitecturePage'));
const TeraziPage        = lazy(() => import('@pages/docs/architecture/pages/terazi/pages/index/TeraziPage'));
const MultihopPage      = lazy(() => import('@pages/docs/architecture/pages/multihop/pages/index/MultihopPage'));

// ── Router ────────────────────────────────────────────────────────
const router = createBrowserRouter([
  // Home — www.phantom.tc/
  {
    path: '/',
    element: <LandingLayout />,
    errorElement: <ErrorPage />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
    ],
  },
  // Documentation — www.phantom.tc/docs/*
  {
    path: '/docs',
    element: <DocumentationLayout />,
    errorElement: <ErrorPage />,
    children: [
      {
        index: true,
        element: <DocsHomePage />,
      },
      {
        path: 'api',
        element: <ApiPage />,
      },
      {
        path: 'architecture',
        element: <ArchitecturePage />,
      },
      {
        path: 'architecture/terazi',
        element: <TeraziPage />,
      },
      {
        path: 'architecture/multihop',
        element: <MultihopPage />,
      },
    ],
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
