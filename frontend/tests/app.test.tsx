import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { it, expect, vi } from 'vitest'
import App from '../src/App'
import { extraction, report, providerError } from './contract/fixtures/responses'
import { validateFile, MAX_UPLOAD_BYTES } from '../src/features/upload/UploadStage'

function mockApi(analysis: () => Promise<Response> = async () => Response.json(report)) {
  const fetch = vi.fn((url: string) =>
    url.endsWith('/health')
      ? Promise.resolve(Response.json({ status: 'ok' }))
      : url.endsWith('/extract')
        ? Promise.resolve(Response.json(extraction))
        : analysis())
  vi.stubGlobal('fetch', fetch)
  return fetch
}

const dropzone = () => screen.getByText('Drop a PDF or DOCX here.').closest('.drop')!
const jevKeys = () => Array.from({ length: sessionStorage.length }, (_, i) => sessionStorage.key(i)!)
  .filter(key => key.startsWith('jev.'))

it('validates format, zero bytes and size before upload', () => {
  expect(validateFile(new File(['x'], 'bad.txt'))).toContain('PDF or DOCX')
  expect(validateFile(new File([], 'empty.pdf'))).toContain('empty')
  expect(validateFile(new File([new Uint8Array(MAX_UPLOAD_BYTES + 1)], 'large.pdf'))).toContain('4 MB')
  expect(validateFile(new File(['x'], 'TEST.DOCX'))).toBeNull()
})

it('accepts a dropped document and rejects several files at once', async () => {
  const fetch = mockApi()
  render(<App />)
  fireEvent.drop(dropzone(), { dataTransfer: { files: [new File(['x'], 'a.pdf'), new File(['x'], 'b.pdf')] } })
  expect(screen.getByRole('alert').textContent).toContain('one document')
  fireEvent.drop(dropzone(), { dataTransfer: { files: [new File(['x'], 'a.docx')] } })
  await screen.findByLabelText('CV text')
  expect(fetch.mock.calls.filter(([url]) => String(url).endsWith('/extract'))).toHaveLength(1)
})

it('preserves edited text and posting after a failure, reports, edits and resets', async () => {
  let attempts = 0
  const fetch = mockApi(async () =>
    ++attempts === 1 ? Response.json(providerError, { status: 503 }) : Response.json(report))
  const user = userEvent.setup()
  render(<App />)

  await user.upload(screen.getByLabelText('Choose CV file'), new File(['synthetic'], 'fixture.pdf'))
  const cv = await screen.findByLabelText('CV text')
  await user.clear(cv)
  await user.type(cv, 'Edited synthetic CV')
  await user.click(screen.getByText('Add a job posting'))
  await user.type(screen.getByLabelText('Job posting'), 'Synthetic posting')
  await user.click(screen.getByRole('button', { name: 'Analyse CV' }))

  await screen.findByRole('alert')
  expect((screen.getByLabelText('CV text') as HTMLTextAreaElement).value).toBe('Edited synthetic CV')
  expect((screen.getByLabelText('Job posting') as HTMLTextAreaElement).value).toBe('Synthetic posting')
  expect(screen.queryByRole('heading', { name: 'The report.' })).toBeNull()

  await user.click(screen.getByRole('button', { name: 'Analyse CV' }))
  await screen.findByRole('heading', { name: 'The report.' })
  expect(screen.getByText('71')).toBeTruthy()
  await user.click(screen.getByText('Question and answer detail'))
  expect(screen.getByText('70.0%')).toBeTruthy()

  const stored = JSON.parse(sessionStorage.getItem('jev.state.v1')!)
  expect(stored.stage).toBe('result')
  expect(stored.cvText).toBe('Edited synthetic CV')
  expect(stored.jobText).toBe('Synthetic posting')
  expect(stored.report.analysis_id).toBe('synthetic-test-request')

  await user.click(screen.getByRole('button', { name: 'Edit text and run a new review' }))
  expect(screen.queryByRole('heading', { name: 'The report.' })).toBeNull()
  expect((screen.getByLabelText('CV text') as HTMLTextAreaElement).value).toBe('Edited synthetic CV')

  await user.click(screen.getByRole('button', { name: 'Clear document and start over' }))
  expect(screen.queryByLabelText('CV text')).toBeNull()
  expect(jevKeys()).toEqual([])
  expect(localStorage.length).toBe(0)
  expect(fetch.mock.calls.filter(([url]) => String(url).endsWith('/analyses'))).toHaveLength(2)
})

it('restores the report and text from this tab after a reload', async () => {
  mockApi()
  const user = userEvent.setup()
  const view = render(<App />)

  await user.upload(screen.getByLabelText('Choose CV file'), new File(['synthetic'], 'fixture.pdf'))
  await screen.findByLabelText('CV text')
  await user.click(screen.getByRole('button', { name: 'Analyse CV' }))
  await screen.findByRole('heading', { name: 'The report.' })

  view.unmount()
  render(<App />)

  expect(await screen.findByRole('heading', { name: 'The report.' })).toBeTruthy()
  expect(screen.getByText('Re-attach the file to show the page')).toBeTruthy()
  expect(screen.getAllByText('fixture.pdf').length).toBeGreaterThan(0)
})

it('disables duplicate submits and locks the text fields during a request', async () => {
  let resolve!: (r: Response) => void
  const fetch = mockApi(() => new Promise(r => { resolve = r }))
  render(<App />)
  fireEvent.change(screen.getByLabelText('Choose CV file'), { target: { files: [new File(['x'], 'fixture.pdf')] } })
  await screen.findByLabelText('CV text')
  const form = screen.getByRole('button', { name: 'Analyse CV' }).closest('form')!
  fireEvent.submit(form)
  fireEvent.submit(form)
  expect((screen.getByLabelText('CV text') as HTMLTextAreaElement).disabled).toBe(true)
  expect((screen.getByRole('button', { name: 'Analysing' }) as HTMLButtonElement).disabled).toBe(true)
  expect(screen.getByRole('button', { name: 'Clear document and start over' })).toHaveProperty('disabled', true)
  expect(fetch.mock.calls.filter(([url]) => String(url).endsWith('/analyses'))).toHaveLength(1)
  await act(async () => resolve(Response.json(report)))
})

it('shows an extraction error without a fake preview', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json(providerError, { status: 503 })))
  render(<App />)
  fireEvent.change(screen.getByLabelText('Choose CV file'), { target: { files: [new File(['x'], 'fixture.pdf')] } })
  await screen.findByRole('alert')
  expect(screen.queryByLabelText('CV text')).toBeNull()
  await waitFor(() => expect(screen.getByText('Backend unavailable')).toBeTruthy())
})

it('drops a stored report from before scores existed and returns to check text', async () => {
  mockApi()
  const oldReport = {
    analysis_id: 'synthetic-old-report', rubric_version: 'v2', model: 'synthetic-test-model',
    findings: [], overview: { questions_total: 0, questions_answered: 0, questions_assessable: 0, rating: null },
    warnings: [], metrics: null,
  }
  sessionStorage.setItem('jev.state.v1', JSON.stringify({
    version: 1, stage: 'result', fileName: 'old.pdf',
    extraction, cvText: extraction.text, jobText: '', report: oldReport, selectedId: 'q-old',
  }))

  render(<App />)

  expect(await screen.findByLabelText('CV text')).toBeTruthy()
  expect(screen.queryByRole('heading', { name: 'The report.' })).toBeNull()
  expect(screen.getByText(/older version/)).toBeTruthy()
  expect((screen.getByLabelText('CV text') as HTMLTextAreaElement).value).toBe(extraction.text)

  const stored = JSON.parse(sessionStorage.getItem('jev.state.v1')!)
  expect(stored.stage).toBe('reviewing')
  expect(stored.report).toBeNull()
  expect(stored.selectedId).toBeNull()
})

it('keeps a stored report that matches the current shape', async () => {
  mockApi()
  sessionStorage.setItem('jev.state.v1', JSON.stringify({
    version: 1, stage: 'result', fileName: 'current.pdf',
    extraction, cvText: extraction.text, jobText: '', report, selectedId: null,
  }))

  render(<App />)

  expect(await screen.findByRole('heading', { name: 'The report.' })).toBeTruthy()
  expect(screen.queryByText(/older version/)).toBeNull()
  expect(screen.getByText('71')).toBeTruthy()
})

it('sends the uploaded PDF as a second multipart part', async () => {
  const fetch = mockApi()
  const user = userEvent.setup()
  render(<App />)

  await user.upload(screen.getByLabelText('Choose CV file'), new File(['synthetic'], 'fixture.pdf'))
  await screen.findByLabelText('CV text')
  await user.click(screen.getByRole('button', { name: 'Analyse CV' }))
  await screen.findByRole('heading', { name: 'The report.' })

  const call = fetch.mock.calls.find(([url]) => String(url).endsWith('/analyses'))!
  const body = call[1].body as FormData
  expect(body).toBeInstanceOf(FormData)
  expect(body.has('request')).toBe(true)
  expect(body.has('file')).toBe(true)
  expect((body.get('file') as File).name).toBe('fixture.pdf')
})
