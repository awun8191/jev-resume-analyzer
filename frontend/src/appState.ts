import { useEffect, useState } from 'react'
import { z } from 'zod'
import { AnalysisReportSchema, ExtractionSchema } from './api/schema'
import type { AnalysisReport, Extraction } from './api/schema'

export interface AppFailure {
  title: string
  detail: string
  requestId: string | null
}

export type Stage = 'empty' | 'extracting' | 'reviewing' | 'analysing' | 'result'

/*
 * State lives in sessionStorage, in this tab only. Nothing is written to
 * localStorage, IndexedDB, cookies or the backend, and the file bytes are never
 * stored. One versioned key keeps an old tab from crashing on a schema change.
 */
export const STORAGE_KEY = 'jev.state.v1'
const STORAGE_PREFIX = 'jev.'

const PersistedSchema = z.object({
  version: z.literal(1),
  stage: z.enum(['empty', 'extracting', 'reviewing', 'analysing', 'result']),
  fileName: z.string(),
  extraction: ExtractionSchema.nullable(),
  cvText: z.string(),
  jobText: z.string(),
  report: AnalysisReportSchema.nullable(),
  selectedId: z.string().nullable(),
})

type Persisted = z.infer<typeof PersistedSchema>

const EMPTY: Persisted = {
  version: 1,
  stage: 'empty',
  fileName: '',
  extraction: null,
  cvText: '',
  jobText: '',
  report: null,
  selectedId: null,
}

function isBlank(state: Persisted) {
  return state.stage === 'empty' && !state.extraction && !state.report
    && !state.cvText && !state.jobText && !state.fileName
}

function clearStored() {
  try {
    for (let index = sessionStorage.length - 1; index >= 0; index -= 1) {
      const key = sessionStorage.key(index)
      if (key && key.startsWith(STORAGE_PREFIX)) sessionStorage.removeItem(key)
    }
  } catch {
    // Storage is unavailable. In-memory state is unaffected.
  }
}

function load(): Persisted {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return EMPTY
    const parsed = PersistedSchema.safeParse(JSON.parse(raw))
    if (!parsed.success) {
      sessionStorage.removeItem(STORAGE_KEY)
      return EMPTY
    }
    const state = parsed.data
    // A request cannot resume after a reload, and a report needs its extraction.
    if (state.stage === 'extracting' || state.stage === 'analysing') {
      return { ...state, stage: state.extraction ? 'reviewing' : 'empty', selectedId: null }
    }
    if (state.stage === 'result' && !state.report) {
      return { ...state, stage: state.extraction ? 'reviewing' : 'empty', selectedId: null }
    }
    if (state.stage !== 'empty' && !state.extraction) return { ...EMPTY, fileName: state.fileName }
    return state
  } catch {
    return EMPTY
  }
}

export function useAppState() {
  const [state, setState] = useState<Persisted>(load)
  const [error, setError] = useState<AppFailure | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [storageNotice, setStorageNotice] = useState<string | null>(null)

  useEffect(() => {
    if (isBlank(state)) {
      clearStored()
      return
    }
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state))
      setStorageNotice(null)
    } catch {
      setStorageNotice('This tab cannot save any more state. Your text is still in memory until the tab closes.')
    }
  }, [state])

  function update(patch: Partial<Persisted>) {
    setState(current => ({ ...current, ...patch }))
  }

  function reset() {
    setState(EMPTY)
    setError(null)
    setFile(null)
    setStorageNotice(null)
    clearStored()
  }

  function edit() {
    setError(null)
    setState(current => ({
      ...current,
      report: null,
      selectedId: null,
      stage: current.extraction ? 'reviewing' : 'empty',
    }))
  }

  function startUpload(next: File) {
    clearStored()
    setFile(next)
    setError(null)
    setState({ ...EMPTY, stage: 'extracting', fileName: next.name })
  }

  function attachFile(next: File) {
    setFile(next)
  }

  function selectFinding(id: string | null) {
    setState(current => ({ ...current, selectedId: id }))
  }

  return {
    stage: state.stage,
    setStage: (stage: Stage) => update({ stage }),
    fileName: state.fileName,
    setFileName: (fileName: string) => update({ fileName }),
    extraction: state.extraction as Extraction | null,
    setExtraction: (extraction: Extraction) => update({ extraction }),
    cvText: state.cvText,
    setCvText: (cvText: string) => update({ cvText }),
    jobText: state.jobText,
    setJobText: (jobText: string) => update({ jobText }),
    report: state.report as AnalysisReport | null,
    setReport: (report: AnalysisReport | null) => update({ report }),
    selectedId: state.selectedId,
    selectFinding,
    error,
    setError,
    storageNotice,
    file,
    startUpload,
    attachFile,
    reset,
    edit,
  }
}
