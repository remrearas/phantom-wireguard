import { Accordion, Tag, InlineLoading, InlineNotification, Button } from '@carbon/react';
import { Renew } from '@carbon/icons-react';
import { useOpenApiSpec } from '../hooks/useOpenApiSpec';
import TagGroup from './TagGroup';
import { useLocale } from '@shared/hooks';
import { translate } from '@shared/translations';
import '../styles/ApiDocPage.scss';

interface OpenApiRendererProps {
  showVersion?: boolean;
}

const OpenApiRenderer = ({ showVersion = false }: OpenApiRendererProps) => {
  const { spec, tagGroups, loading, error, refetch } = useOpenApiSpec();
  const { locale } = useLocale();
  const t = translate(locale);

  if (loading) {
    return (
      <div className="api-doc api-doc--loading">
        <InlineLoading description={t.apiDoc.loading} />
      </div>
    );
  }

  if (error || !spec) {
    return (
      <div className="api-doc api-doc--error">
        <InlineNotification kind="error" title={t.apiDoc.error} hideCloseButton lowContrast />
        <Button kind="ghost" size="sm" renderIcon={Renew} onClick={refetch}>
          {t.apiDoc.retry}
        </Button>
      </div>
    );
  }

  return (
    <div className="api-doc" data-testid="api-doc">
      {showVersion && (
        <div className="api-doc__header">
          <Tag type="blue" size="sm">
            {t.apiDoc.version} {spec.info.version}
          </Tag>
        </div>
      )}

      <Accordion className="api-doc__groups">
        {tagGroups.map((group) => (
          <TagGroup key={group.name} group={group} />
        ))}
      </Accordion>
    </div>
  );
};

export default OpenApiRenderer;
