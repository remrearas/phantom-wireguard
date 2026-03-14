import React from 'react';
import { Grid, Column, ClickableTile } from '@carbon/react';
import { useNavigate } from 'react-router-dom';
import './styles/DocumentationIndex.scss';

export interface DocTopic {
  title: string;
  description: string;
  href: string;
}

interface DocumentationIndexProps {
  topics: DocTopic[];
}

const DocumentationIndex: React.FC<DocumentationIndexProps> = ({ topics }) => {
  const navigate = useNavigate();

  return (
    <Grid className="docs__grid">
      {topics.map((topic) => (
        <Column key={topic.href} lg={16} md={8} sm={4}>
          <ClickableTile
            className="docs__topic-tile"
            onClick={() => navigate(topic.href)}
            data-testid={`docs-topic-${topic.href.split('/').pop()}`}
          >
            <p className="docs__topic-title">{topic.title}</p>
            <p className="docs__topic-desc">{topic.description}</p>
          </ClickableTile>
        </Column>
      ))}
    </Grid>
  );
};

export default DocumentationIndex;
