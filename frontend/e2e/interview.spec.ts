import { expect, test, type Page } from '@playwright/test'
import { createGroup, importCatalog, login, unique } from './helpers'

test.beforeEach(async ({ page }) => login(page))

const QUESTIONS = [
  'Wie sieht Ihr typischer Arbeitstag aus?',
  'Wie bestellen Sie heute Bauteile für das Größenlager?',
  'Wie zufrieden sind Sie mit den Lieferzeiten?',
]

async function startInterview(page: Page, person = unique('Person')) {
  await createGroup(page)
  await importCatalog(page)
  await page.getByRole('link', { name: 'Interview starten' }).click()
  await page.getByLabel('Interviewte Person').fill(person)
  await page.getByLabel('Organisation (optional)').fill('Muster GmbH')
  await page.getByRole('button', { name: 'Interview starten' }).click()
  await expect(page.getByTestId('question-text')).toHaveText(QUESTIONS[0])
  return person
}

const note = (page: Page) => page.getByRole('textbox', { name: 'Notiz' })
const saved = (page: Page) => expect(page.getByTestId('save-state')).toHaveText('gespeichert')
const dot = (page: Page, n: number) => page.getByRole('navigation', { name: 'Alle Fragen' }).locator('[data-status]').nth(n)

test('komplettes Interview per Tastatur und Knöpfen durchklicken', async ({ page }) => {
  await startInterview(page)
  await expect(page.getByTestId('position')).toHaveText('1/3')

  await note(page).fill('Beginnt um 7 Uhr mit der Wareneingangsliste.')
  await saved(page)
  await expect(page.getByTestId('answer-status')).toHaveText('beantwortet')
  await note(page).press('Control+Enter')

  await expect(page.getByTestId('position')).toHaveText('2/3')
  await page.getByRole('button', { name: 'Später nochmal' }).click()

  await expect(page.getByTestId('position')).toHaveText('3/3')
  await note(page).press('Control+ArrowLeft')
  await expect(page.getByTestId('position')).toHaveText('2/3')
  await expect(page.getByTestId('answer-status')).toHaveText('später nochmal')
  await page.keyboard.press('Control+Enter')
  await note(page).press('Control+s')

  await expect(page.getByTestId('summary')).toBeVisible()
  await expect(dot(page, 0)).toHaveAttribute('data-status', 'beantwortet')
  await expect(dot(page, 1)).toHaveAttribute('data-status', 'spaeter')
  await expect(dot(page, 2)).toHaveAttribute('data-status', 'uebersprungen')
  await expect(page.getByTestId('summary')).toContainText('1 Pflichtfrage ist noch ohne Antwort.')

  // Aus der Übersicht zur offenen Frage springen und nachtragen
  await page.getByTestId('summary').getByRole('button', { name: /Bauteile/ }).click()
  await note(page).fill('Per Telefon und E-Mail.')
  await note(page).press('Control+Enter')
  await expect(page.getByTestId('position')).toHaveText('3/3')
  await page.getByRole('navigation', { name: 'Alle Fragen' }).getByRole('button', { name: 'Abschluss' }).click()
  await expect(page.getByTestId('summary')).toBeVisible()
  await expect(dot(page, 1)).toHaveAttribute('data-status', 'beantwortet')

  await page.getByLabel('Gesamtnotiz').fill('Offenes Gespräch, Lieferzeiten sind das Hauptthema.')
  await page.getByRole('button', { name: 'Interview abschließen' }).click()
  await expect(page.getByRole('heading', { name: 'Interview abgeschlossen' })).toBeVisible()

  await page.reload()
  await expect(page.getByLabel('Gesamtnotiz')).toHaveValue('Offenes Gespräch, Lieferzeiten sind das Hauptthema.')
  await page.getByRole('navigation', { name: 'Alle Fragen' }).getByRole('button', { name: /Bauteile/ }).click()
  await expect(note(page)).toHaveValue('Per Telefon und E-Mail.')
  await expect(note(page)).toHaveAttribute('readonly', '')
})

test('Interview unterbrechen und fortsetzen', async ({ page }) => {
  const person = await startInterview(page)
  await note(page).fill('Erste Antwort')
  await note(page).press('Control+Enter')
  await note(page).fill('Zweite Antwort, noch im Tippen')

  // Sofort weg, ohne die Tipp-Pause abzuwarten
  await page.getByRole('link', { name: /Pause/ }).click()
  const row = page.getByTestId('interview-row').filter({ hasText: person })
  await expect(row).toContainText('läuft')
  await expect(row).toContainText('2/3 Fragen bearbeitet')

  await row.getByRole('link', { name: 'Fortsetzen' }).click()
  // Fortsetzen springt zur ersten offenen Frage
  await expect(page.getByTestId('question-text')).toHaveText(QUESTIONS[2])
  await page.keyboard.press('Control+ArrowLeft')
  await expect(note(page)).toHaveValue('Zweite Antwort, noch im Tippen')
  await page.keyboard.press('Control+ArrowLeft')
  await expect(note(page)).toHaveValue('Erste Antwort')
})

test('keine Notiz geht bei Verbindungsabbruch verloren', async ({ page, context }) => {
  await startInterview(page)
  await context.setOffline(true)
  await note(page).fill('Offline getippt')
  await expect(page.getByTestId('save-state')).toContainText('offline', { timeout: 5000 })

  await page.reload().catch(() => {})
  await context.setOffline(false)
  await page.reload()
  await expect(note(page)).toHaveValue('Offline getippt')
  await saved(page)

  // Ein zweiter Browser (ohne lokalen Puffer) sieht den Stand auf dem Server
  const other = await context.browser()!.newPage()
  await login(other)
  await other.goto(page.url())
  await expect(other.getByRole('textbox', { name: 'Notiz' })).toHaveValue('Offline getippt')
  await other.close()
})
