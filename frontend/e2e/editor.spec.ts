import { expect, test, type Locator, type Page } from '@playwright/test'
import { createGroup, importCatalog, login } from './helpers'

test.beforeEach(async ({ page }) => login(page))

const texts = (page: Page) => page.getByTestId('question').locator('p:first-child').allTextContents()

async function drag(page: Page, source: Locator, target: Locator) {
  const from = (await source.boundingBox())!
  const to = (await target.boundingBox())!
  await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2)
  await page.mouse.down()
  await page.mouse.move(from.x + from.width / 2, from.y + 10, { steps: 5 })
  await page.mouse.move(to.x + to.width / 2, to.y + 2, { steps: 15 })
  await page.mouse.up()
}

test('Frage per Drag & Drop verschieben, Reihenfolge bleibt nach Reload', async ({ page }) => {
  await createGroup(page)
  await importCatalog(page)
  const questions = page.getByTestId('question')
  await expect(questions).toHaveCount(3)

  const saved = page.waitForResponse((r) => r.url().includes('/order') && r.ok())
  await drag(page, questions.nth(2).locator('[data-drag-handle]'), questions.nth(0))
  await saved

  const expected = [
    'Wie zufrieden sind Sie mit den Lieferzeiten?',
    'Wie sieht Ihr typischer Arbeitstag aus?',
    'Wie bestellen Sie heute Bauteile für das Größenlager?',
  ]
  expect(await texts(page)).toEqual(expected)
  await page.reload()
  await expect(questions).toHaveCount(3)
  expect(await texts(page)).toEqual(expected)
  // Die Frage ist in den Abschnitt „Einstieg“ gewandert.
  await expect(page.getByRole('heading', { level: 2 }).first()).toHaveText('Einstieg')
  await expect(page.getByTestId('question-list').first().getByTestId('question')).toHaveCount(2)
})

test('Fragen per Tastenknopf verschieben, bearbeiten, ergänzen und löschen', async ({ page }) => {
  await createGroup(page)
  await importCatalog(page)
  const questions = page.getByTestId('question')

  // Innerhalb von „Einkauf“ nach oben, dann über die Abschnittsgrenze (Position bleibt, Abschnitt wechselt).
  const saved = page.waitForResponse((r) => r.url().includes('/order') && r.ok())
  await questions.nth(2).getByRole('button', { name: 'Frage nach oben' }).click()
  await saved
  await expect(questions.nth(1)).toContainText('Lieferzeiten')
  const savedAgain = page.waitForResponse((r) => r.url().includes('/order') && r.ok())
  await questions.nth(1).getByRole('button', { name: 'Frage nach oben' }).click()
  await savedAgain
  await page.reload()
  await expect(questions.nth(1)).toContainText('Lieferzeiten')
  await expect(page.getByTestId('question-list').first().getByTestId('question')).toHaveCount(2)

  await questions.nth(0).getByRole('button', { name: 'Bearbeiten' }).click()
  await page.getByLabel('Frage', { exact: true }).first().fill('Geänderte Frage')
  await questions.nth(0).getByRole('button', { name: 'Speichern' }).click()
  await expect(questions.nth(0)).toContainText('Geänderte Frage')

  const add = page.locator('section', { hasText: 'Frage hinzufügen' })
  await add.getByLabel('Frage', { exact: true }).fill('Neue Abschlussfrage')
  await add.getByLabel('Abschnitt').fill('Abschluss')
  await add.getByRole('button', { name: 'Hinzufügen' }).click()
  await expect(questions).toHaveCount(4)
  await expect(page.getByRole('heading', { name: 'Abschluss', level: 2 })).toBeVisible()

  page.once('dialog', (dialog) => dialog.accept())
  await questions.nth(3).getByRole('button', { name: 'Löschen' }).click()
  await expect(questions).toHaveCount(3)
})
