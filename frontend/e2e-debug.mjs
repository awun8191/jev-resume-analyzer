import { chromium } from '@playwright/test'

const FIXTURE = '/root/projects/jra-worktrees/release/backend/tests/fixtures/two_page_resume.pdf'
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
page.on('console', (m) => console.log('CONSOLE', m.type(), m.text().slice(0, 300)))
page.on('pageerror', (e) => console.log('PAGEERROR', String(e).slice(0, 300)))
page.on('requestfailed', (r) => console.log('REQFAIL', r.url(), r.failure()?.errorText))
page.on('response', async (r) => {
  if (r.url().includes('/api/')) console.log('RESP', r.status(), r.url(), (await r.text().catch(() => '')).slice(0, 300))
})

await page.goto('https://jev-web-one.vercel.app/', { waitUntil: 'networkidle' })
await page.setInputFiles('input[type=file]', FIXTURE)
await page.waitForTimeout(12000)
console.log('--- BODY ---')
console.log((await page.locator('body').innerText()).slice(0, 800))
await browser.close()
