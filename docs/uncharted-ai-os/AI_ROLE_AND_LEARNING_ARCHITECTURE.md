# Uncharted AI OS: AI Role and Learning Architecture

Status: Phase 1C canonical post-V0.1 conceptual architecture. This document
defines product boundaries, operating principles, safeguards, and a validation
sequence. It does not define database tables, API contracts, migrations, or
implemented runtime behaviour.

Read alongside:

- [DOMAIN_MODEL.md](./DOMAIN_MODEL.md) for the implemented Capability contract.
- [ARCHITECTURE.md](./ARCHITECTURE.md) for the Uncharted/Langflow boundary.
- [V0_1_IMPLEMENTATION_SPEC.md](./V0_1_IMPLEMENTATION_SPEC.md) for the
  implemented Phase 1A and Phase 1B scope.

## 1. Canonical product definition

Uncharted AI OS is a system that maps the real work an organisation performs,
benchmarks AI against world-class professional standards, executes that work,
evaluates the quality of the output, measures real-world outcomes, learns from
human feedback and performance data, and continuously improves the AI
organisation based on evidence.

Its intended operating loop is:

```text
MAP WORK
→ ASSIGN WORLD-CLASS ACCOUNTABILITY
→ EXECUTE
→ EVALUATE QUALITY
→ HUMAN APPROVAL WHERE REQUIRED
→ DELIVER
→ MEASURE REAL-WORLD OUTCOMES
→ LEARN
→ EXPERIMENT
→ UPDATE PLAYBOOK
→ REGRESSION EVAL
→ EXECUTE AGAIN
```

Two principles are non-negotiable:

1. AI is benchmarked against **world-class professionals**, not merely against
   whether a model can technically produce an output.
2. **Agents are accountable for outcomes, not outputs.** Producing an Artifact
   is an intermediate responsibility; the system must observe quality, delivery,
   and real-world performance and respond to evidence.

Agent accountability is operational, not legal or moral personhood. Human
owners retain organisational, ethical, and legal accountability. An Agent can
be held accountable for meeting an Outcome Contract, surfacing uncertainty,
requesting missing feedback, and proposing corrective action; it cannot
guarantee outcomes that depend on distribution, market conditions, or other
actors outside its control.

## 2. Scope and implementation status

Phase 1A and Phase 1B already provide the implemented foundation:

- owner-scoped Capability persistence and authenticated API;
- Capability hierarchy and lifecycle;
- current and target AI maturity;
- human oversight, economics, assessments, and execution-context descriptors;
- an optional, independently authorized primary Langflow Flow link;
- a protected, read-only Capability Map and detail drawer; and
- deterministic Capability-specific graph construction and layout.

V0.1 has no Role registry, execution action, Run or Artifact history, Outcome
telemetry, evaluation engine, feedback capture, Experiment engine, versioned
Playbooks, or learning autonomy. Those concepts in this document are planned.
They must not be read back into the existing Capability schema or Flow graph.

Phase 1C is documentation only. All potential persistence described below is a
**future persistence candidate** until the Editorial & Content Director
vertical slice demonstrates that the abstraction is useful and stable.

## 3. Formal concept boundaries

These concepts must remain separate even when a product view joins them.

| Concept | Definition | Must not be collapsed into |
| --- | --- | --- |
| **Role** | Professional accountability for a mission, decisions, standards, and outcomes. Example: `Editorial & Content Director`. | Capability, Agent persona, job title string, or permission role. |
| **Capability** | A repeatable unit of business work that produces a meaningful outcome. Example: `Talking-Head Content Development`. | Role, Flow, Run, or model feature. |
| **Agent** | A runtime AI configuration or reasoning actor that performs, coordinates, or evaluates work. | Role, Capability, or Workflow. |
| **Workflow** | The technical sequence of models, tools, deterministic code, and actions used to execute a Capability. Langflow may implement it as a Flow. | Capability or business accountability. |
| **Run** | One execution instance of a Capability. | Reusable Capability definition or Workflow definition. |
| **Artifact** | A concrete work product created during a Run, such as a script, proposal, report, or workshop design. | The expected-output descriptors currently stored on Capability. |
| **Outcome** | An observation of what happened after an Artifact was used in the real world. | Artifact quality, an evaluator score, or proof of causation. |
| **Playbook** | The governed, versioned operating knowledge or method used by a Role or Capability. | An Agent's mutable chat memory or a Flow definition. |
| **Eval** | A repeatable test for determining whether AI behaviour or an Artifact meets required standards. | Outcome telemetry or a one-off opinion. |
| **Experiment** | A controlled hypothesis test used to improve future performance. | Uncontrolled production variation or a single success story. |

The current Capability `inputs`, `outputs`, and `tools` fields remain ordered
business descriptors. They do not become Run inputs, Artifact records,
executable tool bindings, or Workflow ports.

### 3.1 Role, Capability, Agent, and Workflow

A Role answers **who is accountable and by what professional standard**. A
Capability answers **what repeatable work produces a meaningful outcome**. An
Agent answers **which AI actor is configured to reason or act**. A Workflow
answers **how models, tools, code, and actions are sequenced technically**.

One Role may own multiple Capabilities. In the initial architecture, every
Capability has exactly one accountable World-Class Role. Other Roles or Agents
may support execution, research, critique, or evaluation, but accountability
must remain unambiguous and cannot be shared across those participants.
Generalized many-to-many Role assignment persistence is deliberately deferred
until a real use case proves it necessary.

For the first vertical slice, the assignment is explicit:

```text
Talking-Head Content Development
→ accountable Role: Editorial & Content Director
```

The existing optional `primary_flow_id` remains the V0.1 bridge from a
Capability to one authorized Langflow Flow. It does not assign a Role, create a
Run, prove quality, grant execution permission, or imply that the Flow owns
business outcome data.

### 3.2 Run, Artifact, Quality, and Outcome

A Run is an event. An Artifact is a product of that event. Quality is an
assessment of the work against a professional benchmark. An Outcome is a later
real-world observation. Each has its own time, provenance, and uncertainty.

This separation permits correct diagnosis. A high-quality Artifact can have a
poor Outcome because of topic selection, distribution, timing, or market
conditions. A low-quality Artifact can achieve a strong Outcome because of
sensationalism, unusual distribution, or chance. Neither case should silently
rewrite the professional standard.

## 4. Target architecture

The conceptual target is:

1. **Capability Map** — the existing foundation describing real business work.
2. **World-Class Role Registry** — professional accountability and benchmark
   profiles.
3. **Outcome Contracts** — objectives, quality standards, metrics, guardrails,
   measurement windows, and approval rules per important Capability.
4. **AI Chief of Staff / Manager** — outcome intake, decomposition, routing,
   coordination, acceptance criteria, approval routing, and escalation.
5. **Specialist Agents** — runtime actors operating for defined Roles and
   Capabilities.
6. **Execution Engine** — Langflow Flows, tools, model providers, and
   deterministic code.
7. **Quality / Eval Engine** — repeatable checks, graders, rubrics, regression
   comparisons, and promotion evidence.
8. **Human Approval** — risk-appropriate review and authorization before
   delivery or consequential action.
9. **Artifact / Run History** — attributable execution instances and work
   products.
10. **Outcome Telemetry** — time-windowed observations from the real world.
11. **Feedback System** — human revisions, reasons, decisions, and missing
    feedback requests.
12. **Learning / Experiment Engine** — pattern analysis, hypotheses,
    controlled experiments, and evidence synthesis.
13. **Versioned Playbooks** — governed operating knowledge with evaluation,
    approval, promotion, and rollback.
14. **Memory** — separate stable, episodic, and performance layers with
    relevance-based retrieval.
15. **AI Performance Director** — cross-Role performance review and intervention
    proposals.
16. **Observability / Traceability** — provenance across configuration,
    execution, evaluation, approval, cost, and outcome.

```text
Human owner
    │
    ▼
AI Chief of Staff / Manager
    │ selects accountable Role and Capability
    ▼
Specialist Agent ── uses ──► versioned Playbook
    │
    ▼
Langflow Workflow + tools + models + deterministic code
    │
    ▼
Run ── produces ──► Artifact
    │                    │
    │                    ▼
    │              Quality / Eval gates
    │                    │
    │              Human approval when required
    │                    │
    ▼                    ▼
Trace              Delivery / use
                         │
                         ▼
                  Outcome observations
                         │
                         ▼
Feedback + Experiment + Playbook proposal + regression eval
```

Uncharted AI OS owns the business context and governance around this loop.
Langflow remains the execution engine. No future layer should encode Role,
Outcome Contract, quality, feedback, or Playbook state into `Flow.data`.

## 5. World-Class Role standard

A World-Class Role represents the kind of exceptional practitioner an
organisation with effectively unlimited hiring budget would seek for the
accountability. It is not an “AI assistant,” junior employee, generic expert
persona, or a prompt decorated with claims such as “award-winning expert.”

The benchmark should express observable professional behaviour:

- deep domain experience and pattern recognition;
- strong judgment under incomplete information;
- exceptional, explicit quality standards;
- commercial and organisational awareness;
- professional taste and the ability to distinguish adequate from excellent;
- willingness to challenge weak assumptions and reject mediocre work;
- ability to explain why work is inadequate and how it should improve;
- understanding of trade-offs and second-order consequences;
- peer-calibre methods and relevant external standards; and
- accountability for actual results within a stated sphere of control.

### 5.1 World-Class Benchmark Profile

Each important Role should eventually have a structured benchmark profile:

- **Name** — stable professional accountability label.
- **Mission** — the outcome the Role exists to improve.
- **Scope** — included and excluded responsibilities.
- **World-class benchmark** — observable standard, exemplars, and comparison
  basis; not unsupported superlatives.
- **Responsibilities** — recurring accountabilities.
- **Capabilities** — the business work for which the Role is accountable.
- **Judgment principles** — how the Role handles ambiguity and trade-offs.
- **Quality dimensions** — what excellent work means in this domain.
- **Escalation boundaries** — uncertainty, risk, or authority limits that
  require another Role or a human.
- **Decision rights** — what the Role may decide, recommend, reject, or never do.
- **Human approval expectations** — which work must remain reviewed or led by a
  human.
- **Evidence and calibration sources** — examples, standards, reviewers, and
  dates supporting the benchmark.

The profile should be testable through Evals and real work examples. Peer
recognition or prestige alone is not a quality rubric. Benchmark sources can
become stale, culturally narrow, or unsuitable for the organisation, so they
require provenance and periodic human review.

### 5.2 Accountability for outcomes

A Role may be accountable for several Capabilities. For example:

```text
Editorial & Content Director
├── Audience Insight
├── Topic Discovery
├── Point-of-View Development
├── Hook Development
├── Story Architecture
├── Talking-Head Content Development
├── Editorial Critique
├── Voice Calibration
└── Content Performance Learning
```

The Agent acting for that Role is expected to monitor relevant outcomes,
request missing feedback, identify likely causes, and propose interventions.
It is not considered successful merely because it emitted a syntactically
valid Artifact. Outcome accountability must still distinguish controllable
decisions from external factors and must never justify bypassing approval or
manipulating a metric.

## 6. Outcome Contracts

Every important Capability should eventually have an Outcome Contract. The
contract makes success, quality, evidence, and safety explicit before
execution. It should be Capability-specific and versioned when the concept is
proven; there is no universal metric set.

An Outcome Contract defines:

- **Objective** — the intended change or value.
- **Primary outcome** — the most important real-world result.
- **Quality rubric** — dimensions and anchored standards for the Artifact.
- **Leading or proxy metrics** — earlier signals that may predict the outcome.
- **Real-world business metrics** — later observations of realised value.
- **Guardrail metrics** — conditions that must not be sacrificed to improve the
  primary metric.
- **Measurement window** — when each signal becomes meaningful and when it
  should be considered incomplete.
- **Feedback sources** — people, systems, and evidence expected after delivery.
- **Human approval requirement** — whether review, approval, or human-led action
  is required.
- **Escalation conditions** — uncertainty, evaluator disagreement, missing
  evidence, risk, or threshold failures requiring intervention.
- **Cost and latency expectations** — where speed or spend materially constrains
  the acceptable approach.
- **Attribution limits** — external factors and causal uncertainty that prevent
  a metric from being treated as proof.
- **Learning evidence policy** — the types and strength of evidence required to
  propose or promote a material Playbook change for this Capability.

### 6.1 Example: Talking-Head Content Development

**Primary outcome:** grow the right audience while strengthening Jentz's
authority.

Possible quality dimensions:

- insight quality;
- hook strength;
- originality;
- voice match;
- narrative tension;
- specificity;
- credibility;
- retention potential;
- brand fit; and
- business relevance.

Possible outcome metrics:

- 3-second retention;
- average watch time;
- completion;
- shares and saves;
- profile visits;
- qualified followers; and
- relevant inbound conversations.

Possible guardrails:

- factual accuracy;
- no cheap clickbait;
- no generic AI voice; and
- no audience growth at the expense of positioning.

These examples are not a universal schema. Definitions, data sources,
measurement windows, denominators, segment filters, and missing-data handling
must be specified before metrics are used for decisions.

## 7. Quality gates: generation is not delivery

The normal conceptual path is:

```text
DRAFT
→ SPECIALIST SELF-CHECK
→ INDEPENDENT QUALITY EVALUATOR
→ EVIDENCE / FACT CHECK where relevant
→ BRAND / VOICE CHECK where relevant
→ PASS THRESHOLD?
→ REVISE OR ESCALATE
→ HUMAN APPROVAL where required
→ DELIVERY
```

Each gate should produce a structured result: rubric version, dimension scores
or determinations, evidence, uncertainty, evaluator identity/configuration,
threshold decision, and actionable reasons. A scalar score without reasoning
or dimension evidence is insufficient for important work.

Self-check is useful but not independent evidence. For material work, the
quality evaluator should be logically separate from generation, use an
explicit rubric, and be calibrated against human-reviewed examples. Depending
on risk, independence may require a different prompt, context, model family, or
human reviewer. The evaluator should not see outcome popularity metrics while
grading intrinsic quality unless the rubric explicitly requires them; this
reduces hindsight and popularity bias.

### 7.1 Evaluator calibration

Evals and model-based graders must themselves be evaluated. Important quality
Evals should be calibrated against human-labelled examples, suitable benchmark
datasets, or both. An Agent's self-evaluation may inform revision, but it must
not be the sole quality gate for important work.

Evaluator disagreement must be observable rather than averaged away. The trace
should distinguish disagreement between automated evaluators, between an
evaluator and a human, and between human reviewers. Periodic human calibration
must test whether automated evaluators still reflect the intended World-Class
Benchmark, including critical-failure and edge cases. Evaluator drift is a
performance risk that can invalidate apparent quality trends and should trigger
recalibration, replacement, or increased human review. Phase 1C defines this
requirement but does not select or implement evaluator infrastructure.

Revision loops require limits on attempts, time, cost, and repeated failure.
Crossing a limit escalates; it does not authorize silent delivery or endless
agent-to-agent review.

## 8. AI maturity and eval-first autonomy

The existing maturity names remain authoritative:

- **Manual** — a human performs the work.
- **AI Assisted** — world-class human judgment remains central while AI
  accelerates parts of the work.
- **AI Executable** — AI can perform the Capability at an acceptable
  professional standard, with the required human review or approval.
- **Automated** — AI performs the Capability consistently enough that human
  intervention is exceptional rather than routine.

`not_assessed` remains the explicit stored state when no assessment has been
completed. Maturity is descriptive, not a game, completion percentage, or
instruction to automate. Higher is not inherently better. Risk, taste,
relationships, ethics, or strategic judgment may make human-led operation the
correct target.

### 8.1 Promotion rule

A Capability cannot move from `ai_assisted` to `ai_executable` without an
appropriate evaluation suite. The suite may include:

- deterministic checks;
- schema and output validation;
- model-based graders;
- rubric scoring;
- factuality and evidence checks;
- human-reviewed datasets;
- regression comparisons; and
- outcome validation where the measurement is appropriate and sufficiently
  attributable.

A prompt, model, tool, Workflow, Agent configuration, or Playbook change should
be evaluated against the relevant suite before promotion. Promotion evidence
must identify the tested versions, dataset, thresholds, failures, evaluator,
cost, and date. A passing average must not hide critical guardrail failures or
unsafe subgroups.

Movement to `automated` requires stronger longitudinal evidence: stable quality
across representative cases, acceptable failure and escalation rates, reliable
tool operation, approved outcome performance, and proof that routine human
intervention is genuinely exceptional. Maturity may move down when regression,
drift, or changed risk warrants it.

## 9. Human feedback as supervision evidence

The future feedback path should preserve:

```text
AI draft
→ human revision or decision
→ final Artifact
→ structured difference
→ reason for change
```

Useful feedback context includes:

- Run, Capability, Role, Agent configuration, and Playbook version;
- original AI draft and final approved Artifact, or references to them;
- localized differences rather than only the final text;
- reviewer, time, approval decision, and confidence;
- reason classification plus optional explanation;
- whether the change corrects an error, reflects preference, adds missing
  context, responds to external constraints, or is merely stylistic; and
- privacy, consent, and retention classification.

Initial classifications for talking-head content may include:

- hook too generic;
- too corporate;
- too verbose;
- weak tension;
- poor specificity;
- incorrect claim;
- wrong context;
- weak ending;
- does not sound like Jentz; and
- missed commercial implication.

Human edits are evidence, not automatically correct universal rules. A change
may be idiosyncratic, contradictory, rushed, context-specific, or wrong. The
learning process should accumulate patterns, preserve dissent, and propose a
Playbook change for evaluation rather than copying every edit into stable
memory or instructions.

## 10. Quality and Outcome are separate evidence streams

**Quality** asks whether the work itself was excellent according to the
professional benchmark. **Outcome** asks what happened after the work was used
in the real world.

| Observed combination | Plausible interpretation | Required response |
| --- | --- | --- |
| High quality, strong outcome | The approach may be effective, but causation still needs evidence. | Replicate and test before generalising. |
| High quality, weak outcome | Distribution, timing, topic, offer, audience, or external conditions may be weak. | Diagnose outside the Artifact before lowering the quality standard. |
| Low quality, strong outcome | Sensationalism, novelty, distribution, or chance may be driving performance. | Protect guardrails; do not reward poor professional work automatically. |
| Low quality, weak outcome | Work and/or strategy likely needs intervention. | Diagnose dimensions, revise, and consider an experiment. |

Quality evaluators and outcome analysis may inform each other at the learning
stage, but raw popularity must not become the definition of professional
quality. Outcome records must preserve measurement windows and attribution
limits; evaluator records must preserve rubric and version.

### 10.1 Causal evidence ladder

Outcome learning must distinguish:

```text
OBSERVATION
→ ASSOCIATION
→ HYPOTHESIS
→ EXPERIMENT
→ STRONGER CAUSAL EVIDENCE
```

A successful or failed Outcome is not proof that a hook, Playbook instruction,
Workflow decision, model, or Agent caused it. Plausible confounders include
audience mix, distribution, timing, topic demand, offer quality, seasonality,
platform changes, prior brand exposure, concurrent campaigns, client context,
and chance. Outcome analysis should record known confounders, missing context,
alternative explanations, and the current strength of causal evidence.

Repeated association can justify a hypothesis; it does not by itself establish
causation. Controlled Experiments can strengthen causal evidence when their
design and execution are credible, but conclusions must remain scoped to the
tested population, conditions, and measurement window.

## 11. Continuous learning loop

Each World-Class Role should eventually operate this governed loop:

```text
EXECUTE
→ MEASURE
→ REQUEST MISSING FEEDBACK
→ ANALYSE
→ IDENTIFY PATTERNS
→ FORM HYPOTHESIS
→ DESIGN EXPERIMENT
→ RUN EXPERIMENT
→ PROPOSE PLAYBOOK CHANGE
→ REGRESSION EVAL
→ HUMAN APPROVAL WHERE MATERIAL
→ PROMOTE PLAYBOOK VERSION
→ EXECUTE AGAIN
```

Weekly review is a management cadence, not the only learning cadence. A system
may collect early signals continuously, request feedback when an expected
window closes, and defer conclusions until evidence is mature.

Example windows:

- **Instagram Reel:** early signal after hours, meaningful performance after
  roughly 24 hours, and longer-tail assessment after 7 days.
- **Proposal:** client response, revision or objection, and eventual won, lost,
  or delayed status.
- **Workshop:** immediate participant feedback, facilitator debrief, and
  30–60-day application or outcome where available.

These are starting examples, not universal constants. The Outcome Contract
defines the relevant windows. Missing feedback should remain visibly missing;
the system must not impute success or treat an immature window as failure.

Learning proposals should include supporting and disconfirming evidence,
uncertainty, affected scope, expected benefit, guardrail risk, evaluation plan,
and rollback plan. Repeated patterns can raise confidence, but correlation
alone does not establish causation.

## 12. Experimentation model

The preferred loop is:

```text
HYPOTHESIS
→ CONTROLLED EXPERIMENT
→ EVIDENCE
→ LEARNING
```

For example:

- **Hypothesis:** contrarian declarative hooks outperform instructional hooks
  for corporate-culture content.
- **Treatment:** five contrarian openings.
- **Control:** five comparable instructional openings.
- **Primary metric:** 3-second retention.
- **Secondary metrics:** completion and shares.
- **Guardrail:** quality and relevance of audience engagement.

A useful Experiment defines the eligible cases, treatment and control,
assignment method, primary metric, secondary metrics, guardrails, measurement
window, stopping rule, minimum useful evidence, confounders, and decision rule
before results are read. Small samples must be labelled uncertain. Sequential
tests, repeated peeking, and selective reporting can manufacture false wins.

One successful post, proposal, or workshop is a case, not a general rule.
Material Playbook changes require evidence proportional to their impact and
reversibility. When controlled experimentation is impossible, the system must
label observational evidence honestly and prefer reversible proposals.

## 13. Versioned Playbooks

Important Agents must not silently rewrite their own operating instructions.
A Playbook is governed knowledge; a Playbook Version is an immutable candidate
or effective snapshot.

Conceptually, a future Playbook needs an accountable Role or Capability and a
current effective version. A future Playbook Version may capture:

- version identity;
- content, instructions, and methods;
- change rationale;
- supporting and disconfirming evidence;
- Eval result and regression comparison;
- Outcome comparison where mature and meaningful;
- proposer and proposal time;
- approver and approval decision;
- effective time and affected scope; and
- rollback target, conditions, and result.

The change lifecycle is:

```text
EVIDENCE
→ PROPOSED CHANGE
→ EVAL
→ HUMAN APPROVAL where material
→ VERSION PROMOTION
→ MONITOR
→ RETAIN OR ROLLBACK
```

### 13.1 Capability evidence policy

Each Capability should eventually define an evidence policy for deciding when
learning is strong enough to propose or promote a Playbook change. There is no
universal numeric threshold: evidence requirements depend on risk,
reversibility, frequency, measurement delay, data quality, and the cost of a
wrong change.

The policy may consider repeated observations, contextual human feedback, Eval
results, controlled Experiments, consistency across representative cases,
uncertainty and confounders, and regression results. One strong or weak Outcome
must not materially change a Playbook on its own. Evidence sufficient to
propose a bounded Experiment may still be insufficient to promote an effective
version.

Material promotion remains governed, attributable, scoped, monitored, and
reversible. It must satisfy the Capability's evidence policy, regression and
guardrail requirements, and human-approval rule.

Promotion should be atomic and attributable. Old versions remain available for
reproduction and rollback. A change can be rejected, narrowed, time-limited,
or shadow-tested. Emergency rollback should not require reconstructing deleted
instructions from logs.

Materiality depends on risk: external claims, brand positioning, pricing,
legal or safety behaviour, approval boundaries, tool permissions, and
high-impact strategic methods should require explicit human approval. The exact
materiality policy remains to be designed in the vertical slice.

## 14. Memory architecture

Future retrieval should use three conceptually distinct memory layers:

### 14.1 Stable memory

Slow-changing principles such as company positioning, brand philosophy,
pricing philosophy, quality standards, user preferences, and professional
principles. Stable memory requires strong provenance, deliberate approval, and
infrequent change.

### 14.2 Episodic memory

Relevant prior cases such as a proposal lost for a specific reason, a client
objection, a successful facilitation decision, or a rejected content concept.
Episodes retain context and should not be generalized automatically.

### 14.3 Performance memory

Evidence of what happened across cases: hook performance, proposal conversion
patterns, activity feedback, negotiation results, quality distributions, and
failure rates. Performance memory must preserve definitions, windows, cohorts,
and uncertainty.

No Role should receive one giant undifferentiated memory blob. Retrieval should
be relevant to the Role, Capability, decision, current context, authority, and
time. Each memory item or source should eventually carry provenance,
classification, confidence, applicable scope, recency, retention policy, and
supersession or dispute status.

Untrusted inputs, retrieved documents, and inferred lessons must not be allowed
to overwrite stable memory. Sensitive or stale material needs expiry,
revocation, correction, and deletion mechanisms. Retrieval quality itself
requires evaluation because irrelevant memory can degrade judgment as surely
as missing memory.

## 15. Deterministic computation and AI judgment

Use deterministic computation for deterministic work.

| Prefer deterministic code | Prefer AI judgment |
| --- | --- |
| Metric collection and normalization | Interpretation |
| Aggregation and averages | Hypothesis generation |
| Comparisons, filtering, and sorting | Professional judgment |
| Schema and output validation | Synthesis |
| Basic statistical calculations | Creative development |
| Threshold and policy checks | Critique |
| Reproducible experiment assignment | Experiment design under ambiguity |

AI may explain deterministic results but should not be the authoritative
calculator when code can produce a safer, cheaper, faster, and reproducible
answer. Deterministic outputs still require correct definitions, input quality,
and tests.

## 16. AI Chief of Staff / Manager

The AI Chief of Staff is an orchestration Role, not another generic expert. Its
responsibilities may include:

- understand the requested outcome and relevant Outcome Contract;
- clarify missing information and authority;
- decompose work into Capabilities or bounded tasks;
- select the accountable specialist Role and suitable Agent configuration;
- sequence tasks and deterministic steps;
- define acceptance criteria and stop conditions;
- request evidence-backed revisions;
- route to required human approval;
- escalate uncertainty, disagreement, or risk; and
- coordinate multiple specialists only when specialization or parallel work is
  likely to improve the result.

Preferred structure:

```text
Jentz
└── AI Chief of Staff / Manager
    └── accountable Specialist Role / Agent
        └── supporting specialists only when justified
```

The Manager must not gain implicit authority to execute, deliver, spend, change
Playbooks, or bypass specialist/human decisions. Orchestration decisions and
acceptance criteria should be traceable.

### 16.1 Multi-agent decision rule

Multi-agent execution is appropriate when distinct expertise, independent
evidence, adversarial review, or meaningful parallelism improves an Outcome
Contract enough to justify extra cost, latency, coordination, and failure
surface.

Good research example:

- academic evidence specialist;
- competitor specialist;
- community and sentiment specialist;
- disconfirming-evidence specialist; and
- a manager that synthesizes their attributable findings.

Poor example: five undifferentiated Agents repeatedly reviewing the same
headline. Redundant chatter is not independence. Start with one accountable
specialist and deterministic tools; add a specialist only when its unique
contribution can be evaluated.

When specialists disagree, the Manager should preserve each recommendation,
evidence, confidence, and scope; apply a declared decision rule; and escalate
material unresolved conflicts. It must not average incompatible judgments into
false consensus.

## 17. AI Performance Director

The AI Performance Director is a top-level management Role for improving the
AI organisation itself. It is not an operational specialist and does not
silently edit specialist Playbooks.

It reviews across Roles:

- quality scores and dimension trends;
- real-world outcomes and attribution limits;
- human overrides and revision patterns;
- evaluator disagreement and calibration drift;
- failure, escalation, and tool-failure rates;
- model and Agent-configuration performance;
- cost and latency;
- Experiments and confidence in their results;
- Playbook proposals, promotions, and rollbacks; and
- evidence supporting maturity movement.

An example review might report:

```text
Editorial Director
- retention improving
- voice consistency declining
- controlled voice-calibration experiment recommended

Proposal Director
- win rate declining
- recent losses cite weak commercial framing
- value-framing experiment recommended

Research Director
- accuracy and turnaround improving
- no intervention recommended
```

The Performance Director proposes investigation, experiments, resourcing,
configuration changes, maturity reassessment, or rollback. Material actions
continue through the normal evidence, Eval, approval, and version-promotion
path. It should expose uncertainty and missing data rather than manufacture a
single organisation-wide performance score.

## 18. Observability and Run trace

Every future executable Capability Run must carry one end-to-end correlation
identity through execution, evaluation, approval, delivery, and subsequent
Outcome observations:

```text
Capability Run
→ Role
→ Outcome Contract
→ Playbook version
→ Agent configuration
→ Langflow execution
→ model/tool calls
→ sources
→ Artifact
→ Evals
→ human revisions
→ approval
→ delivery
→ Outcome
```

This may eventually be represented by a `run_id` or an equivalent correlation
identifier. Phase 1C does not select its storage or schema. The requirement is
that every participating system can carry or map the identity without relying
on timestamps, names, or content matching. Later Outcome observations may
arrive after the execution has ended but must retain the same correlation to
the originating Run.

Every important future Run should be attributable to:

- accountable Role and supporting Roles;
- Capability;
- Outcome Contract and Playbook version;
- Agent configuration version;
- model/provider configuration and model-routing decision;
- configured reasoning level where applicable, but not hidden chain-of-thought;
- tools and deterministic steps used;
- inputs, sources, retrievals, and relevant memory references;
- authorized Langflow Workflow/Flow and execution identity;
- output Artifact and its version or content reference;
- Eval suite, evaluator versions, dimension results, and threshold decision;
- human revisions, reasons, approval status, and approver;
- delivery decision and channel where authorized;
- latency, token/tool usage, and cost; and
- Outcome observations with source, time, window, and attribution limits.

The goal is causal investigation: when performance changes, the AI Performance
Director can determine what changed and why. Traceability should use the shared
correlation identity, explicit version IDs, and source references rather than
copying all content into one log.

Observability is not permission to retain everything. Sensitive inputs,
Artifacts, human feedback, model prompts, and client data need data
classification, access control, minimization, redaction, retention, export, and
deletion rules. Private model reasoning must not be treated as a required trace
artifact; decisions, evidence, configuration, and concise rationale are the
auditable boundary.

## 19. Model routing

Use the least expensive and fastest model proven by Evals to maintain the
required quality and safety for the Capability and gate.

Conceptually:

```text
high-value judgment / strategy
→ strongest appropriate reasoning model

complex synthesis
→ capable reasoning model

first drafts / transformations
→ cheaper model where Evals show quality is sufficient

classification / extraction
→ small, fast model where appropriate

deterministic computation
→ code
```

Routing must not hard-code one vendor or model name into the architecture.
Model and routing-policy versions should be evaluable and attributable. A
fallback is a configuration change for trace purposes, not an invisible detail.
Routing considers data policy, tool support, reliability, latency, cost,
context limits, and evaluator evidence—not price alone.

## 20. Security, authority, and delivery boundaries

The V0.1 owner boundary remains unchanged. Future collaboration, Role
assignment, traces, feedback, memory, or outcomes require a separately designed
authorization model; Flow permissions must not be reused as a shortcut for
business-data access.

### 20.1 Early human authority floor

For the first Role vertical slice and early Uncharted AI OS architecture, AI
must not independently perform any of the following without an explicitly
authorized human approval path:

- external delivery or publication;
- financial spending;
- contractual commitments;
- destructive actions;
- material permission or security changes; or
- material Playbook promotion.

The approval path must identify the authorized human, the action and scope
being approved, and the decision before the consequential step occurs. An Eval
pass, high maturity label, Manager recommendation, or prior approval for a
different Run is not a substitute. Future evidence may justify different,
explicitly approved autonomy levels for bounded actions, but bypassing routine
human approval is not part of the first vertical slice.

Future execution must preserve these rules:

- Capability access does not grant Flow execution permission.
- Flow execution permission does not grant Capability, Artifact, Outcome,
  Playbook, or memory access.
- A Manager or specialist receives least-privilege tools and data for the task.
- External sources and retrieved memory are data, not instructions with
  authority to change policy.
- Consequential delivery, publication, communication, purchasing, deletion,
  permission changes, and sensitive-data transmission require explicit
  authority and risk-appropriate approval.
- Human approval requirements in an Outcome Contract must be enforced at the
  orchestration or Workflow boundary; descriptive metadata alone is not a
  control.
- Revision, execution, spend, latency, and tool-call budgets stop runaway loops.
- Failure, uncertainty, missing evidence, or conflicting instructions should
  fail closed or escalate according to the Capability's risk.

## 21. Critical design review

The architecture is intentionally ambitious. The following risks must be
treated as design inputs, not afterthoughts.

| Risk | Why it matters | Safeguard | Where the safeguard belongs |
| --- | --- | --- | --- |
| Unnecessary Agent proliferation | More Agents add cost, latency, coordination failure, and false consensus without guaranteed quality. | Default to one accountable specialist plus deterministic tools; require a distinct expertise/evidence rationale and comparative Eval before adding Agents. | First Role vertical slice and future orchestration policy. |
| Overlapping concepts | Role, Agent, Workflow, Capability, and Playbook can become duplicate containers for prompts and ownership. | Preserve the formal definitions in Section 3; require every proposed field to have one authoritative owner. | Phase 1C architecture gate; review again before any future persistence. |
| Noisy-feedback overfitting | Human edits and small performance samples may encode mood, context, or chance. | Store context and reasons; aggregate patterns; seek disconfirming evidence; use experiments and confidence labels; never auto-promote a single edit. | First Role vertical slice. |
| Silent self-modification | Agents that rewrite instructions can drift, remove safeguards, or make failures irreproducible. | Immutable Playbook versions; evidence-backed proposals; regression Eval; material human approval; explicit promotion and rollback. | Future architecture, prototyped manually in the first vertical slice. |
| Evaluator/model bias | A generator grading itself may reward its own style; model graders can drift or share blind spots. | Separate generation and evaluation contexts; version rubrics/evaluators; calibrate against human examples; measure disagreement; use independent or human review for material cases. | Phase 1E Eval design and ongoing future governance. |
| Metric gaming and Goodhart's Law | Optimizing retention, conversion, or speed alone can damage trust, positioning, accuracy, or long-term value. | Pair primary metrics with quality rubrics and guardrails; monitor metric shifts and segments; prohibit promotion on a guardrail failure. | Outcome Contract in Phase 1E and future Performance Director reviews. |
| Quality/outcome conflation | Popularity can reward poor work; strong work can suffer from distribution or timing. | Keep quality and Outcome evidence separate; blind intrinsic graders to popularity; analyze the four combinations in Section 10. | Phase 1E and first execution/feedback slice. |
| Weak causal attribution | Outcomes often depend on factors outside the Artifact or Agent's control. | Record attribution limits and confounders; use controlled experiments where feasible; label observational evidence; avoid causal claims from correlation. | First Role vertical slice and future Experiment engine. |
| Stale or corrupted memory | Old, poisoned, irrelevant, or over-broad memory can systematically degrade decisions. | Layer memory; attach provenance, scope, recency, confidence, retention, dispute, and supersession; evaluate retrieval; isolate untrusted inputs. | Future memory architecture. |
| Privacy and security exposure | Runs, Artifacts, feedback, client data, and memory may be substantially more sensitive than Capability metadata. | Data classification, minimization, consent, encryption, least privilege, redaction, retention/deletion, and separate business-data authorization. Preserve V0.1 owner scope until this exists. | V0.1 boundary already; detailed policy before Phase 1G data capture and future sharing. |
| Runaway autonomy | Recursive revisions, tools, delivery, or learning can create spend and real-world harm. | Hard budgets, maximum attempts, stop conditions, least-privilege tools, approval gates, fail-closed escalation, and no autonomous Playbook promotion. | First prototype and all future runtime phases. |
| Cost and latency growth | Multiple models, graders, and loops can make ordinary work uneconomic or too slow. | Outcome Contract budgets; deterministic computation; eval-proven model routing; cache safe deterministic work; measure marginal quality gain per step. | Phase 1F prototype and future routing policy. |
| Contradictory specialist advice | Different experts may apply incompatible assumptions or optimize different outcomes. | Preserve attributable recommendations and evidence; declare decision rights; Manager applies a decision rule or escalates rather than averaging. | Future orchestration, tested if multi-agent work appears in the vertical slice. |
| Poor provenance | Without one correlation identity, versions, and sources, regressions cannot be diagnosed or reproduced. | Carry one end-to-end Run correlation identity across Role, Capability, Workflow, model/tool calls, Agent, Playbook, rubric, inputs, sources, Artifact, approvals, cost, delivery, and Outcome. | Minimal trace in Phase 1F; generalized observability later. |
| Weak approval boundaries | Descriptive oversight fields can be mistaken for enforced controls. | Define approval in the Outcome Contract and enforce it at orchestration/Workflow delivery boundaries; record approver and decision. | V0.1 already distinguishes metadata from HITL; enforcement begins only in an approved runtime phase. |
| Inability to roll back learning | A bad instruction or routing change may contaminate later work. | Immutable versions, prior-version retention, scoped promotion, canary/shadow evaluation, rollback triggers, and post-promotion monitoring. | Manual prototype in Phase 1H; future Playbook system. |
| Weak experimentation discipline | Repeated peeking and cherry-picking create confident but false learning. | Predeclare hypothesis, primary metric, sample/window, guardrails, stopping and decision rules; preserve negative results and uncertainty. | Phase 1H and future Experiment engine. |
| Performance drift | Models, tools, audience, business context, and evaluator behaviour change. | Scheduled regression Evals, reference sets, live quality/outcome monitoring, evaluator calibration, change detection, and maturity downgrade/rollback. | First vertical-slice baseline plus future Performance Director. |
| Vague “world-class” benchmark | Superlative prompts can encode taste without evidence and make evaluation circular. | Define observable behaviours, anchored rubrics, exemplars, decision rights, disqualifying failures, and human calibration. | Phase 1D. |
| Benchmark bias or staleness | A benchmark may be culturally narrow, copied from the wrong market, or obsolete. | Record sources, context, date, applicability, dissent, and review cadence; permit organisation-specific adaptation without lowering explicit standards silently. | Phase 1D and future Role Registry governance. |
| Vendor or model lock-in | Product behaviour becomes inseparable from a model name or provider-specific feature. | Version provider-neutral Agent requirements, use Eval-based routing, and preserve portable artifacts and rubrics. | Future architecture; validate with at least one fallback in Phase 1F where practical. |

No safeguard turns uncertain outcome data into certainty. The architecture
should prefer honest uncertainty, reversible change, and explicit escalation
over false automation confidence.

## 22. First advanced vertical slice

The recommended first World-Class Role is:

> **Editorial & Content Director**

The primary Capability is:

> **Talking-Head Content Development**

Its single accountable Role is **Editorial & Content Director**. Supporting
Roles or Agents may contribute, but they do not share accountability for this
Capability.

This is a strong validation slice because it is frequent, current AI output is
visibly inadequate, Jentz has strong quality judgment, human edits provide rich
supervision evidence, Instagram provides measurable performance signals,
learning cycles are relatively quick, and quality can be separated from
distribution and Outcome.

Potential subordinate Capabilities are:

- Audience Insight;
- Topic Discovery;
- Point-of-View Development;
- Hook Development;
- Story Architecture;
- Script Development;
- Editorial Critique;
- Voice Calibration; and
- Performance Analysis.

The slice should begin with one accountable Role and the minimum Agent set. It
should not create a specialist Agent for every subordinate Capability. Add
specialization only when a measurable failure mode and Eval justify it.

The slice should validate:

- whether the Role benchmark improves actual editorial judgment;
- whether the Outcome Contract is usable before work begins;
- whether the rubric predicts human approval without merely imitating one
  reviewer;
- whether draft-to-final differences produce useful, contextual evidence;
- whether quality and performance telemetry support different diagnoses;
- whether one controlled Experiment yields safer learning than anecdotal
  updates;
- whether Playbook proposals and rollback are understandable to a human; and
- whether the added evaluation cost and latency earn a material quality gain.

This document does not implement or seed the Role or Capability.

## 23. Candidate real Capability Map

Strong candidates for an initial real Uncharted Lab map remain:

- Research & Insight Synthesis;
- Proposal Development;
- Workshop / Programme Architecture;
- Talking-Head Content Development; and
- Meeting & Coaching Synthesis.

Possible later research decomposition:

```text
Research & Insight Synthesis
├── Academic / White Paper Research
├── Market Research
├── Competitor Intelligence
├── Community / Sentiment Research
├── Client Research
└── Insight Synthesis
```

These are product candidates, not seed data. Existing V0.1 Capability
hierarchy semantics—decomposition only—continue to apply.

## 24. Future persistence candidates

The following information will probably need durable representation if the
vertical slice proves it valuable, but Phase 1C deliberately does not select
tables, columns, cardinalities, or APIs:

- Role identity, benchmark profiles, accountability, and profile versions;
- Capability accountability and supporting-participation history, without
  committing to generalized many-to-many Role assignment persistence;
- Outcome Contracts and their versions;
- Agent configurations and model-routing policy versions;
- Run identity and trace references;
- Artifact metadata, versions, and controlled content references;
- Eval suites, cases, rubric versions, evaluator results, and promotion records;
- human reviews, revisions, change reasons, and approval decisions;
- Outcome observations, sources, windows, cohorts, and attribution limits;
- Experiment hypotheses, designs, assignments, evidence, and decisions;
- Playbooks, immutable versions, proposals, promotions, and rollbacks;
- stable, episodic, and performance memory with provenance and retention;
- performance reviews, intervention proposals, and their dispositions; and
- cost, latency, failure, and tool-use summaries needed for governance.

The first slice may use bounded fixtures, existing Langflow traces, explicit
files, or manually curated evaluation datasets where safe. Avoid introducing a
generic persistence abstraction merely because the concept appears in this
list. Persist only after ownership, lifecycle, access, versioning, retention,
and query needs are observed.

## 25. Conservative implementation sequence after Phase 1C

### Phase 1D — World-Class Editorial & Content Director design

Define the Role mission, scope, observable benchmark, responsibilities,
decision rights, judgment principles, quality dimensions, escalation
boundaries, approval expectations, benchmark sources, and representative
excellent/weak examples. Confirm it as the single accountable Role for the
primary Capability. Do not build a general Role registry yet.

The Phase 1D Role profile is specified in
[EDITORIAL_CONTENT_DIRECTOR.md](./roles/EDITORIAL_CONTENT_DIRECTOR.md).

### Phase 1E — Talking-Head Outcome Contract and Eval design

Define the primary outcome, quality rubric with anchored dimensions, metrics,
guardrails, measurement windows, feedback sources, approval policy,
representative evaluation cases, critical-failure rules, evaluator calibration,
cost/latency budgets, and a Capability-specific evidence policy and promotion
threshold. Establish a human baseline and privacy/retention plan before
collecting new data; do not create a universal numeric evidence threshold.

The Phase 1E Capability and evaluation specification is defined in
[TALKING_HEAD_CONTENT_DEVELOPMENT.md](./capabilities/TALKING_HEAD_CONTENT_DEVELOPMENT.md).

### Phase 1F — Instrumented, approval-gated prototype

Prototype one draft → evaluate → revise/escalate → human approval loop using
existing Langflow, model, tool, and deterministic-code capabilities. Start with
offline or sandbox cases. Carry one end-to-end Run correlation identity and
capture a minimal attributable trace. Do not automate external delivery,
promote Playbooks, or generalize persistence.

### Phase 1G — Human revision and Outcome evidence

For the approved slice, capture AI draft, human revision, final Artifact,
structured change reason, approval, and time-windowed Outcome feedback under
the data-governance rules. Keep quality and Outcome streams separate and expose
missing or immature feedback.

### Phase 1H — Governed learning and Experiment proposal

Run a human-facilitated management review, identify a repeated pattern, write a
falsifiable hypothesis, design and run one controlled Experiment where
practical, propose one scoped Playbook change, run regression Evals, require
material human approval, and prove rollback. The review cadence may be weekly;
the evidence windows remain Capability-specific.

### Phase 1I — Generalisation gate

Review whether the slice improved professional quality and useful outcomes at
acceptable cost, latency, risk, and human effort. Only then decide which Role,
Run, Artifact, Outcome, Eval, Experiment, Playbook, memory, and trace
abstractions deserve generalized persistence and APIs. A weak result should
lead to simplification or another bounded experiment, not platform expansion.

This sequence is more conservative than building generalized registries before
the slice: it puts benchmark and Eval design before runtime autonomy, data
governance before feedback capture, and a formal generalisation gate after one
complete learning cycle.

## 26. Deliberately unresolved decisions

Phase 1C does not resolve:

- whether future business-layer scope is personal, workspace, organisation, or
  another explicitly authorized boundary beyond V0.1 owner scope;
- how the exactly-one accountable Role rule and any supporting participation
  should eventually be represented and governed without a generalized
  many-to-many assignment design;
- who may create, approve, promote, or roll back Role profiles, Outcome
  Contracts, Agent configurations, and Playbooks;
- the materiality and risk policy that determines required approval;
- where Artifact content lives, which versions are retained, and how sensitive
  client work is encrypted, exported, or deleted;
- which external systems are authoritative for Outcome telemetry and how
  consent, identity matching, missing data, and corrections work;
- how causal attribution and evidence sufficiency differ by Capability;
- the exact rubric scales, promotion thresholds, human baseline, and evaluator
  disagreement policy for the first Role;
- how the mandatory end-to-end Run correlation identity maps to Langflow's
  execution identity and whether an Uncharted `run_id` is required;
- the portable representation of Agent configurations and model-routing
  policies;
- the Playbook content format and granularity between Role-wide and
  Capability-specific methods;
- memory retention, retrieval authorization, dispute, correction, and
  organisation-wide versus personal preference boundaries;
- statistical methods and minimum evidence appropriate for small-sample
  Experiments;
- cost and latency budgets by quality gate; and
- when, if ever, external delivery may proceed without routine human approval.

These require evidence from Phase 1D–1H and explicit product decisions. They
must not be answered implicitly by a premature database schema.

## 27. Invariants carried forward and added by Phase 1C

All future implementation must preserve these constraints:

1. Capability remains repeatable business work, not a Role, Agent, Workflow,
   Run, Artifact, Outcome, Playbook, Eval, or Experiment.
2. Every Capability has exactly one accountable World-Class Role in the
   initial post-V0.1 architecture; supporting participants do not share it.
3. The Capability business graph remains separate from Langflow's technical
   Flow graph.
4. Langflow remains the execution engine; Uncharted does not create a competing
   workflow runtime.
5. The optional Capability-to-Flow link remains independently authorized and
   grants no execution permission.
6. The V0.1 owner boundary remains in force until a separately designed
   business-layer authorization model replaces or extends it.
7. Maturity describes an operating model; it does not schedule execution or
   make “more automated” inherently better.
8. Human oversight metadata is not proof of an enforced approval control.
9. The first vertical slice requires authorized human approval before every
   consequential action named in Section 20.1.
10. An Agent's self-evaluation is not the sole quality gate for important work;
    evaluators require human calibration and observable disagreement.
11. Quality and Outcome remain distinct evidence streams, and Outcome learning
    distinguishes observation, association, hypothesis, Experiment, and
    stronger causal evidence.
12. No important Agent silently modifies its effective Playbook.
13. No material Playbook change follows from one Outcome; promotion follows a
    Capability-specific evidence policy and remains governed and reversible.
14. Every future executable Capability Run carries one end-to-end correlation
    identity through Langflow execution, evaluation, approval, delivery, and
    Outcome.
15. No future learning claim is promoted without provenance, evaluation, and a
    rollback path proportional to its materiality.
