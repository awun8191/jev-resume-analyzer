import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { extraction, multiReport, providerError } from '../contract/fixtures/responses'

const syntheticFile = {
  name: 'SYNTHETIC-fixture.pdf',
  mimeType: 'application/pdf',
  buffer: Buffer.from('SYNTHETIC TEST INPUT. Parser is mocked in this test.'),
}

const jevKeys = () => Array.from({ length: sessionStorage.length }, (_, i) => sessionStorage.key(i)!)
  .filter(key => key.startsWith('jev.'))

test('unavailable backend: keyboard upload, honest error, no report', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveTitle('JEV Resume Analyzer')
  await expect(page.getByText('Backend unavailable')).toBeVisible()

  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: 'Skip to content' })).toBeFocused()
  await page.keyboard.press('Tab')
  const fileInput = page.getByLabel('Choose CV file')
  await expect(fileInput).toBeFocused()

  const chooser = page.waitForEvent('filechooser')
  await page.keyboard.press('Enter')
  await (await chooser).setFiles(syntheticFile)

  await expect(page.getByRole('alert')).toContainText('HTTP 502')
  await expect(page.getByLabel('CV text')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'Report' })).toHaveCount(0)
  await page.screenshot({ path: 'test-results/real-backend-unavailable.png', fullPage: true })
})

for (const width of [375, 1280]) {
  test(`SYNTHETIC API fixtures: full flow, keyboard, accessibility and layout ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    const errors: string[] = []
    page.on('pageerror', e => errors.push(e.message))
    let attempts = 0
    const payloads: string[] = []
    await page.route('**/api/v1/**', async route => {
      const url = route.request().url()
      if (url.endsWith('/health')) return route.fulfill({ json: { status: 'ok' } })
      if (url.endsWith('/extract')) return route.fulfill({ json: extraction })
      payloads.push(route.request().postDataBuffer()?.toString('utf8') ?? '')
      attempts++
      return route.fulfill({
        status: attempts === 1 ? 503 : 200,
        json: attempts === 1 ? providerError : multiReport,
      })
    })

    await page.goto('/')
    await expect(page).toHaveTitle('JEV Resume Analyzer')
    // Visible test-only label; never part of application code or a live success path.
    await page.evaluate(() => {
      const banner = document.createElement('p')
      banner.textContent = 'SYNTHETIC API FIXTURE TEST / NOT LIVE RESULTS'
      banner.style.cssText = 'background:#fff4cc;color:#342800;padding:12px;text-align:center;font:14px sans-serif'
      document.body.prepend(banner)
    })

    async function audit() {
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      const smallTargets = await page.evaluate(() =>
        [...document.querySelectorAll('button:not(.box), summary')]
          .filter(el => {
            const rect = el.getBoundingClientRect()
            return rect.height > 0 && rect.height < 44
          })
          .map(el => (el.textContent || '').trim().slice(0, 40)))
      expect(smallTargets).toEqual([])
      const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
      expect(results.violations.map(v => ({ id: v.id, nodes: v.nodes.map(n => n.target) }))).toEqual([])
    }

    await audit()
    await page.screenshot({ path: `test-results/upload-${width}.png`, fullPage: true })

    await page.getByLabel('Choose CV file').setInputFiles(syntheticFile)
    await page.getByLabel('CV text').fill('Edited SYNTHETIC test CV')
    await page.locator('summary').filter({ hasText: 'Add a job posting' }).click()
    await page.getByLabel('Job posting', { exact: true }).fill('SYNTHETIC job posting')
    if (width < 900) {
      await page.getByRole('button', { name: 'Show document' }).click()
    }
    await expect(page.getByText('No page preview', { exact: true })).toBeVisible()
    await audit()
    await page.screenshot({ path: `test-results/preview-${width}.png`, fullPage: true })

    await page.getByRole('button', { name: 'Analyse CV' }).click()
    await expect(page.getByRole('alert')).toContainText('preserved')
    await expect(page.getByLabel('CV text')).toHaveValue('Edited SYNTHETIC test CV')
    await expect(page.getByLabel('Job posting', { exact: true })).toHaveValue('SYNTHETIC job posting')

    await page.getByRole('button', { name: 'Analyse CV' }).click()
    await expect(page.getByRole('heading', { name: 'Report' })).toBeVisible()
    await expect(page.locator('.score .score__value')).toContainText('65')
    await expect(page.locator('.score__flags')).toContainText('Content and layout')
    await expect(page.locator('.subscore')).toHaveCount(2)
    await expect(page.locator('.subscore[data-owner="structure"] .subscore__value')).toContainText('81')
    // The three highest findings are visible; the rest is behind one control.
    await expect(page.locator('.finding')).toHaveCount(3)
    await expect(page.getByRole('button', { name: 'Show all 4 findings' })).toBeVisible()
    await page.getByRole('button', { name: /All dimensions/ }).click()
    await expect(page.locator('.dim-group[data-owner="content"] .dim')).toHaveCount(3)
    await expect(page.locator('.dim-group[data-owner="structure"] .dim')).toHaveCount(2)
    await audit()
    await page.screenshot({ path: `test-results/report-${width}.png`, fullPage: true })

    // The document pane is collapsible below 900px and was opened above.
    await expect(page.getByText('Re-attach the file')).toHaveCount(0)
    // Three content findings plus two located structure checks.
    await expect(page.locator('.docpane__list button')).toHaveCount(5)

    // A structure check selects its row and turns the pane. The disclosure has
    // to be open first, because the row stays collapsed by default.
    await page.getByRole('button', { name: /Structure findings/ }).click()
    await page.getByRole('button', { name: 'Two column layout is dense. Major issue. Page 1.' }).click()
    await expect(page.locator('.docpane__list button[aria-pressed="true"]')).toContainText('Two column layout is dense')

    // A box selects its finding; a finding selects its box.
    await page.locator('.docpane__list button').first().click()
    await expect(page.getByRole('button', { name: /^Work clarity:/ }).first())
      .toHaveAttribute('aria-current', 'true')

    // A row is one line and opens its detail on tap.
    const row = page.getByRole('button', { name: /^Work clarity:/ }).first()
    await row.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByText('62.0%')).toBeVisible()
    await page.locator('summary').filter({ hasText: 'Request details' }).click()
    await audit()
    await page.screenshot({ path: `test-results/report-detail-${width}.png`, fullPage: true })

    expect(payloads).toHaveLength(2)
    for (const body of payloads) {
      expect(body).toContain('name="request"')
      expect(body).toContain('"cv_text":"Edited SYNTHETIC test CV"')
      expect(body).toContain('"job_text":"SYNTHETIC job posting"')
      expect(body).toContain('"mode":"review"')
      expect(body).toContain('name="file"')
      expect(body).toContain('filename="SYNTHETIC-fixture.pdf"')
    }
    expect(await page.evaluate(jevKeys)).toHaveLength(1)

    await page.getByRole('button', { name: 'Edit text and run a new review' }).click()
    await expect(page.getByRole('heading', { name: 'Report' })).toHaveCount(0)
    await page.getByRole('button', { name: 'New review' }).click()
    await page.getByRole('button', { name: 'Clear this tab' }).click()
    await expect(page.getByLabel('Choose CV file')).toBeVisible()
    expect(await page.evaluate(jevKeys)).toEqual([])
    expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0])
    expect(errors).toEqual([])
  })
}
