import { expect, test } from '@playwright/test'
import { login } from './helpers'

test('Hinweis auf neue Version und Neuladen beim nächsten Seitenwechsel', async ({ page }) => {
  await login(page)
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Personengruppen' })).toBeVisible()

  // Ab jetzt meldet der Server einen anderen Stand
  await page.route('/api/health', (route) => route.fulfill({ json: { status: 'ok', version: 'neuer-stand' } }))
  await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')))
  await expect(page.getByTestId('update-banner')).toBeVisible()

  const reload = page.waitForEvent('load')
  await page.getByRole('link', { name: 'Interviews' }).first().click()
  await reload
  await expect(page).toHaveURL(/\/interviews$/)
})

test('Abmelden lädt die App neu', async ({ page }) => {
  await login(page)
  const reload = page.waitForEvent('load')
  await page.getByRole('button', { name: 'Abmelden' }).click()
  await reload
  await expect(page).toHaveURL(/\/login$/)
})
