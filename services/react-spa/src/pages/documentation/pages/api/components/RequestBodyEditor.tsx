import { TextArea, Button } from '@carbon/react';
import { Upload } from '@carbon/icons-react';
import { useRef } from 'react';
import type { RequestBodyObject } from '../types/openapi';
import { useLocale } from '@shared/hooks';
import { translate } from '@shared/translations';

interface RequestBodyEditorProps {
  requestBody: RequestBodyObject;
  isFileUpload: boolean;
  bodyValue: string;
  onBodyChange: (value: string) => void;
  file: File | null;
  onFileChange: (file: File | null) => void;
}

const RequestBodyEditor = ({
  isFileUpload,
  bodyValue,
  onBodyChange,
  file,
  onFileChange,
}: RequestBodyEditorProps) => {
  const { locale } = useLocale();
  const t = translate(locale);
  const fileRef = useRef<HTMLInputElement>(null);

  if (isFileUpload) {
    return (
      <div className="api-doc__file-upload">
        <input
          ref={fileRef}
          type="file"
          style={{ display: 'none' }}
          onChange={(e) => onFileChange(e.target.files?.[0] ?? null)}
        />
        <Button
          kind="tertiary"
          size="sm"
          renderIcon={Upload}
          onClick={() => fileRef.current?.click()}
        >
          {t.apiDoc.selectFile}
        </Button>
        {file && <span className="api-doc__file-name">{file.name}</span>}
      </div>
    );
  }

  return (
    <TextArea
      id="request-body"
      labelText={t.apiDoc.requestBody}
      value={bodyValue}
      onChange={(e) => onBodyChange(e.target.value)}
      rows={6}
      className="api-doc__body-editor"
    />
  );
};

export default RequestBodyEditor;
