import { useState } from 'react';
import {
  Button,
  TextInput,
  Tag,
  InlineLoading,
  InlineNotification,
} from '@carbon/react';
import { SendFilled } from '@carbon/icons-react';
import CodeHighlight from '@shared/components/visualization/CodeHighlight';
import type { ParsedOperation } from '../types/openapi';
import { generateBodyTemplate } from '../utils/specParser';
import { executeRequest, type RequestResult } from '../utils/requestBuilder';
import RequestBodyEditor from './RequestBodyEditor';
import { useLocale } from '@shared/hooks';
import { translate } from '@shared/translations';

interface TryItOutProps {
  operation: ParsedOperation;
}

const TryItOut = ({ operation }: TryItOutProps) => {
  const { locale } = useLocale();
  const t = translate(locale);

  const pathParams = operation.parameters.filter((p) => p.in === 'path');
  const queryParams = operation.parameters.filter((p) => p.in === 'query');

  const [paramValues, setParamValues] = useState<Record<string, string>>(() => {
    const defaults: Record<string, string> = {};
    for (const p of [...pathParams, ...queryParams]) {
      defaults[p.name] = p.schema?.default !== undefined ? String(p.schema.default) : '';
    }
    return defaults;
  });

  const [bodyValue, setBodyValue] = useState<string>(() => {
    if (!operation.requestBody || operation.hasFileUpload) return '';
    const contentType = Object.keys(operation.requestBody.content)[0];
    const schema = operation.requestBody.content[contentType]?.schema;
    if (!schema) return '';
    return JSON.stringify(generateBodyTemplate(schema), null, 2);
  });

  const [file, setFile] = useState<File | null>(null);
  const [response, setResponse] = useState<RequestResult | null>(null);
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSend = async () => {
    setExecuting(true);
    setError(null);
    setResponse(null);

    const pathP: Record<string, string> = {};
    const queryP: Record<string, string> = {};

    for (const p of pathParams) {
      pathP[p.name] = paramValues[p.name] ?? '';
    }
    for (const p of queryParams) {
      const val = paramValues[p.name] ?? '';
      if (val !== '') queryP[p.name] = val;
    }

    let fileFieldName = 'file';
    if (operation.requestBody && operation.hasFileUpload) {
      const ct = Object.keys(operation.requestBody.content)[0];
      const schema = operation.requestBody.content[ct]?.schema;
      if (schema?.properties) {
        fileFieldName = Object.keys(schema.properties)[0] ?? 'file';
      }
    }

    try {
      const result = await executeRequest({
        method: operation.method,
        path: operation.path,
        pathParams: pathP,
        queryParams: queryP,
        body: bodyValue || null,
        file,
        fileFieldName,
        isFileUpload: operation.hasFileUpload,
      });
      setResponse(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed');
    } finally {
      setExecuting(false);
    }
  };

  const updateParam = (name: string, value: string) => {
    setParamValues((prev) => ({ ...prev, [name]: value }));
  };

  return (
    <div className="api-doc__tryit">
      <h6 className="api-doc__section-title">{t.apiDoc.tryItOut}</h6>

      {(pathParams.length > 0 || queryParams.length > 0) && (
        <div className="api-doc__tryit-params">
          {[...pathParams, ...queryParams].map((p) => (
            <TextInput
              key={p.name}
              id={`param-${operation.operationId}-${p.name}`}
              labelText={`${p.name} (${p.in})`}
              value={paramValues[p.name] ?? ''}
              onChange={(e) => updateParam(p.name, e.target.value)}
              size="sm"
              placeholder={p.schema?.default !== undefined ? String(p.schema.default) : ''}
            />
          ))}
        </div>
      )}

      {operation.requestBody && (
        <RequestBodyEditor
          requestBody={operation.requestBody}
          isFileUpload={operation.hasFileUpload}
          bodyValue={bodyValue}
          onBodyChange={setBodyValue}
          file={file}
          onFileChange={setFile}
        />
      )}

      <div className="api-doc__tryit-actions">
        <Button
          size="sm"
          renderIcon={SendFilled}
          onClick={() => void handleSend()}
          disabled={executing}
        >
          {t.apiDoc.send}
        </Button>
        {executing && <InlineLoading description={t.apiDoc.sending} />}
      </div>

      {error && (
        <InlineNotification
          kind="error"
          title={error}
          hideCloseButton
          lowContrast
          className="api-doc__tryit-error"
        />
      )}

      {response && (
        <div className="api-doc__tryit-response">
          <div className="api-doc__tryit-response-meta">
            <Tag
              type={response.status < 300 ? 'green' : response.status < 500 ? 'magenta' : 'red'}
              size="sm"
            >
              {response.status} {response.statusText}
            </Tag>
            <span className="api-doc__tryit-duration">
              {response.duration}{t.apiDoc.milliseconds}
            </span>
          </div>
          <div className="api-doc__tryit-body">
            <CodeHighlight code={response.body} lang="json" />
          </div>
        </div>
      )}
    </div>
  );
};

export default TryItOut;
