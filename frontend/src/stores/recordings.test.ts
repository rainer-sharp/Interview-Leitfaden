import { describe, expect, it } from 'vitest'
import { elapsed, formatSize, isBusy } from './recordings'

describe('recordings', () => {
  it('formatiert Dateigrößen deutsch', () => {
    expect(formatSize(10)).toBe('1 KB')
    expect(formatSize(5 * 1024 * 1024 + 300_000)).toBe('5,3 MB')
    expect(formatSize(2.5 * 1024 ** 3)).toBe('2,50 GB')
  })

  it('erkennt laufende Aufträge', () => {
    expect(isBusy({ transkript_status: 'wartend' })).toBe(true)
    expect(isBusy({ transkript_status: 'laeuft' })).toBe(true)
    expect(isBusy({ transkript_status: 'fertig' })).toBe(false)
  })

  it('berechnet die Laufzeit aus UTC-Zeitstempeln ohne Zone', () => {
    expect(elapsed(null, null)).toBe('')
    expect(elapsed('2026-11-10T10:00:00', '2026-11-10T10:03:05')).toBe('3 min 05 s')
    expect(elapsed('2026-11-10T10:00:00', null, Date.parse('2026-11-10T10:00:42Z'))).toBe('42 s')
  })
})
