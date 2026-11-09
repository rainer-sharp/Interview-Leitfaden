import { describe, expect, it } from 'vitest'
import type { Answer, AnswerStatus } from '../types'
import { countByStatus, firstOpenIndex, formatDate, shortcutFor, statusAfterNote } from './interviewState'

const answer = (status: AnswerStatus) => ({ status }) as Answer
const key = (k: string, extra: Partial<KeyboardEvent> = {}) =>
  shortcutFor({ key: k, ctrlKey: true, metaKey: false, altKey: false, shiftKey: false, ...extra })

describe('interviewState', () => {
  it('Notiz macht offene Fragen zu beantworteten, übersprungen bleibt', () => {
    expect(statusAfterNote('offen', 'x')).toBe('beantwortet')
    expect(statusAfterNote('offen', '  ')).toBe('offen')
    expect(statusAfterNote('beantwortet', '')).toBe('offen')
    expect(statusAfterNote('uebersprungen', 'x')).toBe('uebersprungen')
    expect(statusAfterNote('spaeter', '')).toBe('spaeter')
  })

  it('setzt beim Fortsetzen an der ersten offenen Frage an', () => {
    expect(firstOpenIndex([answer('beantwortet'), answer('offen')])).toBe(1)
    expect(firstOpenIndex([answer('spaeter')])).toBe(1)
    expect(countByStatus([answer('offen'), answer('offen'), answer('spaeter')])).toEqual({
      offen: 2,
      beantwortet: 0,
      uebersprungen: 0,
      spaeter: 1,
    })
  })

  it('erkennt die Tastenkürzel aus der Spezifikation', () => {
    expect(key('Enter')).toBe('next')
    expect(key('ArrowLeft')).toBe('back')
    expect(key('s')).toBe('skip')
    expect(key('Enter', { ctrlKey: false, metaKey: true })).toBe('next')
    expect(key('Enter', { ctrlKey: false })).toBeNull()
    expect(key('s', { shiftKey: true })).toBeNull()
  })

  it('formatiert Datum deutsch', () => {
    expect(formatDate('2026-11-09')).toBe('09.11.2026')
  })
})
