import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { it, expect, vi } from 'vitest'
import App from '../src/App'
import { extraction, report, providerError } from './contract/fixtures/responses'
import { validateFile, MAX_UPLOAD_BYTES } from '../src/features/upload/UploadStage'
function mockApi(analysis: () => Promise<Response> = async () => Response.json(report)) {
  const fetch = vi.fn((url: string) => url.endsWith('/health') ? Promise.resolve(Response.json({ status: 'ok' })) : url.endsWith('/extract') ? Promise.resolve(Response.json(extraction)) : analysis())
  vi.stubGlobal('fetch', fetch); return fetch
}
it('validates format, zero bytes and size before upload', () => {
  expect(validateFile(new File(['x'], 'bad.txt'))).toContain('PDF or DOCX')
  expect(validateFile(new File([], 'empty.pdf'))).toContain('empty')
  expect(validateFile(new File([new Uint8Array(MAX_UPLOAD_BYTES + 1)], 'large.pdf'))).toContain('10 MiB')
  expect(validateFile(new File(['x'], 'TEST.DOCX'))).toBeNull()
})
it('supports drop and rejects multiple files', async () => {
  const fetch = mockApi(); render(<App />)
  const zone = screen.getByText('Bring your document').parentElement!
  fireEvent.drop(zone, { dataTransfer: { files: [new File(['x'], 'a.pdf'), new File(['x'], 'b.pdf')] } })
  expect(screen.getByRole('alert').textContent).toContain('one document')
  fireEvent.drop(zone, { dataTransfer: { files: [new File(['x'], 'a.docx')] } })
  await screen.findByLabelText(/CV text/)
  expect(fetch.mock.calls.filter(([url]) => url.endsWith('/extract'))).toHaveLength(1)
})
it('preserves edited CV and posting on failure, retries explicitly, edits and resets', async () => {
  let attempts = 0
  const fetch = mockApi(async () => ++attempts === 1 ? Response.json(providerError, { status: 503 }) : Response.json(report))
  const user = userEvent.setup(); render(<App />)
  await user.upload(screen.getByLabelText('Choose CV file'), new File(['synthetic'], 'fixture.pdf'))
  const cv = await screen.findByLabelText(/CV text/)
  await user.clear(cv); await user.type(cv, 'Edited synthetic CV')
  await user.click(screen.getByText('Add a job posting'))
  await user.type(screen.getByLabelText('Job posting'), 'Synthetic posting')
  await user.click(screen.getByRole('button', { name: 'Analyse CV' }))
  await screen.findByRole('alert')
  expect((screen.getByLabelText(/CV text/) as HTMLTextAreaElement).value).toBe('Edited synthetic CV')
  expect((screen.getByLabelText('Job posting') as HTMLTextAreaElement).value).toBe('Synthetic posting')
  expect(screen.queryByText('Your CV, examined.')).toBeNull()
  await user.click(screen.getByRole('button', { name: 'Analyse CV' }))
  await screen.findByText('Your CV, examined.')
  expect(screen.getByText('Not available')).toBeTruthy()
  await user.click(screen.getByText('Question & answer details'))
  expect(screen.getByText('70.0%')).toBeTruthy()
  await user.click(screen.getByRole('button', { name: 'Edit text & run a new review' }))
  expect(screen.queryByText('Your CV, examined.')).toBeNull()
  expect((screen.getByLabelText(/CV text/) as HTMLTextAreaElement).value).toBe('Edited synthetic CV')
  await user.click(screen.getByRole('button', { name: 'Clear document & start over' }))
  expect(screen.queryByLabelText(/CV text/)).toBeNull()
  expect(localStorage.length).toBe(0); expect(sessionStorage.length).toBe(0)
  expect(fetch.mock.calls.filter(([url]) => url.endsWith('/analyses'))).toHaveLength(2)
})
it('disables duplicate submits and editing during requests', async () => {
  let resolve!: (r: Response) => void
  const fetch = mockApi(() => new Promise(r => { resolve = r }))
  render(<App />)
  fireEvent.change(screen.getByLabelText('Choose CV file'), { target: { files: [new File(['x'], 'fixture.pdf')] } })
  await screen.findByLabelText(/CV text/)
  const form = screen.getByRole('button', { name: 'Analyse CV' }).closest('form')!
  fireEvent.submit(form); fireEvent.submit(form)
  expect((screen.getByLabelText(/CV text/) as HTMLTextAreaElement).disabled).toBe(true)
  expect((screen.getByRole('button', { name: 'Analysing…' }) as HTMLButtonElement).disabled).toBe(true)
  expect(fetch.mock.calls.filter(([url]) => url.endsWith('/analyses'))).toHaveLength(1)
  await act(async () => resolve(Response.json(report)))
})
it('shows extraction errors without fake preview', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json(providerError, { status: 503 })))
  render(<App />)
  fireEvent.change(screen.getByLabelText('Choose CV file'), { target: { files: [new File(['x'], 'fixture.pdf')] } })
  await screen.findByRole('alert'); expect(screen.queryByLabelText(/CV text/)).toBeNull()
  await waitFor(() => expect(screen.getByText('Backend unavailable')).toBeTruthy())
})
