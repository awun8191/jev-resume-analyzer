import { useState } from 'react'
import type { AnalysisReport, Extraction } from './api/schema'

export interface AppFailure { title: string; detail: string; requestId: string | null }
export type Stage = 'empty' | 'extracting' | 'reviewing' | 'analysing' | 'result'
export function useAppState() {
  const [stage, setStage] = useState<Stage>('empty')
  const [fileName, setFileName] = useState('')
  const [extraction, setExtraction] = useState<Extraction | null>(null)
  const [cvText, setCvText] = useState('')
  const [jobText, setJobText] = useState('')
  const [report, setReport] = useState<AnalysisReport | null>(null)
  const [error, setError] = useState<AppFailure | null>(null)
  function reset() {
    setStage('empty'); setFileName(''); setExtraction(null); setCvText('')
    setJobText(''); setReport(null); setError(null)
  }
  function edit() { setReport(null); setError(null); setStage('reviewing') }
  return { stage, setStage, fileName, setFileName, extraction, setExtraction,
    cvText, setCvText, jobText, setJobText, report, setReport, error, setError, reset, edit }
}
