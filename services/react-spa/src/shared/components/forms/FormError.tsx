import React from 'react';
import { InlineNotification } from '@carbon/react';

interface FormErrorProps {
  error: string | null;
  className?: string;
}

const FormError: React.FC<FormErrorProps> = ({ error, className }) => {
  if (!error) return null;
  return (
    <InlineNotification
      kind="error"
      title={error}
      lowContrast
      hideCloseButton
      className={className}
    />
  );
};

export default FormError;
