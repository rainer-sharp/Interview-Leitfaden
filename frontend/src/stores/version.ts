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

/**
 * Lesbare Versionsangabe aus dem Stand des Servers (git describe):
 * v1.0.0 → 1.0.0 · v1.0.0-3-gabc1234 → 1.0.0+3 (abc1234) · abc1234 → abc1234; Zusatz -geaendert → (geändert).
 */
export function formatVersion(raw: string): string {
  let rest = raw.trim()
  const changed = rest.endsWith('-geaendert')
  if (changed) rest = rest.slice(0, -'-geaendert'.length)
  const match = /^v?(\d+\.\d+\.\d+(?:[-.][0-9A-Za-z.]+?)?)(?:-(\d+)-g([0-9a-f]+))?$/.exec(rest)
  let text = rest
  if (match) text = match[2] ? `${match[1]}+${match[2]} (${match[3]})` : match[1]
  return changed ? `${text} (geändert)` : text
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
