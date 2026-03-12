import React from 'react';
import { Grid, Column, ClickableTile } from '@carbon/react';
import { useNavigate } from 'react-router-dom';
import { useLocale } from '@shared/hooks';
import { translate } from '@shared/translations';
import './styles/documentation.scss';

interface DocTopic {
  key: string;
  href: string;
}

const TOPICS: DocTopic[] = [
  { key: 'terazi', href: '/documentation/terazi' },
];

const DocumentationIndex: React.FC = () => {
  const { locale } = useLocale();
  const t = translate(locale);
  const navigate = useNavigate();

  const docs = t.documentation.topics as Record<string, { title: string; description: string }>;

  return (
    <Grid className="docs__grid">
      {TOPICS.map((topic) => {
        const meta = docs[topic.key];
        if (!meta) return null;
        return (
          <Column key={topic.key} lg={8} md={4} sm={4}>
            <ClickableTile
              className="docs__topic-tile"
              onClick={() => navigate(topic.href)}
              data-testid={`docs-topic-${topic.key}`}
            >
              <p className="docs__topic-title">{meta.title}</p>
              <p className="docs__topic-desc">{meta.description}</p>
            </ClickableTile>
          </Column>
        );
      })}
    </Grid>
  );
};

export default DocumentationIndex;
