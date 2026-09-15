# Capability Specification: Talking-Head Content Development

## 1. Status

Status: Phase 1E documentation specification, awaiting review.

This document defines the V1 Outcome Contract and evaluation architecture for
Talking-Head Content Development. It does not implement an Agent, Eval,
Workflow, Run, Artifact store, telemetry collector, approval control, database
schema, API, or frontend behaviour.

Read alongside:

- [AI Role and Learning Architecture](../AI_ROLE_AND_LEARNING_ARCHITECTURE.md)
  for the Phase 1C concept boundaries and governance;
- [Editorial & Content Director](../roles/EDITORIAL_CONTENT_DIRECTOR.md) for
  the Phase 1D World-Class Role benchmark;
- [Domain Model](../DOMAIN_MODEL.md) for the unchanged Capability definition;
  and
- [Architecture](../ARCHITECTURE.md) for the Uncharted/Langflow boundary.

All fields, records, statuses, datasets, and traces described here are
conceptual. They are not persistence or API designs.

## 2. Capability identity

| Attribute | V1 definition |
| --- | --- |
| Capability | Talking-Head Content Development |
| Domain meaning | Repeatable business work that produces a meaningful outcome |
| Accountable World-Class Role | Editorial & Content Director |
| Initial cohort | Organic professional/thought-leadership Instagram Reel |
| Speaker | Jentz |
| Language | English |
| Approximate duration | 30–60 seconds |
| Publication authority | Explicit human approval required |
| Execution engine | Langflow may support a future Workflow; it does not own this Capability |

The Capability is the orchestration-level parent for producing an
approval-ready editorial package intended for an organic professional
Instagram talking-head Reel. It coordinates sufficiently developed editorial
intent, specialist capability steps, their attributable Artifacts, and an
independent readiness decision. Producing a polished Script is not sufficient:
the package must preserve the Content Job, audience, insight, Jentz point of
view, attention logic, evidence integrity, voice, promise, and strategic fit.

The Capability is not a Role, Agent, Workflow, Run, or Artifact. A future Agent
may act for the accountable Role; it does not become the Capability.

## 3. Scope

### 3.1 What the Capability owns

Within the V1 cohort, Talking-Head Content Development owns orchestration of
the complete editorial package, including:

- validating that required upstream inputs are present and adequate for
  content construction;
- challenging an input and returning it upstream when its underlying judgment
  is weak;
- coordinating the specialist capability steps needed to create each
  attributable Artifact;
- maintaining coherence across attention, packaging, story, claims, Script,
  and voice;
- conducting a specialist self-check and responding to independent evaluation;
- aggregating the creator Artifacts and the independent evaluator's decision
  into the parent Run record; and
- returning work, blocking on evidence, or escalating rather than disguising
  unresolved quality, evidence, or authority problems.

The parent Run may conceptually involve this decomposition:

    TALKING-HEAD CONTENT DEVELOPMENT
    ├── ATTENTION & RETENTION ENGINEERING
    │   └── Attention Thesis / Attention Map
    ├── HOOK & PACKAGING DEVELOPMENT
    │   └── Hook / packaging direction
    ├── STORY ARCHITECTURE
    │   └── Narrative structure
    ├── SCRIPT DEVELOPMENT
    │   └── Spoken Script
    ├── CLAIM GOVERNANCE
    │   └── Claim Map
    ├── VOICE CALIBRATION
    │   └── Jentz-specific refinement
    └── EDITORIAL EVALUATION
        └── Independent readiness decision

These are conceptual parent/child Capability boundaries for attribution,
diagnosis, evaluation, observability, maturity assessment, and learning. They
do not prescribe database records, a persistence relationship, or one Agent
per step. The initial implementation may use one primary Editorial Director
Agent to perform several creation steps, while independent evaluation remains
logically separate.

The decomposition does not absorb upstream professional judgment: approved
attention strategy and other upstream editorial inputs remain prerequisites,
and weak upstream thinking must be returned to its accountable Capability.
Every Capability retains the existing definition: “A repeatable unit of
business work that produces a meaningful outcome.”

### 3.2 What it does not own

The Capability does not own:

- audience or cultural research as a whole;
- content opportunity discovery or portfolio strategy;
- inventing a useful insight when the approved insight is inadequate;
- manufacturing a Jentz point of view;
- general-purpose research beyond content-specific evidence needs;
- recording performance, camera, lighting, sound, editing production footage,
  captions, graphics, cover production, or art direction;
- paid media, platform engineering, organic distribution, or scheduling;
- external publication or control of distribution;
- sales conversion;
- automatic Outcome attribution;
- material Playbook promotion; or
- changing permissions, spending money, contracting, or destructive action.

### 3.3 Return work to the right boundary

The Capability may clarify or challenge upstream inputs. It must not
brute-force an upstream failure into apparently polished copy.

| Input problem | Required boundary response |
| --- | --- |
| Weak or unsupported insight | Return upstream to Insight Development |
| Missing, generic, or inauthentic point of view | Return upstream to Point-of-View Development |
| Wrong or materially vague audience | Return upstream to the audience/content-planning owner |
| Unclear strategic purpose or inadequate Content Job | Return upstream to Content Job or opportunity definition |
| Attention thesis lacks a truthful reason to stop or continue | Return upstream to Attention & Retention Engineering |
| Material evidence is missing but obtainable | Block on evidence rather than dramatize the claim |
| Legitimate ambiguity exceeds delegated judgment | Escalate to Jentz or another authorized human |

A correct Return Upstream is evidence of professional judgment, not
automatically a failed Run.

## 4. V1 content cohort

The initial benchmark is deliberately narrow:

- organic Instagram Reel;
- professional or thought-leadership content;
- one visible speaker: Jentz;
- English;
- approximately 30–60 seconds;
- primarily talking-head;
- no paid amplification assumed; and
- explicit human approval before publication.

The duration is a cohort descriptor, not an automatic quality rule. A piece
should be shortened, lengthened, reformatted, or rejected if the idea cannot be
served honestly in the cohort.

This V1 evaluation must not be silently generalized to:

- personal reflections;
- product reviews;
- cultural commentary;
- entertainment-first videos;
- TikTok;
- LinkedIn;
- YouTube;
- long-form video;
- multi-speaker content; or
- paid-distribution creative.

Each materially different format, audience context, platform, language, or
Content Job mix is a future cohort or variant. A cohort change requires
representative examples, recalibrated anchors, telemetry verification, and
regression review rather than a renamed prompt.

## 5. Accountable Role

The single accountable World-Class Role is:

> **Editorial & Content Director**

The Role owns the professional judgment standard and accountability for
quality and intended Outcomes within its sphere of influence. Supporting
Agents or future Roles may research, fact-check, evaluate, produce, or advise,
but they do not share this Capability's accountability.

Any Agent acting for the Role is accountable for the applicable Outcome
Contract, including correct refusal, upstream return, evidence blocking, and
escalation. Artifact generation alone does not constitute success.

Jentz retains final publication authority. Human authority does not make the
Role deferential: it remains obliged to challenge weak ideas, misleading hooks,
unsupported claims, poor edits, audience mismatch, and performance
misinterpretation.

## 6. Content Job

Every Run must declare one primary Content Job and may declare one secondary
Content Job. The job forces a priority; it is not a fixed database enum, a
complete objective, or a universal success metric.

The Content Job names the primary kind of effect; the content objective states
the specific change sought from this audience in this Run. “Authority” is a
job. “Help HR leaders recognize that buying AI tools before redesigning work
creates avoidable failure” is an objective.

Initial planning vocabulary:

| Content Job | Intended editorial effect | Common misuse to avoid |
| --- | --- | --- |
| Authority | Demonstrate credible, distinctive expertise to the relevant audience | Mistaking confident tone or reach for earned authority |
| Reach | Increase exposure among more of the right audience | Optimizing raw views or broad attention regardless of audience quality |
| Trust | Strengthen credibility, candour, reliability, or relationship | Treating agreeable or unchallenging content as trustworthy |
| Conversation | Prompt substantive, relevant discussion or response | Rewarding comments generated by confusion, outrage, or bait |
| Education | Improve useful understanding, judgment, or ability | Stacking information without insight or application |
| Positioning | Associate Jentz with a distinctive, strategically valuable point of view or territory | Chasing novelty that Jentz cannot credibly own |
| Conversion | Support a defined, appropriate next step or downstream business signal | Claiming sales ownership or using coercive calls to action |
| Experiment | Contribute a governed case to a predeclared editorial comparison while preserving quality and guardrails | Treating one Run as proof or publishing low-quality variants merely to create data |

Each Run must instantiate the chosen job with:

- primary objective;
- target audience;
- desired audience response;
- one or a small number of decision-relevant success signals;
- guardrail signals;
- relevant measurement window and known limitations; and
- the decision the evidence is intended to inform.

The optional secondary job must not compete with the primary job. If the piece
must make incompatible trade-offs, split it into separate work rather than
claiming every job.

Example:

| Content Job field | Example |
| --- | --- |
| Primary | Authority |
| Secondary | Conversation |
| Audience | Corporate leaders and HR/L&D decision-makers |
| Desired response | “This person understands a problem I experience and has a useful, distinctive perspective on it.” |
| Candidate success signals | Relevant saves/shares, substantive decision-maker responses, qualified profile or conversation signals |
| Guardrails | No unsupported authority claim, wrong-audience growth, cheap controversy, or positioning damage |

Content Job labels overlap conceptually: Authority, Trust, and Positioning can
reinforce one another, while Reach can support any of them. One primary label
is therefore a prioritization device. The specific objective, audience
response, measures, and trade-offs are authoritative.

## 7. Input Contract

The Capability should begin only when these conceptual inputs are available:

| Required input | Adequacy test |
| --- | --- |
| Content Job | One primary job, at most one compatible secondary job, and an explicit objective |
| Target audience | Specific enough to judge relevance, language, tension, and desired response |
| Content objective | States the intended audience or strategic change rather than “make a Reel” |
| Approved insight or observation | Useful, specific, supportable, and strong enough to justify content |
| Jentz point of view | Authentic, distinctive enough for the job, defensible, and not manufactured by the writer |
| Supporting evidence where relevant | Fit for the material claims and distinguishable from inference or opinion |
| Attention thesis | States why this audience is expected to stop, continue, and receive the promised payoff |
| Guardrails | Truth, confidentiality, brand, audience, authority, and job-specific constraints |

Useful contextual inputs may also include:

- cohort and platform constraints;
- source material and provenance;
- Jentz voice references relevant to this context;
- portfolio context and recent repetition;
- required or prohibited calls to action;
- production assumptions that materially affect the script; and
- known uncertainty, sensitive information, or approval constraints.

Input validation is a professional gate, not a form-completeness exercise. The
Capability should state what is inadequate, why it matters, which upstream
decision owns it, and what evidence or revision would allow work to resume.

This section defines no request schema, storage model, or API.

## 8. Output Artifacts

A successful parent Run should conceptually aggregate an approval-ready
editorial package whose Artifacts retain their producing capability-step
provenance:

| Artifact | Conceptual producing capability step |
| --- | --- |
| Attention Thesis and Attention Map | Attention & Retention Engineering |
| Hook and packaging direction | Hook & Packaging Development |
| Story Architecture | Story Architecture |
| Base spoken Script | Script Development / Talking-Head realization |
| Claim Map | Claim Governance |
| Voice-refined Script | Voice Calibration |

The package records the versions used by the Run. Inclusion in the package
does not imply that every Artifact originated inside the parent Capability; an
approved upstream Artifact may be adopted and made attributable rather than
silently recreated. This provenance requirement is conceptual and does not
select a persistence schema.

The Independent Editorial Evaluator—not the primary creator—authors exactly
one readiness decision: Ready for Human Approval, Minor Revision, Major
Revision, Return Upstream, Blocked — Evidence, Reject, or Human Escalation. The
parent Run may aggregate that decision with the editorial Artifacts, but the
decision is not a generator-owned output and does not grant publication
authority. Jentz retains the final publication decision.

Instead of an approval-ready editorial package, a Run may stop with:

- requested upstream revision;
- unresolved evidence requirement;
- human escalation;
- or rejection with an attributable reason.

## 9. Attention Thesis

An Attention Thesis is an explicit, pre-script hypothesis that states:

- who the intended audience is;
- the audience state expected on entry;
- why the topic matters to that audience now;
- what is expected to contribute to stopping attention;
- what is expected to contribute to continued attention;
- what payoff is promised;
- why the promise is truthful and strategically appropriate; and
- confidence, uncertainty, and relevant alternative explanations.

Possible mechanism vocabulary includes:

- self-relevance;
- information gap;
- curiosity;
- suspense;
- stakes;
- contradiction;
- prediction or prediction error;
- surprise;
- novelty;
- emotional movement;
- open loops;
- progressive revelation;
- rehooks;
- escalation;
- micro-payoffs;
- pattern changes;
- specificity;
- contrast;
- anticipation;
- resolution; and
- memory anchors.

These are contextual design tools, not guaranteed behavioural laws. The
specification and future system should say “expected to contribute,”
“hypothesized,” or “potential mechanism,” never “mechanism X causes retention.”

A dramatic mechanism cannot compensate for a weak insight, false claim, wrong
audience, or missing point of view. In those cases, return upstream.

## 10. Attention Map

The Attention Map is a pre-script planning Artifact for the complete attention
architecture, not only the opening line.

For each beat or segment it should be possible to state:

- audience state entering the beat;
- intended attention job and potential mechanism;
- information, meaning, emotion, or practical value delivered;
- unresolved tension or question;
- expected reason to continue;
- micro-payoff or main payoff;
- transition to the next beat; and
- uncertainty, risk, or plausible failure mode where useful.

A conceptual template is:

| Beat | Entering audience state | Attention job/mechanism | Value delivered | Unresolved tension | Reason to continue | Payoff | Transition | Uncertainty |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Context-specific | What the audience knows, feels, expects, or doubts | Capture, sustain, renew, reward, or pay off | Genuine progress in this beat | What remains honestly unresolved | Why the next beat matters | Micro or main payoff | Intended change of state | What may not work or may be misread |

Every segment should have an attention job. A hook earns only the next few
seconds; every subsequent beat must earn continued attention through
meaningful progress, value, tension, change, or reward.

The preferred rhythm is:

    CURIOSITY
    → VALUE / REWARD
    → NEW TENSION
    → VALUE / REWARD
    → DEEPER QUESTION
    → MAIN PAYOFF

Avoid:

    TEASE
    → TEASE
    → TEASE
    → TEASE
    → CTA

Potential rehooks include reversal, escalation, specificity, surprising
evidence, consequence, a new question, emotional shift, contradiction,
stronger stakes, and a production or visual change. No mechanism or number of
rehooks is mandatory. Production changes can be recommended editorially but
are executed by the relevant production owner.

Illustrative timings may help plan one Artifact, but no universal timestamp,
beat count, drop-off point, or retention formula belongs in this contract.

## 11. Story Architecture

The Attention Map and Story Architecture interact but answer different
questions:

| Artifact | Primary question |
| --- | --- |
| Attention Map | Why is the right audience expected to continue at each beat? |
| Story Architecture | How should the meaning, argument, evidence, and emotional movement unfold? |

Story Architecture may use setup, tension, example, consequence, reversal,
explanation, escalation, resolution, and memorable close. These are possible
story functions, not mandatory stages.

A strong story architecture:

- has one governing movement appropriate to the Content Job;
- establishes and develops the central tension or question;
- sequences evidence and examples so meaning changes rather than accumulates;
- removes competing ideas that dilute the payoff;
- makes the point of view and consequence intelligible;
- earns its resolution; and
- supports natural spoken delivery.

Attention devices must not distort story meaning, and story completeness must
not justify a dead or overly expository attention experience. When the two
plans conflict, the Role must revise the architecture or return upstream rather
than optimize one in isolation.

## 12. Claim Map

A Claim Map is required whenever the editorial package contains meaningful
claims. If no material external claim is present, the map should state that
conclusion rather than being silently omitted.

Each meaningful claim should be classified as:

- **Factual claim** — externally verifiable assertion about the world;
- **Jentz opinion** — Jentz's belief, judgment, interpretation, or preference;
- **Personal experience** — a claim about Jentz's own experience, confirmed by
  him where material;
- **Inference** — a conclusion drawn from evidence but not directly established
  by it; or
- **Illustrative/hypothetical example** — a constructed example clearly framed
  as such.

For a factual claim, record conceptually:

- the exact claim or attributable script passage;
- source or evidence;
- evidence quality and fitness;
- confidence and material uncertainty;
- verification status; and
- decision: retain, qualify, replace, remove, block for evidence, or escalate.

Possible working verification language includes Verified, Partially Verified,
Unverified, Contradicted, or Not Applicable. These are conceptual labels, not a
schema.

Example:

| Claim Map field | Example |
| --- | --- |
| Claim | “70% of transformations fail.” |
| Type | Factual claim |
| Evidence | None |
| Status | Unverified |
| Decision | Blocked — Evidence |

Contrast:

| Claim Map field | Example |
| --- | --- |
| Claim | “I think many companies are buying AI before redesigning the work.” |
| Type | Jentz opinion |
| Requirement | Frame clearly as opinion; verify any supporting external assertions separately |

Reclassifying a factual assertion as opinion is not a loophole. The surrounding
language, likely audience interpretation, materiality, and implied evidence
must be evaluated. Fabricated evidence is a hard fail.

The Claim Map is the conceptual provenance bridge for future fact-checking and
Run traceability. This document does not select its persistence format.

## 13. Outcome Contract

The V1 Outcome Contract separates three things:

1. **Capability completion outcome** — an approval-ready editorial package
   intended for the V1 Reel cohort, or a professionally correct alternative
   decision state;
2. **Quality objective** — excellence against the World-Class and
   Jentz-specific benchmark layers; and
3. **Real-world Outcome hypothesis** — the intended audience or business effect
   selected through the Content Job and observed only after approved
   publication.

Ready for Human Approval is not a real-world Outcome. Likewise, a published
Artifact's engagement does not retroactively define its intrinsic quality.

### 13.1 V1 Capability outcome

Develop an approval-ready editorial package intended for an organic
professional/thought-leadership Instagram talking-head Reel that:

- communicates a distinctive and credible Jentz point of view;
- is appropriate for the defined Content Job;
- gives the right audience an honest reason to stop;
- sustains attention through meaningful progression and reward;
- fulfils its promise;
- preserves trust; and
- strengthens Jentz's intended positioning.

The Capability produces editorial planning and spoken-script Artifacts. It
does not record or edit production footage, publish, or control distribution.
Ready for Human Approval means only that Jentz may consider the package for
publication.

### 13.2 Contract components

| Component | V1 contract |
| --- | --- |
| Quality objective | Meet the applicable anchored standards without a hard fail or hidden critical weakness |
| Primary Content Job | Exactly one per Run, instantiated with objective and desired audience response |
| Secondary Content Job | Optional and subordinate to the primary job |
| Audience | Explicit, relevant, and specific enough for editorial and Outcome interpretation |
| Creator Artifacts | Provenance-bearing Attention Thesis/Map, hook and packaging direction, Story Architecture, Script, Claim Map, and voice refinement, or a valid alternative stop state |
| Independent evaluation | One evaluator-authored readiness decision aggregated into the parent Run without becoming a generator-owned output |
| Integrity guardrails | Factual support, honest framing, promise fulfilment, confidentiality, no prohibited manipulation |
| Strategic guardrails | No wrong-audience optimization, positioning damage, empty reach, or portfolio harm |
| Human approval | Required before every external publication in V1 |
| Available Outcome signals | Selected by Content Job only after source and definition verification |
| Measurement limitations | Availability, denominator, cohort, window, production/distribution confounders, and attribution uncertainty remain visible |
| Learning rule | Observation may form a hypothesis; material Playbook change requires stronger governed evidence and rollback |

### 13.3 Metric selection principle

The Content Job should select a small, decision-relevant measurement set:

- one primary Outcome signal when a credible measurable proxy or direct signal
  exists;
- one or two diagnostic signals when they materially improve diagnosis; and
- one or two guardrails where optimizing the primary signal could cause harm.

No metric is universal. A proxy must state why it may reflect the intended
Outcome, how it can mislead, and what decision it supports. If the necessary
telemetry or baseline is unavailable, the Outcome remains unknown rather than
being replaced by an easy engagement total.

No numerical target or promotion threshold is defined in Phase 1E because
telemetry availability, historical baselines, representative cohorts, and
acceptable-risk decisions have not yet been verified.

The primary Outcome question should follow the Content Job:

| Primary Content Job | Run-specific Outcome question |
| --- | --- |
| Authority | Did the right audience receive credible evidence of distinctive expertise? |
| Reach | Did exposure expand among more of the intended audience without sacrificing relevance or trust? |
| Trust | Did the content strengthen justified confidence, candour, or relationship with the intended audience? |
| Conversation | Did it create substantive, relevant discussion or inbound dialogue? |
| Education | Did the audience gain useful understanding, judgment, or ability? |
| Positioning | Did it strengthen the intended association between Jentz and a valuable point of view or territory? |
| Conversion | Did it contribute to the explicitly defined qualified next step without claiming exclusive causal credit? |
| Experiment | Did this Run contribute a valid, guardrail-compliant case to the predeclared comparison? |

These questions still require verified measures, sources, baselines, and
windows. They are not claims that a platform can answer them directly.
For an Experiment job, hypothesis evaluation occurs across the governed set of
comparable Runs; no individual Run establishes the result.

## 14. Evaluation domains

Evaluation is hierarchical. It produces a profile of domain judgments,
evidence, uncertainty, hard-fail checks, and a decision state—not one giant
numeric score.

### A. Integrity

Diagnostic concerns include:

- factual accuracy;
- evidence discipline and source fitness;
- honest framing and appropriate qualification;
- clear separation of fact, opinion, experience, inference, and hypothetical;
- promise fulfilment;
- confidentiality and trust; and
- absence of deceptive or prohibited manipulation.

### B. Editorial Value

Diagnostic concerns include:

- relevance to the intended audience;
- insight quality;
- point-of-view strength;
- originality and non-derivative contribution;
- strategic usefulness; and
- value proportionate to the audience's attention.

### C. Attention Architecture

Diagnostic concerns include:

- initial capture for the correct audience;
- progression and changing audience state;
- sustained-attention logic across the whole piece;
- appropriate rehooks;
- useful micro-payoffs;
- absence of obvious dead sections; and
- a main payoff that fulfils the promise.

### D. Expression

Diagnostic concerns include:

- story quality and coherence;
- specificity;
- clarity;
- spoken naturalness and performability;
- Jentz voice fidelity;
- pacing and economy; and
- emotional movement where appropriate.

### E. Strategic Fit

Diagnostic concerns include:

- fulfilment of the primary Content Job;
- target-audience fit;
- intended positioning;
- portfolio contribution and avoidance of repetition;
- brand and trust alignment; and
- business relevance without unsupported conversion claims.

### 14.1 Capability-step diagnostic attribution

Future evaluation should identify the conceptual capability step most directly
associated with a weakness, including related or uncertain contributors when
responsibility is not exclusive. For example:

| Capability step | Anchored diagnostic judgment |
| --- | --- |
| Insight Development | Strong |
| Point-of-View Development | Strong |
| Attention & Retention Engineering | Weak |
| Story Architecture | Acceptable |
| Script Development | Strong |
| Voice Calibration | Strong |

This is qualitative diagnostic attribution, not numeric scoring, a persistence
design, or proof that one step exclusively caused an Outcome. It prevents the
parent Capability from becoming an undifferentiated “content quality” bucket
and supports future diagnosis, observability, maturity assessment, and
learning. The five primary evaluation domains and the overall readiness
decision remain intact.

Some criteria concern the single editorial package; portfolio contribution,
performance literacy, and learning reliability require broader evidence. An
evaluator must mark a criterion Not Assessable when required context is
missing rather than inventing a grade. Not Assessable is an evidence state,
not a quality anchor.

## 15. Evaluation anchors

Each primary domain should resolve to one of four anchored judgments:

- **Strong** — clearly meets the world-class intent for this cohort;
- **Acceptable** — professionally usable for human consideration, with no
  material weakness;
- **Weak** — meaningful deficiency requiring revision or upstream correction;
  or
- **Critical problem** — hard fail, fundamental mismatch, or risk that blocks
  Ready for Human Approval.

The evaluator must cite observable evidence and uncertainty. Decimal creative
scores such as “Originality = 7.43” imply unsupported precision and are
prohibited.

### 15.1 Integrity anchors

| Anchor | Observable behaviour |
| --- | --- |
| Strong | Meaningful claims are correctly classified and well supported; sources fit the claim; uncertainty is proportionate; framing is honest; the promise is fully delivered; trust and confidentiality are protected. |
| Acceptable | No material integrity problem; any source, qualification, or wording issue is non-material, localized, and resolvable without changing the argument. |
| Weak | Attribution, qualification, claim classification, or promise fulfilment is unreliable enough to require material revision, but no fabricated or irreparable violation is present. |
| Critical problem | Fabricated evidence, materially unsupported assertion, materially misleading framing, broken promise, prohibited manipulation, sensitive disclosure, or serious legal/reputational risk. |

### 15.2 Editorial Value anchors

| Anchor | Observable behaviour |
| --- | --- |
| Strong | The correct audience receives a specific, non-obvious, useful insight and a distinctive, defensible Jentz point of view with clear consequence. |
| Acceptable | Relevant and useful with a credible point of view, but less distinctive, deep, or consequential than exemplary work; no fundamental idea problem. |
| Weak | Generic, familiar, thin, derivative, weakly relevant, or unclear about why the idea matters; substantial redevelopment is needed. |
| Critical problem | No meaningful idea or point of view, materially wrong audience, strategically harmful premise, or upstream input so inadequate that content construction should not continue. |

### 15.3 Attention Architecture anchors

| Anchor | Observable behaviour |
| --- | --- |
| Strong | The opening gives the correct audience a credible reason to stop; progression repeatedly delivers value; curiosity or tension changes rather than stagnates; micro-payoffs reward attention; the main payoff fulfils the promise; no obvious dead section exists. |
| Acceptable | The attention logic is coherent and honest with a fulfilled payoff; a localized beat may be predictable, slow, or less rewarding but does not undermine the whole. |
| Weak | A compelling opening has little support afterward, exposition dominates, progression stalls, tension resolves too early, rehooks feel mechanical, or the payoff is predictable or underwhelming. |
| Critical problem | The hook materially misrepresents the content, value is intentionally withheld without reward, manipulation breaches guardrails, or the architecture cannot plausibly sustain the promised experience. |

### 15.4 Expression anchors

| Anchor | Observable behaviour |
| --- | --- |
| Strong | Clear, specific, economical, natural to speak, recognizably Jentz, well paced, and structurally expressive without generic AI language or unnecessary polish. |
| Acceptable | Performable and clear with credible voice; only localized stiffness, redundancy, pacing, or phrasing issues remain. |
| Weak | Written rather than spoken, generic, vague, repetitive, overlong, tonally wrong, poorly paced, or materially unlike Jentz; substantive revision is needed. |
| Critical problem | Meaning is incoherent or seriously distorted, voice representation is materially false, or expression creates an integrity, confidentiality, or reputational breach. |

### 15.5 Strategic Fit anchors

| Anchor | Observable behaviour |
| --- | --- |
| Strong | The primary Content Job, audience response, positioning, portfolio contribution, and business relevance are explicit and mutually reinforcing. |
| Acceptable | The work clearly serves the primary job and audience without positioning harm, though portfolio or secondary value may be modest. |
| Weak | The job is diffuse, competing objectives weaken the piece, audience fit is uncertain, positioning contribution is generic, or the work repeats the portfolio without purpose. |
| Critical problem | The primary job or audience is wrong, the premise conflicts with positioning or guardrails, or publication would create material strategic harm. |

Anchors are operational descriptions, not validated thresholds. Phase 1F must
test whether humans can apply them consistently and whether they discriminate
usefully across representative cases.

### 15.6 V1 minimum professional threshold

“Good enough” for the evaluator to assign Ready for Human Approval means:

- every required domain is Strong or Acceptable;
- no hard fail or guardrail breach is present;
- no required criterion is Not Assessable because of missing material context;
- all material factual claims are verified, responsibly qualified, removed, or
  otherwise resolved;
- the primary Content Job, audience, insight, point of view, attention thesis,
  and story premise remain valid;
- the output package is complete and internally coherent; and
- any residual weakness is genuinely non-material rather than hidden in an
  average.

This is a qualitative readiness rule, not a validated maturity threshold. The
independent evaluator authors the readiness decision; Jentz still decides
whether to approve, revise, defer, or reject publication.

## 16. Decision states

The independent evaluator should return exactly one evaluation decision state
with attributable reasons:

| Decision state | Meaning |
| --- | --- |
| Ready for Human Approval | The package may be presented to Jentz; it has no unresolved hard fail, evidence block, upstream defect, or material Capability-level weakness. It is not permission to publish. |
| Minor Revision | A localized change is required; the core insight, point of view, attention plan, structure, and Content Job remain valid. |
| Major Revision | Substantial Capability-level rewriting or reconstruction is required, but the upstream premise remains viable. |
| Return Upstream | The primary defect belongs to another Capability or planning decision, such as insight, point of view, audience, strategic purpose, or attention thesis. |
| Blocked — Evidence | A material claim cannot currently be substantiated or responsibly framed; resume only when evidence is supplied, the claim is qualified, or it is removed. |
| Reject | The work is strategically unsuitable, prohibited, duplicative without purpose, or irreparable within reasonable effort. |
| Human Escalation | Legitimate ambiguity, value conflict, sensitive judgment, or authority question requires Jentz or another authorized human. |

The evaluator should also report the five domain anchors, hard-fail findings,
uncertainty, and requested next action. A creator's self-score must not be shown
to the independent evaluator before its initial decision.

## 17. Hard fail, revision, and upstream taxonomy

These categories answer different questions and must not be merged.

### 17.1 True hard-fail candidates

- fabricated evidence, source, quotation, data, or experience;
- materially unsupported factual claim presented as established;
- materially misleading framing or omission;
- a hook that materially misrepresents the content;
- confidential or sensitive disclosure;
- prohibited or deceptive manipulation; and
- serious legal, safety, or reputational violation.

A hard fail always blocks Ready for Human Approval and cannot be averaged away.
It does not always imply the same terminal response:

- an unsupported but plausibly verifiable claim normally maps to Blocked —
  Evidence;
- a removable misleading hook may require Major Revision;
- fabrication, prohibited conduct, or serious disclosure may require Reject or
  Human Escalation.

### 17.2 Return Upstream examples

- weak or unsupported insight;
- missing useful point of view;
- wrong or materially vague audience;
- unclear strategic purpose;
- inadequate or conflicting Content Job; and
- an attention thesis without an honest basis.

### 17.3 Capability-level revision examples

- weak hook that remains faithful to a valid premise;
- generic language;
- weak progression;
- low specificity;
- poor or under-delivered payoff;
- voice mismatch;
- pacing problem;
- unnecessary length; and
- a Claim Map qualification that does not alter the upstream idea.

Revision is not the remedy for every hard fail or upstream defect. The
assigned state follows the ownership and severity of the primary problem.

## 18. World-Class and Jentz-specific standards

Two benchmark layers must remain distinct.

### 18.1 World-Class Editorial Standard

This layer judges professional quality independently of individual preference:

- integrity and evidence discipline;
- audience relevance;
- insight and point-of-view quality;
- attention and story architecture;
- originality and editorial taste;
- clarity, specificity, spoken naturalness, and payoff;
- strategic/commercial judgment; and
- causal and experimental discipline.

### 18.2 Jentz-specific standard

This layer judges:

- voice and tone;
- professional positioning;
- acceptable degree and form of provocation;
- preferred phrasing in context;
- fidelity to lived experience and actual belief;
- communication style; and
- context-specific authenticity.

Human labels and evaluator output should distinguish:

- professional editorial quality;
- Jentz voice/positioning fidelity; and
- Jentz's final preference or publication decision.

A Jentz edit does not automatically prove editorial improvement. An evaluator
should be allowed to say:

> “This sounds more like Jentz, but the edit weakens the opening, logic, or
> payoff.”

Conversely, a professionally strong phrase that Jentz would never say is not
ready. Jentz retains final authority, while his preference remains evidence
with context rather than infallible world-class ground truth.

## 19. Human baseline dataset

A future benchmark dataset should preserve enough context to evaluate
professional judgment rather than only final prose. Each example may include:

- Content Job;
- audience and objective;
- upstream inputs;
- source material and evidence;
- AI draft;
- Jentz revisions;
- final version;
- localized differences and reasons;
- Jentz retrospective quality judgment;
- separate professional-quality and Jentz-fidelity labels where available;
- Attention Thesis and Attention Map;
- Story Architecture;
- Claim Map;
- decision state and human approval;
- Outcome data if published; and
- production/distribution context and known confounders.

The dataset should deliberately include:

- strong and weak performers;
- high-quality work with weak Outcomes;
- weak-quality work with strong Outcomes;
- scripts Jentz likes and dislikes;
- heavily and lightly edited AI drafts;
- rejected and returned-upstream cases;
- evidence-blocked and hard-fail cases;
- different professional topics;
- different Content Jobs; and
- borderline cases that produce legitimate disagreement.

Performance must not automatically determine quality labels. A final version
must not automatically be labelled superior to every draft. Reviewers should
record the applicable benchmark layer, evidence, confidence, and reason.

The dataset is a future governed asset, not a collection of whatever content
is easiest to retrieve.

## 20. Dataset splits

Future evaluation should use three distinct sets:

| Dataset | Purpose | Access principle |
| --- | --- | --- |
| Development set | Examples available during Agent, prompt, Workflow, Playbook, and rubric improvement | Accessible to authorized improvement work; may be inspected and learned from |
| Calibration set | Human-labelled examples used to assess and recalibrate evaluator alignment | Restricted from routine generation tuning; used to measure evaluator agreement and failure modes |
| Holdout set | Cases hidden from prompt, Playbook, evaluator, and model-routing tuning until a governed evaluation | Access-controlled and rotated only through an explicit review process |

Splitting must occur by underlying idea, source, or content lineage—not by
randomly separating near-identical drafts of the same piece. Otherwise a draft
in development can contaminate a revised sibling in holdout.

Repeatedly inspecting holdout failures turns the holdout into development
data. Any exposed case should be reclassified, and a new representative
holdout should be protected. Dataset versions, cohort coverage, provenance,
label ownership, and leakage risks should eventually be attributable.

## 21. Pairwise and blind evaluation

Pairwise comparison is recommended where absolute creative judgment is
unstable or insufficiently discriminating.

For Version A versus Version B, ask:

- Which better fulfils the primary Content Job, and why?
- Which has stronger Editorial Value?
- Which has stronger Attention Architecture?
- Which has stronger integrity and promise fulfilment?
- Which sounds more authentically Jentz?
- Which is more suitable for human publication consideration?
- Does either contain a hard fail?

Where feasible, randomize order and hide whether a version came from Jentz, AI,
the current Playbook, a candidate Playbook, or another model. Remove irrelevant
metadata while retaining the Content Job, audience, evidence, and voice
references needed for valid judgment.

Pairwise preference does not replace absolute gates. Both versions may be weak,
both may violate integrity, and the preferred version may still be unready.
Evaluator reasons should be recorded before revealing source identity.

Blinding reduces source and authority bias; it does not remove evaluator bias,
rubric bias, or stylistic preference.

## 22. Independent evaluator

The initial conceptual topology is:

    EDITORIAL DIRECTOR
    → creates the editorial package

    DETERMINISTIC CHECKS
    → validate objective structure where possible

    INDEPENDENT EDITORIAL EVALUATOR
    → evaluates against the Outcome Contract, anchors, and hard gates

    CONDITIONAL EVIDENCE / FACT CHECKER
    → invoked only when material claims require it

    JENTZ
    → makes the final human judgment and publication decision

The creator's self-check may improve the package but must not be the sole
quality gate. The independent evaluator should use a logically separate
context and versioned instructions. Whether a separate model family materially
improves independence must be tested rather than assumed.

Deterministic checks should handle deterministic structure, for example:

- one primary Content Job is declared;
- required Artifacts and sections are present;
- no more than one secondary Content Job is declared;
- required Claim Map statuses and source references are populated;
- a Ready for Human Approval decision does not coexist with a known unresolved
  material evidence block;
- expected fields use permitted conceptual values; and
- trace references are internally consistent.

Deterministic checks must not pretend to judge insight, originality, voice, or
story quality.

### 22.1 Pre-publication evaluator blinding

Before making its independent quality judgment, the evaluator may see:

- Content Job;
- audience and objective;
- approved upstream inputs and guardrails;
- evidence and relevant sources;
- Attention Thesis and Attention Map;
- Story Architecture;
- Script;
- Claim Map;
- appropriate Jentz voice references; and
- the evaluation rubric and cohort.

It must not see:

- eventual performance of that exact published Artifact;
- the creator's self-score or self-recommended domain anchors;
- whether the draft came from a favoured model, Playbook, or person when
  provenance can be safely blinded; or
- another evaluator's judgment before completing its own.

After independent judgment, disagreements may be reconciled visibly. Blinding
must not hide safety provenance, authorized data classification, or information
required to assess a claim.

## 23. Revision budget

The V1 starting hypothesis is:

    INITIAL GENERATION
    → INDEPENDENT EVALUATION
    → UP TO TWO SUBSTANTIVE CAPABILITY-LEVEL REVISIONS
    → IF STILL BELOW THE REQUIRED STANDARD:
       RETURN UPSTREAM OR HUMAN ESCALATION

Two revisions is provisional, not a validated threshold. Phase 1F should record
revision type, reason, quality movement, cost, and latency to determine whether
the limit is useful.

A substantive revision changes the hook, attention progression, story
architecture, Script argument, or another material part of the editorial
package. Local factual corrections, formatting fixes, or one bounded Minor
Revision should not become a loophole for unlimited iterative rewriting; the
future prototype must define how attempts are counted.

Stop earlier when:

- a hard fail requires evidence, rejection, or escalation;
- the real defect is upstream;
- the Content Job or audience is invalid;
- successive revisions repeat the same weakness;
- uncertainty exceeds delegated authority; or
- cost or latency exceeds the approved budget.

**Do not brute-force a weak idea into an acceptable Script.**

## 24. Production and distribution causal boundary

The future Run trace must preserve four distinct layers:

| Layer | Examples |
| --- | --- |
| Editorial Artifact | Attention Thesis/Map, hook and packaging direction, Story Architecture, base and voice-refined Scripts, Claim Map |
| Production Artifact | Recorded performance, camera, lighting, sound, editing, visual treatment, captions, cover or thumbnail |
| Distribution | Platform delivery, timing, organic distribution, audience served, concurrent activity, external conditions |
| Outcome | Observed audience or business response after approved publication |

The independent readiness decision is an evaluation record attached to the
parent Run, not an Editorial Artifact authored by the generator. The Run
correlates that decision with the provenance-bearing editorial Artifacts while
keeping Editorial Artifact, Production Artifact, Distribution, and Outcome
separate.

Poor Outcome does not prove poor Editorial Artifact quality. Potential
confounders include:

- delivery quality;
- recording quality;
- edit pacing;
- opening visual;
- audio;
- captions;
- cover;
- posting conditions;
- audience served;
- distribution effects;
- platform changes;
- topic demand;
- competing events; and
- external events or random variation.

Accountability for Outcome requires the Editorial Director to investigate and
coordinate; it does not imply exclusive causal control. Production,
distribution, and Outcome observations must correlate to the originating Run
identity without being collapsed into the Script or editorial quality label.

## 25. Telemetry Availability Contract

Phase 1E makes no claim that Instagram exposes every desired metric or the
required granularity. Every platform-dependent candidate below is:

> **VERIFY DURING IMPLEMENTATION**

A future Telemetry Availability Contract should record for each metric:

- metric name and semantic definition;
- authoritative source;
- availability status;
- population and denominator;
- granularity and segment availability;
- collection method;
- reliability, completeness, and known platform caveats;
- measurement window and expected maturity;
- freshness or retrieval delay; and
- owner of verification.

Candidate metrics to verify:

- views;
- reach;
- opening retention where a defined measure is available;
- watch time;
- completion;
- retention data or curve;
- replays;
- shares;
- saves;
- comments;
- profile visits;
- follows;
- follower/non-follower distribution;
- relevant audience signals;
- relevant inbound conversations; and
- downstream business signals where a separate authoritative source exists.

Availability should resolve conceptually to Verified Available, Verified
Unavailable, or Unknown, with date and scope. Absence of a metric must not be
filled by model inference or an unrelated proxy. Platform definitions may
change and therefore require periodic re-verification.

## 26. Normalized Outcome analysis

Raw totals are insufficient because audience size, reach, duration, cohort,
distribution, and time vary.

Where verified source data and valid denominators support them, future
diagnostics may include:

- shares divided by reach;
- saves divided by reach;
- follows divided by reach;
- profile visits divided by reach;
- watch time divided by duration; and
- relevant interactions divided by reach.

The precise numerator, denominator, eligible population, unit, and zero/missing
handling must be defined before use. A ratio is not automatically better than a
total and can become unstable at small denominators.

Useful comparison candidates include:

- Jentz historical baseline;
- primary Content Job baseline;
- format baseline;
- duration cohort;
- topic cohort;
- audience cohort; and
- organic-distribution cohort.

Baselines should be versioned by definition and time period, and comparisons
should show sample size, distribution, and uncertainty where available.
Phase 1E defines no formula, weighting, target, or universal benchmark while
telemetry and history remain unverified.

## 27. Expected versus Actual Attention

The future learning structure is:

    EXPECTED ATTENTION MAP
    ↓
    ACTUAL AVAILABLE ATTENTION / OUTCOME SIGNALS
    ↓
    OBSERVED DROP / SPIKE / RESPONSE
    ↓
    POSSIBLE EXPLANATIONS
    ↓
    ALTERNATIVE EXPLANATIONS / CONFOUNDERS
    ↓
    HYPOTHESIS
    ↓
    EXPERIMENT
    ↓
    EVIDENCE

Never conclude:

> “Retention dropped here, therefore mechanism X failed.”

Attention Map mechanisms are hypotheses. Beat-to-time alignment may be
distorted by Jentz's delivery, edits, cuts, visual changes, platform reporting,
or unavailable retention granularity. An observed pattern should record
competing explanations and the evidence required to distinguish them.

## 28. Quality and Outcome

Quality and Outcome remain separate evidence streams.

| Observed combination | Interpretation discipline |
| --- | --- |
| High Quality + High Outcome | Promising association; replicate and test before attributing cause or changing the Playbook. |
| High Quality + Low Outcome | Investigate distribution, topic demand, production, timing, audience size/fit, platform effects, and external conditions. |
| Low Quality + High Outcome | Investigate sensationalism, controversy, novelty, trend timing, distribution anomaly, and wrong-audience attraction; do not reward weak work automatically. |
| Low Quality + Low Outcome | Diagnose the editorial package and its external context; revise, return upstream, or form a bounded hypothesis. |

Neither Outcome automatically rewrites the pre-publication quality label. A
later discovery of hidden factual error may correct the quality record through
an attributable review, but popularity itself is not such evidence.

Outcome analysis must distinguish:

    OBSERVATION
    → ASSOCIATION
    → HYPOTHESIS
    → EXPERIMENT
    → STRONGER CAUSAL EVIDENCE

## 29. Evaluator calibration

The evaluator must itself be evaluated and must never be described as ground
truth.

Future calibration should:

- compare automated domain anchors, decision states, reasons, and hard-fail
  detections with human-labelled calibration examples;
- distinguish World-Class editorial judgments from Jentz-specific judgments;
- inspect disagreement by domain, cohort, Content Job, severity, and reviewer;
- use pairwise and blind evaluation where it improves discrimination;
- retain protected holdout cases;
- test borderline, adversarial, hard-fail, Return Upstream, and evidence-block
  cases;
- measure false readiness and missed critical failures separately from minor
  disagreements;
- periodically recalibrate after model, rubric, cohort, platform, Playbook, or
  benchmark changes;
- monitor evaluator drift over time; and
- prevent creator and evaluator from jointly optimizing only to known examples
  or surface features of the rubric.

Human labels are the intended calibration authority but can still disagree,
drift, or encode preference. Calibration should preserve reviewer identity,
benchmark layer, reasons, confidence, and adjudication rather than manufacture
false consensus.

The independent evaluator should not see creator self-scores, same-Artifact
performance, or other evaluator results before its initial judgment.

## 30. Maturity reliability gate

Movement from AI Assisted to AI Executable must be based on reliability across
a representative holdout, not an average creative score or a few exemplary
outputs.

Future evaluation should track:

- Ready for Human Approval;
- Minor Revision;
- Major Revision;
- Return Upstream;
- Blocked — Evidence;
- Reject;
- Human Escalation; and
- critical or hard failures.

Interpretation must preserve correctness. For example, a justified Return
Upstream or Blocked — Evidence can demonstrate strong professional reliability;
an incorrect Ready decision on the same case is a severe failure.

Reliability review should consider:

- comparison with a human/world-class baseline;
- representative task and Content Job mix;
- cohort coverage and drift;
- failure frequency and severity;
- false-ready and missed-hard-fail cases;
- consistency across repeated or equivalent cases where appropriate;
- size and type of required human revision;
- correct upstream routing and evidence blocking;
- evaluator agreement and calibration uncertainty;
- required human oversight;
- cost and latency budget; and
- regression under prompt, model, Workflow, tool, or Playbook changes.

Phase 1E defines no numeric promotion threshold. Thresholds require empirical
baseline distributions, acceptable-risk decisions, and evidence that the
evaluation suite predicts human/world-class judgment on unseen work.

AI Executable may still require human review or approval. Under the V1 rule
that every publication requires human approval, the end-to-end publishing loop
cannot qualify as Automated. Automated would require stronger longitudinal
evidence and a separately approved change to authority boundaries; it is not a
goal of the first vertical slice.

## 31. Minimum Agent topology

The first implementation hypothesis is:

1. **Primary Editorial Director Agent** — creates and revises the editorial
   package while acting for the accountable Role.
2. **Independent Editorial Evaluator** — judges the package against the
   Outcome Contract, anchors, and hard gates without seeing creator self-scores.
3. **Conditional evidence/fact checker** — invoked only when material factual
   claims or source complexity warrant it.

Jentz remains the authorized human decision-maker. Deterministic code should
handle deterministic structure, validation, comparison, normalization, and
metric calculation.

Do not map one Agent to each upstream Capability, evaluation criterion, or
Attention Map beat. The minimum set should be tested against simpler and more
specialized alternatives using comparative Evals, cost, latency, and failure
analysis. Additional Agents require evidence of a distinct contribution.

## 32. Data governance

Before Phase 1F uses real examples, it must define handling for:

- content confidentiality;
- client-sensitive examples and source material;
- personal stories and information about Jentz or third parties;
- unpublished ideas, drafts, recordings, and rejected content;
- source provenance, licensing, quotation, and correction;
- retention periods and expiry;
- deletion, correction, export, and dispute;
- evaluator and fact-checker access;
- development, calibration, and holdout-set access;
- separation between client data and Jentz-specific data;
- use, retrieval, and retention of platform analytics;
- consent where third-party information appears;
- vendor/model data handling and training settings;
- least-privilege access and auditability; and
- whether an example may be reused for Agent, evaluator, or Playbook
  improvement.

Client information must not become Jentz-specific voice training data merely
because both are used in one Run. Unpublished material and human edits remain
sensitive even when no personal data is obvious.

This section defines governance questions and principles, not storage,
retention tables, access schemas, or vendor configuration.

## 33. Future implementation implications

Phase 1F should prototype one attributable, approval-gated loop using bounded
offline or sandbox cases before any external publication:

    VALIDATE INPUTS
    → CREATE EDITORIAL PACKAGE
    → DETERMINISTIC CHECKS
    → INDEPENDENT EVALUATION
    → FACT CHECK WHERE REQUIRED
    → REVISE / RETURN / BLOCK / ESCALATE
    → JENTZ HUMAN DECISION

The prototype should carry one end-to-end correlation identity across the
Content Job, upstream inputs, Artifact versions, Agent and evaluator
configurations, model/tool calls, sources, decisions, human edits, approval,
cost, and latency. It should not design generalized persistence before the
working slice exposes actual lifecycle, access, and query needs.

Within that identity, each editorial Artifact should remain attributable to
its conceptual capability step so a parent-Run failure can be diagnosed rather
than reduced to one undifferentiated content-quality result.

No Phase 1F prototype should publish, spend, promote a Playbook, or weaken
human authority without separate authorization.

### 33.1 Critical design review

| Material risk | Safeguard added | Owner |
| --- | --- | --- |
| Talking-Head Content Development absorbs upstream work | Required Input Contract, explicit ownership exclusions, and Return Upstream decisions; Run-specific construction artifacts do not authorize invention of insight or point of view. | Phase 1E |
| Parent orchestration obscures specialist-step responsibility | Conceptual child boundaries, Artifact provenance, and qualitative diagnostic attribution; no Agent-per-step or persistence requirement. | Phase 1E; trace representation validated in Phase 1F |
| Primary creator certifies its own readiness | Only the independent evaluator authors the readiness decision; the parent Run merely aggregates it, and Jentz retains publication authority. | Phase 1E |
| Content Jobs are too broad or overlap | Treat labels as prioritization vocabulary; require explicit objective, audience response, signals, guardrails, and one primary job. | Phase 1E; validate in Phase 1F |
| Evaluator shares creator bias | Logical separation, blinded self-score/provenance, human calibration, disagreement tracking, and comparative model/context tests. | Phase 1E design; Phase 1F validation |
| Evaluation gaming and rubric overfitting | Multi-domain evidence, hard gates, pairwise tests, held-out cases, lineage-level splits, and no giant score. | Phase 1E |
| Benchmark contamination | Separate development, calibration, and holdout sets; split by idea lineage; retire exposed holdouts. | Phase 1E governance; Phase 1F dataset practice |
| Jentz preference is mistaken for world-class quality | Maintain separate professional-quality, voice-fidelity, and final-preference labels; permit explicit disagreement. | Phase 1E |
| Psychology vocabulary becomes unsupported certainty | Treat mechanisms as contextual hypotheses and require alternative explanations; prohibit causal mechanism claims from one Outcome. | Phase 1E |
| Instagram telemetry is assumed rather than verified | Telemetry Availability Contract; mark every platform-dependent metric Verify During Implementation; unknown remains unknown. | Phase 1E; Phase 1F verification |
| Correlation is mistaken for causation | Preserve the evidence ladder, confounders, controlled Experiments, and scoped conclusions. | Phase 1E; later Experiment architecture |
| Script quality is confounded with production/distribution | Trace editorial, production, distribution, and Outcome layers separately under one correlation identity. | Phase 1E boundary; Phase 1F trace |
| Metric gaming rewards empty attention | One decision-relevant primary signal with diagnostic and guardrail signals; protect integrity, trust, positioning, and audience quality. | Phase 1E Outcome Contract |
| Short-term engagement overpowers positioning | Content Job-specific windows, portfolio/brand guardrails, and longer-term signals; never make views universal. | Phase 1E; later Outcome telemetry |
| Revision becomes an endless loop | Provisional two-substantive-revision budget, repeated-failure stop, cost/latency stop, upstream return, and human escalation. | Phase 1E principle; Phase 1F tuning |
| Agent proliferation increases cost and false consensus | Three-actor maximum hypothesis with conditional fact checking; require comparative Eval evidence before specialization. | Phase 1E; Phase 1F |
| Evaluation cost and latency outweigh quality gain | Risk-proportionate checks, deterministic work in code, invocation only where needed, and explicit Phase 1F budgets. | Phase 1F |
| Sensitive examples leak across contexts | Data classification, least privilege, client/Jentz separation, consent, access, retention, and deletion policy before real-data use. | Phase 1F prerequisite; later architecture |
| V1 benchmark drifts into other cohorts | Explicit V1 cohort identity; require new examples, anchors, telemetry verification, and regression for variants. | Phase 1E; later cohort governance |
| Maturity is gamed through averages | Reliability profile by decision state and severity, protected holdout, false-ready tracking, and no numeric threshold before calibration. | Phase 1E; Phase 1F evidence |

### 33.2 Deliberately unpersisted concepts

Phase 1E does not define storage for:

- Content Jobs or Outcome Contracts;
- Attention Theses, Attention Maps, Story Architectures, Scripts, or Claim
  Maps;
- evaluator results, human labels, revisions, or decision states;
- datasets and split membership;
- telemetry availability or Outcome observations;
- Agent/evaluator configurations; or
- Run correlation identities.

They remain conceptual artifacts and future persistence candidates until the
Phase 1F prototype demonstrates stable ownership, lifecycle, versioning,
authorization, retention, and query requirements.

## 34. Open Phase 1F decisions

Phase 1F must resolve or explicitly defer:

- which bounded offline cases constitute the initial representative
  development and calibration sample;
- who labels World-Class quality besides Jentz, if anyone, and how
  disagreement is adjudicated;
- the working representation of the Input Contract, provenance-bearing
  specialist Artifacts, evaluation profile, and separate evaluator-authored
  decision state without premature generalized schema;
- whether the provisional two-substantive-revision budget is useful and how
  localized versus substantive attempts are counted;
- which structural checks are deterministic and which require an evaluator;
- when the conditional fact checker is invoked and what source-quality rules
  it applies;
- the evaluator's instructions, context separation, model independence,
  confidence language, and human-calibration procedure;
- the initial development/calibration/holdout split and controls against idea
  lineage leakage;
- how Jentz records editorial quality, voice fidelity, edit reasons, and final
  decisions consistently enough for evaluation;
- whether and how Attention Map beats can be aligned to a final production
  timeline without claiming causal attribution;
- which Instagram metrics and granularities are actually available through
  authorized sources, under what terms, and with what reliability;
- the first Content Job-specific primary, diagnostic, and guardrail signal
  candidates after telemetry and historical baselines are verified;
- the definition of audience relevance and any authoritative downstream
  business signal;
- the end-to-end Run correlation approach and mapping to Langflow execution;
- data classification, consent, access, retention, correction, and deletion
  rules before real examples are used;
- the human approval handoff and proof that Ready for Human Approval cannot
  trigger publication;
- acceptable prototype cost, latency, revision, and failure budgets;
- how cohort identity and drift are detected; and
- what evidence would justify continuing, simplifying, or stopping before any
  generalized persistence or runtime expansion.
