import type { Answer, AnswerStatus } from '../types'

/** Spiegelt die Server-Regel, damit die Status-Punkte sofort reagieren. */
export function statusAfterNote(status: AnswerStatus, notiz: string): AnswerStatus {
  if (status === 'offen' && notiz.trim()) return 'beantwortet'
  if (status === 'beantwortet' && !notiz.trim()) return 'offen'
  return status
}

export function firstOpenIndex(answers: Answer[]): number {
  const index = answers.findIndex((a) => a.status === 'offen')
  return index === -1 ? answers.length : index
}

export function countByStatus(answers: Answer[]): Record<AnswerStatus, number> {
  const counts: Record<AnswerStatus, number> = { offen: 0, beantwortet: 0, uebersprungen: 0, spaeter: 0 }
  for (const answer of answers) counts[answer.status]++
  return counts
}

export const STATUS_LABEL: Record<AnswerStatus, string> = {
  offen: 'offen',
  beantwortet: 'beantwortet',
  uebersprungen: 'übersprungen',
  spaeter: 'später nochmal',
}

export type Shortcut = 'next' | 'back' | 'skip'

export function shortcutFor(event: Pick<KeyboardEvent, 'key' | 'ctrlKey' | 'metaKey' | 'altKey' | 'shiftKey'>): Shortcut | null {
  if (!(event.ctrlKey || event.metaKey) || event.altKey || event.shiftKey) return null
  if (event.key === 'Enter') return 'next'
  if (event.key === 'ArrowLeft') return 'back'
  if (event.key === 's' || event.key === 'S') return 'skip'
  return null
}

export function formatDate(iso: string): string {
  const [year, month, day] = iso.split('-')
  return `${day}.${month}.${year}`
}

export function today(): string {
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}
