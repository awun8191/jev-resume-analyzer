import { ApiError } from './api/client'
import type { AppFailure } from './appState'
export function failureFromUnknown(error: unknown): AppFailure {
  return {
    title: 'The request did not complete',
    detail: error instanceof ApiError ? error.message : 'An unexpected client error occurred. Please try again.',
    requestId: error instanceof ApiError ? error.requestId : null,
  }
}
