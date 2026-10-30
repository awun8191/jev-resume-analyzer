# Rubric v3: evidence review and content scoring model

Status: proposed. Rubric v3 runs beside v2. No analysis flow, HTTP contract, or frontend
code changes in this task.

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
with a written threshold, aggregated with fixed weights. Granularity comes from 14 checks
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
