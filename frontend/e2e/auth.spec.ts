import { expect, test } from '@playwright/test'
import { login } from './helpers'

test('ohne Anmeldung landet man auf der Login-Seite und danach am Ziel', async ({ page }) => {
  await page.goto('/interviews')
  await expect(page).toHaveURL(/\/login\?weiter=(%2F|\/)interviews$/)

  await page.getByLabel('Passwort').fill('falsch')
  await page.getByRole('button', { name: 'Anmelden' }).click()
  await expect(page.getByRole('alert')).toHaveText('Das Passwort ist falsch.')

  await page.getByLabel('Passwort').fill('e2e-passwort')
  await page.getByRole('button', { name: 'Anmelden' }).click()
  await expect(page.getByRole('heading', { name: 'Interviews' })).toBeVisible()

  await page.getByRole('button', { name: 'Abmelden' }).click()
  await expect(page).toHaveURL(/\/login/)
  await page.goto('/')
  await expect(page).toHaveURL(/\/login/)
})

test('Backup lässt sich herunterladen', async ({ page }) => {
  await login(page)
  const download = page.waitForEvent('download')
  await page.getByRole('link', { name: 'Backup' }).click()
  expect((await download).suggestedFilename()).toMatch(/^interview-backup-.*\.zip$/)
})
