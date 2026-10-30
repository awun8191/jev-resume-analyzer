# Rubric v3: evidence review and content scoring model

Superseded in part: section 16 records rubric v3.1, which adds six prevalence checks and
replaces the weights in sections 9, 10 and 15. The reasoning in sections 1 to 8 still holds.
Section 12 rule 7 matches the implemented coverage rule.

Status: proposed. Rubric v3 runs beside v2. No analysis flow or frontend code changes in this
task. The one contract change is an optional `section` field, documented in section 10.1.

Scope: the content score only. A second score covers structure, meaning layout, spacing,
typography, alignment, and density. Another agent owns that score. This document defines
how the two scores combine and how the report presents them.

## 1. How to read the evidence

The sources below fall into four groups. They do not carry equal weight.

| Group | What it can support | Examples |
| --- | --- | --- |
| A. Meta-analytic selection research | How well hiring methods predict job performance | Sackett et al. 2022; Van Iddekinge et al. 2019 |
| B. Field experiments | What changes real callback rates | Quillian et al. 2017; Kroft et al. 2013 |
| C. Employer and career-center guidance | What practitioners agree a resume should contain | NACE; MIT CAPD; Yale OCS; Ladders |
| D. Measurement design | How to build a score that repeats | Lozano et al. 2008; RAND SF-36 scoring; EEOC rules |

Group C is consensus practice, not experimental proof. This document marks claims that
rest on group C. No source in this review isolates bullet wording as a cause of interview
conversion. The model below therefore claims document quality, and it does not claim
callback effects.

## 2. What happens in the first screening pass

Ladders ran an eye-tracking study with 30 professional recruiters. The 2018 update reports
an average initial screening time of 7.4 seconds per resume, against 6 seconds in the 2012
study [1]. The study describes a fast visual scan of layout, job titles, text flow, and
keywords. It also reports that the worst-performing resumes shared three traits: cluttered
layouts, no section headers or job headers to guide the eye, and reliance on keyword
stuffing [1].

Two limits apply. First, the sample is 30 recruiters, so the exact seconds are indicative,
not precise. Second, the study measures reading behavior, not hiring validity. It supports
one narrow claim: information that a reader cannot find and interpret in a scan cannot
help the applicant. It does not support a claim that a given layout causes an interview.

Employer surveys point at the same content. NACE reports that about 90 percent of
respondents to its Job Outlook 2025 survey seek evidence of problem solving, about 80
percent seek teamwork, and at least 70 percent seek written communication, initiative, a
strong work ethic, and technical skills [2]. The survey had 237 respondents, of whom 162
were NACE employer members, so treat the percentages as directional.

Implication for this rubric: reward described problem solving, technical work, and results.
Do not reward adjectives, tool names, employer names, or job titles on their own.

## 3. What the selection research says, and what it forbids

Sackett, Zhang, Berry, and Lievens re-examined the well-known validity meta-analyses. They
found that prior estimates were too high by .10 to .20 points, and that the structured
interview is the top-ranked selection procedure [3]. Van Iddekinge, Arnold, Frieder, and
Roth meta-analyzed prehire work experience across 81 samples. The corrected correlation
with job performance was .06, with training performance .11, and with turnover .00 [4].

Two conclusions follow.

1. Resume content is a weak predictor of job performance at best. A resume score must not
   be presented as a hiring probability or as an interview forecast.
2. Amount of experience is close to uninformative. The score must not reward tenure,
   seniority words, or employer prestige. It rewards the work that the document describes.

This is the reason the rubric has no item for years of experience, no item for job titles,
and no recency weighting.

## 4. Bullet structure and section content

Yale's Office of Career Strategy teaches an Action + Project + Result pattern, and an
"Accomplished [X] as measured by [Y] by doing [Z]" variant. It asks writers to quantify the
result, to contextualize it with a baseline, and to describe what the applicant did rather
than what the team did [5].

MIT's resume checklist asks for an action verb at the start of each phrase, evidence and
quantification of impact, keywords that apply to the industry or the job listing, employer
and title for each role, dates for each role, and no first-person pronouns [6]. MIT also
states that unpaid work, volunteer work, and personal projects belong on the resume [7].

The two guides agree on five elements: action, object, result, magnitude where available,
and ownership. They differ on how absolute the number requirement is. Yale says to
quantify when possible. MIT says to give evidence and quantify relevant information. Many
roles, such as teaching, care work, and public administration, have no clean percentage to
report.

Design consequence: the outcome check does not require a number. A separate, smaller check
rewards a magnitude when one exists. When the document states no result at all, the
magnitude check is not applicable, so one gap is not charged twice.

## 5. Length, dates, and formatting

MIT's checklist gives the common advice: one page, two pages for an advanced degree or 10
or more years of experience, margins between 0.5 and 1.0 inches, font size between 10 and
12 points, consistent date format, and no template that an applicant tracking system may
misread [6].

This rubric does not score any of that. Margins, font size, page count, and date format are
structural properties. The structure score owns them. This rubric keeps only one record
check: each role states employer, title, and date boundaries. Presence of a date is a
content fact. Consistent date formatting is a structural fact.

Applicant tracking systems also deserve a caution. Vendors parse documents differently.
There is no universal ATS score, and no public evidence supports the claim that a specific
format guarantees rejection. The Ladders finding that keyword stuffing marks weak resumes
[1] is the defensible part: keywords help when they sit inside described work. That is why
the relevance checks require described work and why the skills check requires listed tools
to appear in the work text.

## 6. Rating-scale design

Lozano, García-Cueto, and Muñoz simulated scales with two to nine response options. Both
reliability and validity improved as options increased, with an optimum between four and
seven, and little further gain beyond seven [8]. A ten-point judgment with no written
anchors therefore adds variance, not information.

The design response is not a finer opinion. It is a checklist of binary decisions, each
with a written threshold, aggregated with fixed weights. Granularity comes from the checks
and their weights. Reproducibility comes from arithmetic, not from model prose.

Missing evidence needs an explicit rule. The RAND SF-36 scoring instructions state that
blank items are not taken into account, and that a scale score is the average over the
items the respondent answered [9]. This rubric adopts that rule: `not_applicable` and
`unable_to_assess` leave the denominator, and a reported range shows how much the answer
set could move the score.

Two scoring hazards follow from the scale design.

- Double counting. Each check measures one construct. The ownership checks do not repeat
  the impact checks, and the clarity checks do not repeat either. Section 11 records the
  merges that removed overlapping items.
- False precision. Scores are integers, bands are five wide ranges, and a range accompanies
  the content score. No decimal score is displayed.

## 7. Fairness, gaps, and non-traditional backgrounds

Field experiments show that screening already carries penalties that have nothing to do
with document quality. Quillian, Pager, Hexel, and Midtbøen analyzed 28 field experiments
covering 55,842 applications. Since 1989, white applicants received about 36 percent more
callbacks than African American applicants and about 24 percent more than Latino applicants
[10]. Kroft, Lange, and Notowidigdo sent fictitious resumes to real postings in 100 cities.
The callback probability fell as the unemployment spell lengthened [11]. Fuller and Raman
document degree inflation, where employers demand degrees for roles that did not previously
require them, and argue that this screens out capable workers [12].

These findings drive five hard rules.

1. No identity signal. The rubric never asks about name, gender, age, nationality, address,
   or photo. No question asks the model to infer them.
2. No gap penalty. No check reads timeline continuity. Dates are read for presence only.
3. No degree requirement. The education check is not applicable when the document has no
   education section. Its weight is 3 of 100.
4. Unpaid work counts. Employment, volunteering, and personal projects are all work, which
   follows MIT guidance [7].
5. No prestige or seniority points. Company size, brand, and title carry no weight.

Legal context: the EEOC Uniform Guidelines use a four-fifths rule, where a selection rate
below 80 percent of the highest group's rate indicates a substantially different rate [13].
This product does not select anyone, so the rule does not apply directly. It does apply if
anyone later repurposes the score for screening. Section 14 states the monitoring
condition.

Residual risk: a language model may infer demographic traits from phrasing, school names,
or locations. The rubric cannot remove that risk. It reduces exposure by asking only about
document structure and evidence, by forbidding inference about the person, and by
monitoring score distributions when labeled data exists. This is a limitation, not a solved
problem.

## 8. What the evidence does not support

The following are out of scope by design, with the reason.

| Rejected element | Reason |
| --- | --- |
| Overall hiring probability | Resume content is a weak predictor [3][4]; any number would overclaim |
| ATS score or pass/fail | Vendors differ and no public validity evidence exists; Ladders shows only that keyword stuffing correlates with weak resumes [1] |
| Truthfulness verdict | The document cannot establish facts about the person; no check asks for honesty |
| Generated advice or rewrites | Product rule; fixes restate the rubric question and the points at stake |
| Global "communication quality" | Not decidable and not distinct from clarity; the v2 item is dropped in section 11 |
| Resume length penalty | Structural, owned by the structure score [6] |
| Mandatory summary | Absence is not a defect; the v1 summary check is dropped in section 11 |

## 9. The content model

Seven dimensions. The weights sum to 100.

| Dimension | Weight | What it measures | Why this weight |
| --- | --- | --- | --- |
| Impact | 25 | Results the work produced, and whether a result states its size | The largest block. Employer and career-center guidance puts results first [2][5][6], and described outcomes are the most informative content a resume can offer |
| Scope | 15 | Who the work served and how large the setting was | Impact is not interpretable without context; Yale asks writers to contextualize the result [5] |
| Ownership | 15 | The author's own action, and whether the author made decisions | Team results without an author action are not evidence about the applicant [5][6] |
| Relevance | 15 | Link between the document and the posting | Tailoring is standard guidance [6]; the block applies only when a posting exists |
| Clarity | 15 | Whether a claim names its object and reads without insider context | A claim that a reader cannot parse cannot count as evidence; written communication is an employer priority [2] |
| Completeness | 10 | Whether the record states roles, education, and projects | A complete record supports the other dimensions; the block stays small because presence alone is weak evidence |
| Skills | 5 | Whether listed tools appear in described work | Smallest block because a list is the most gameable element; Ladders links keyword stuffing to weak resumes [1] |

The content score does not reward tenure, seniority, employer prestige, page count, or
document length. Section 3 gives the reasons.

## 10. The question set

Fourteen checks. Each check names one section, states a threshold, and has no adjective
that a reader must interpret. Answer states stay `present`, `absent`, `not_applicable`,
`unable_to_assess`.

| id | Dimension | Weight | Section | Full credit (`present`) | Zero credit (`absent`) |
| --- | --- | --- | --- | --- | --- |
| impact_outcome | Impact | 15 | experience, projects | One entry states an action and the result, deliverable, or change that followed | Duties are listed with no stated result |
| impact_magnitude | Impact | 10 | experience, projects | One result states a count, rate, percentage, duration, money amount, or volume with a unit or baseline | Results exist and none gives a quantity with a unit or baseline |
| scope_actors | Scope | 8 | experience, projects | One entry names the users, customers, team, system, department, or public served | No entry names who the work served |
| scope_size | Scope | 7 | experience, projects | One entry states a countable feature of the setting: team size, user count, volume, budget, traffic, sites, engagement length | No countable feature of the setting appears |
| ownership_own_action | Ownership | 9 | experience, projects | One description uses an author-action construction and does not attribute the action only to a team or employer | Every activity is attributed to a team, the employer, or another person |
| ownership_decision | Ownership | 6 | experience, projects | One entry names a selection, design, or direction-setting action and its object | Every action is support, assistance, or participation |
| relevance_responsibility | Relevance | 8 | experience, projects, against posting | One CV task is substantively related to a stated responsibility | No CV task relates to a stated responsibility |
| relevance_requirement | Relevance | 7 | education, skills, experience, against posting | The CV states a requested qualification, or a clear equivalent | No requested qualification and no clear equivalent appears |
| clarity_concrete | Clarity | 8 | experience, projects | One description names a specific object the work acted on | Descriptions name only duty categories |
| clarity_self_contained | Clarity | 7 | all sections | Every internal name has a short function phrase, and abbreviations are expanded once | One description depends on an unexplained internal name |
| complete_roles | Completeness | 4 | experience | Every role states employer, title, and date boundaries | One role omits employer, title, or a date boundary |
| complete_education | Completeness | 3 | education, certifications | Every entry states institution or issuer, credential, field, and date | One entry omits institution, credential, field, or date |
| complete_projects | Completeness | 3 | projects | Every project states its purpose and the author's contribution | One project omits purpose or contribution |
| skills_evidence | Skills | 5 | skills | At least half of the listed tools and methods appear in the work text | Fewer than half appear |

Applicability rules, stated inside each question:

- Seven questions are not applicable when the document has no experience, volunteering, or
  project entries. They do not become zero.
- `impact_magnitude` is not applicable when the document states no result at all. This
  prevents a double charge for one gap.
- `complete_education` is not applicable when the document has no education or
  certification section. Omitting education is not a defect for every candidate [12].
- `complete_projects` is not applicable when the document has no project entries.
- `skills_evidence` is not applicable when the document has no skills list.
- The two relevance questions are not applicable when the posting is absent or states no
  identifiable item.

### 10.1 Section identifiers

Every question carries one `section`. The set is closed: `header`, `summary`, `experience`,
`education`, `skills`, `projects`, `all`. Exactly one value per question.

A question that reads two or more sections carries `all`. The interface then highlights the
whole document instead of guessing a single box. `header` and `summary` exist in the set but
no v3 question uses them, because the header and summary checks were dropped in section 11.

The backend defines the mapping once, in `app/rubrics/cv_review_v3.py`: the `SECTIONS` map
and the `section_for(question_id)` helper. `scoring_v3` repeats `section` on every fix and
every dimension row. `as_dict` serializes it. A dimension row gets the section its questions
share, or `all` when they differ. A finding carries an optional `section` field.

| question id | section | Why |
| --- | --- | --- |
| impact_outcome | all | Reads experience and project entries |
| impact_magnitude | all | A result can sit in experience or in a project |
| scope_actors | all | Reads experience and project entries |
| scope_size | all | Reads experience and project entries |
| ownership_own_action | all | Reads experience and project entries |
| ownership_decision | all | Reads experience and project entries |
| relevance_responsibility | all | CV tasks can sit in experience or in a project |
| relevance_requirement | all | A qualification can sit in education, skills, or experience |
| clarity_concrete | all | Reads experience and project entries |
| clarity_self_contained | all | Internal names can appear in any section |
| complete_roles | experience | Only employment entries are judged |
| complete_education | education | Only education and certification entries are judged |
| complete_projects | projects | Only project entries are judged |
| skills_evidence | skills | Reads the skills list against the work text |

## 11. What changed from v1 and v2

The earlier rubrics hold 16 document-level checks, plus 3 checks generated for each bullet.
Rubric v3 holds 14 document-level checks. Four old checks are dropped, 12 feed the new set,
and 2 are new.

| Old check | Outcome | Reason |
| --- | --- | --- |
| work_clarity | Split into impact_outcome and clarity_concrete | One item asked for a "concrete task", which mixed readability with results |
| personal_contribution | Renamed ownership_own_action | Clear construct, unclear wording |
| interpretability | Split into clarity_concrete and clarity_self_contained | A single vague item became two decidable ones |
| outputs_results | Merged into impact_outcome | Kept the result requirement; the number requirement moved to its own item |
| scope_context | Split into scope_actors and scope_size | "Context for scope" allowed any answer |
| summary_specificity | Dropped | A summary is optional, and absence is not a defect; the remaining specificity content sits in the clarity checks |
| header_contact | Dropped from the score | Contact presence is near-universal among readable documents, so it does not discriminate; a missing email or phone is a warning, not a quality point |
| education | Becomes complete_education at weight 3 | Kept, with a not-applicable rule for candidates who list no education |
| experience_dates | Merged into complete_roles | The old item also implied format consistency, which is structural |
| experience_identity | Merged into complete_roles | Two presence checks about the same entries became one |
| skills_evidence | Kept at weight 5 | The only anti-keyword-stuffing item that reads the work text |
| skills_organization | Dropped | Grouping is presentation, not evidence; it belongs to structure if it belongs anywhere |
| project_purpose | Merged into complete_projects | Purpose and contribution describe the same entry |
| communication | Dropped | "Communication consistency" is not decidable, and it duplicated the clarity checks |
| responsibility_evidence | Becomes relevance_responsibility | Tightened: a shared tool name with no described work now fails |
| qualification_evidence | Becomes relevance_requirement | Kept, with the eligibility limit stated in the criteria |
| Per-bullet checks (3 per bullet) | Dropped from v3 | The count is unbounded, it conflicts with the per-request question budget, and it repeats document-level checks at higher cost. The v2 module stays in place for the running flow |

New items are impact_magnitude and ownership_decision. Each answers a question that the
research identifies and that no old item measured.

## 12. Scoring rules

The function is `backend/app/rubrics/scoring_v3.py`. It is pure Python. It uses no network,
no clock, and no randomness.

Definitions:

- `earned` is the sum of weights answered `present`.
- `assessed` is the sum of weights answered `present` or `absent`.
- `applicable` is `assessed` plus the weight of prepared questions answered
  `unable_to_assess` or not answered at all.
- `prepared` is the set of question ids that the request actually asked. It excludes the
  two relevance questions when no posting exists.

Rules:

1. `present` earns the full weight. `absent` earns zero.
2. `not_applicable` leaves the numerator and the denominator. The question had no
   application, so it carries no points.
3. `unable_to_assess` leaves the denominator but stays in the reported range. It never
   becomes zero [9].
4. A prepared question with no answer counts as `unable_to_assess`, not as `absent`.
5. If `assessed` is below 50 of 100, the content score is null, with the reason
   "insufficient assessable evidence". The product shows no number, not a low number.
6. The range is `low = 100 * earned / applicable` and
   `high = 100 * (earned + applicable - assessed) / applicable`, rounded half up. The
   content score always falls inside the range. A wide range means that more evidence was
   unreadable or unreturned.
7. Coverage is `assessed / applicable`. A question answered `not_applicable` leaves the
   coverage denominator together with the score denominator, so an inapplicable check is not
   reported as missing evidence. `unable_to_assess` stays in `applicable`, so it lowers
   coverage and widens the range. Section 16.4 states the same rule for v3.1.
8. Dimension subtotals use the same rule inside the dimension: earned weight over assessed
   weight, null when nothing in the dimension was assessed.

Combination with the structure score:

```
content = round_half_up(100 * earned / assessed)
total   = round_half_up(0.7 * content + 0.3 * structure)
band    = 90 or more very strong; 75 strong; 60 adequate; 40 partial; below 40 thin
```

Content carries 70 percent because it is the part with traceable evidence and the part that
hiring guidance addresses. Structure carries 30 percent because layout decides whether the
content is found in a 7.4-second scan [1], but formatting must not outweigh what the
candidate did. The structure score never changes the content subtotal, and the content
score never changes the structure subtotal.

Missing score cases:

| Case | Rule | Reported mode |
| --- | --- | --- |
| Both scores present | `total = round_half_up(0.7 * content + 0.3 * structure)` | combined |
| Structure missing (DOCX upload, rendering failure) | `total = content` | content_only |
| Content missing (fewer than 50 assessable points) | `total = structure` | structure_only |
| Both missing | `total = null` | unavailable |

A missing score never lowers the total. The mode is displayed as a chip next to the total,
so a content-only total is not read as a combined total.

Rounding is half up, not half to even. Python's `round()` would make 68.5 depend on parity.
Identical answers produce identical output, and answer order does not matter.

## 13. Report information hierarchy

Order on the page:

1. Total score, its band label, the mode chip, and the range when the range is wider than
   five points.
2. The two subtotals, Structure and Content, each with the same band labels, and the
   content range and coverage.
3. Dimension subtotals, grouped under the score that owns them. Content owns Impact, Scope,
   Ownership, Relevance, Clarity, Completeness, and Skills. Structure owns its own
   dimension list, supplied by the structure module.
4. Findings, grouped under their dimension. Each finding carries an owner label, Content or
   Structure, a section id, and shows the question, the criteria, the answer, and the answer
   distribution when the provider returns one. The section id places the finding beside the
   resume box it judges. `all` means the whole document.
5. The top three content fixes.

Band labels appear once, in a legend. The same five labels apply to the total, the content
score, and the structure score. A 55 means Partial evidence wherever it appears.

| Range | Label |
| --- | --- |
| 90 to 100 | Very strong evidence |
| 75 to 89 | Strong evidence |
| 60 to 74 | Adequate evidence |
| 40 to 59 | Partial evidence |
| 0 to 39 | Thin evidence |

Top three fixes: rank dimensions by points not earned, `weight * (1 - score / 100)`, then
by dimension weight, then by the fixed dimension order. Take the three highest. For each,
name the heaviest question answered `absent` in that dimension. A fix shows the dimension,
the points at stake, and the rubric question. It never shows a rewrite, a suggestion, or a
prediction. Dimensions with no assessed weight, such as Relevance without a posting, never
appear. When the content score is null, the fixes section shows the insufficient-evidence
state instead.

## 14. Failure modes and limits

| Failure mode | Response in the rubric | Residual risk |
| --- | --- | --- |
| Keyword stuffing | Relevance needs described work; skills carry 5 points; tool lists alone earn nothing [1] | A model may still read a dense list as described work |
| Metric inflation | A magnitude needs a unit or baseline; a number with no referent earns nothing | A false number still earns the points; the tool issues no truthfulness verdict |
| Verb inflation | ownership_decision requires the object of the action, not the verb alone | The judgment stays with the model |
| Summary boilerplate | No summary item exists, so generic claims earn nothing | None beyond the clarity checks |
| Career gaps | No continuity check, no recency weight, no gap question [11] | A model may notice a gap while answering another question; the score does not price it |
| Non-traditional background | Unpaid and volunteer work count as work [7]; education is not applicable when absent; no degree, title, or prestige points [12] | Employers may still apply their own filters; this score cannot fix that |
| Identity signal | No name, age, gender, nationality, address, or photo question [10] | Text can reveal traits indirectly; monitor distributions |
| Layout duplication | Length, font, margins, density, and date format are excluded and belong to structure [6] | None by design |
| Writing to the rubric | Weights are public, so an applicant can target them | The checks require evidence that an interviewer could probe; the score reports the question, not a verdict |
| False precision | Integers, five bands, range, coverage | Users may still read 74 as close to 75; the band text is the primary label |

Calibration status: none yet. The weights are a structured judgment based on the sources in
this review, not regression estimates. The next step is a human-labeled set of 30 to 50
documents, two independent raters, and a comparison of dimension scores against rater
agreement. Change a weight only with a recorded reason. Do not publish accuracy claims
before that work.

Legal note: this product does not select or rank applicants. If any party repurposes the
score for screening, the four-fifths rule applies and the operator must monitor selection
rates by group [13].

## 15. Integration notes

- `cv_review_v3.py` and `scoring_v3.py` sit beside v1 and v2. No router, model, or service
  imports them yet. The HTTP contract does not change.
- Entry point: `score_report(answers, structure_score=None, prepared=None)`. `answers` maps
  question id to answer state. `prepared` defaults to every id in `IDS`. The live flow prepares
  all of them and lets the relevance questions answer `not_applicable` when no posting exists,
  which removes their weight from the score denominator and from coverage.
- `as_dict(result)` returns plain data for report assembly. Each dimension row and each fix
  carries `section`.
- `SECTIONS` and `section_for(question_id)` in `cv_review_v3.py` are the only definition of
  the question-to-section mapping. Do not copy the table into a second module.
- Unknown ids, answers outside `prepared`, and invalid structure scores raise `ValueError`.
  These are wiring faults, not user errors. `section_for` raises `KeyError` for an unknown id.
- `not_applicable` and `unable_to_assess` keep their existing meanings from the frontend
  contract. Neither becomes zero.
- The frontend contract reserves `rating` for an approved mapping and describes it as
  communication quality. When integration happens, the total takes that field, and the
  label must read document evidence. Do not reuse the phrase communication quality, and do
  not imply a hiring chance. Put the mode and the coverage in the `basis` string.

## 16. Rubric v3.1: prevalence twins

Status: implemented on `feat/rubric-v3.1`. The report version string stays `v3`. Question ids,
sections and the four answer states are unchanged, so the interface contract does not move.
Only the question set and the weights change.

### 16.1 Why v3.1 exists

v3 had fourteen checks, and nine of them used an existential threshold: "at least one entry".
One quantified bullet therefore earned all 25 Impact points and 17.5 points of the final total,
while eleven vague entries cost nothing. The heaviest dimension had no consistency requirement.
A candidate could pass the whole rubric with one good line inside an otherwise empty document.

v3.1 adds one prevalence twin to each dimension that had an existential threshold, and moves
weight from the existence check to the twin. Every weight stays binary. There is no partial
credit and no new answer state. The existence check still answers "does one entry show this?".
The twin answers "do at least half of the relevant entries show it?".

### 16.2 Weight table

Twenty checks, 100 points. Dimension totals are unchanged.

| id | Dimension | Weight | Change from v3 |
| --- | --- | --- | --- |
| impact_outcome | Impact | 8 | was 15 |
| impact_prevalence | Impact | 9 | new |
| impact_magnitude | Impact | 4 | was 10 |
| impact_magnitude_prevalence | Impact | 4 | new |
| scope_actors | Scope | 5 | was 8 |
| scope_prevalence | Scope | 6 | new |
| scope_size | Scope | 4 | was 7 |
| ownership_own_action | Ownership | 6 | was 9 |
| ownership_prevalence | Ownership | 6 | new |
| ownership_decision | Ownership | 3 | was 6 |
| relevance_responsibility | Relevance | 5 | was 8 |
| relevance_prevalence | Relevance | 6 | new |
| relevance_requirement | Relevance | 4 | was 7 |
| clarity_concrete | Clarity | 5 | was 8 |
| clarity_prevalence | Clarity | 5 | new |
| clarity_self_contained | Clarity | 5 | was 7 |
| complete_roles | Completeness | 4 | unchanged |
| complete_education | Completeness | 3 | unchanged |
| complete_projects | Completeness | 3 | unchanged |
| skills_evidence | Skills | 5 | unchanged |

| Dimension | v3.1 | v3 |
| --- | --- | --- |
| Impact | 25 | 25 |
| Scope | 15 | 15 |
| Ownership | 15 | 15 |
| Relevance | 15 | 15 |
| Clarity | 15 | 15 |
| Completeness | 10 | 10 |
| Skills | 5 | 5 |
| Total | 100 | 100 |

Completeness keeps its existential weights because each of its checks is already universal:
"every employment entry" and "every project entry" require all entries, not one. Skills already
uses an at-least-half rule over the listed items.

### 16.3 The at-least-half rule

Half means half or more of the relevant set, rounded up. One of two entries passes. The
denominators differ by check:

| Check | Denominator |
| --- | --- |
| impact_prevalence | experience, volunteering and project entries |
| impact_magnitude_prevalence | stated results |
| scope_prevalence | experience, volunteering and project entries |
| ownership_prevalence | experience, volunteering and project descriptions |
| relevance_prevalence | CV work descriptions |
| clarity_prevalence | experience, volunteering and project descriptions |

Applicability:

- Every prevalence check is not applicable when the document has no experience, volunteering or
  project entries.
- `impact_magnitude_prevalence` is also not applicable when the document states no result at
  all. There is no set of results to compare, and `impact_magnitude` already charges that gap.
- `relevance_prevalence` is not applicable when `job_text` is absent or the posting states no
  identifiable responsibility.

The model compares entries inside one document. It is not asked to count words or to remember
answers to other questions. The prompt still forbids relying on an answer to another check.

### 16.4 Coverage

One rule, implemented once in `score_report` and stated once here:

```
coverage = assessed / applicable
```

`not_applicable` leaves the coverage denominator, exactly as it leaves the score denominator.
The choice matters for documents without a posting. Under the old prepared-weight denominator
such a document showed coverage 0.85 although nothing was missing. Under this rule it shows 1.0,
and the range stays 100 to 100. `unable_to_assess` stays in `applicable`, so it still lowers
coverage and widens the range. That is the distinction the two non-answers are meant to carry:
one had no application, the other could not be read.

### 16.5 Known limitation

Prevalence still depends on the model's ability to compare entries within the document. The
score is arithmetic, but the comparison is a judgment. Three residual risks remain.

1. Entry segmentation. The model decides what counts as one entry. A role with four bullets may
   read as one entry or as four. The prompt names "experience, volunteering and project
   entries", not bullets, but the document layout decides the reading.
2. Small denominators. One entry is one of one, and one of two passes. A two-entry document
   nearly always passes prevalence. The check separates a mixed document from a consistent one
   only when the document has several entries.
3. No calibration. The weights and the half threshold are a structured judgment, not a
   regression estimate. The same 30 to 50 document study described in section 14 applies.

The one-entry failure is accepted. A single-entry CV is not a common case for the target user,
and the existence checks still have to pass. Tightening the rule to a minimum entry count would
add a document-length judgment that the research in section 5 does not support.

### 16.6 Test evidence

`tests/unit/test_rubric_profiles.py` scores three fixed answer sets. No model is involved.

| Profile | Content score | Impact | Band |
| --- | --- | --- | --- |
| Strong throughout | 100 | 25 of 25 | Very strong evidence |
| One strong entry, five vague entries | 64 | 12 of 25 | Adequate evidence |
| Weak throughout | 13 | 0 of 25 | Thin evidence |

The middle profile passes every existence check and no prevalence check. It sits 36 points below
the strong profile, against a required separation of 15. It no longer reaches 25 of 25 Impact.

## References

1. Ladders. "Ladders updates popular recruiter eye-tracking study." 6 November 2018.
   https://www.prnewswire.com/news-releases/ladders-updates-popular-recruiter-eye-tracking-study-with-new-key-insights-on-how-job-seekers-can-improve-their-resumes-300744217.html
   Study report: https://www.bu.edu/com/files/2018/10/TheLadders-EyeTracking-StudyC2.pdf
2. NACE. "What are employers looking for when reviewing college students' resumes?"
   9 December 2024. https://www.naceweb.org/talent-acquisition/candidate-selection/what-are-employers-looking-for-when-reviewing-college-students-resumes
3. Sackett, P. R., Zhang, C., Berry, C. M., and Lievens, F. "Revisiting meta-analytic
   estimates of validity in personnel selection." Journal of Applied Psychology, 2022.
   https://pubmed.ncbi.nlm.nih.gov/34968080/
4. Van Iddekinge, C. H., Arnold, J. D., Frieder, R. E., and Roth, P. L. "A meta-analysis of
   the criterion-related validity of prehire work experience." Personnel Psychology 72(4),
   2019. https://digitalcommons.unf.edu/unf_faculty_publications/785/
5. Yale Office of Career Strategy. "Writing impactful resume bullets."
   https://ocs.yale.edu/resources/writing-impactful-resume-bullets/
6. MIT Career Advising and Professional Development. "Resume checklist and worksheet."
   https://capd.mit.edu/resources/resume-checklist/
7. MIT Career Advising and Professional Development. "Career toolkit: crafting an effective
   resume." https://capd.mit.edu/resources/career-toolkit-crafting-an-effective-resume/
8. Lozano, L. M., García-Cueto, E., and Muñoz, J. "Effect of the number of response
   categories on the reliability and validity of rating scales." Methodology 4(2), 2008.
   https://www.researchgate.net/publication/236979916
9. RAND Corporation. "36-Item Short Form Survey (SF-36) scoring instructions."
   https://www.rand.org/health/surveys/mos/36-item-short-form/scoring.html
10. Quillian, L., Pager, D., Hexel, O., and Midtbøen, A. H. "Meta-analysis of field
    experiments shows no change in racial discrimination in hiring over time." PNAS 114(41),
    2017. https://www.pnas.org/doi/10.1073/pnas.1706255114
11. Kroft, K., Lange, F., and Notowidigdo, M. J. "Duration dependence and labor market
    conditions: theory and evidence from a field experiment." NBER Working Paper 18387,
    2012. https://www.nber.org/system/files/working_papers/w18387/w18387.pdf
12. Fuller, J. B., and Raman, M. "Dismissed by degrees." Harvard Business School, 2017.
    https://www.hbs.edu/ris/Publication%20Files/dismissed-by-degrees_707b3f0e-a772-40b7-8f77-aed4a16016cc.pdf
13. U.S. Equal Employment Opportunity Commission. "Questions and answers to clarify and
    provide a common interpretation of the Uniform Guidelines on Employee Selection
    Procedures." https://www.eeoc.gov/laws/guidance/questions-and-answers-clarify-and-provide-common-interpretation-uniform-guidelines
