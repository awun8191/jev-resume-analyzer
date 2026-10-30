import type { FindingBox } from '../../api/schema'
import type { PageSection } from './pdfLayout'

export interface PagePreview {
  imageUrl?: string
  width?: number
  height?: number
  sections?: PageSection[]
}

/* One drawable entry, from either score. `state` is already a word, so the pane
 * never has to interpret a rubric answer or a severity. `kind` separates content
 * findings from structure checks. */
export interface BoxFinding {
  id: string
  kind: 'content' | 'structure'
  page: number | null
  box: FindingBox | null
  section?: string | null
  label: string
  state: string
  severity: string | null
}
