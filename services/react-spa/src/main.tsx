import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './shared/styles/carbon-config.scss';
import App from './App';
import { printConsoleBranding } from '@shared/utils/console-branding';

printConsoleBranding();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
