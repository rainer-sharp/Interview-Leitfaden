import { expect, test } from '@playwright/test'
import { createGroup, login, testdata, unique } from './helpers'

test.beforeEach(async ({ page }) => login(page))

test('Datei hochladen, Vorschau prüfen, speichern', async ({ page }) => {
  const group = await createGroup(page)
  await page.getByRole('link', { name: 'Fragenliste importieren' }).click()

  await page.getByLabel('Datei (CSV, XLSX oder JSON)').setInputFiles(testdata('fragen_cp1252.csv'))
  const preview = page.getByTestId('import-preview')
  await expect(preview).toContainText('Größenlager')
  await expect(preview.locator('tbody tr')).toHaveCount(3)
  await expect(page.getByText('Zeichensatz windows-1252')).toBeVisible()

  const name = unique('Katalog')
  await page.getByLabel('Name des Katalogs').fill(name)
  await page.getByRole('button', { name: '3 Fragen speichern' }).click()
  await page.waitForURL(/\/kataloge\/\d+/)

  await page.goto('/')
  await page.getByRole('link', { name: group }).click()
  await expect(page.getByRole('link', { name })).toBeVisible()
  await expect(page.getByText('3 Fragen')).toBeVisible()
})

test('fehlerhafte Datei zeigt Fehlerliste und lässt sich nicht speichern', async ({ page }) => {
  await createGroup(page)
  await page.getByRole('link', { name: 'Fragenliste importieren' }).click()
  await page.getByLabel('Datei (CSV, XLSX oder JSON)').setInputFiles(testdata('fragen_fehlerhaft.csv'))

  const errors = page.getByTestId('import-errors')
  await expect(errors).toContainText('Zeile 3: Position 1 ist doppelt')
  await expect(errors).toContainText('Zeile 4: Die Frage ist leer.')
  await expect(errors).toContainText('Unbekannter Typ „freitext“')
  await expect(page.getByRole('button', { name: /Fragen speichern/ })).toHaveCount(0)
})
