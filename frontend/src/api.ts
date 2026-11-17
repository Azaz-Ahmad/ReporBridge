export async function api<T>(token: string, path: string, method = 'GET', body?: unknown): Promise<T> {
  const response = await fetch('/api' + path, {
    method,
    headers: { Authorization: 'Bearer ' + token, ...(body ? { 'Content-Type': 'application/json' } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  const content = await response.json();
  if (!response.ok) throw new Error(content.reason || (typeof content.detail === 'string' ? content.detail : content.detail?.message || 'The request could not be completed.'));
  return content as T;
}
