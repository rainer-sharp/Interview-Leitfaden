import { describe, expect, it } from 'vitest'
import type { Question } from '../types'
import { moveBetweenSections, moveSection, moveStep, renameSection, toSections } from './catalogOrder'

const q = (id: number, abschnitt: string): Question => ({
  id,
  abschnitt,
  questionnaire_id: 1,
  position: id,
  text: `F${id}`,
  hinweis: '',
  pflicht: false,
  typ: 'text',
})
const base = [q(1, 'A'), q(2, 'A'), q(3, 'B')]
const view = (list: Question[]) => list.map((x) => `${x.id}${x.abschnitt}`).join(' ')

describe('catalogOrder', () => {
  it('fasst nur zusammenhängende Abschnitte zusammen', () => {
    expect(toSections([q(1, 'A'), q(2, 'B'), q(3, 'A')]).map((s) => s.abschnitt)).toEqual(['A', 'B', 'A'])
  })

  it('verschiebt zwischen Abschnitten und übernimmt den neuen Abschnitt', () => {
    expect(view(moveBetweenSections(base, 1, 0, 0, 0))).toBe('3A 1A 2A')
    expect(view(moveBetweenSections(base, 0, 0, 0, 1))).toBe('2A 1A 3B')
  })

  it('wechselt an der Grenze erst den Abschnitt, dann die Position', () => {
    expect(view(moveStep(base, 3, -1))).toBe('1A 2A 3A')
    expect(view(moveStep(base, 2, -1))).toBe('2A 1A 3B')
    expect(view(moveStep(base, 1, -1))).toBe('1A 2A 3B')
    expect(view(moveStep(base, 3, 1))).toBe('1A 2A 3B')
  })

  it('verschiebt ganze Abschnitte', () => {
    expect(view(moveSection(base, 1, -1))).toBe('3B 1A 2A')
    expect(view(moveSection(base, 1, 1))).toBe('1A 2A 3B')
  })

  it('benennt nur den gewählten Abschnitt um', () => {
    expect(view(renameSection(base, 0, 'C'))).toBe('1C 2C 3B')
  })
})
