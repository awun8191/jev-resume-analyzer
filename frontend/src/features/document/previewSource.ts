import type { PagePreview } from './types'

/*
 * Seam for page previews.
 *
 * This branch does not rasterise PDFs. Page images are produced locally in a
 * later integration branch, most likely with pdf.js reading the in-memory File
 * and handing back object URLs. Nothing here sends the file anywhere, and no
 * image is stored.
 */
export function previewPages(_file: File | null): PagePreview[] {
  return []
}
