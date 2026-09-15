# Uncharted AI OS Domain Model

Status: V0.1 product and domain contract. Phase 1A and Phase 1B implement the
Capability foundation described here. Planned post-V0.1 concepts are named
only to protect their boundaries; their detailed design lives in
[AI_ROLE_AND_LEARNING_ARCHITECTURE.md](./AI_ROLE_AND_LEARNING_ARCHITECTURE.md).

## Product definition

Uncharted AI OS is a system that maps the real work an organisation performs,
benchmarks AI against world-class professional standards, executes that work,
evaluates the quality of the output, measures real-world outcomes, learns from
human feedback and performance data, and continuously improves the AI
organisation based on evidence.

The implemented V0.1 surface is deliberately narrower: it maps repeatable
business work, records its assessment and oversight context, and can connect a
Capability to an optional authorized Langflow Flow. Execution, evaluation,
outcome measurement, Roles, Playbooks, learning, and experimentation remain
planned architecture rather than V0.1 functionality.

Langflow remains the workflow and execution engine underneath Uncharted AI OS.
The Uncharted Capability Map is a business graph. It is separate from
Langflow's technical flow graph.

## Core definition

A **Capability** is:

> A repeatable unit of business work that produces a meaningful outcome.

Use this term consistently. A Capability is not:

- A single execution, run, or job.
- An ambiguous AI skill or model feature.
- A professional Role or accountability assignment.
- An Agent configuration or reasoning actor.
- A Langflow Flow.
- An Artifact, Outcome, Playbook, Eval, or Experiment.
- A department, team, project, or folder.

A Capability may be supported or implemented by a Langflow Flow, but the two
remain different domain objects with different lifecycles and responsibilities.

## Adjacent concepts beyond V0.1

The following terms protect future boundaries. They do not add fields, tables,
APIs, or runtime behaviour to V0.1.

| Concept | Meaning | Relationship to Capability |
| --- | --- | --- |
| **Role** | Professional accountability, such as `Editorial & Content Director`. | A Role may be accountable for multiple Capabilities. |
| **Capability** | Repeatable business work that produces a meaningful outcome. | The existing V0.1 business object and map node. |
| **Agent** | A runtime AI configuration or reasoning actor that performs, coordinates, or evaluates work. | An Agent may act for a Role on a Capability but is not the Role or Capability. |
| **Workflow** | The technical sequence of models, tools, code, and actions used to execute work. | A Langflow Flow may implement or support a Capability through the existing optional link. |
| **Run** | One execution instance of a Capability. | A Run records what happened once; it is not a reusable Capability definition. |
| **Artifact** | A work product created during a Run, such as a script, proposal, report, or workshop design. | A Capability describes expected outputs; an Artifact is an actual instance. |
| **Outcome** | What happened after an Artifact was used in the real world. | Outcome evidence is temporally and causally distinct from the Artifact and its quality. |
| **Playbook** | Versioned operating knowledge or method used by a Role or Capability. | A Playbook may guide execution without becoming the Capability or Workflow. |
| **Eval** | A repeatable test of whether AI behaviour or an Artifact meets defined standards. | An evaluation suite supplies promotion and regression evidence for a Capability. |
| **Experiment** | A controlled hypothesis test intended to improve future performance. | Experiment evidence may support a proposed Playbook or configuration change. |

In the initial post-V0.1 architecture, every Capability has exactly one
accountable World-Class Role. Other Roles or Agents may support execution,
research, critique, or evaluation, but they do not share that accountability.
For the first vertical slice, `Talking-Head Content Development` is accountable
to the `Editorial & Content Director`. Generalized many-to-many Role assignment
persistence is deferred until real use proves it necessary.

## Capability fields

### Identity and classification

| Field | Meaning |
| --- | --- |
| `id` | Stable identifier for the Capability. |
| `name` | Concise name for the repeatable unit of work. |
| `description` | Explanation of the work and the meaningful outcome it produces. |
| `functional_area` | Open organisational classification used to group the Capability. |
| `parent_capability_id` | Optional self-reference used only for decomposition into sub-capabilities. |
| `status` | Lifecycle state: `active` or `archived`. |

In V0.1, `id` is a server-generated UUID. `name` and `functional_area` are
required. `status` is required and defaults to `active`. `description` and
`parent_capability_id` are nullable.

Text validation is deliberately bounded:

| Field | V0.1 validation |
| --- | --- |
| `name` | Trimmed; 1-120 characters. |
| `functional_area` | Trimmed; 1-120 characters. |
| `description` | Nullable; when present, maximum 2,000 characters. |

Trim all supplied text fields. Normalize a nullable text value that is blank
after trimming to null.

`functional_area` must not be implemented as a fixed department enum. Different
organisations use different operating models and vocabulary. Initial Uncharted
Lab examples include:

- Clients
- Programmes
- Marketing & Content
- Research
- Operations

Allowed `status` values are:

| Value | Meaning |
| --- | --- |
| `active` | The Capability is part of the current map. |
| `archived` | The Capability is retained for history but is not part of the active operating model. |

### Ownership

| Field | Meaning |
| --- | --- |
| `user_id` | The Langflow user associated with ownership of the Capability. |
| `workspace_id` | The existing Langflow workspace scope associated with the Capability, when one is available. |

V0.1 is owner-only. `user_id` is authoritative and is always assigned by the
server from the authenticated Langflow user. Every Capability lookup and
mutation must be scoped directly to that user, and a request for another
user's Capability behaves as not found.

`workspace_id` is nullable and is not required in V0.1. The API must not accept
an arbitrary workspace ID from an untrusted request. Until Langflow provides a
trusted workspace context for this feature, new V0.1 records store it as null.
Do not build Workspace infrastructure or introduce `organisation_id`,
`tenant_id`, or another parallel tenancy concept.

### AI transformation

| Field | Meaning |
| --- | --- |
| `current_maturity` | Description of how the work currently operates. |
| `target_maturity` | Optional agreed target operating model. May be null. |
| `human_oversight` | Required or recommended human role in normal operation. |
| `oversight_notes` | Qualitative explanation of why that oversight level is appropriate. |

Allowed maturity values are:

| Value | Definition |
| --- | --- |
| `not_assessed` | No formal AI assessment has been completed. |
| `manual` | The work is primarily human-executed. |
| `ai_assisted` | AI contributes materially, but a human still orchestrates the process. |
| `ai_executable` | AI can perform the main work end-to-end, with human review or approval remaining part of normal operation. |
| `automated` | Execution can be initiated and completed with minimal routine human intervention. |

Maturity is descriptive, not a ranking of quality. `automated` is not inherently
better than `ai_assisted`, and a target should reflect the appropriate operating
model rather than the highest available label.

Future maturity decisions must use the relevant World-Class Role benchmark,
not mere technical output generation. In particular, movement from
`ai_assisted` to `ai_executable` requires an appropriate evaluation suite and
evidence that the Capability can meet its acceptable professional standard
with the stated human review or approval. `automated` means routine human
intervention has become exceptional; it does not mean oversight, escalation,
or accountability disappears. Some Capabilities should remain human-led.

`target_maturity` may be null when no target has been agreed. Use
`not_assessed`, rather than a null `current_maturity`, to represent the explicit
current state that no formal assessment has been completed.

In V0.1, `current_maturity` is required and defaults to `not_assessed`.
`target_maturity`, `human_oversight`, and `oversight_notes` are nullable.
`oversight_notes`, when present, has a maximum length of 2,000 characters.

### Human oversight

Allowed `human_oversight` values are:

| Value | Definition |
| --- | --- |
| `none` | No routine human intervention required. |
| `review_recommended` | AI output can normally be used, but human review is recommended. |
| `approval_required` | AI may perform the work, but a human must approve before external use or consequential action. |
| `human_led` | AI may assist, but the critical judgement or action remains human-controlled. |

`oversight_notes` records why the selected level is required. The field is part
of the business assessment; it must not be treated as proof that a linked
Langflow Flow contains a technical human-in-the-loop control.

### Work economics

| Field | Meaning |
| --- | --- |
| `frequency_value` | Number of occurrences in the selected frequency period. |
| `frequency_period` | Period represented by the frequency value. |
| `baseline_human_effort_minutes_per_run` | Total human labour required for one occurrence under the baseline operating model. |

Allowed `frequency_period` values are:

- `day`
- `week`
- `month`
- `quarter`
- `year`
- `ad_hoc`
- `unknown`

For example, work performed three times per week is stored as:

```text
frequency_value = 3
frequency_period = week
```

Do not force users to estimate annual frequency. Any annualised estimate must
be a derived value with its assumptions made clear, not a replacement for the
recorded cadence.

`frequency_period` may be null when cadence has not been assessed. For `day`,
`week`, `month`, `quarter`, and `year`, `frequency_value` may be any positive
finite decimal greater than zero, including fractional values such as `0.5`
times per month. For `ad_hoc` and `unknown`, `frequency_value` must be null.
The value is also null when the period is null.

`baseline_human_effort_minutes_per_run` means total human labour, not elapsed
wall-clock duration. If three people each spend one hour on one occurrence, the
value is `180` human minutes.

The effort field is a nullable integer greater than or equal to zero. V0.1 does
not calculate time savings.

### Assessment

| Field | Meaning |
| --- | --- |
| `business_value` | Directional 1-5 assessment of business importance. |
| `ai_feasibility` | Directional 1-5 assessment of how feasible AI execution or material assistance is. |
| `ai_execution_risk` | Directional 1-5 assessment of the consequences of errors during AI execution. |
| `assessment_notes` | Qualitative reasoning and context behind the ratings. |
| `assessed_at` | When the assessment was completed or last materially updated. |
| `assessed_by` | The existing Langflow user identity responsible for the assessment. |

When present, each rating must be an integer from 1 through 5. These are
directional assessment scales for prioritisation and discussion. They must not
be presented as scientifically precise measurements.

#### Business value

| Score | Label | Definition |
| --- | --- | --- |
| 1 | Low | Minor convenience with little material business impact. |
| 2 | Limited | Useful but not materially important. |
| 3 | Moderate | Noticeable impact on quality, efficiency, or customer experience. |
| 4 | High | Directly affects important business outcomes. |
| 5 | Critical | Strongly linked to revenue, customers, strategic outcomes, or major risk. |

#### AI feasibility

| Score | Label | Definition |
| --- | --- | --- |
| 1 | Very Low | Requires substantial contextual human judgement or inaccessible data. |
| 2 | Low | AI can only assist marginally. |
| 3 | Moderate | Significant portions can be AI-assisted. |
| 4 | High | AI can reliably perform most of the work. |
| 5 | Very High | The work is structured, repeatable, and technically straightforward for AI execution. |

#### AI execution risk

| Score | Label | Definition |
| --- | --- | --- |
| 1 | Very Low | Errors are easily reversible. |
| 2 | Low | Limited negative consequences. |
| 3 | Moderate | Human review is advisable. |
| 4 | High | Errors could cause material financial, reputational, or customer impact. |
| 5 | Critical | Errors could create legal, safety, regulatory, or major strategic consequences. |

`assessment_notes` should preserve the qualitative reasoning that numeric
ratings cannot express, including assumptions, evidence, uncertainty, and known
constraints.

All three ratings, `assessment_notes`, `assessed_at`, and `assessed_by` are
nullable. `assessment_notes`, when present, has a maximum length of 5,000
characters. Creation is not itself an assessment: a newly created unassessed
Capability must retain null assessment fields rather than artificial scores or
timestamps.

### Execution context

| Field | Meaning |
| --- | --- |
| `inputs` | Information or materials normally required to perform the Capability. |
| `outputs` | Meaningful outcomes or artefacts produced by the Capability. |
| `tools` | Systems or tools normally involved in performing the Capability. |

In V0.1 these remain simple ordered arrays/lists of business descriptors. They
do not represent Langflow node ports, component inputs and outputs, or
executable Langflow Tool objects. Do not create separate input, output, or tool
tables yet.

Each array defaults to `[]`. Normalize each entry by trimming surrounding
whitespace, reject an entry that becomes empty, and reject entries longer than
200 characters. Each request may provide at most 50 entries per array. Remove
exact, case-sensitive duplicates after trimming while preserving the first
occurrence and display order.

### Hierarchy

`parent_capability_id` has exactly one meaning in V0.1:

> The child is a decomposition or sub-capability of the parent.

It does not mean dependency, execution order, information flow, or a general
relationship. Do not introduce these relationship types in V0.1:

- `depends_on`
- `triggers`
- `uses`
- `feeds_into`
- `related_to`

The parent must exist and belong to the same owner. A Capability cannot parent
itself, cycles are forbidden, and V0.1 sets no maximum depth. When workspace
scope is introduced later, parent and child must also have compatible scope.
An active child cannot have an archived parent.

Normal V0.1 product behaviour uses archival, not destructive deletion.
Archiving never cascades. A Capability with active children cannot be archived;
the user must first archive or re-parent those children. Permanent hard
deletion is not part of the main V0.1 experience.

### Langflow link

| Field | Meaning |
| --- | --- |
| `primary_flow_id` | The optional primary Langflow Flow currently implementing or supporting this Capability. |

`primary_flow_id` links to the stable identifier of an existing Langflow Flow.
It does not make the Capability a Flow, and it does not move business assessment
metadata into the Flow.

Do not assume that the relationship will always be one-to-one. A future
`CapabilityFlowLink` model may support multiple flows per Capability, but that
model is explicitly outside V0.1 and must not be implemented yet.

The link is made by Flow ID, never inferred from a name. Creating or changing a
link requires an independent check that the authenticated user may read that
Flow. Linking does not grant execution permission; any later execution must
still pass Langflow's existing Flow execution authorization.

Deleting a linked Flow must leave the Capability intact and set
`primary_flow_id` to null. If the Flow still exists but later becomes
inaccessible, the Capability survives, no restricted Flow metadata is exposed,
and the UI represents the reference as unavailable or inaccessible.

### System fields

| Field | Meaning |
| --- | --- |
| `created_at` | When the Capability record was created. |
| `updated_at` | When the Capability record was last updated. |

Both values are server-generated. `updated_at` changes whenever the Capability
record is updated.

## Domain invariants

Implementation must preserve these invariants:

1. Capability business data is independent of Langflow Flow graph data.
2. `functional_area` is open organisational vocabulary, not a fixed enum.
3. `parent_capability_id` expresses decomposition only.
4. `target_maturity` may be null; `current_maturity` uses `not_assessed` for an unassessed state.
5. Maturity is descriptive and does not trigger workflow execution or scheduling.
6. Human oversight assessment is not automatically equivalent to technical HITL enforcement.
7. Assessment scores remain separate; V0.1 has no composite AI Opportunity Score.
8. `primary_flow_id` is optional and does not imply a permanent one-to-one relationship.
9. Archived capabilities remain part of the historical record.
10. Owner-only V0.1 access is enforced with `user_id`; `workspace_id` is nullable compatibility metadata, not an alternate access path.
11. Unassessed fields remain null; the system does not invent assessment values.
12. Presentation roots and functional-area grouping nodes are not Capability records.

## Initial examples for development and demonstration

These examples document the intended first data set. V0.1 must not seed them
automatically at application startup or attach them to production users. The
implementation specification defines an explicit, non-production fixture
strategy.

| Capability | Functional area |
| --- | --- |
| Proposal Builder | Clients |
| Workshop Architect | Programmes |
| Talking-Head Script Writer | Marketing & Content |
| Market Research | Research |
| Meeting Synthesiser | Operations |

## Explicit V0.1 exclusions

V0.1 does not introduce:

- A `CapabilityMap` model.
- A `CapabilityFlowLink` model.
- Separate models for inputs, outputs, or tools.
- General-purpose capability relationship types.
- A composite AI Opportunity Score.
- Automatic scheduling based on maturity.
- A replacement for Langflow Flow, execution, jobs, or permissions.
- Shared or team Capability maps and Capability-specific RBAC.
- Automatic workflow execution or scheduling.
- Saved map coordinates, viewport state, or drag-and-drop persistence.
