import { layoutDocument } from './pdfLayout'
import type { PdfPageSource } from './pdfLayout'
import { loadPdfJs } from './pdfWorker'
import type { PagePreview } from './types'

/*
 * Page previews stay in this tab. pdf.js reads the uploaded File from memory,
 * draws each page to a canvas and reads the text layer from the same document.
 * The bytes are never uploaded and never stored.
 */

export type PreviewLoader = (file: File) => Promise<PagePreview[]>

/* Render at twice the point size so the pane stays sharp when zoomed. */
const PREVIEW_SCALE = 2
const MAX_PREVIEW_WIDTH = 1400

export function isPdf(file: File): boolean {
  return file.type === 'application/pdf' || /\.pdf$/i.test(file.name)
}

async function rasterisePdf(file: File): Promise<PagePreview[]> {
  const pdfjs = await loadPdfJs()
  const bytes = new Uint8Array(await file.arrayBuffer())
  const task = pdfjs.getDocument({ data: bytes })
  const document = await task.promise

  try {
    const pages: PagePreview[] = []
    const sources: PdfPageSource[] = []
    let aligned = true

    for (let number = 1; number <= document.numPages; number += 1) {
      const page = await document.getPage(number)
      const base = page.getViewport({ scale: 1 })
      const scale = Math.min(PREVIEW_SCALE, MAX_PREVIEW_WIDTH / base.width)
      const viewport = page.getViewport({ scale })

      const canvas = window.document.createElement('canvas')
      canvas.width = Math.max(1, Math.ceil(viewport.width))
      canvas.height = Math.max(1, Math.ceil(viewport.height))
      await page.render({ canvas, viewport }).promise

      pages.push({
        imageUrl: canvas.toDataURL('image/jpeg', 0.82),
        width: viewport.width,
        height: viewport.height,
      })
      /* Text item coordinates are unrotated page space. A rotated page would
       * need a different transform, so the document keeps the reported boxes. */
      if (base.rotation % 360 !== 0) aligned = false
      sources.push({
        textContent: await page.getTextContent(),
        height: base.height,
        width: base.width,
      })
    }

    if (aligned) {
      for (const section of layoutDocument(sources)) {
        const target = pages[section.page]
        if (!target) continue
        if (!target.sections) target.sections = []
        target.sections.push(section)
      }
    }

    return pages
  } finally {
    await task.destroy()
  }
}

export async function previewPages(
  file: File | null,
  load: PreviewLoader = rasterisePdf,
): Promise<PagePreview[]> {
  if (!file || !isPdf(file)) return []
  try {
    return await load(file)
  } catch {
    /* A scanned or damaged file has no preview. The pane keeps its current
     * empty state instead of drawing a box the text cannot support. */
    return []
  }
}
