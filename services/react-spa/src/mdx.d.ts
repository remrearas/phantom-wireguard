// noinspection JSUnusedGlobalSymbols

declare module '*.mdx' {
  import type { ComponentType } from 'react';
  const Component: ComponentType;
  export default Component;
  export const frontmatter: Record<string, unknown>;
}
