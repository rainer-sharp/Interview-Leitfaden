import { describe, expect, it } from 'vitest'
import { evaluationBusy, sourcesHint } from './evaluation'

describe('evaluation', () => {
  it('erkennt laufende Bewertungen', () => {
    expect(evaluationBusy({ status: 'wartend' })).toBe(true)
    expect(evaluationBusy({ status: 'laeuft' })).toBe(true)
    expect(evaluationBusy({ status: 'fertig' })).toBe(false)
    expect(evaluationBusy(null)).toBe(false)
  })

  it('nennt die Quellen der Bewertung', () => {
    expect(sourcesHint({ hat_transkript: true, transkription_laeuft: false })).toContain('Transkript')
    expect(sourcesHint({ hat_transkript: false, transkription_laeuft: false })).toContain('nur Notizen')
    expect(sourcesHint({ hat_transkript: false, transkription_laeuft: true })).toContain('läuft noch')
  })
})
