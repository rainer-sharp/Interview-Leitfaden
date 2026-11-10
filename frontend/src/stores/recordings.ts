import type { Recording, TranscriptStatus } from '../types'

export const TRANSCRIPT_STATUS_LABEL: Record<TranscriptStatus, string> = {
  keine: 'nicht transkribiert',
  wartend: 'wartet auf den Server',
  laeuft: 'wird transkribiert …',
  fertig: 'transkribiert',
  fehler: 'Fehler',
}

export const ACCEPTED_AUDIO = '.mkv,.mp4,.mov,.webm,.mp3,.m4a,.aac,.wav,.ogg,.oga,.opus,.flac,audio/*'

export function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1).replace('.', ',')} MB`
  return `${(bytes / 1024 ** 3).toFixed(2).replace('.', ',')} GB`
}

export function isBusy(recording: Pick<Recording, 'transkript_status'>): boolean {
  return recording.transkript_status === 'wartend' || recording.transkript_status === 'laeuft'
}

/** Dauer zwischen Start und Ende (oder jetzt), z. B. „3 min 05 s“. */
export function elapsed(start: string | null, end: string | null, now = Date.now()): string {
  if (!start) return ''
  // Der Server liefert UTC ohne Zeitzonen-Angabe.
  const from = Date.parse(start.endsWith('Z') ? start : `${start}Z`)
  const to = end ? Date.parse(end.endsWith('Z') ? end : `${end}Z`) : now
  const seconds = Math.max(0, Math.round((to - from) / 1000))
  const minutes = Math.floor(seconds / 60)
  const rest = String(seconds % 60).padStart(2, '0')
  return minutes ? `${minutes} min ${rest} s` : `${seconds} s`
}
