import { it, expect, vi } from 'vitest'
import { extractDocument, runAnalysis, checkHealth } from '../src/api/client'
import { extraction, report, providerError } from './contract/fixtures/responses'
it('sends a multipart file without setting boundary or credentials', async () => {
  const fetch = vi.fn().mockResolvedValue(Response.json(extraction)); vi.stubGlobal('fetch', fetch)
  await extractDocument(new File(['SYNTHETIC'], 'test.pdf'))
  const [url, init] = fetch.mock.calls[0]
  expect(url).toBe('/api/v1/documents/extract'); expect(init.body.get('file').name).toBe('test.pdf')
  expect(init.headers).toBeUndefined(); expect(init.credentials).toBe('omit')
})
it('sends confirmed text with review mode and optional posting', async () => {
  const fetch = vi.fn().mockResolvedValue(Response.json(report)); vi.stubGlobal('fetch', fetch)
  await runAnalysis({ cv_text: 'test', job_text: 'job', mode: 'review' })
  expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ cv_text: 'test', job_text: 'job', mode: 'review' })
})
it.each([413, 415, 422, 429, 502, 503, 504])('normalises HTTP %s without retry', async status => {
  const fetch = vi.fn().mockResolvedValue(Response.json(providerError, { status })); vi.stubGlobal('fetch', fetch)
  await expect(runAnalysis({ cv_text: 'test', mode: 'review' })).rejects.toMatchObject({ status, requestId: 'synthetic-error-id' })
  expect(fetch).toHaveBeenCalledTimes(1)
})
it('rejects malformed success and non-JSON failure without leaking body', async () => {
  const fetch = vi.fn().mockResolvedValueOnce(Response.json({ fake: true })).mockResolvedValueOnce(new Response('<html>private trace</html>', { status: 500 }))
  vi.stubGlobal('fetch', fetch)
  await expect(runAnalysis({ cv_text: 'test', mode: 'review' })).rejects.toMatchObject({ code: 'RESPONSE_INVALID' })
  await expect(checkHealth()).rejects.toMatchObject({ code: 'HTTP_500' })
})
it('handles network failure', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network')))
  await expect(checkHealth()).rejects.toMatchObject({ kind: 'network' })
})
it('times out and never retries a POST', async () => {
  const fetch = vi.fn((_url, init) => new Promise((_resolve, reject) => {
    init.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
  })); vi.stubGlobal('fetch', fetch)
  await expect(runAnalysis({ cv_text: 'test', mode: 'review' }, 5)).rejects.toMatchObject({ kind: 'timeout' })
  expect(fetch).toHaveBeenCalledTimes(1)
})
