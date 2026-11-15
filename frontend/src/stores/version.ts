import { ref } from 'vue'

/**
 * Erkennt ein Update auf dem Server: Die App merkt sich beim Laden den Stand aus /api/health und vergleicht ihn
 * regelmäßig und beim Zurückkehren in den Tab. Ohne Neuladen liefe sonst das alte Frontend gegen das neue Backend.
 */
export const loadedVersion = ref<string | null>(null)
export const updateAvailable = ref(false)

export const CHECK_INTERVAL_MS = 5 * 60 * 1000

type Fetcher = () => Promise<string | null>

async function fetchVersion(): Promise<string | null> {
  try {
    const response = await fetch('/api/health', { cache: 'no-store' })
    if (!response.ok) return null
    const body = (await response.json()) as { version?: string }
    return body.version ?? null
  } catch {
    return null // Server kurz weg (z. B. gerade beim Update): beim nächsten Mal wieder
  }
}

export async function checkVersion(fetcher: Fetcher = fetchVersion): Promise<boolean> {
  const current = await fetcher()
  if (!current) return updateAvailable.value
  if (loadedVersion.value === null) loadedVersion.value = current
  else if (current !== loadedVersion.value) updateAvailable.value = true
  return updateAvailable.value
}

export function reloadApp(path?: string) {
  if (path) window.location.assign(path)
  else window.location.reload()
}

export function watchVersion() {
  void checkVersion()
  setInterval(() => void checkVersion(), CHECK_INTERVAL_MS)
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') void checkVersion()
  })
}
