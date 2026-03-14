export interface RequestConfig {
  method: string;
  path: string;
  pathParams: Record<string, string>;
  queryParams: Record<string, string>;
  body: string | null;
  file: File | null;
  fileFieldName: string;
  isFileUpload: boolean;
}

export interface RequestResult {
  status: number;
  statusText: string;
  body: string;
  duration: number;
  contentType: string;
}

export function buildUrl(
  path: string,
  pathParams: Record<string, string>,
  queryParams: Record<string, string>,
): string {
  let url = path;

  for (const [key, value] of Object.entries(pathParams)) {
    url = url.replace(`{${key}}`, encodeURIComponent(value));
  }

  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(queryParams)) {
    if (value !== '') {
      searchParams.set(key, value);
    }
  }

  const qs = searchParams.toString();
  return qs ? `${url}?${qs}` : url;
}

export async function executeRequest(config: RequestConfig): Promise<RequestResult> {
  const url = buildUrl(config.path, config.pathParams, config.queryParams);
  const token = localStorage.getItem('token');

  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;

  let fetchBody: BodyInit | undefined;

  if (config.isFileUpload && config.file) {
    const formData = new FormData();
    formData.append(config.fileFieldName || 'file', config.file);
    fetchBody = formData;
  } else if (config.body && config.method !== 'get') {
    headers['Content-Type'] = 'application/json';
    fetchBody = config.body;
  }

  const start = performance.now();

  const res = await fetch(url, {
    method: config.method.toUpperCase(),
    headers,
    body: fetchBody,
  });

  const duration = Math.round(performance.now() - start);
  const contentType = res.headers.get('content-type') ?? '';

  let body: string;
  if (contentType.includes('application/json')) {
    const json = await res.json();
    body = JSON.stringify(json, null, 2);
  } else if (contentType.includes('text/')) {
    body = await res.text();
  } else {
    const blob = await res.blob();
    body = `[Binary: ${blob.size} bytes]`;
  }

  return {
    status: res.status,
    statusText: res.statusText,
    body,
    duration,
    contentType,
  };
}
