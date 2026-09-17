import { z } from 'zod'
const number = z.number().finite()
const box = z.array(number).length(4)
export const EvidenceSchema = z.object({
  version: z.literal('1'), source_text_sha256: z.string().regex(/^[a-f0-9]{64}$/),
  source_format: z.enum(['pdf', 'docx']),
  pages: z.array(z.object({
    number: z.number().int().positive(), width_pt: number.nullable(), height_pt: number.nullable(),
    rotation: z.number().int().nullable(), margins_pt: box.nullable(),
    margin_kind: z.enum(['configured', 'estimated_content_whitespace', 'not_assessed']),
  })).max(100),
  spans: z.array(z.object({
    id: z.string(), text: z.string(), page: z.number().int().positive().nullable(),
    bbox: box.nullable(), font_name: z.string().nullable(), font_size_pt: number.nullable(),
    location: z.string(), alignment: z.string().nullable(),
  })).max(5000),
  links: z.array(z.object({
    label: z.string(), target: z.string().nullable(), page: z.number().int().positive().nullable(),
    bbox: box.nullable(), kind: z.enum(['external', 'internal', 'unresolved']),
  })).max(500), limitations: z.array(z.string()).max(30),
})
