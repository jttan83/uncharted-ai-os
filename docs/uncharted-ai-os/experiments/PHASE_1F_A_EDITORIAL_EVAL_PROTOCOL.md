# Phase 1F-A Editorial Evaluation Protocol

## 1. Status and authority

Status: Phase 1F-A.0 pre-registered experiment protocol, awaiting approval.

Protocol version: `phase-1f-a-v1`.

This document defines the experiment that must precede any broader Phase 1F
implementation. It tests whether the Uncharted AI OS editorial operating
method produces materially better editorial decisions than strong simpler
workflows at an acceptable increase in cost, latency, human effort, and
operational complexity.

This is a documentation specification. It creates no runtime, Agent, Workflow,
database, schema, migration, UI, Langflow integration, dependency, dataset, or
external publication action.

Read this protocol with:

- [Uncharted AI OS Architecture](../ARCHITECTURE.md);
- [AI Role and Learning Architecture](../AI_ROLE_AND_LEARNING_ARCHITECTURE.md);
- [Editorial & Content Director](../roles/EDITORIAL_CONTENT_DIRECTOR.md); and
- [Talking-Head Content Development](../capabilities/TALKING_HEAD_CONTENT_DEVELOPMENT.md).

Those documents remain authoritative. In particular:

- Capability remains repeatable business work, not a Role, Agent, Workflow,
  Run, Artifact, or Eval;
- Editorial & Content Director remains the single accountable World-Class
  Role;
- Talking-Head Content Development remains the orchestration-level parent
  Capability;
- the independent evaluator, not the creator, authors the readiness decision;
- Ready for Human Approval is not permission to publish; and
- Quality and real-world Outcome remain separate evidence streams.

Approval of this protocol freezes the experiment design. A later operational
manifest must fill every implementation-specific version and budget before
holdout cases are accepted. No value may remain `TBD` when holdout execution
begins.

## 2. Decision question and claims under test

### 2.1 Primary decision question

Does condition C produce editorial decisions that Jentz judges materially
better than conditions A and B—especially the strong single-Agent baseline
B—without an unacceptable increase in human effort, economic cost, latency,
failure surface, or complexity?

The primary Phase 1F-A evidence is Jentz's blind editorial judgment. The AI
evaluator's result is treatment machinery and diagnostic evidence; it is not
the experiment's ground truth or primary outcome.

### 2.2 Treatment hypothesis

The staged Uncharted AI OS method is expected to improve one or more material
editorial decisions: whether to proceed, return upstream, block on evidence,
reject, escalate, or present an approval-ready package; the strength of the
point of view, attention architecture, payoff, and Jentz voice; and the amount
of rewriting Jentz requires.

Any advantage must remain visible against a genuinely strong single-Agent
baseline. Beating only an intentionally weak prompt would not justify the
architecture.

### 2.3 Simpler-system hypothesis

Condition B may capture most or all of the benefit of the World-Class Role and
Outcome Contract without condition C's orchestration and independent
evaluation loop. Condition A may also remain sufficient for some or all cases.
Either result is valid and should lead to simplification rather than defensive
expansion.

### 2.4 What this pilot cannot establish

This small pilot does not establish:

- statistical superiority across content generally;
- a universal World-Class editorial benchmark;
- real-world Instagram Outcome advantage;
- causal effects of an individual prompt, Artifact, capability step, or Eval;
- `ai_executable` or `automated` maturity;
- permission to publish without human approval; or
- a need for generalized persistence or an Agent framework.

A GO decision authorizes only the bounded Phase 1F-B work named in the final
gate. It is not product validation or a maturity promotion.

### 2.5 Validation claim boundary

Phase 1F-A validates only whether the tested workflow has useful
Jentz-specific product and editorial-operating value for the frozen cohort.
It does not prove universal editorial superiority, World-Class performance in
the abstract, transfer to another creator or platform, or real-world Outcome
advantage. Independent expert calibration and broader representative evidence
remain future work. Reports must state this boundary next to any GO, SIMPLIFY,
or STOP / REDESIGN decision.

## 3. Frozen V1 cohort

Every development and holdout case must be intended for this cohort:

| Cohort attribute | Frozen V1 value |
| --- | --- |
| Channel and distribution | Organic Instagram Reel; no paid amplification |
| Content type | Professional or thought-leadership content |
| Speaker | Jentz, single speaker |
| Language | English |
| Approximate duration | 30–60 seconds |
| Primary format | Talking head |
| Publication authority | Explicit Jentz approval required before publication |

The duration is a cohort descriptor, not a quality formula. The correct
editorial decision may be to reframe, change format, return upstream, or reject
an idea that cannot be served honestly in this cohort.

No condition records footage, edits a Production Artifact, publishes, or
controls distribution. It produces an editorial decision and, where justified,
an approval-ready editorial candidate for separate human consideration.

Personal reflections, entertainment-first videos, product reviews, cultural
commentary, TikTok, LinkedIn, YouTube, long-form video, multi-speaker content,
and paid creative are outside this experiment. A material cohort change
requires a new experiment version rather than an informal exception.

## 4. Experimental unit and case packet

The experimental unit is one case evaluated under all three conditions. Each
case receives an opaque `case_id`. Each condition produces one terminal
editorial decision and, where appropriate, an approval-ready editorial
candidate for the same case.

Before any condition runs, the case is represented once as a canonical source
record. From it, the frozen procedure creates two input surfaces:

1. **Frozen editorial case brief for B and C.** B and C receive the exact same
   byte-equivalent brief, attachments, voice references, available evidence,
   and evidence-access boundary.
2. **Ecological current-workflow input for A.** A receives the simpler input
   pattern Jentz would reasonably use in the current workflow. Its derivation
   is frozen before holdout and must not be selectively degraded or improved
   after seeing any output.

The B/C editorial case brief should contain the Phase 1E Input Contract to the
extent genuinely available:

- one primary Content Job and at most one compatible secondary job;
- target audience;
- content objective and desired audience response;
- approved insight or observation, or an explicit indication that it is weak
  or unresolved;
- Jentz point of view, or an explicit indication that it is missing;
- supporting evidence and source provenance where relevant;
- Attention Thesis where already established, or its explicit absence;
- truth, confidentiality, brand, audience, and authority guardrails;
- relevant Jentz voice references;
- portfolio or repetition context where material; and
- production assumptions that materially constrain the spoken Script.

Missing or weak inputs must not be silently repaired for B or C alone. Case
preparation occurs before generation, is condition-neutral, and cannot use any
condition output. If Jentz supplies a clarification before execution, the
canonical source record is versioned; B and C receive the same updated
editorial brief, and A is regenerated only through its frozen ecological-input
rule. No condition-specific human clarification is permitted after generation
begins.

The two causal comparisons are deliberately different:

- **A versus C — ecological improvement:** does the complete proposed method
  outperform a fair representation of current practice, including its normal
  input pattern?
- **B versus C — architectural improvement:** with the same frozen editorial
  brief, evidence, World-Class context, and comparable resource ceiling, does
  staged orchestration plus independent evaluation add value beyond a strong
  single Agent?

Only B versus C supports a claim about marginal architectural value. A versus
C cannot isolate whether any gain came from better briefing, stronger context,
more inference, or the architecture.

The holdout should reflect real work, including naturally occurring ambiguity
or inadequate inputs. Cases must not be artificially damaged to create an
advantage for condition C.

## 5. Frozen experimental conditions

The operational manifest must contain the exact prompt text, context assembly,
model configuration, tools, output contract, and budgets for each condition.
Jentz must confirm before freeze that A fairly represents his current/simple
practice and B is a serious baseline.

### 5.1 Condition A — Simple/current workflow

Condition A is a reasonable, competent representation of Jentz's current or
simple ChatGPT workflow:

- one direct generation session using the frozen simple prompt and ecological
  A input derived through the frozen current-workflow rule;
- normal concise context or instruction that Jentz would plausibly provide;
- the same generator model/version, reasoning configuration, tool permissions,
  and base output budget used by the other generators where technically
  possible;
- evidence exposure governed by the frozen ecological A input rule rather than
  selectively changed after results are visible;
- permission to challenge, ask for missing evidence through its terminal
  response, or decline a weak brief; and
- the standard blind output envelope required for fair comparison.

It does not receive intentionally vague instructions, degraded evidence,
inferior model settings, artificial time pressure, or a prompt designed to
fail. It does not receive condition C's staged orchestration or independent
evaluator loop.

The exact number of conversational turns must match the frozen representation
of the current workflow. For this pilot the default is one generation turn
without Jentz feedback before blind assessment. If development shows that a
different fixed interaction is essential to face validity, it must be changed
before freeze and applied identically to every A holdout Run.

### 5.2 Condition B — Strong single-Agent baseline

Condition B is the strongest credible simpler alternative:

- one primary Editorial Director Agent operating in one isolated context,
  without another Agent or independent evaluator;
- the exact frozen editorial case brief and evidence supplied to C;
- the applicable World-Class Role context, Phase 1E Outcome Contract,
  integrity guardrails, decision taxonomy, and Jentz-specific context;
- permission to plan and self-check internally, use the allowed tools, return
  upstream, block on evidence, reject, or escalate; and
- the standard blind output envelope.

Condition B may reason holistically, self-critique, revise, and produce
excellent work. It receives a comparable maximum generation, revision, and
total inference budget to C where practical, including the same maximum of two
substantive candidate revisions. It may allocate that budget to single-Agent
planning, critique, and revision but does not receive a separate evaluator,
evaluator-authored readiness decision, staged multi-actor orchestration, or
condition C's internal Artifacts.

Maximum parity does not require waste: if B reaches its terminal submission
using less inference, it may stop and the unused allocation is recorded. The
operational manifest must state how B's maximum call/token envelope compares
with C's generator, evaluator, fact-check, and revision envelope.

### 5.3 Condition C — Uncharted AI OS

Condition C implements the Phase 1E operating method conceptually:

1. receive the exact frozen editorial case brief, evidence, World-Class Role,
   Outcome Contract, and Jentz-specific context supplied to B;
2. validate the Input Contract;
3. perform attributable editorial steps for attention, packaging, story,
   Script, claims, and voice;
4. emit provenance-bearing editorial Artifacts;
5. run deterministic structural validation;
6. obtain an independent evaluator decision against the five domains, anchors,
   hard gates, and Outcome Contract;
7. invoke the frozen conditional evidence/fact-check policy where required;
8. revise, return upstream, block, reject, or escalate within the frozen
   budget; and
9. aggregate the final Artifacts and evaluator-authored decision under one Run
   correlation identity.

The primary creator cannot certify its own readiness. The independent
evaluator must not see the creator's self-score, A or B outputs, Jentz's later
judgments, or another evaluator result before making its decision.

Condition C may perform at most two substantive evaluator-directed revisions
after initial generation. Every post-evaluation regeneration that materially
changes attention, packaging, story, argument, claims, or voice counts toward
that limit. The exact prompt and completion budgets per attempt are frozen.
Condition C's first-pass package and final package must both be retained so the
incremental effect of evaluation and revision can be examined.

### 5.4 Standard blind output envelope

Every condition must be capable of returning the same external categories:

- **Proceed / candidate**;
- **Editorial revision required**;
- **Revise brief**;
- **Evidence required**;
- **Do not develop**; or
- **Human judgment required**.

These neutral categories are the only decision vocabulary shown during primary
blind review. Condition C may retain the richer internal Phase 1E taxonomy, but
terms such as Ready for Human Approval, Minor Revision, Major Revision, Return
Upstream, Blocked — Evidence, Reject, and Human Escalation must not appear in
the blind envelope.

“Proceed / candidate” means only that a candidate is supplied for editorial
judgment. It is not Ready for Human Approval and never authorizes publication.

The manifest freezes a deterministic, condition-neutral mapping. The initial
mapping is:

| Internal decision meaning | Blind external category |
| --- | --- |
| Candidate judged ready for human consideration | Proceed / candidate |
| Candidate exists but requires Capability-level editorial revision | Editorial revision required |
| Upstream audience, objective, insight, point-of-view, or brief defect | Revise brief |
| Material claim support is missing | Evidence required |
| Content should not be developed for this cohort/purpose | Do not develop |
| Legitimate ambiguity or authority decision requires Jentz | Human judgment required |

A and B need not use Uncharted-specific internal labels, but their outputs must
be expressible through the same external categories. If deterministic
normalization cannot map a response without editorial interpretation, the Run
is flagged for protocol review rather than manually recategorized after seeing
its quality.

Each external submission provides only the category and normalized information
needed to judge it. A candidate includes the spoken Script. A non-candidate
includes a concise, audience-facing explanation of the material issue and the
next information or decision required. The blind envelope is not proof that A
or B has an independent evaluator.

## 6. Control and fairness requirements

The prompt/orchestration method is the intended treatment difference. The
following must otherwise be held constant where technically possible:

| Control | Requirement |
| --- | --- |
| Generator model | Same provider model and immutable version or snapshot for A, B, and C |
| Reasoning configuration | Same named level, sampling configuration, temperature, and other exposed reasoning controls for each primary generator |
| Case input | Byte-equivalent frozen editorial case brief for B and C; A uses its separately frozen ecological current-workflow input rule |
| Evidence | Identical available evidence, source snapshot, cutoff, attachments, and access rights for B and C; any ecological A difference is explicit and traced |
| Tools | Same tool availability and tool-result snapshot where practical; condition-specific tool use is traced |
| Language and cohort | Same frozen V1 requirements |
| B/C resource ceiling | Comparable maximum generation, revision, and total inference budget, with the same maximum substantive-revision count where practical |
| Initial generator | Same major completion-token/output budget and timeout for each initial A, B, and C generator where practical |
| Safety and authority | Same confidentiality, truth, publication, and consequential-action constraints |
| Output comparison surface | Same normalized blind presentation fields |
| Execution window | Run the three conditions in a compact block and randomize execution order to reduce provider or time drift |

Condition-specific instructions necessarily differ. B and C receive the same
World-Class context and case material; C additionally receives staged Artifact
and evaluator machinery. A retains the frozen ecological input pattern. Prompt
length, call topology, evaluator tokens, revision tokens, and orchestration
overhead are treatment characteristics, but B must receive a comparable
maximum inference opportunity so C cannot win merely through a much larger
budget. Maximum and actual use must both be measured.

If an external research tool is allowed, the manifest must freeze its query
budget and data-access policy. Prefer a frozen evidence packet for this pilot;
live search can introduce time-varying evidence and unequal tool success. A
conditional fact checker may inspect only the same permitted evidence unless a
pre-registered rule authorizes additional retrieval for every condition.

Where a model provider does not expose an immutable snapshot, seed, reasoning
setting, or exact usage/cost, record that limitation. Do not claim the control
was held. A material model or provider change during holdout execution
invalidates the affected comparison block and requires a new experiment
version or replacement cases before unblinding.

### 6.1 Resource parity, attempts, retries, and failures

- A receives the fixed number of turns and revisions in the frozen ecological
  current-workflow representation.
- B receives one initial single-Agent generation and at most two substantive
  self-directed revisions within its frozen parity envelope.
- C receives one initial generation and at most two substantive revisions
  directed by its independent evaluation loop.
- The manifest must make B and C maximum total inference budgets comparable
  within a predeclared tolerance or document why exact parity is technically
  impossible before any holdout idea is accepted.
- A stochastic rerun because an output is disliked is prohibited.
- A transient infrastructure failure may receive at most one identical retry
  under a policy frozen for all conditions.
- The failed attempt, reason, partial usage, latency, and retry remain in the
  trace.
- A second infrastructure failure becomes a condition failure; it is not
  silently replaced.
- Provider truncation caused by a frozen inadequate budget counts against the
  condition. A platform-wide outage affecting fairness pauses the experiment.

For every condition record model calls, infrastructure retries, semantic
revisions, input/output/cached/reasoning usage where available, wall-clock and
model latency, and monetary cost. Report both allowed maximum and actual use.

The operational comparison measures complete workflows, but B/C resource
parity makes the architectural contrast more credible. Report B and C
first-pass and final submissions separately. A C win does not by itself prove
that staging or independent evaluation caused the gain; later ablation may
still be required.

### 6.2 Unavoidable-difference log

Before unblinding, record every known difference that could affect the result,
including prompt length, unavailable seeds, provider fallback, tool calls,
context truncation, evaluator model, execution order, errors, or manual
handling. A difference discovered after results are known must still be
reported and cannot be rationalized away.

## 7. Development cases and protected pilot holdout

### 7.1 Development set

Use approximately three already-discussed examples only for harness debugging,
prompt development, Artifact-shape refinement, evaluator calibration, and
procedure rehearsal.

Every topic, idea, angle, phrase, source packet, or close variant already
discussed in project documents or prompt-tuning work is contaminated. It may
be useful for development but cannot count as holdout evidence, even if a
specific final Script was not previously generated.

Development Runs must be labelled `development`. They may be repeated and
inspected, but their results cannot appear in the protected pilot evidence or
be used to make the GO/SIMPLIFY/STOP decision.

### 7.2 Protected holdout

Only after the harness, prompts, evaluator instructions, Artifact formats,
budgets, procedure, and decision rules are frozen will Jentz provide
approximately 6–10 fresh real ideas. They must not have appeared in project
documents, development examples, prompt tuning, evaluator tuning, or prior
condition rehearsals.

Jentz must provide the intended holdout batch before any condition output is
reviewed. Cases are screened only for cohort eligibility, duplication,
contamination, safety, and the ability to create the required canonical source
record and frozen input surfaces. Do not select cases based on which condition
is expected to win.

If more than ten eligible ideas are supplied, the manifest's predeclared
selection method chooses the tested cases before generation; remaining cases
become untouched reserves. If fewer than six valid fresh cases remain, do not
claim a completed pilot. Obtain replacements before execution or end with
STOP / REDESIGN because the protocol could not produce valid evidence.

A case discovered to be contaminated before unblinding is retired and replaced
from the untouched reserve. Discovery after unblinding is reported; the case
is excluded from decision evidence and cannot be replaced after condition
performance is known without declaring a new experiment version.

### 7.3 Holdout access and confidentiality

Fresh ideas and unpublished content are sensitive evaluation data. The
operational manifest must state who can access raw cases, condition outputs,
the mapping key, and Jentz judgments; provider data-use settings; retention and
deletion expectations; and whether client or third-party information is
permitted. Raw holdout content should not be copied into general project docs
or reused outside this experiment.

## 8. Freeze point and experiment manifest

Before any holdout idea is accepted, Phase 1F-A.1 must emit one compact,
machine-readable experiment freeze manifest and mark it frozen. JSON, YAML, or
another deterministic serialization is acceptable; the chosen format and
canonicalization rule must be fixed. The long protocol remains the normative
design. The manifest is the reproducible execution snapshot and may not weaken
or silently reinterpret it.

Holdout execution is prohibited until the manifest has been reviewed and every
required value is concrete. It must record or content-address:

- experiment ID and version;
- protocol version and freeze timestamp;
- development-case roster and contaminated-topic exclusion record;
- exact A, B, and C prompts or Playbook versions;
- exact canonical source-record template, ecological A derivation rule,
  identical B/C editorial-brief template, and blind-presentation format;
- primary generator and evaluator provider/model versions;
- reasoning, sampling, seed, timeout, and context settings;
- permitted tools, evidence snapshot, fact-check invocation rule, and tool
  budgets;
- condition-specific turn structure, B/C revision budgets, and the resource-
  parity method/tolerance;
- per-attempt and total token, inference, call, latency, and cost budgets;
- deterministic validation rules;
- evaluator instructions, anchors, hard gates, and blinding rules;
- balanced-position assignment algorithm, case/repeat selection algorithm,
  random seed, seed-custody rule, and mapping protection;
- deterministic mapping from internal decisions to the standard blind output
  envelope;
- Jentz comparison questions and response options;
- primary, diagnostic, resource, and guardrail measures;
- case eligibility, reserve selection, replacement, retry, failure, and
  stopping rules;
- repeatability-subset size and selection rule, derived-seed rule, and
  diagnostic analysis boundary;
- GO/SIMPLIFY/STOP interpretation rules;
- data-access, model-data-use, retention, and deletion controls; and
- named experiment operator and mapping custodian, even if Jentz performs both
  at different times with access separation.

The manifest must contain actual values, not aspirations. Hashes or immutable
file versions should make the frozen material attributable. The harness must
be able to emit and read the same snapshot without relying on undocumented
operator memory; this requirement does not select a database schema.

Any material tuning after a holdout case or output has been observed creates a
new experiment version. Material changes include prompts, model/version,
reasoning, tools, evidence access, revision budget, evaluator instructions,
Artifact representation, randomization/blinding, comparison questions,
resource budgets, case eligibility, or decision rules. Exposed holdout cases
are retired rather than recycled into the new version.

Clerical corrections that cannot affect generation, evaluation, presentation,
or interpretation must be logged. If there is reasonable doubt, treat the
change as material.

## 9. Execution and blinding procedure

For each protected case:

1. assign the frozen opaque `case_id`, finalize one canonical source record,
   and derive the frozen A and B/C input surfaces;
2. derive the condition execution order from the protected seed;
3. execute A, B, and C in isolated contexts under the frozen settings;
4. retain raw outputs, errors, first-pass and final B/C Artifacts, and all
   required resource traces;
5. transform each terminal output into the standard blind envelope without
   editorial rewriting;
6. assign an opaque `blind_presentation_id` to each output;
7. assign each output to a first, second, or third position through the frozen
   balanced schedule;
8. store the condition-to-presentation mapping separately from the review
   bundle;
9. conduct Stage 1 independent review one blind submission at a time and lock
   each assessment before showing its competitors;
10. begin Stage 2 comparative review only after every main-holdout Stage 1
    assessment is locked;
11. where Jentz selects a candidate he would actually use, complete the frozen
    timed-edit capture while condition identity remains hidden;
12. lock all primary judgments, comparisons, edits, and reasons before
    revealing any mapping, condition-specific supporting Artifact, full AI
    evaluation profile or evaluator provenance, resource result, or aggregate
    pattern;
13. record a condition-identity guess and confidence only after the substantive
    judgment and timed edit are locked; and
14. reveal the mapping only after all holdout cases and the pre-unblinding
    evidence summary are complete.

Assignment must be reproducible and balanced, not an unconstrained random
permutation per case. Use seeded allocation across the six possible A/B/C
orders, or an equivalent balanced design, so each condition occupies first,
second, and third position approximately equally. For the final valid holdout,
each condition's position counts must differ by no more than one. Seeded
randomness may choose among valid balanced schedules and assign schedules to
case IDs; it may not destroy the balance constraint.

The seed and condition mapping must remain inaccessible to Jentz during
review. The same assigned position order is used for Stage 1 sequence and
Stage 2 layout so positions are attributable rather than silently changed.

The manifest must also freeze a seeded case-review order and a review-session
policy. Record session, timestamp, duration, and breaks so fatigue or changing
standards can be inspected. Do not reorder difficult cases after seeing any
condition output.

### 9.1 Presentation normalization

The primary blind bundle should expose only information needed to judge the
editorial decision:

- opaque presentation ID;
- one standard external decision category;
- final spoken Script or candidate when one exists;
- a concise external explanation and requested next action when no candidate
  is supplied; and
- an explicit statement that no Script was produced when the condition
  requests brief revision, evidence, non-development, or human judgment.

Use common typography, field order, labels, and file naming. Strip condition
names, prompt or Playbook identity, model names, Attention Maps, Claim Maps,
Story Architecture, capability-step provenance, evaluator output or identity,
internal reasoning, token/cost/latency data, and distinctive orchestration
metadata. Normalization may remove presentation cues but must not improve
prose, invent reasons, suppress a refusal, or conceal a material claim problem.

The standard external category may be deterministically derived from an
internal decision, but no internal evaluator score, anchor, rationale, or label
is exposed. After all primary judgment, comparison, and selected-candidate edit
records are frozen, a separately labelled diagnostic review may reveal full
Artifacts, internal decisions, evaluator results, provenance, prompts, and
resource data. That review is secondary and unblinded.

Blinding cannot guarantee that Jentz will not recognize a style or infer C
from a correct non-script decision. Identity guesses measure this leakage; they
do not justify removing a substantively important editorial decision.

### 9.2 Repeatability subset

One stochastic output per condition cannot establish reliability. Before any
holdout output is generated, select a small diagnostic subset through the
frozen seed:

- two cases when the valid holdout contains six or seven cases; or
- three cases when it contains eight to ten cases.

Each selected case receives exactly one additional independent Run under A,
B, and C. Repeat Runs use isolated contexts, the same frozen condition
settings and input, a separately derived seed where supported, and the same
B/C resource-parity rule. They are generated before any holdout output is
reviewed and cannot trigger tuning or an additional retry.

Repeat outputs receive new Run and blind presentation IDs. Review them in a
separate blind diagnostic session after the main-case primary judgments are
locked, using another balanced presentation schedule. Familiarity with the
case is recorded as a limitation.

Repeat Runs measure within-condition stability of decision category, serious
failures, rewrite burden, and editorial preference. They are not independent
holdout cases, do not increase the primary denominator, and cannot be counted
as extra wins for the GO gate. No claim of statistical repeatability or
significance may be made from this subset.

## 10. Primary human judgment

Jentz evaluates each version as an editorial decision, not merely as prose.
The review form and response vocabulary are frozen before holdout execution.

### 10.1 Stage 1 — independent per-candidate assessment

Show one blind submission at a time without access to the other two versions
for that case. Capture and lock:

- whether its standard external decision category is professionally
  appropriate;
- whether Jentz would use the candidate as presented, use it after a minor
  edit, require major redevelopment, revise the brief, require evidence, not
  develop it, or require a separate human judgment;
- estimated rewrite burden: none, localized/minor, substantial/major, or
  effectively a new piece;
- actual review time where measured;
- material integrity, audience, point-of-view, attention, payoff, voice, or
  strategic concern;
- confidence in the judgment;
- concise reasons; and
- whether the judgment is editorial, Jentz-specific personal preference, or
  both.

Jentz must submit the assessment before the next candidate is shown. Stage 1
responses cannot be edited after Stage 2 begins except through an attributable
correction that preserves the original.

### 10.2 Stage 2 — within-case comparison

Only after every main-holdout Stage 1 assessment is locked, show each case's
three normalized submissions together in their assigned balanced order and
ask:

1. Which version or versions would you publish, subject to the required human
   approval? `None` and multiple selections are valid.
2. If more than one is acceptable, which is the strongest editorial decision,
   or are they materially tied?
3. Which requires the least rewriting? Ties and `not assessable` are valid.
4. Which has the strongest point of view?
5. Which has the strongest sustained-attention architecture, not merely the
   strongest opening?
6. Which provides the strongest and best-fulfilled payoff?
7. Which has the strongest natural Jentz voice?
8. Did any version make a better decision by not producing a Script?
9. What material difference drove each choice?
10. Did editorial preference differ from personal preference? If so, how?
11. How uncertain is the comparison, and what evidence would change it?

Every comparative item permits tie, multiple acceptable, none acceptable,
uncertainty, and not assessable where legitimate. Forced ranking is prohibited
when the difference is not meaningful.

### 10.3 Selected-candidate edit capture

After comparative preference is locked and while workflow identity remains
hidden, identify the candidate Jentz would actually use for the case, if any.
For that candidate record:

- editing start and end time, interruptions, and active editing duration;
- the original candidate text;
- the final edited text;
- a localized machine-generated or human-verifiable diff;
- reasons for every substantive change;
- whether each change concerns integrity, point of view, attention, payoff,
  voice, strategic fit, factual support, or personal preference; and
- whether the final result is genuinely usable or still requires upstream work.

If no candidate would be used, record that decision and reason; do not force an
edit merely to create data. Estimated no/minor/major rewrite labels remain
required for every blind candidate so actual editing of the selected candidate
does not become the only human-effort comparison.

### 10.4 Human judgment limitations

Jentz is the authoritative first-slice owner and voice authority, but one
reviewer's judgment is not universal World-Class ground truth. Preserve
reasons, confidence, ties, editorial-versus-personal distinctions, and later
changes of mind. An optional qualified external editorial review may be
pre-registered as secondary evidence, but it cannot be added after seeing
results or silently replace Jentz as the primary outcome.

## 11. Correct non-script outcomes

Return Upstream, Blocked — Evidence, Reject, and Human Escalation are valid
professional outcomes. A condition must not be penalized for withholding a
polished Script when Jentz judges that the brief, point of view, insight,
evidence, cohort, or authority boundary makes that the better decision.

For every non-script disposition, Jentz assesses:

- whether the identified problem is real and material;
- whether the destination or escalation is correct;
- whether the rationale is specific and proportionate;
- whether the condition requested the minimum useful next action; and
- whether a world-class professional should reasonably have proceeded.

Correct restraint contributes to Quality and Reliability. Incorrect or
over-conservative refusal is not rewarded: false Return Upstream, unnecessary
evidence blocking, reflexive escalation, or rejection of a viable case counts
as a judgment failure and human-effort cost. A condition cannot win by refusing
more often.

## 12. Four separate success dimensions

The pilot reports four profiles. It must not combine them into a weighted
score, average, leaderboard, or fabricated measure of overall intelligence.

### 12.1 Quality Advantage

Question: does the condition make materially better editorial decisions and
produce materially stronger approval candidates?

Evidence includes:

- blind publish consideration and strongest-editorial-decision selections;
- rewrite-burden category;
- point-of-view, sustained-attention, payoff, and voice comparisons;
- integrity and promise fulfilment;
- correct challenge, return, blocking, rejection, and escalation;
- severity and reasons for weaknesses; and
- full-Artifact usefulness in the secondary diagnostic review.

A material improvement changes publishability, decision correctness,
substantive revision burden, or a critical editorial dimension. A preferred
synonym or cosmetic phrasing difference is not a material win.

### 12.2 Reliability Advantage

Question: does the condition make the correct kind of decision more
consistently and avoid severe failures?

Evidence includes:

- Proceed / candidate, Editorial revision required, Revise brief, Evidence
  required, Do not develop, and Human judgment required compared with Jentz's
  blind judgment;
- condition C's richer internal Phase 1E decision as secondary diagnostic
  evidence after unblinding;
- false-ready, missed-hard-fail, fabricated-claim, broken-promise, and
  confidentiality failures;
- false blocking, false rejection, and unnecessary escalation;
- completion, truncation, tool, validation, and infrastructure failures;
- adherence to the revision and authority budgets; and
- consistency across the representative case mix without hiding severity in
  an average.

One unique critical integrity or authority failure can outweigh several minor
stylistic wins. Reliability is reported by failure type and severity, not one
percentage detached from the small denominator.

### 12.3 Human-Effort Advantage

Question: does the workflow reduce the human work required to reach a sound
publication decision and acceptable Artifact?

Evidence includes:

- Jentz review time where measured;
- estimated and actual rewrite category;
- timed editing of the blind candidate Jentz would actually use;
- original and final edited text, localized diff, and substantive change
  reasons;
- amount and type of localized change;
- number of clarifications or decisions requested from Jentz;
- cognitive burden of understanding the output and its risks;
- usefulness versus overload of supporting Artifacts; and
- time spent resolving incorrect refusal, evaluator disagreement, or unclear
  provenance.

Canonical source-record preparation common to all conditions is reported
separately. Time needed to derive A's ecological request and to construct the
structured B/C editorial brief must also be recorded separately; the A/C
ecological comparison must not hide additional briefing effort. AI compute
time is not human effort. A longer structured package is not an advantage
unless it improves a real decision or reduces downstream work. Time spent
administering the three-way experiment is experiment overhead and must not be
attributed to a condition as normal operating effort.

### 12.4 Economic Advantage

Question: is the marginal value worth the operational resource increase?

Evidence includes:

- model and tool calls;
- input, output, cached, and reasoning usage where exposed;
- estimated and actual monetary cost where available;
- wall-clock and model latency;
- retries and failed-call cost;
- evaluator, fact-check, and revision overhead;
- human time required for common source preparation, A-input derivation, and
  B/C editorial-brief construction;
- Jentz review and selected-candidate editing time, shown as raw time and, only
  if a rate was frozen in advance, an optional time-cost estimate;
- orchestration steps and failure surface; and
- expected implementation, maintenance, calibration, and operational
  complexity.

Report absolute values and C's increment over both A and B by case and across
the pilot. If provider cost or usage is unavailable, label it unknown; do not
invent precision. Latency and complexity remain visible even when monetary
cost is small. Measured usage and latency must be separated from estimated
future implementation or maintenance effort.

## 13. Analysis plan

### 13.1 Comparisons

The primary contrast is C versus B: architectural improvement under identical
editorial inputs and comparable maximum resources. C versus A is ecological
improvement over current practice. B versus A helps distinguish the value of
stronger briefing and World-Class context from the marginal value of
orchestration and evaluation.

Use within-case paired evidence. For every question, report:

- valid denominator;
- A, B, and C selections;
- C-over-B, B-over-C, and material-tie cases;
- none/multiple/not-assessable responses;
- confidence and concise reasons;
- failure severity and non-script decision correctness; and
- missing, excluded, contaminated, or failed cases.

Do not create one aggregate creative score or choose weights after seeing
results. Do not treat correlated questions as independent votes. With 6–10
cases, descriptive counts, paired case narratives, ranges, and uncertainty are
more honest than a claim of statistical significance.

The repeatability subset is analyzed separately by original case. Report
decision-category stability, serious-failure recurrence, rewrite-burden
movement, and whether Jentz materially changes his preference. Do not pool
repeat Runs into the main denominator or treat them as independent cases.

### 13.2 Pre-unblinding summary

Before revealing condition mappings, lock:

- every per-version and within-case Jentz judgment;
- selected-candidate editing time, final text, diff, and change reasons;
- repeatability-subset judgments, separately labelled diagnostic;
- exclusions and protocol deviations;
- presentation-order and guessed-identity data;
- resource traces and failures, without showing them to Jentz during primary
  judgment;
- a blind-ID evidence table; and
- the rules/code that will map condition identities into the final report.

After mapping reveal, generate the condition comparison mechanically where
possible. Preserve the blind-ID table so retrospective reinterpretation is
visible.

### 13.3 Interpretation discipline

- C's final result and first-pass result are reported separately.
- A C win after revision does not prove which staged component caused it.
- B matching C is evidence for simplification, not an Eval failure to hide.
- A matching B and C is evidence that the extra context and structure did not
  earn their cost in this cohort/sample.
- A material B/C tie defaults toward B; a material three-way tie defaults
  toward the simplest valid workflow for that case class.
- No individual case, phrase, or evaluator rationale becomes a Playbook rule.
- Fresh holdout outputs cannot be moved into prompt examples until this
  experiment is closed and they are formally retired from holdout status.
- Real-world Outcome claims require later publication and telemetry evidence;
  they are outside this experiment.

## 14. Resource budgets and acceptability

Before freeze, Jentz must approve explicit hard ceilings and target ranges for:

- initial generation calls and tokens per condition;
- comparable B/C maximum total inference, call, and token envelopes, including
  the permitted tolerance and treatment of C evaluator/fact-check usage;
- B self-critique/revision and C evaluator/fact-check/revision calls and tokens;
- maximum two substantive revisions for both B and C;
- wall-clock latency per condition and per case bundle;
- monetary cost per case and for the pilot;
- transient retry count;
- Jentz review and rewrite time; and
- implementation and operating complexity acceptable for Phase 1F-B.

The manifest must state what happens when a ceiling is exceeded. Default:
stop the affected condition, retain the partial trace, count the breach, and do
not grant an unregistered extra attempt.

Resource acceptability is a product judgment made against the observed quality
and reliability difference. Budgets must be frozen before holdout outputs are
seen so an expensive preferred result cannot retroactively redefine
“acceptable.”

## 15. Decision gate

After all mappings are revealed, the pilot must end with exactly one decision.
The burden of proof lies with added complexity.

### GO

Choose GO only when all are true:

- C shows a meaningful blind Quality advantage over B, repeated across at
  least two independent holdout cases and not limited to cosmetic preference;
- C also shows at least one additional material benefit over B, such as lower
  estimated or actual revision burden, fewer serious failures, better correct
  refusal/routing, lower human effort, or another predeclared operational
  benefit;
- there is no equal-or-greater opposing pattern, unique critical failure, or
  guardrail regression that neutralizes that advantage;
- C is not winning only because of an invalid control, leakage, selective
  retry, or contaminated case;
- the Human-Effort and Economic profiles remain within their predeclared hard
  ceilings and Jentz judges the incremental burden acceptable; and
- the advantage is operationally meaningful enough to justify the bounded
  Phase 1F-B follow-up.

GO means “test and refine the useful structured components in Phase 1F-B.” It
does not mean the whole architecture is necessary, causal, production-ready,
or ready for generalized implementation.

### SIMPLIFY

Choose SIMPLIFY when a valid pilot indicates that:

- B captures essentially the same editorial value as C with lower complexity,
  cost, latency, or human burden;
- C and B are materially tied, because a tie defaults toward the simpler
  single-Agent system;
- C's advantage over B is isolated, marginal, inconsistent, or offset by
  human effort, cost, latency, failures, or complexity;
- only one bounded C component appears useful and should be tested without the
  complete loop; or
- A is adequate for some case classes and a lighter routing rule is more
  appropriate than universal C execution.

SIMPLIFY must name the smallest workflow or component hypothesis worth keeping.
It must not quietly rebuild condition C under a different label.

### STOP / REDESIGN

Choose STOP / REDESIGN when:

- neither B nor C shows credible material value over A;
- C fails to justify its additional complexity and no smaller structured
  component has credible value worth retaining;
- C causes worse critical judgment, integrity, authority, or reliability;
- resource or complexity ceilings are materially breached without
  compensating value;
- contamination, unblinding, model drift, missing trace, or procedural failure
  makes the pilot incapable of supporting a decision; or
- fewer than six valid protected cases remain and cannot be replaced under the
  frozen rules.

STOP / REDESIGN may mean stop the architecture, redesign the protocol, narrow
the cohort, or form a different hypothesis. It is not permission to declare
success because a harness was built.

“Successfully built the system” is never a success criterion.

This gate is a bounded product judgment, not a statistical-significance test.
No p-value, confidence claim, or universal superiority statement may be
invented from this pilot.

## 16. Minimum Run trace for the later harness

Every condition Run must carry one correlation identity. At minimum capture:

- `run_id`;
- experiment ID and version;
- protocol and manifest version;
- `case_id`, canonical source-record version, and condition input-surface
  version;
- common source-preparation and condition input-derivation human time;
- workflow condition A, B, or C;
- original Run ID for a pre-registered repeat, or explicit `not_a_repeat`;
- execution order and timestamps;
- generator and evaluator model/provider version;
- reasoning and sampling configuration;
- prompt or Playbook version;
- permitted and actually used tools/evidence snapshot;
- random seed where exposed;
- maximum permitted and actual inference/call/token budget;
- initial attempts, infrastructure retries, semantic revisions, and revision
  reasons;
- per-step and total latency;
- usage and cost where available, with unavailable fields explicit;
- raw and normalized Artifacts, including B and C first-pass and final
  versions;
- capability-step provenance for C Artifacts;
- deterministic validation result;
- evaluator and fact-check result where applicable;
- terminal disposition and reasons;
- standard blind-envelope category;
- `blind_presentation_id`, Stage 1/Stage 2 presentation position, and review
  session;
- mapping-key reference kept outside the review bundle;
- Jentz's locked independent judgment, comparison, confidence, reasons, and
  estimated rewrite effort;
- selected-candidate editing time, original/final text references, localized
  diff, and substantive change reasons; and
- deviations, failures, exclusions, and data-handling classification.

This is a trace contract, not a persistence schema. Phase 1F-A.1 may use
bounded files or in-memory structures suitable for the pilot. Hidden
chain-of-thought is not a trace requirement; attributable configuration,
Artifacts, evidence, decisions, concise rationale, and resource use are.

## 17. Holdout-protection rules

Protected cases and their close variants must not be used for:

- prompt or Playbook rewriting;
- few-shot examples;
- evaluator instruction or rubric tuning;
- Artifact-format tuning;
- budget or retry-policy tuning;
- repeated generation until a preferred answer appears;
- model selection after comparing performance on the case;
- deciding which cases to report; or
- informal demonstrations that reveal outputs before judgments are locked.

Access for execution does not make a case development data. If any case or
output is inspected to tune generation, evaluation, formatting, budgets, or
procedure, retire the case and every close variant and replace it with a fresh
eligible case before the new experiment version begins.

The only permitted additional generation is the single pre-registered Run for
each condition on the seeded repeatability subset. It occurs under the frozen
manifest before review, is diagnostic, and cannot be extended after seeing a
result.

Do not repeatedly peek at partial aggregate results. Jentz may complete cases
in sessions, but no condition mapping or condition-level aggregate is revealed
until all judgments are locked. Safety issues may stop the experiment without
revealing mappings.

## 18. Deviations, stopping, and invalid evidence

A protocol deviation log is mandatory. It records what happened, affected
Runs/cases, when it was discovered, whether mappings or outcomes were known,
and the predeclared consequence.

Pause before unblinding when:

- the frozen model or critical tool becomes unavailable;
- a case packet was not supplied equally;
- the mapping or seed is exposed to Jentz;
- a presentation contains an internal decision label, condition label,
  evaluator output, internal Artifact, or distinctive metadata leak;
- balanced position counts or the two-stage review order are violated;
- a retry or budget rule is applied unequally;
- output normalization would require editorial judgment; or
- sensitive data may have been exposed beyond its authorized boundary.

Correct only through a rule allowed by the frozen manifest. Otherwise retire
the affected case or create a new experiment version. Never repair the better-
performing condition while retaining a weaker comparator output.

Early stopping for apparent superiority or inferiority is prohibited in this
small pilot. Stop early only for safety, authority, privacy, systemic provider
failure, mapping compromise, or a hard resource ceiling. Report all completed
cases and why the pilot stopped.

## 19. Phase 1F-A.1 implementation boundary

If this protocol is approved, Phase 1F-A.1 may implement only:

- compact machine-readable freeze-manifest emission and validation;
- typed Artifact representations;
- A/B/C execution interfaces;
- deterministic validation;
- Run/correlation tracing;
- seeded blind randomization;
- comparison-bundle generation;
- result capture; and
- latency and cost capture where available.

It must not implement:

- a UI;
- a database, schema, or migration;
- Instagram ingestion or publication;
- a weekly learning engine;
- generalized Role, Capability, Agent, Run, Artifact, Eval, Experiment, or
  Playbook persistence;
- a generalized Agent framework;
- deep Langflow or product integration;
- autonomous publication, delivery, spending, permission changes, destructive
  action, or Playbook promotion; or
- product-wide model routing.

Use the smallest local harness capable of executing the frozen protocol and
producing reviewable evidence. Langflow is not required merely to prove that a
Langflow integration could be built.

## 20. Critical design review and safeguards

### 20.1 Head of AI Systems & Evaluation lens

| Material risk | Safeguard in this protocol |
| --- | --- |
| C wins because it receives more calls or tokens, not because its architecture is better | Give B a comparable maximum inference/revision envelope, trace maximum and actual use, preserve B/C first-pass and final outputs, and treat component attribution as unresolved pending ablation. |
| A is a straw baseline or B is quietly weakened | Jentz validates A's face validity and B's strength before freeze; B receives the World-Class context, guardrails, tools, evidence, and permission to make non-script decisions. |
| Development contamination inflates apparent generalization | Approximately three known cases are development-only; 6–10 fresh ideas arrive only after the full freeze; close variants are excluded. |
| Evaluator or cross-condition leakage | Isolated contexts; C evaluator cannot see A/B, creator self-score, Jentz judgment, or other evaluator results; primary review shows only the neutral external envelope, without evaluator output, provenance, or the full evaluation profile. |
| Generator and evaluator share correlated model blind spots | Treat logical separation as limited independence, freeze and report the evaluator model, test disagreements on development cases, and keep Jentz's blind judgment—not the model grader—as primary evidence. |
| Unequal retry, timeout, or token policy creates selective advantage | Frozen per-condition budgets, one identical infrastructure retry maximum, no disliked-output reruns, and full failed-attempt trace. |
| Rich C formatting reveals identity or wins through volume | Common normalized primary presentation; full structured Artifacts withheld until secondary diagnostic review; identity guesses measure residual leakage. |
| Benchmark gaming optimizes known review questions | Fresh holdout, frozen questions, no holdout tuning, multi-dimensional reasons, hard failures, and no scalar reward. |
| Case selection favours one condition | Jentz supplies the batch before outputs; eligibility and reserve selection are predeclared and condition-neutral. |
| Model or platform drift breaks comparability | Compact randomized execution blocks, immutable versions where possible, explicit limitation log, and re-versioning after material change. |
| Presentation order, fatigue, or reviewer drift favours a condition or case | Seed and approximately balance within-case presentation order, seed case-review order, freeze session rules, and record review timestamps, duration, and breaks. |
| Small sample produces false confidence | Descriptive paired evidence, explicit uncertainty, no significance claim, at least six valid cases, and GO limited to a bounded follow-up. |
| One reviewer conflates preference with universal quality | Separate editorial and personal preference, capture reasons/confidence/ties, and permit a pre-registered secondary expert without changing the primary outcome. |

### 20.2 Head of Experimental Design lens

| Material risk | Safeguard in this protocol |
| --- | --- |
| A and C are compared as if they isolate architecture | Label A/C ecological and B/C architectural; only B and C receive the identical frozen editorial brief and evidence. |
| Structured briefing improves B/C but its human preparation cost is hidden | Record common source preparation, ecological A derivation, and incremental B/C brief-construction time separately; include the difference in A/C human-effort and economic interpretation. |
| Maximum budgets look equal while actual inference differs materially | Record maximum and actual calls, retries, revisions, tokens, latency, and cost; report early stopping and unused allocation rather than forcing waste. |
| Unconstrained random order creates position imbalance | Allocate seeded schedules under a hard balance constraint so each condition occupies each position within one case of the others. |
| Seeing competing versions anchors the first judgment | Stage 1 shows and locks each blind candidate independently; Stage 2 comparison begins only afterward. |
| Repeat Runs inflate the apparent sample or enable rerolling | Pre-register a seeded two- or three-case subset, allow exactly one additional Run per condition, and analyze repeats separately from the primary denominator. |
| Internal taxonomy or structured artifacts trivially unblind C | Use one neutral external decision envelope; hide internal labels, Artifacts, evaluator output, prompts, reasoning, and resources until primary judgment is frozen. |
| Deterministic normalization changes substantive meaning | Freeze and rehearse the mapping on development cases; flag an unmappable response rather than manually reinterpret it after output quality is visible. |
| Actual editing is observed only for the selected candidate | Retain estimated rewrite burden for all candidates; treat selected-candidate time/diff as operational evidence, not a condition-wide unbiased estimate. |
| Attrition or exclusions are outcome-dependent | Freeze eligibility, reserve, replacement, and exclusion rules; preserve every exclusion and whether condition performance was known. |
| Many correlated questions create a false vote count | Report dimensions separately, do not count questions as independent observations, and make no statistical-significance claim. |

### 20.3 Head of Product lens

| Material risk | Safeguard in this protocol |
| --- | --- |
| The experiment cannot genuinely reject the architecture | Explicit GO/SIMPLIFY/STOP gate; C must beat strong B, not merely A; successful implementation has no evidentiary value. |
| Engineering precedes proof | A.1 is limited to typed Artifacts, interfaces, validation, trace, blinding, bundles, results, and resource capture; no UI, database, framework, or deep integration. |
| Complexity is treated as free | Human effort, cost, latency, call count, failure surface, maintenance, and cognitive overhead remain separate evidence and have predeclared ceilings. |
| A bundled C win is misread as proof every component is necessary | GO authorizes component-level validation or ablation in Phase 1F-B; SIMPLIFY names the smallest useful mechanism. |
| The method is applied to every case regardless of value | Report A/B/C by case and allow lighter routing when A or B is sufficient; do not universalize C from an average. |
| Pilot evidence is mistaken for business Outcome evidence | Scope the pilot to editorial decisions and human effort; Instagram performance and causal Outcome learning remain later work. |
| A tie is used to rationalize the more elaborate system | Default material ties to the simpler workflow and require both blind Quality advantage and another material benefit for GO. |

### 20.4 Head of Editorial Operations lens

| Material risk | Safeguard in this protocol |
| --- | --- |
| Comparison rewards polished prose rather than editorial judgment | Judge the external decision, challenge, evidence handling, point of view, sustained attention, payoff, voice, and rewrite burden—not prose alone. |
| Correct rejection or upstream routing is scored as missing output | Explicit non-script assessment rewards proportionate professional restraint. |
| C games reliability through over-refusal | False blocks, false returns, unnecessary escalation, and rejection of viable work count as failures and human effort. |
| Strong opening disguises weak continuation | Ask separately about sustained attention and fulfilled payoff; do not use hook preference as a proxy. |
| Jentz voice preference erases World-Class quality | Record editorial and personal preference separately and allow them to disagree. |
| Cohort variation hides weak method transfer | Freeze one narrow organic Instagram talking-head cohort; re-version rather than generalize to other platforms or formats. |
| Case packets over-clean real editorial ambiguity | Preserve naturally missing or weak inputs equally across conditions and assess whether each condition responds professionally. |

### 20.5 Cross-cutting data and authority safeguards

| Material risk | Safeguard in this protocol |
| --- | --- |
| Fresh ideas or unpublished content leak into general development data | Restrict access, freeze provider data-use settings, avoid copying raw cases into general docs, and define retention/deletion before execution. |
| A blind bundle is mistaken for approval | Every candidate remains unapproved; Jentz's experiment judgment does not itself trigger publication. |
| Experiment findings silently change a Playbook | The pilot produces a decision and hypotheses only; any later material Playbook change still requires evidence, regression Eval, approval, version promotion, and rollback. |
| Run traces become indiscriminate content archives | Capture attributable minimum evidence with classification and retention controls; do not require hidden reasoning. |

## 21. Pre-holdout readiness checklist

The mapping custodian must confirm all items before accepting the first fresh
holdout idea:

- [ ] Protocol approved and versioned.
- [ ] Approximately three contaminated development cases completed.
- [ ] A confirmed by Jentz as a fair current/simple workflow.
- [ ] B challenged and confirmed as a strong single-Agent baseline.
- [ ] Exact A/B/C prompts and standard blind output envelope frozen.
- [ ] Compact machine-readable freeze manifest emitted and validated.
- [ ] A ecological input rule and byte-identical B/C case-brief rule frozen.
- [ ] Generator/evaluator models, reasoning, tools, evidence, and budgets
      frozen.
- [ ] Comparable B/C maximum inference and two-revision envelopes frozen.
- [ ] C evaluator and fact-check invocation rules frozen.
- [ ] Deterministic validation and full trace tested on development only.
- [ ] Comparison questions, response options, and materiality anchors frozen.
- [ ] Standard blind envelope and deterministic internal-state mapping frozen.
- [ ] Balanced position assignment, two-stage review, seed custody, mapping
      separation, and presentation normalization rehearsed without holdout
      data.
- [ ] Repeatability-subset selection and diagnostic analysis rules frozen.
- [ ] Retry, replacement, exclusion, deviation, and stop rules frozen.
- [ ] Hard resource ceilings approved by Jentz.
- [ ] Data access, provider use, confidentiality, retention, and deletion rules
      approved.
- [ ] GO/SIMPLIFY/STOP rules frozen.
- [ ] No holdout content has entered prompts, examples, evaluators, or docs.

If any item is false, holdout execution does not begin.

## 22. Required experiment outputs

The completed pilot must produce a review bundle containing:

- frozen protocol and operational manifest versions;
- development/holdout separation and contamination attestation;
- case eligibility, exclusions, reserves, and deviations;
- blinded presentation bundles and protected mapping record;
- locked Jentz judgments with reasons, confidence, ties, and preference type;
- per-case A/B/C Quality, Reliability, Human-Effort, and Economic profiles;
- first-pass versus final B/C diagnostics;
- separately labelled repeatability-subset diagnostics;
- selected-candidate editing time, final edited text, diff, and reasons;
- failures, hard gates, non-script decisions, retries, latency, usage, and cost;
- unresolved confounds and identity-leakage results;
- a concise evidence argument for exactly one gate decision; and
- GO, SIMPLIFY, or STOP / REDESIGN with the smallest authorized next step.

No output should imply that the pilot measured published Instagram Outcomes or
proved causal superiority beyond the tested cases and frozen cohort.

## 23. Decisions deliberately deferred to the operational freeze

Phase 1F-A.0 defines the experiment but cannot truthfully invent values that
depend on the not-yet-built harness or provider account. Before holdout, the
manifest must resolve:

- exact prompt and Playbook text;
- exact model snapshots and exposed reasoning/sampling settings;
- exact development-case roster and contaminated-topic register;
- protected holdout range, final-count rule, and reserve selection method;
- evidence/tool snapshot and conditional fact-check rule;
- concrete B/C parity tolerance and token, call, latency, monetary, and
  human-time ceilings;
- exact random seed generation and custody mechanism;
- presentation normalizer and proof it does not alter substance;
- exact review form wording and any pre-registered secondary reviewer;
- implementation-specific failure classification; and
- confidential-data handling and retention periods.

These are required pre-execution values, not permission to tune after holdout
exposure. Failure to resolve them blocks the experiment.
