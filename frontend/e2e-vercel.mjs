import { chromium } from '@playwright/test'

const FIXTURE = '/root/projects/jra-worktrees/release/backend/tests/fixtures/two_page_resume.pdf'
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
const errors = []
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()) })
page.on('pageerror', (e) => errors.push(String(e)))

await page.goto('https://jev-web-one.vercel.app/', { waitUntil: 'networkidle' })
await page.setInputFiles('input[type=file]', FIXTURE)
await page.getByText('Check the extracted text.').waitFor({ timeout: 60000 })
await page.getByRole('button', { name: /Analyse CV/i }).click()
await page.waitForFunction(() => /TOTAL SCORE|Not scored/i.test(document.body.innerText), null, { timeout: 180000 })
await page.waitForTimeout(1500)

const text = await page.locator('body').innerText()
const i = text.indexOf('TOTAL SCORE')
console.log(text.slice(Math.max(0, i - 200), i + 500))
await page.screenshot({ path: '/root/.hermes/cache/scratch/jev-vercel-report.png' })
console.log('ERRORS:', errors.slice(0, 6).join(' | ') || 'none')
await browser.close()
