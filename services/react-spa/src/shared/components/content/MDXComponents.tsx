import { CodeSnippet } from '@carbon/react';

// noinspection JSUnusedGlobalSymbols
export const components = {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  pre: (props: any) => {
    const code = props.children;
    if (code?.props?.children) {
      return <CodeSnippet type="multi">{code.props.children}</CodeSnippet>;
    }
    return <pre {...props} />;
  },
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  code: (props: any) => <code {...props} />,
};
