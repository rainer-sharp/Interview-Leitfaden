export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message)
  }
}

let onUnauthorized: () => void = () => {}

export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler
}

async function errorFrom(response: Response): Promise<ApiError> {
  let message = `Fehler ${response.status}`
  try {
    const body = await response.json()
    message = typeof body.detail === 'string' ? body.detail : 'Die Eingabe ist ungültig.'
  } catch {
    // Keine JSON-Antwort, z. B. vom Proxy: Statuscode reicht als Meldung.
  }
  return new ApiError(response.status, message)
}

export async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const isForm = body instanceof FormData
  let response: Response
  try {
    response = await fetch(`/api${path}`, {
      method,
      headers: body === undefined || isForm ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, 'Der Server ist nicht erreichbar.')
  }
  if (response.status === 401) onUnauthorized()
  if (!response.ok) throw await errorFrom(response)
  return (response.status === 204 ? undefined : await response.json()) as T
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
  put: <T>(path: string, body?: unknown) => request<T>('PUT', path, body),
  delete: (path: string) => request<void>('DELETE', path),
}
