import React from 'react';
import { Grid, Column } from '@carbon/react';
import MDXProvider from './MDXProvider';
import './styles/MDXContent.scss';

interface MDXPageRendererProps {
  content: React.ComponentType;
  className?: string;
}

const MDXPageRenderer: React.FC<MDXPageRendererProps> = ({ content: Content, className = '' }) => {
  return (
    <section className={`mdx-page ${className}`}>
      <Grid>
        <Column lg={16} md={8} sm={4}>
          <MDXProvider>
            <article className="mdx-content">
              <Content />
            </article>
          </MDXProvider>
        </Column>
      </Grid>
    </section>
  );
};

export default MDXPageRenderer;
