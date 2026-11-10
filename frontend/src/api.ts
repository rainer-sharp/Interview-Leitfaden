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

/** Upload mit Fortschritt (fetch kennt keinen Upload-Fortschritt; Aufnahmen können mehrere GB groß sein). */
export function upload<T>(path: string, form: FormData, onProgress?: (fraction: number) => void): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `/api${path}`)
    xhr.responseType = 'json'
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress?.(event.loaded / event.total)
    }
    xhr.onerror = () => reject(new ApiError(0, 'Der Server ist nicht erreichbar.'))
    xhr.onload = () => {
      if (xhr.status === 401) onUnauthorized()
      if (xhr.status >= 200 && xhr.status < 300) return resolve(xhr.response as T)
      const detail = xhr.response?.detail
      reject(new ApiError(xhr.status, typeof detail === 'string' ? detail : `Fehler ${xhr.status}`))
    }
    xhr.send(form)
  })
}
