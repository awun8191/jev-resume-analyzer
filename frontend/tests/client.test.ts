import { it, expect, vi } from 'vitest'
import { extractDocument, runAnalysis, checkHealth, analysisForm, apiBaseUrl, apiUrl } from '../src/api/client'
import { extraction, report, providerError } from './contract/fixtures/responses'

const pdf = () => new File(['SYNTHETIC PDF'], 'fixture.pdf', { type: 'application/pdf' })
type Fetched = (url: string, init: RequestInit) => Promise<Response>
const reply = (body: unknown, status = 200) =>
  vi.fn<Fetched>(() => Promise.resolve(Response.json(body, { status })))
const readBlob = (blob: Blob) => new Promise<string>((resolve, reject) => {
  const reader = new FileReader()
  reader.onload = () => resolve(String(reader.result))
  reader.onerror = () => reject(reader.error)
  reader.readAsText(blob)
})

it('sends a multipart file without setting boundary or credentials', async () => {
  const fetch = reply(extraction); vi.stubGlobal('fetch', fetch)
  await extractDocument(new File(['SYNTHETIC'], 'test.pdf'))
  const [url, init] = fetch.mock.calls[0]
  expect(url).toBe('/api/v1/documents/extract'); expect(init.body.get('file').name).toBe('test.pdf')
  expect(init.headers).toBeUndefined(); expect(init.credentials).toBe('omit')
})

it('posts the request JSON and the PDF as multipart parts', async () => {
  const fetch = reply(report); vi.stubGlobal('fetch', fetch)
  await runAnalysis({ cv_text: 'test', job_text: 'job', mode: 'review' }, pdf())

  const [url, init] = fetch.mock.calls[0]
  expect(url).toBe('/api/v1/analyses')
  expect(init.body).toBeInstanceOf(FormData)
  // The browser sets the boundary, so no content type is pinned by hand.
  expect(init.headers).toBeUndefined()
  expect(init.credentials).toBe('omit')

  const body = init.body as FormData
  expect([...body.keys()].sort()).toEqual(['file', 'request'])
  expect(JSON.parse(await readBlob(body.get('request') as Blob))).toEqual({
    cv_text: 'test', job_text: 'job', mode: 'review',
  })
  expect((body.get('file') as File).name).toBe('fixture.pdf')
  expect((body.get('file') as File).size).toBeGreaterThan(0)
})

it('omits the file part for a DOCX upload and for no file', async () => {
  const fetch = reply(report); vi.stubGlobal('fetch', fetch)
  await runAnalysis({ cv_text: 'test', mode: 'review' }, new File(['SYNTHETIC'], 'cv.docx'))
  await runAnalysis({ cv_text: 'test', mode: 'review' }, null)

  for (const [, init] of fetch.mock.calls) {
    const body = init.body as FormData
    expect(body.has('request')).toBe(true)
    expect(body.has('file')).toBe(false)
  }
})

it('sends confirmed text with review mode and optional posting', async () => {
  const body = analysisForm({ cv_text: 'test', job_text: 'job', mode: 'review' }, null)
  expect([...body.keys()]).toEqual(['request'])
  expect(JSON.parse(await readBlob(body.get('request') as Blob))).toEqual({
    cv_text: 'test', job_text: 'job', mode: 'review',
  })
})

it('falls back to a JSON body when the server rejects multipart', async () => {
  const fetch = vi.fn<Fetched>()
    .mockResolvedValueOnce(Response.json(providerError, { status: 415 }))
    .mockResolvedValueOnce(Response.json(report))
  vi.stubGlobal('fetch', fetch)

  const result = await runAnalysis({ cv_text: 'test', mode: 'review' }, pdf())
  expect(result.analysis_id).toBe(report.analysis_id)
  expect(fetch).toHaveBeenCalledTimes(2)
  expect(fetch.mock.calls[1][1].body).toBe('{"cv_text":"test","mode":"review"}')
  expect(fetch.mock.calls[1][1].headers).toEqual({ 'Content-Type': 'application/json' })
})

it('does not fall back on any other failure', async () => {
  const fetch = reply(providerError, 503)
  vi.stubGlobal('fetch', fetch)
  await expect(runAnalysis({ cv_text: 'test', mode: 'review' }, pdf())).rejects.toMatchObject({ status: 503 })
  expect(fetch).toHaveBeenCalledTimes(1)
})

it.each([413, 422, 429, 502, 503, 504])('normalises HTTP %s without retry', async status => {
  const fetch = reply(providerError, status); vi.stubGlobal('fetch', fetch)
  await expect(runAnalysis({ cv_text: 'test', mode: 'review' })).rejects.toMatchObject({ status, requestId: 'synthetic-error-id' })
  expect(fetch).toHaveBeenCalledTimes(1)
})
it('rejects malformed success and non-JSON failure without leaking body', async () => {
  const fetch = vi.fn<Fetched>().mockResolvedValueOnce(Response.json({ fake: true })).mockResolvedValueOnce(new Response('<html>private trace</html>', { status: 500 }))
  vi.stubGlobal('fetch', fetch)
  await expect(runAnalysis({ cv_text: 'test', mode: 'review' })).rejects.toMatchObject({ code: 'RESPONSE_INVALID' })
  await expect(checkHealth()).rejects.toMatchObject({ code: 'HTTP_500' })
})
it('handles network failure', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network')))
  await expect(checkHealth()).rejects.toMatchObject({ kind: 'network' })
})
it('times out and never retries a POST', async () => {
  const fetch = vi.fn<Fetched>((_url, init) => new Promise<Response>((_resolve, reject) => {
    init.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
  })); vi.stubGlobal('fetch', fetch)
  await expect(runAnalysis({ cv_text: 'test', mode: 'review' }, null, 5)).rejects.toMatchObject({ kind: 'timeout' })
  expect(fetch).toHaveBeenCalledTimes(1)
})

it('joins the API base without a double slash', () => {
  expect(apiBaseUrl(undefined)).toBe('')
  expect(apiBaseUrl('')).toBe('')
  expect(apiBaseUrl('   ')).toBe('')
  expect(apiBaseUrl('https://api.example.com')).toBe('https://api.example.com')
  expect(apiBaseUrl('https://api.example.com/')).toBe('https://api.example.com')
  expect(apiBaseUrl('https://api.example.com//')).toBe('https://api.example.com')
  expect(apiBaseUrl(' https://api.example.com/ ')).toBe('https://api.example.com')
  expect(`${apiBaseUrl('https://api.example.com/')}/api/v1/health`).toBe('https://api.example.com/api/v1/health')
})

it('uses a relative URL when no API base is configured', () => {
  expect(apiUrl('/health')).toBe('/api/v1/health')
  expect(apiUrl('/analyses')).toBe('/api/v1/analyses')
})

it('prefixes every request with VITE_API_BASE_URL when it is set', async () => {
  vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com/')
  vi.resetModules()
  try {
    const mod = await import('../src/api/client')
    const fetch = vi.fn<Fetched>((url) => Promise.resolve(
      Response.json(url.endsWith('/health') ? { status: 'ok' } : extraction)))
    vi.stubGlobal('fetch', fetch)
    await mod.checkHealth()
    await mod.extractDocument(new File(['SYNTHETIC'], 'test.pdf'))
    expect(fetch.mock.calls.map(([url]) => url)).toEqual([
      'https://api.example.com/api/v1/health',
      'https://api.example.com/api/v1/documents/extract',
    ])
  } finally {
    vi.unstubAllEnvs()
    vi.resetModules()
  }
})

