import { describe, expect, it } from 'vitest'
import { pickProject } from './project'

describe('pickProject', () => {
  const list = [{ id: 4 }, { id: 2 }, { id: 9 }]

  it('behält ein gemerktes Projekt, das es noch gibt', () => {
    expect(pickProject(list, 9)).toBe(9)
  })

  it('nimmt sonst das älteste', () => {
    expect(pickProject(list, 7)).toBe(2)
    expect(pickProject(list, null)).toBe(2)
  })

  it('ohne Projekte keins', () => {
    expect(pickProject([], 3)).toBeNull()
  })
})
