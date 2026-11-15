import { expect, test } from '@playwright/test'
import { createGroup, login, unique } from './helpers'

test.beforeEach(async ({ page }) => login(page))

test('Backup wiederherstellen und rückgängig machen', async ({ page }) => {
  await page.goto('/sicherung')
  const download = page.waitForEvent('download')
  await page.getByRole('link', { name: 'Backup herunterladen' }).click()
  const backupPath = await (await download).path()

  const later = await createGroup(page, unique('Nach dem Backup'))

  await page.goto('/sicherung')
  const restore = page.getByTestId('restore')
  await restore.getByLabel('Backup-Datei (.zip oder .db)').setInputFiles(backupPath)
  const button = restore.getByRole('button', { name: 'Wiederherstellen' })
  await expect(button).toBeDisabled()
  await restore.getByRole('checkbox').check()
  await button.click()
  await expect(restore.getByTestId('restore-result')).toContainText('Wiederhergestellt.')

  await page.goto('/')
  await expect(page.getByRole('link', { name: later })).toHaveCount(0)

  // Rückgängig: der Stand vor der Wiederherstellung steht oben in der Liste
  await page.goto('/sicherung')
  const copies = page.getByTestId('safety-copies')
  await copies.getByRole('button', { name: 'Zurückholen' }).first().click()
  await copies.getByRole('button', { name: 'Ja, zurückholen' }).click()
  await expect(restore.getByTestId('restore-result')).toBeVisible()
  await page.goto('/')
  await expect(page.getByRole('link', { name: later })).toBeVisible()
})
