import type { AnswerCategory, FindingBox } from '../../api/schema'
import type { PageSection } from './pdfLayout'

export interface PagePreview {
  imageUrl?: string
  width?: number
  height?: number
  sections?: PageSection[]
}

export interface BoxFinding {
  id: string
  page: number | null
  box: FindingBox | null
  section?: string | null
  label: string
  answer: AnswerCategory
  severity: string | null
}
