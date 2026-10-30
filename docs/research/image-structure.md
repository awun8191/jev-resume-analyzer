# Assessing a resume as an image: TypeSafe images, Box, and a structure score

Status: research and spike complete. Not wired into the analysis flow.
Branch: `feat/image-structure`.
Model used for every measurement below: `jev-1.14.0`, returned by the provider.

This document answers one question: what can the TypeSafe image route tell us about
document structure and layout, and what must we build around it to produce a
defensible structure score.

## 1. Summary

The image route works. A PDF page can be rendered to PNG, sent in one multipart
request, and answered with Box, Noul and Choice questions in about 260 to 410 ms.

Presence and layout questions are reliable. Section boxes and formatting boxes return
valid coordinates, but their confidence is low: the highest value observed in 60 Box
answers was 0.59, and the median was about 0.17. The provider labels images and Box as
"dreamer-ready", not production ready.

Therefore the recommended design uses the image route for the structure score, uses
Noul and Choice answers for the points, and uses Box answers only as optional
highlighting when confidence is high enough. It never derives a deduction from a box
alone unless the box is confident.

## 2. What the image route can and cannot do

Can do:

- Render a page, read it as an image, and answer questions about what is visible.
- Return one bounding box per Box question, as fractions of the image.
- Report confidence for each Box answer.
- Answer yes/no (Noul) and multiple-choice (Choice) questions about the same image.

Cannot do:

- Report "not found" for a Box. A Box question about an absent element still returns
  four edges. Pair every Box with a Noul.
- Return more than one box per question. Ask one question per target.
- Accept an image outside the pixel limits. The API rejects it, it never resizes.
- Guarantee stable request or answer shape between releases.

Sources: <https://docs.typesafe.ai/images>, <https://docs.typesafe.ai/primitives/box>.

## 3. Exact request shape

One image request has four top-level fields: `model`, `state`, `assets` and
`questions`. The `assets` map holds each image once, keyed by a reference string.
Every reference must appear in `state`, in `instructions` or in `criteria`.

The header `TypeSafe-Danger-Zone-Images: true` is mandatory. Without it the API
returns 400 for any request that contains an image or a Box question.

### 3.1 Transport

Multipart is recommended. The JSON body is the first part, named `request`. Each image
is a separate file part with content type `image/png`, `image/jpeg`, `image/jpg` or
`application/octet-stream`. Part names must be unique, and `request` is reserved.

Base64 works and is simpler to log, but it adds about one third to each image and that
size counts against the 32 MiB body limit. Use it only when multipart is not possible.

The spike uses multipart for every measured run below. Both transports build the same
`assets` entries; only `part` versus `format` and `data_base64` changes.

### 3.2 Measured body

The spike sends this shape for a two-page resume:

```json
{
  "model": "jev-1.14.0",
  "state": {
    "document": "Each entry under pages is one rendered page of a single resume, in reading order.",
    "page_count": 2,
    "pages": {"p1": "<uuid>", "p2": "<uuid>"}
  },
  "assets": {
    "<uuid>": {"type": "image", "part": "page-1"},
    "<uuid-2>": {"type": "image", "part": "page-2"}
  },
  "questions": {
    "layout": {"type": "choice", "instructions": "...", "criteria": {"one_column": "..."}},
    "p1_margins": {"type": "choice", "instructions": "Judge only the margins ...", "criteria": {"pass": "...", "minor": "...", "major": "...", "unable_to_assess": "..."}}
  }
}
```

The state path `pages.p1` is the name that instructions use. A Box question must name
its image, by reference or by state path, or the request is invalid. The builder
enforces this rule before sending.

### 3.3 Model pinning

Box questions need Jev 1.14. `jev-latest` points to `jev-1.14.0` today, but an alias
moves when a release ships, and the provider states that answers can change with it.
Pin `jev-1.14.0` for Box and structure requests, and record the `model` field from each
response. Every measured response reported `jev-1.14.0`.

Sources: <https://docs.typesafe.ai/models>, <https://docs.typesafe.ai/images#turning-on-images>.

## 4. Rasterising a page

### 4.1 pypdfium2 or PyMuPDF

| | pypdfium2 5.13 (installed) | PyMuPDF 2.0 |
| --- | --- | --- |
| Licence | BSD-3-Clause and Apache-2.0 | AGPL-3.0 or commercial |
| Linux x86_64 wheel | 3.8 MB | 68.9 MB |
| Already installed | Yes, through pdfplumber | No |
| Median page render and PNG encode | 96.7 ms | 72.1 ms |

The render benchmark ran 15 times per library on page 1 of the synthetic fixture at
1212 by 1568 pixels, on this host, and the median is reported. PyMuPDF is about 25
percent faster. It costs 65 MB of install size and an AGPL licence that would apply to
the distributed application.

Recommendation: use pypdfium2. It is already in the dependency tree because pdfplumber
needs it, its licence is permissive, and 25 ms per page is not the bottleneck. Adding
PyMuPDF is not justified.

pypdfium2 and Pillow arrive through pdfplumber today. The spike imports both directly.
When this route is approved for production, declare them as direct dependencies with
explicit version bounds, so a pdfplumber change cannot remove them silently. This branch
does not change `pyproject.toml`.

Wheel sizes come from the PyPI metadata for pypdfium2 5.14.0 and PyMuPDF 2.0.
Licence names come from the same metadata and from the installed distribution.

### 4.2 Rasteriser rules

`backend/app/services/page_render.py` implements these rules:

- Render with PDFium, which applies the page rotation. A rotated page keeps its upright
  aspect ratio.
- Pin the longest side to 1568 px, which is the largest accepted side.
- Re-render with a corrected scale when PDFium rounds a side up past 1568 px. Do not
  downsample, because resampling blurs small text.
- Pad a page whose short side falls under 280 px onto a white canvas, and centre it.
  Store the canvas offset, because Box fractions refer to the canvas, not to the page.
- Refuse a page that still breaks a limit, instead of sending it.
- Encode PNG. The route accepts JPEG too; PNG keeps text edges exact and the files are
  small enough (see section 6).

Measured output for the synthetic two-page resume: 1212 by 1568 px, 161,627 bytes for
page 1, 73,219 bytes for page 2.

## 5. Pixel and page budget per request

| Limit | Value | Our measured use |
| --- | --- | --- |
| Image file | 16 MiB | 158 KiB and 72 KiB |
| Each side | 280 to 1568 px | 1212 by 1568 |
| Total pixels | 78,400 to 2,458,624 | 1,900,416 |
| Request body | 32 MiB | 234,846 bytes of images plus 2,516 bytes of JSON |
| All images | 32 MiB | 234,846 bytes |
| Expanded request | 32 MiB after reference expansion | Not measurable from the client |
| Context | 64k per request, 32k per question | 13,050 input tokens for 2 pages |

Bytes are not the binding limit. Context is. One page with 13 questions used 5,720
input tokens. Two pages with 25 questions used 10,984. The marginal cost of a second
page is about 5,260 tokens, so the 64k per-request context holds roughly 11 pages at
this resolution, before question text.

Recommendation: send one page per request in version one, and cap a document at three
pages per request if a single call is required. Keep each page at full 1568 px. Do not
downscale to fit more pages, because small text is the main risk.

## 6. Converting a Box answer to the page

A Box answer gives `top`, `bottom`, `left` and `right` as fractions of the image sent.
Multiply by the image size to get pixels. Subtract the canvas offset. Divide by the
render scale to get PDF points.

```
x_px = fraction_left * canvas_width_px - offset_x_px
y_px = fraction_top * canvas_height_px - offset_y_px
x_pt = x_px / scale
y_pt = y_px / scale
```

`backend/app/services/box_geometry.py` implements this transform, clips to the page
content, and refuses unordered or non-finite boxes. The point result uses a top-left
origin, which matches the existing `bbox` contract on a text span in
`app/models/evidence.py`. A PDF viewer therefore needs one more step only: multiply the
point box by its own zoom factor, in CSS pixels per point.

Verified check: the header box from a live answer, `top 0.07 bottom 0.10 left 0.08
right 0.34`, converts to pixels 97, 110, 412, 157 and points 49.0, 55.6, 208.1, 79.3 on
a 1212 by 1568 page. Drawn on the page, that rectangle sits tightly on the name line and
correctly excludes the contact line below it. The arithmetic is exact.

The application has no PDF viewer today. `DocumentEvidence.tsx` shows text evidence
only, so the box coordinates have no consumer yet.

## 7. Section detection and structural defects

### 7.1 What works

Presence of a section is reliable. In the live runs, a Noul question about a section
that exists scored 0.96 to 1.00, and a Noul question about a section that does not
exist on that page scored 0.01 to 0.03. The model also identified the correct page.

Layout is reliable. The Choice question with five layout options answered
`one_column` with probability 0.99 to 1.00 on both a single-page and a two-page
request, which matches the fixture.

Formatting judgements are reliable. Seven Choice questions about margins, alignment,
hierarchy, spacing, density, entry format and page balance answered `pass` with
probability 0.79 to 0.99, except page balance, which answered `major` at 0.53 to 0.99
for a page that really is half empty.

### 7.2 What does not work yet

Box confidence is too low to drive a deduction. Across 60 Box answers in five live
runs, confidence ranged from 0.03 to 0.59. The median was about 0.17. No answer reached
0.60.

Box scope is loose. The summary box covered the summary paragraph plus the EXPERIENCE
heading and the first job title. The experience box covered the heading, the first job
title and one bullet, not the whole section. Entry boxes were tighter: the third job
box matched its entry exactly, but the first job box stopped after two of six bullets.

A box, once drawn, is worth less than a confident answer. Use answers for points and
boxes for display.

### 7.3 Detecting defects

| Defect | How to detect it | Works today |
| --- | --- | --- |
| Two-column reading trap | Choice on layout | Yes |
| Table or text-box layout | Choice on layout | Yes |
| Section missing or unlabelled | Noul per section | Yes |
| Section order wrong | Section boxes, sorted by top | No, box confidence is too low |
| Margins too tight | Choice on margins, plus box | Yes for the judgement |
| Inconsistent entry format | Choice on entry format | Yes |
| Cramped density or long lines | Choice on density | Yes |
| Orphaned heading at page end | Choice on page balance and spacing, plus a cross-page check in code | Partly |
| Text overflow or clipping | Noul on readability | Yes |
| Page imbalance | Choice on page balance | Yes |

An orphaned heading needs one extra deterministic check: when a section heading sits in
the bottom tenth of a page and its first entry starts on the next page, flag it. That
check needs no model call and no box.

## 8. The structure score

`backend/app/rubrics/structure_v1.py` implements a deterministic 0 to 100 score. The
questions live in `backend/app/rubrics/structure_questions_v1.py`, so wording can change
without moving a weight.

### 8.1 Weights

| Check | Weight | Fails when |
| --- | --- | --- |
| Hierarchy | 14 | Headings are not clearly larger or heavier than body text |
| Density | 12 | Lines are too long or the page is crowded |
| Margins | 10 | Content touches an edge or margins are uneven |
| Sections | 10 | A required section is missing or unlabelled |
| Entry format | 10 | Entries in one section use different patterns |
| Alignment | 8 | Blocks do not share a small set of left edges |
| Spacing | 8 | Vertical rhythm is not repeatable |
| Columns | 8 | Body text uses more than one column |
| Tables | 8 | Body text sits in table cells or text boxes |
| Section order | 6 | Sections are out of the conventional order |
| Page balance | 6 | A page is half empty or overcrowded |

The weights sum to 100, and an import guard fails if they do not.

### 8.2 Rules

- Pass removes nothing. Minor removes half the weight. Major removes all of it.
- A check that cannot be assessed leaves the denominator. An unclear page is therefore
  neither perfect nor zero.
- When two pages answer the same check, the worst answer wins. A poor page cannot hide
  behind a good one.
- The score is `round(100 * (assessable - lost) / assessable)`.
- If less than 60 points are assessable, the score is null and the reason is
  `insufficient_evidence`.
- Section presence and order are document level. A two-page CV is not penalised because
  page two has no header.

### 8.3 Unreadable and low-confidence pages

A page that is not readable is not scored. `score` is null, the reason is
`page_not_readable`, and one finding states that no points were awarded or removed.
A null score is not 0 and not 100.

A readable but empty page is a real defect. `score` is 0, the reason is `page_empty`,
and one finding states that the page has no content.

Low confidence on a Box does not remove points, because points come from the Choice or
Noul answer. It changes what the interface draws: below 0.5 confidence the finding is
shown against the whole page instead of a misleading rectangle, and the report lists a
limitation that says so.

### 8.4 Finding shape

Every finding carries:

- `key`: the check that failed.
- `page`: 0-based page index.
- `box`: top, bottom, left and right as fractions of the page, or the whole page.
- `severity`: minor, major, or unverified.
- `points_lost`: integer points.
- `evidence`: one short sentence, at most 160 characters of model note plus the fixed
  rubric sentence.
- `box_confidence`: the provider confidence, when a box exists.

The unit tests assert the box fractions are inside 0 to 1, that the page index is
0-based, that a low-confidence box collapses to the whole page, and that the conversion
to pixels matches `box_geometry`.

## 9. Measured results

Five live requests, all with the synthetic two-page fixture, all multipart, all 200 OK.

| Run | Pages | Questions | Input tokens | Output tokens | Wall clock | Structure score |
| --- | --- | --- | --- | --- | --- | --- |
| Sections | 1 | 13 | 5,720 | 300 | 258.9 ms | not computed |
| Sections | 2 | 25 | 10,984 | 540 | 291.0 ms | not computed |
| Entries | 1 | 6 | 5,446 | 130 | 259.2 ms | not computed |
| Structure | 1 | 29 | 6,774 | 807 | 272.5 ms | 83, sections major |
| Structure | 2 | 55 | 13,050 | 1,521 | 409.0 ms | 94, page balance major |

The one-page structure run scored 83 because EDUCATION and SKILLS are on page two and
the request only saw page one. This is correct behaviour for the input and it proves the
point: score the whole document, not one page in isolation.

The two-page run scored 94. It lost 6 points for page balance, which is correct: the
fixture leaves the lower half of both pages empty. Section order was unverified because
every section box was below 0.5 confidence.

Raw request and response bodies are in `docs/research/evidence-*.json`. They contain no
API key, no personal data and no image bytes. The fixture is synthetic and lives at
`backend/tests/fixtures/two_page_resume.pdf`.

## 10. Cost and latency

Input price is 42 US dollars per billion tokens, which is 0.042 US dollars per million
tokens. Output tokens are free. Source: <https://docs.typesafe.ai/models>.

| Item | Tokens | Cost |
| --- | --- | --- |
| One page, 13 questions | 5,720 | 0.000240 USD |
| One page, 29 structure questions | 6,774 | 0.000285 USD |
| Two pages, 25 questions | 10,984 | 0.000461 USD |
| Two pages, 55 structure questions | 13,050 | 0.000548 USD |
| Second page, marginal | about 5,260 | about 0.000221 USD |

A two-page review that runs the text content path (4,086 input tokens measured earlier
in this project) and the structure path comes to about 17,136 tokens, or 0.000720 USD.
One thousand such reviews cost about 0.72 USD.

Latency measured end to end from this host: 259 to 409 ms. One page costs about 0.26 s,
two pages about 0.29 to 0.41 s. These are single samples, not a percentile study.

TypeSafe publishes no image token estimate: "We'll be providing guidance on estimating
image token usage soon". The numbers above are measured, not derived. A different
resolution or a denser page will differ.

## 11. Integration shape

The analysis response will carry two scores and one total.

```json
{
  "structure": {"score": 94, "rubric_version": "structure-1", "findings": [...]},
  "content": {"score": 81, "rubric_version": "content-1"},
  "combined": {"score": 90, "structure_weight": 0.3, "content_weight": 0.7}
}
```

Proposed weight: structure 0.3, content 0.7.

Reason: the product exists to tell an applicant whether the CV communicates. Content
covers the substance of every bullet and every entry, so it carries more weight.
Structure covers what a reader sees before reading, and a badly broken layout can hide
good content, so 30 percent is enough to move the total without letting a cosmetic
preference outweigh the substance. The weight is a product decision and must be stored
with the report, not hard coded in the interface.

Combined score is computed only when both scores exist. When the structure score is
null, the report shows the content score alone, and the total is null with a stated
reason. Never substitute 0 or 100 for a missing score.

### 11.1 When the image path is unavailable

| Case | Behaviour |
| --- | --- |
| DOCX upload | Text path only. No structure score, and the report says the layout was not assessed. |
| PDF that fails to rasterise | Text path only. The report gives the same notice. |
| PDF page that is unreadable | Structure score null with `page_not_readable`, content score unaffected. |
| Image request returns 4xx or 5xx | Structure score null, one warning, no retry. The content report still returns. |
| Text edited in the preview | Structure score invalidated, because the image no longer matches the text. |

The structure score must never block a review. It is an additional finding set, not a
prerequisite.

### 11.2 API and frontend impact

Not implemented on this branch. When approved, the change is additive:

- One new optional block in the analysis response: `structure`.
- One new warning code when the image path was skipped.
- One new optional field per finding: `page` and `box`, which the existing finding
  contract does not have.
- The frontend draws boxes only when `box_confidence` is at or above 0.5.

## 12. DOCX

DOCX has no rendered page. The current parser reads paragraph text and table cells, and
it records sections, not pages.

Rasterising DOCX requires LibreOffice in headless mode, or a Word-compatible renderer.
That is a runtime dependency of several hundred megabytes, a process pool, a timeout
budget, and a font set that must match what the applicant saw. It also changes the
privacy story: a document would be converted on the server, and the converted copy must
stay in memory.

Recommendation: DOCX gets the text path only in version one. State the limitation in the
report: "Layout was not assessed for this file type." Revisit LibreOffice only if DOCX
usage is large enough to justify the dependency. That is a decision for the product
owner, not a side effect of this work.

## 13. Privacy

Page images leave the device. They travel to `api.typesafe.ai` over TLS and are analysed
there. This is a stronger disclosure than sending text, because an image cannot be
redacted by the applicant in the preview: names, phone numbers, photographs and
handwriting are all in the pixels.

TypeSafe states that Jev is not trained on customer requests or responses, and that zero
data retention is available for enterprise customers. Retention terms must still be
verified for this account before public use. Source:
<https://docs.typesafe.ai/models#data-handling>.

Implementation rules for the app path:

- Render pages in memory. Do not write an uploaded page or a rendered page to disk.
- Do not write the request body to a log. The current gateway already avoids body logs.
- Send only the pages that are needed, and only when the applicant has confirmed the
  analysis.
- Disclose image analysis in the interface before the request, next to the existing text
  disclosure.
- The spike writes evidence JSON only when `--evidence` is passed, and only for the
  synthetic fixture.

## 14. Risks

1. Dreamer-ready status. The provider states that the request format, the answers and the
   limits can change between releases. Pin the model and keep the request builder in one
   module.
2. Low Box confidence. A UI that draws boxes must degrade to the whole page below 0.5.
   Do not present a low-confidence box as fact.
3. Box scope. Section boxes are loose. Do not claim a box is exact to the pixel.
4. Cost of change. The production gateway caps a request at 100,000 bytes. An image
   request needs 32 MiB. The two paths must not share one budget constant.
5. Token growth. Each page adds about 5,260 input tokens. A 40-page CV cannot be scored
   in one call, and even 11 pages is at the edge of the default context.
6. Privacy expectation. An applicant who redacts contact details in the text preview
   still sends the full page image unless the image comes from the redacted text, which
   it cannot. Disclose this clearly.

## 15. Text-path fallback

The current text path stays as it is. It already provides layout-adjacent evidence:
page size, estimated margins, font sizes, link targets and span coordinates from
pdfplumber. `app/services/layout_checks.py` turns that into findings, and
`app/parsers/pdf.py` warns about reading order and partial text.

The fallback is therefore not new work. When the image route is unavailable, the report
keeps the existing metadata findings and adds one notice that the structure score was
not produced. It must not silently produce a structure score from text alone, because
text cannot show margins, alignment, page balance or columns.

## 16. What is verified, and what is not

Verified by live calls on this host, model `jev-1.14.0`:

- Multipart image request with the danger zone header returns 200.
- One 1212 by 1568 page costs about 5,400 to 6,800 input tokens.
- Two pages cost about 11,000 to 13,100 input tokens and fit one request.
- Latency is 259 to 409 ms.
- Noul presence answers and the layout Choice answer are correct and confident.
- Formatting Choice answers are confident and correct on the fixture.
- Box answers are geometrically usable, and the fraction to pixel conversion is exact.
- Box confidence is low: 0.03 to 0.59 over 60 answers.
- The structure score runs end to end and returns 94 for the two-page fixture.

Not verified, or assumed:

- Any layout other than single column. The fixture has no two-column page, no table
  layout, no text-box layout and no rotated pages. Those paths are covered by unit tests
  with synthetic input only.
- Behaviour on real, messy resumes: photographs, graphics, coloured headers, scanned
  pages.
- Base64 transport against the live API. Only multipart was sent.
- The 32 MiB expanded request limit and the per-image 16 MiB limit at their boundaries.
  The requests here are two orders of magnitude smaller.
- Per-image token accounting. The provider does not publish it; the numbers are totals.
- Any model version other than `jev-1.14.0`.
- Latency percentiles. The samples are single requests.
- Whether Box scope improves at higher confidence. The fixture produced no confident box.
- DOCX rasterisation, which is deliberately out of scope.
- Retention and deletion terms for this account, which need a contract review.

## 17. Spike files

| File | Purpose |
| --- | --- |
| `backend/app/services/page_render.py` | PDF page to bounded PNG, with canvas offset |
| `backend/app/services/box_geometry.py` | Fraction to pixel and point conversion |
| `backend/app/services/image_request.py` | Request builder, multipart encoder, guards |
| `backend/app/models/image_answers.py` | Box, Noul and option answer models |
| `backend/app/rubrics/structure_v1.py` | Structure score and finding shape |
| `backend/app/rubrics/structure_questions_v1.py` | Question text for the structure route |
| `backend/scripts/image_spike.py` | Dry run or one billable request, with evidence output |
| `backend/tests/fixtures/two_page_resume.pdf` | Synthetic two-page resume |
| `backend/tests/fixtures/make_resume.py` | Regenerates the fixture |
| `backend/tests/unit/test_page_render.py` | Rasteriser limits and geometry |
| `backend/tests/unit/test_box_geometry.py` | Box conversion and validation |
| `backend/tests/unit/test_image_request.py` | Payload shape, header, guards |
| `backend/tests/unit/test_structure_rubric.py` | Score weights, edge cases, mapping |
| `backend/tests/live/test_image_live.py` | Gated live request, synthetic fixture only |

Run the spike without spending money:

```
cd backend
uv run python scripts/image_spike.py tests/fixtures/two_page_resume.pdf --pages 1 --preset structure
```

Run one billable request:

```
cd backend
uv run python scripts/image_spike.py tests/fixtures/two_page_resume.pdf --pages 1 2 \
  --preset structure --send --evidence docs/research/evidence-run.json
```

Run the gated live test:

```
cd backend
JEV_RUN_IMAGE_LIVE=1 uv run pytest tests/live/test_image_live.py -s
```

The default test suite never reaches the network and needs no key. The live test skips
unless `JEV_RUN_IMAGE_LIVE=1` and a key are both present.

## 18. References

- Images, request shape, limits, errors: <https://docs.typesafe.ai/images>
- Box primitive and confidence: <https://docs.typesafe.ai/primitives/box>
- Noul primitive: <https://docs.typesafe.ai/primitives/noul>
- OCR confidence and bounding boxes cookbook: <https://docs.typesafe.ai/cookbooks/ocr_confidence_bounding_boxes>
- Models, price, context length, aliases, data handling: <https://docs.typesafe.ai/models>
- Confidence: <https://docs.typesafe.ai/confidence>
- PyPI metadata for pypdfium2: <https://pypi.org/pypi/pypdfium2/json>
- PyPI metadata for PyMuPDF: <https://pypi.org/pypi/PyMuPDF/json>
