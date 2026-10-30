import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

/*
 * pdf.js parses in a worker. Vite serves the worker as its own asset, so
 * parsing never blocks the UI thread, and the file is read from memory only.
 */
export const PDF_WORKER_URL = workerUrl

export type PdfJs = typeof import('pdfjs-dist')

export async function loadPdfJs(): Promise<PdfJs> {
  const pdfjs = await import('pdfjs-dist')
  pdfjs.GlobalWorkerOptions.workerSrc = PDF_WORKER_URL
  return pdfjs
}
