# Uncharted AI OS Architecture

Status: V0.1 architecture decisions. This document defines the intended
boundaries for future implementation. It does not claim that the Capability Map
runtime, persistence, APIs, or frontend routes already exist.

Read [DOMAIN_MODEL.md](./DOMAIN_MODEL.md) before changing these boundaries.

## Architectural intent

Uncharted AI OS adds a business capability-mapping product layer above
Langflow. Langflow remains the technical workflow builder and execution engine.

```text
Uncharted Capability Map
├── Capability business graph
├── AI transformation assessments
├── work economics and human oversight
└── optional primary_flow_id
       │
       ▼
Langflow Flow
├── technical nodes and edges
├── model and tool configuration
└── existing Langflow/LFX execution
```

The two graphs may be connected, but they are not merged:

- The **Capability graph** describes business work and decomposition.
- The **Flow graph** describes executable technical components and their
  connections.

## Responsibility boundary

| Uncharted AI OS owns | Langflow owns |
| --- | --- |
| Business capability mapping | Workflow execution |
| Current AI maturity | Agents |
| Target AI maturity | Model providers |
| Human oversight | Tool integrations |
| Business value | Flow APIs |
| AI feasibility | Execution history |
| AI execution risk | Permissions around Flow execution |
| Work effort and frequency | Technical flow graph persistence |
| Capability decomposition hierarchy | Flow builder and component semantics |
| Links from capabilities to Langflow flows | Runtime streaming, background execution, and HITL mechanics |

## Architecture decisions

### 1. Capability and Flow are separate domain models

A Capability represents repeatable business work. A Langflow Flow represents a
technical workflow definition. They have different fields, lifecycles, access
patterns, and meanings.

The optional `primary_flow_id` reference connects the models without collapsing
them into one.

### 2. Business assessment metadata does not belong in `Flow.data`

Langflow stores the technical workflow graph in `Flow.data` as nodes, edges,
and viewport data. Uncharted maturity, value, feasibility, risk, effort,
oversight, and hierarchy metadata must be persisted separately.

This avoids changing saved-flow semantics, keeps existing flows compatible, and
prevents business data from being overwritten by flow-editor operations.

### 3. Langflow Folder is not the Capability hierarchy

Langflow Folder, presented as Project in parts of the application, organises
technical flows and contributes to authorization scope. It must not be
repurposed as a functional area or Capability parent.

Capability decomposition uses `parent_capability_id`. Functional grouping uses
the open-text `functional_area` field.

### 4. Reuse user and workspace ownership concepts

V0.1 is owner-only. Capability ownership uses the server-assigned `user_id` as
the authoritative security boundary. Capability queries always include the
authenticated user's ID, including when a Langflow authorization plugin is
enabled. Missing and other-user records return the same not-found response.

Do not add `organisation_id`, `tenant_id`, or a separate tenancy hierarchy in
V0.1. `workspace_id` remains a nullable compatibility field and is not required
or accepted from an untrusted client request.

The current fork carries nullable `workspace_id` values and workspace
authorization domains but does not define a standalone local Workspace database
model. New V0.1 Capability records therefore leave `workspace_id` null unless a
future, separately approved implementation can derive it from trusted server
context. Phase 1 does not build new Workspace infrastructure.

### 5. Use an isolated `@xyflow/react` Capability Map

The Capability Map should use the repository's existing `@xyflow/react`
dependency, but it must have its own:

- Node data types.
- Node components.
- Capability-specific edge data and component.
- Selection and interaction state.
- Layout rules.
- Business validation.
- Persistence mapping.

An additional feature-local Zustand store is optional. Server-owned capability
records should use the frontend's established TanStack Query request and cache
pattern; transient view state should remain local until cross-component
coordination justifies a dedicated store.

Although the application currently provides a React Flow provider high in the
authenticated shell, the Capability Map must mount its own feature-local
`ReactFlowProvider`. It must not use `GenericNode`, `NoteNode`, `DefaultEdge`,
`AllNodeType`, `flowStore`, `flowsManagerStore`, workflow handles, or workflow
autosave logic.

### 6. Langflow remains the execution owner

Uncharted AI OS must not implement another workflow runtime. A linked
Capability ultimately opens or invokes the existing Langflow Flow through
Langflow's established APIs and authorization checks.

Langflow remains responsible for execution modes, streaming, background jobs,
execution history, Flow permissions, technical HITL suspension and resumption,
models, tools, and agents.

### 7. Uncharted AI OS owns business transformation context

Uncharted AI OS owns the Capability fields defined in
[DOMAIN_MODEL.md](./DOMAIN_MODEL.md), including current and target maturity,
human oversight, work economics, assessments, execution context, functional
grouping, and decomposition.

The Uncharted layer may describe whether oversight is required. That
description is not, by itself, an execution control. If a future product
requirement demands enforced approval, the linked Flow or an explicitly defined
orchestration boundary must implement it.

### 8. There is no `CapabilityMap` table in V0.1

The owner-scoped Capability collection represents the map. Nullable
`workspace_id` is retained on individual records for compatibility but does not
define a second V0.1 access scope. A map container would add identity,
lifecycle, and permission questions that the first version does not need.

Introduce a `CapabilityMap` model only when a concrete requirement exists for
multiple maps, map-specific permissions, separate versions, or distinct saved
views.

### 9. There is no AI Opportunity Score in V0.1

Persist business value, AI feasibility, AI execution risk, work economics,
maturity, and oversight as their underlying fields. Do not combine them into an
opaque score.

Derived prioritisation may be explored later only with documented assumptions
and without presenting directional assessments as scientific measurements.

### 10. Maturity does not schedule execution

`current_maturity` and `target_maturity` describe operating models. Setting
either field to `automated` must not create a schedule, trigger a run, or bypass
human oversight.

Scheduling and event-triggered execution are separate product capabilities and
require their own explicit design.

### 11. Preserve Langflow graph and Flow semantics

Avoid changes to:

- `src/lfx/` workflow and graph execution.
- `src/backend/base/langflow/graph/` and processing internals.
- Existing Flow persistence fields and `Flow.data` structure.
- Existing Flow API contracts.
- The workflow builder's nodes, edges, stores, and autosave behaviour.
- Component class names and saved-flow identifiers.
- Model-provider, tool, agent, and bundle integrations.

### 12. Prefer low-conflict additive integration

Future implementation should be concentrated in new, fork-owned modules, with
only narrow registrations in shared Langflow files. This minimises conflicts
when merging future upstream Langflow changes.

Expected additive locations are:

```text
docs/uncharted-ai-os/                         # Product and architecture decisions
src/frontend/src/pages/CapabilitiesPage/      # Capability Map surface
src/frontend/src/controllers/API/queries/capabilities/
src/frontend/src/types/capabilities/
src/backend/base/langflow/api/v1/             # Capability resource API
src/backend/base/langflow/services/database/models/capability/
src/backend/base/langflow/alembic/versions/    # Additive schema revision
```

The exact runtime files are future Phase 1 work and are not created by this
documentation milestone.

## Alignment with the current Langflow architecture

### Frontend and routing

The current frontend is a React/TypeScript SPA. Authentication, TanStack Query,
and a React Flow provider are mounted above authenticated routes. The planned
`/capabilities` page belongs under the protected, authenticated dashboard
branch and `CustomDashboardWrapperPage`, as a sibling of the pathless
`CollectionPage` route and Settings, not under `/flow/:id` and not inside the
flow collection. `CollectionPage` is coupled to flow/folder state and its empty
screen, so the Capability page should own its own page shell and states.

The existing workflow canvas is controlled by workflow-specific Zustand state
and custom node/edge implementations. The Capability Map must mount a
feature-local `ReactFlowProvider` boundary and use controlled, capability-only
state so its graph interactions cannot mutate an open Langflow Flow.

### Backend and API boundary

Langflow's FastAPI application mounts stable resource APIs under `/api/v1` and
the current workflow execution API under `/api/v2/workflows`. When Phase 1 is
approved, Capability CRUD belongs in an additive v1 resource API. Execution of
a linked Flow continues through the existing v2 workflow API.

The frontend and backend do not share domain objects directly. Any future
Capability API shape must be represented by both backend validation schemas and
frontend TypeScript types.

### Persistence

Langflow uses SQLModel/SQLAlchemy and Alembic. A future Capability table should
be registered with the existing model metadata and introduced through an
additive Alembic revision. It must not alter the Flow table or encode Capability
data in Flow JSON.

The planned `primary_flow_id` should reference the stable Flow identifier and
remain nullable. Its foreign key should use `ON DELETE SET NULL`, which matches
patterns already present in the repository. Deleting a linked Flow must not
delete the Capability. If a Flow still exists but is no longer readable, API
responses must not expose its metadata and the frontend displays the reference
as unavailable.

### Authentication and authorization

Capability APIs must use the existing authenticated user dependency and retain
an owner-scoped security floor. Capability access and Flow execution are
separate authorization decisions:

1. Permission to read or edit a Capability does not grant permission to read,
   edit, or execute its linked Flow.
2. Permission to execute a Flow does not grant permission to edit the business
   assessment on a Capability.
3. Linking a Flow must not bypass the Flow's existing read and execution
   permissions.

Full cross-user or workspace Capability sharing requires an explicit extension
of the authorization resource vocabulary. It must not be approximated by
reusing Flow permissions for Capability records.

V0.1 deliberately does not add Capability actions to Langflow's authorization
resource vocabulary. Link validation reuses the existing authorized Flow-read
dependency; later Flow execution still uses the existing execute guard.

### Terminology

The current codebase uses the lowercase terms `capability` and `capabilities`
in generic technical contexts, including authorization probes and provider or
protocol feature descriptions. It does not currently define the business
Capability model described here.

Future code should keep the business model in an Uncharted-owned namespace and
use domain-qualified naming where context would otherwise be ambiguous. Do not
repurpose existing technical capability probes, tags, or protocol fields.

## V0.1 SkillTree graph shape

The Phase 1 experience is a top-down, automatically laid-out SkillTree. It
contains three visual roles:

1. One synthetic root such as `My Capability Map`.
2. Synthetic grouping nodes derived from distinct `functional_area` values.
3. Persisted Capability nodes.

The root and functional-area nodes are presentation only. They have stable,
namespaced client IDs but are never persisted. A functional area must never be
created as a parent Capability merely to obtain the desired layout.

```text
My Capability Map                         presentation root
├── Clients                              presentation grouping node
│   └── Proposal Builder                 Capability
├── Programmes                           presentation grouping node
│   └── Workshop Architect               Capability
├── Marketing & Content                  presentation grouping node
│   └── Talking-Head Script Writer       Capability
├── Research                             presentation grouping node
│   └── Market Research                  Capability
└── Operations                           presentation grouping node
    └── Meeting Synthesiser              Capability
```

The only persisted Capability-to-Capability relationship is the optional parent
link:

```text
Parent Capability
└── Child Capability
    meaning: decomposition / sub-capability only
```

The frontend renders that relationship as an edge. It must not infer
dependency, sequence, triggers, tool use, or data movement from it.

Each top-level Capability is attached to the grouping node for its own
`functional_area`; descendants attach only to their real parent. This preserves
a tree even if a descendant's classification differs from its top-level
ancestor. The descendant's own functional area remains visible in details.

Layout is derived, deterministic, and not persisted. The repository already
depends on `elkjs`; Phase 1 should use a new Capability-specific ELK layered
layout configured top-down, with stable sorted input and fixed node sizes. Do
not reuse the workflow-specific `layoutUtils.ts`, whose types, ports, and
spacing rules belong to the technical Flow graph. No new dependency is needed.

The owner-scoped Capability collection is the map; no map record is required.

## Resolved Phase 1 boundaries

The V0.1 access model, defaults, nullability, validation, hierarchy and archive
rules, Flow-link deletion and visibility behaviour, array normalization,
derived layout, SkillTree roles, and non-production example-data strategy are
now resolved. The executable contract and concrete repository touch points are
defined in [V0_1_IMPLEMENTATION_SPEC.md](./V0_1_IMPLEMENTATION_SPEC.md).

Phase 1 is split into an owner-scoped backend foundation followed by a
read-only SkillTree vertical slice. It includes no execution action and no edit
forms.

## Evolution seams, not V0.1 features

The following are deliberately acknowledged without being implemented:

- `CapabilityFlowLink` for multiple flows per Capability.
- `CapabilityMap` for multiple independently managed maps.
- Typed input, output, and tool models.
- Additional explicitly named business relationship types.
- Saved layouts or multiple views.
- Capability-specific run attribution.
- Scheduling and external triggers.
- Composite prioritisation models.

Each requires a separate product decision and should not be inferred from the
V0.1 fields.

## Initial examples for development and demonstration

These examples must be supplied through an explicit frontend development/test
fixture, not an application-startup database seed:

| Capability | Functional area |
| --- | --- |
| Proposal Builder | Clients |
| Workshop Architect | Programmes |
| Talking-Head Script Writer | Marketing & Content |
| Market Research | Research |
| Meeting Synthesiser | Operations |

Production `/capabilities` data always comes from the authenticated API. The
fixture uses null `primary_flow_id` values and does not match Flows by name.
