import { beforeEach, describe, expect, it } from 'vitest'
import { checkVersion, loadedVersion, updateAvailable } from './version'

describe('version', () => {
  beforeEach(() => {
    loadedVersion.value = null
    updateAvailable.value = false
  })

  it('merkt sich den Stand beim Laden und meldet erst einen anderen als Update', async () => {
    expect(await checkVersion(async () => 'c908556')).toBe(false)
    expect(loadedVersion.value).toBe('c908556')
    expect(await checkVersion(async () => 'c908556')).toBe(false)
    expect(await checkVersion(async () => 'e1f2a3b')).toBe(true)
    expect(updateAvailable.value).toBe(true)
  })

  it('ignoriert einen nicht erreichbaren Server', async () => {
    await checkVersion(async () => 'c908556')
    expect(await checkVersion(async () => null)).toBe(false)
    expect(loadedVersion.value).toBe('c908556')
  })

  it('ein gemeldetes Update bleibt bestehen', async () => {
    await checkVersion(async () => 'alt')
    await checkVersion(async () => 'neu')
    expect(await checkVersion(async () => null)).toBe(true)
  })
})
