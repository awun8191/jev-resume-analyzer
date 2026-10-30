import { z } from 'zod'
import { AnalysisReportSchema, AnalysisRequestSchema, ErrorEnvelopeSchema,
  ExtractionSchema, HealthSchema, type AnalysisRequest } from './schema'

export type ApiErrorKind = 'api' | 'network' | 'timeout' | 'invalid_response'
export class ApiError extends Error {
  readonly kind: ApiErrorKind
  readonly code: string
  readonly retryable: boolean
  readonly requestId: string | null
  readonly status: number | null
  constructor(p: { kind: ApiErrorKind; code: string; message: string; retryable: boolean;
    requestId?: string | null; status?: number | null }) {
    super(p.message); this.name = 'ApiError'; this.kind = p.kind; this.code = p.code
    this.retryable = p.retryable; this.requestId = p.requestId ?? null; this.status = p.status ?? null
  }
}

/* Relative URLs only. No keys, provider SDK, storage, body logging or automatic retries. */

/* Empty means same origin, which is the Vite dev proxy. A preview deployment
 * sets VITE_API_BASE_URL to the API preview URL. Trailing slashes are stripped
 * so the join below never produces a double slash. */
export function apiBaseUrl(raw: string | undefined): string {
  return (raw ?? '').trim().replace(/\/+$/, '')
}
export const API_BASE_URL = apiBaseUrl(import.meta.env.VITE_API_BASE_URL)
export const apiUrl = (path: string) => `${API_BASE_URL}/api/v1${path}`

async function request<T>(path: string, schema: z.ZodType<T, z.ZodTypeDef, unknown>, init: RequestInit, timeoutMs: number): Promise<T> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const response = await fetch(apiUrl(path), { ...init, signal: controller.signal, credentials: 'omit' })
    let raw: unknown
    try { raw = await response.json() }
    catch (error) { if (controller.signal.aborted) throw error; raw = undefined }
    if (!response.ok) {
      const parsed = ErrorEnvelopeSchema.safeParse(raw)
      if (parsed.success) throw new ApiError({ kind: 'api', code: parsed.data.error.code,
        message: parsed.data.error.message, retryable: parsed.data.error.retryable,
        requestId: parsed.data.request_id, status: response.status })
      throw new ApiError({ kind: 'api', code: `HTTP_${response.status}`, status: response.status,
        message: `The analysis server returned HTTP ${response.status}. Try again in a moment.`,
        retryable: response.status >= 500 || response.status === 429 })
    }
    const parsed = schema.safeParse(raw)
    if (!parsed.success) throw new ApiError({ kind: 'invalid_response', code: 'RESPONSE_INVALID',
      message: 'The server response did not match the API contract. No report was inferred.', retryable: false, status: response.status })
    return parsed.data
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (controller.signal.aborted) throw new ApiError({ kind: 'timeout', code: 'REQUEST_TIMEOUT',
      message: 'The request timed out. The server may still be processing it. A retry may incur another provider charge.', retryable: true })
    throw new ApiError({ kind: 'network', code: 'NETWORK_UNREACHABLE',
      message: 'Could not reach the analysis server. Check the connection and try again.', retryable: true })
  } finally { clearTimeout(timer) }
}
export function checkHealth(timeoutMs = 10_000) {
  return request('/health', HealthSchema, { method: 'GET' }, timeoutMs)
}
export function extractDocument(file: File, timeoutMs = 60_000) {
  const body = new FormData(); body.append('file', file)
  return request('/documents/extract', ExtractionSchema, { method: 'POST', body }, timeoutMs)
}

/* Only a PDF can be laid out by the structure route. A DOCX request sends the
 * text alone, which returns a content only report. */
export function isPdfUpload(file: File): boolean {
  return file.type === 'application/pdf' || /\.pdf$/i.test(file.name)
}

/* The workspace shape: one `request` part with the JSON body and, for a PDF, one
 * `file` part with the original bytes. The browser owns the boundary header. */
export function analysisForm(payload: AnalysisRequest, file: File | null): FormData {
  const body = new FormData()
  const request = AnalysisRequestSchema.parse(payload)
  body.append('request', new Blob([JSON.stringify(request)], { type: 'application/json' }), 'request.json')
  if (file && isPdfUpload(file)) body.append('file', file, file.name)
  return body
}

/* A server that predates the multipart route answers 415 for it. That one case
 * falls back to the JSON body, which still returns a content only report. No
 * setting, no retry loop: one fallback attempt and nothing more. */
function multipartUnsupported(error: ApiError): boolean {
  if (error.status === 415) return true
  return error.code === 'MULTIPART_UNSUPPORTED' || error.code === 'UNSUPPORTED_MEDIA_TYPE'
}

export async function runAnalysis(
  payload: AnalysisRequest,
  file: File | null = null,
  timeoutMs = 120_000,
) {
  const body = analysisForm(payload, file)
  try {
    return await request('/analyses', AnalysisReportSchema, { method: 'POST', body }, timeoutMs)
  } catch (error) {
    if (!(error instanceof ApiError) || !multipartUnsupported(error)) throw error
    /* Each attempt has its own timeout. The fallback is one request, never a
     * billable retry of a request the server already accepted. */
    return request('/analyses', AnalysisReportSchema, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(AnalysisRequestSchema.parse(payload)),
    }, timeoutMs)
  }
}
