import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { extraction, report, providerError } from '../contract/fixtures/responses'
const syntheticFile = { name: 'SYNTHETIC-fixture.pdf', mimeType: 'application/pdf', buffer: Buffer.from('SYNTHETIC TEST INPUT. Parser is mocked in this test.') }

test('actual unavailable backend: keyboard upload and honest error, no report', async ({ page }) => {
  await page.goto('/')
    await expect(page).toHaveTitle('JEV Resume Analyzer')
  await expect(page.getByText('Backend unavailable')).toBeVisible()
  await page.keyboard.press('Tab')
  await expect(page.getByLabel('Choose CV file')).toBeFocused()
  const chooser = page.waitForEvent('filechooser')
  await page.keyboard.press('Enter')
  await (await chooser).setFiles(syntheticFile)
  await expect(page.getByRole('alert')).toContainText('HTTP 502')
  await expect(page.getByLabel('CV text')).toHaveCount(0)
  await expect(page.getByText('Your CV, examined.')).toHaveCount(0)
  await page.screenshot({ path: 'test-results/real-backend-unavailable.png', fullPage: true })
})

for (const width of [375, 1280]) {
  test(`SYNTHETIC API fixtures: full flow, keyboard, accessibility and layout ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    const errors: string[] = []; page.on('pageerror', e => errors.push(e.message))
    let attempts = 0
    const payloads: unknown[] = []
    await page.route('**/api/v1/**', async route => {
      const url = route.request().url()
      if (url.endsWith('/health')) return route.fulfill({ json: { status: 'ok' } })
      if (url.endsWith('/extract')) return route.fulfill({ json: extraction })
      payloads.push(route.request().postDataJSON()); attempts++
      return route.fulfill({ status: attempts === 1 ? 503 : 200, json: attempts === 1 ? providerError : report })
    })
    await page.goto('/')
    await expect(page).toHaveTitle('JEV Resume Analyzer')
    // Visible test-only label; never part of application code or a live success path.
    await page.evaluate(() => {
      const banner = document.createElement('p'); banner.textContent = 'SYNTHETIC API FIXTURE TEST · NOT LIVE RESULTS'
      banner.style.cssText = 'background:#fff4cc;color:#342800;padding:12px;text-align:center;font:14px sans-serif'
      document.body.prepend(banner)
    })
    async function audit() {
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      const results = await new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()
      expect(results.violations.map(v => ({ id: v.id, nodes: v.nodes.map(n => n.target) }))).toEqual([])
    }
    await audit()
    await page.screenshot({ path: `test-results/upload-${width}.png`, fullPage: true })
    await page.getByLabel('Choose CV file').setInputFiles(syntheticFile)
    await page.getByLabel('CV text').fill('Edited SYNTHETIC test CV')
    await page.getByText('Add a job posting').focus(); await page.keyboard.press('Enter')
    await page.getByLabel('Job posting', { exact: true }).fill('SYNTHETIC job posting')
    await audit()
    await page.screenshot({ path: `test-results/preview-${width}.png`, fullPage: true })
    await page.getByRole('button', { name: 'Analyse CV' }).click()
    await expect(page.getByRole('alert')).toContainText('preserved')
    await expect(page.getByLabel('CV text')).toHaveValue('Edited SYNTHETIC test CV')
    await expect(page.getByLabel('Job posting', { exact: true })).toHaveValue('SYNTHETIC job posting')
    await page.getByRole('button', { name: 'Analyse CV' }).click()
    await expect(page.getByText('Your CV, examined.')).toBeVisible()
    await page.getByText('Question & answer details').focus(); await page.keyboard.press('Enter')
    await expect(page.getByText('70.0%')).toBeVisible()
    await page.getByText('Request details & metrics').click()
    await audit()
    await page.screenshot({ path: `test-results/report-${width}.png`, fullPage: true })
    expect(payloads).toEqual(Array(2).fill({ cv_text: 'Edited SYNTHETIC test CV', job_text: 'SYNTHETIC job posting', mode: 'review' }))
    await page.getByRole('button', { name: 'Edit text & run a new review' }).click()
    await expect(page.getByText('Your CV, examined.')).toHaveCount(0)
    await page.getByRole('button', { name: 'Clear document & start over' }).click()
    await expect(page.getByLabel('Choose CV file')).toBeVisible()
    expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0])
    expect(errors).toEqual([])
  })
}
