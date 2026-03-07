import React from 'react';
import { useRouteError, isRouteErrorResponse } from 'react-router-dom';
import NotFoundPage from './NotFoundPage';

const ErrorPage: React.FC = () => {
  const error = useRouteError();

  if (isRouteErrorResponse(error) && error.status === 404) {
    return <NotFoundPage />;
  }

  return <NotFoundPage />;
};

export default ErrorPage;
