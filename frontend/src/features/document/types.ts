import type { AnswerCategory, FindingBox } from '../../api/schema'

export interface PagePreview {
  imageUrl?: string
}

export interface BoxFinding {
  id: string
  page: number
  box: FindingBox
  label: string
  answer: AnswerCategory
  severity: string | null
}
