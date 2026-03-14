import React, { useEffect, useState } from 'react';
import SwaggerUI from 'swagger-ui-react';
import 'swagger-ui-react/swagger-ui.css';
import './styles/ApiDocPage.scss';

const ApiDocPage: React.FC = () => {
  const [spec, setSpec] = useState<object | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    fetch('/api/core/hello/openapi', {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((res) => res.json())
      .then((data) => setSpec(data))
      .catch(() => {});
  }, []);

  if (!spec) return null;

  return (
    <div className="api-doc">
      <SwaggerUI
        spec={spec}
        requestInterceptor={(req) => {
          const token = localStorage.getItem('token');
          if (token) req.headers.Authorization = `Bearer ${token}`;
          return req;
        }}
        defaultModelsExpandDepth={-1}
        docExpansion="list"
        tryItOutEnabled
      />
    </div>
  );
};

export default ApiDocPage;
