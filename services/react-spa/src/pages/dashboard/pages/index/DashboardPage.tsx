import React from 'react';
import { useLocale } from '@shared/hooks';
import MDXPageRenderer from '@shared/components/content/MDXPageRenderer';
import ContentTr from './index.mdx';
import ContentEn from './index.en.mdx';

const CONTENT_MAP: Record<string, React.ComponentType> = {
  tr: ContentTr,
  en: ContentEn,
};

const DashboardPage: React.FC = () => {
  const { locale } = useLocale();
  const Content = CONTENT_MAP[locale] || CONTENT_MAP.tr;
  return <MDXPageRenderer content={Content} className="dashboard-page" />;
};

export default DashboardPage;
