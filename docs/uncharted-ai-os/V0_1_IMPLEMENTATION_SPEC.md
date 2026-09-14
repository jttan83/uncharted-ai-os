# Uncharted AI OS V0.1 Implementation Specification

Status: approved implementation contract for Phase 1. This document describes
work to be implemented later; no runtime code or migration is part of this
documentation change.

Read [DOMAIN_MODEL.md](./DOMAIN_MODEL.md) and
[ARCHITECTURE.md](./ARCHITECTURE.md) before using this specification.

## 1. Outcome and boundaries

Phase 1 adds an owner-only Capability resource and a protected, read-only
SkillTree at `/capabilities`. It does not add another workflow runtime.

Phase 1 is delivered in two increments:

- **Phase 1A — Backend foundation:** persistence, owner-scoped resource API,
  validation, Flow-link validation, and backend tests.
- **Phase 1B — Read-only SkillTree:** protected route, queries, derived graph,
  automatic top-down layout, read-only detail drawer, and frontend tests.

Phase 1 does not include workflow execution, editing UI, automatic database
seeding, shared maps, Capability RBAC, saved layout, or changes to Langflow Flow
semantics.

## 2. Repository alignment reviewed

This specification was checked against the current fork at the time it was
written:

- FastAPI v1 routes are exported from
  `src/backend/base/langflow/api/v1/__init__.py` and mounted by
  `src/backend/base/langflow/api/router.py` under `/api/v1`.
- Authentication/session aliases are provided by
  `langflow.api.utils.CurrentActiveUser`, `DbSession`, and
  `DbSessionReadOnly`.
- SQLModel metadata is populated through
  `src/backend/base/langflow/services/database/models/__init__.py` and is the
  Alembic target metadata.
- `Flow.id` is a UUID. Flow carries nullable `user_id`, `folder_id`, and
  `workspace_id`; `Flow.data` is the technical node/edge graph.
- There is no standalone local Workspace table. Nullable `workspace_id` is
  already used as scope metadata on resources such as Flow and Folder.
- `get_authorized_flow_for_read` in
  `src/backend/base/langflow/api/v1/authz_route_dependencies.py` performs the
  existing share-aware Flow fetch, read authorization, and deny-to-404 policy.
- The frontend route tree is declared in `src/frontend/src/routes.tsx`.
  `CustomDashboardWrapperPage` is the correct authenticated parent for the new
  page; `CollectionPage` is flow/folder-specific.
- Frontend server state uses TanStack Query through the repository's request
  processor. Workflow canvas state is held in workflow-specific Zustand stores.
- Both `@xyflow/react` and `elkjs` are already frontend dependencies.
- `src/frontend/src/utils/layoutUtils.ts` is coupled to technical workflow node
  types, ports, and spacing and is not a reusable Capability layout boundary.

These facts justify an additive v1 resource API, a separate frontend page, and
a feature-local ELK layout implementation.

## 3. V0.1 access and security contract

### 3.1 Capability ownership

V0.1 is strictly owner-only:

1. Every endpoint requires an authenticated active Langflow user.
2. `user_id` is assigned from `current_user.id`; it is never accepted from a
   create or update payload.
3. Every single-record read or mutation selects by both `Capability.id` and
   `Capability.user_id == current_user.id`.
4. List and child queries always filter by `Capability.user_id ==
   current_user.id`.
5. A missing Capability and another user's Capability both return `404` with
   the same generic detail.
6. Do not use a share-aware or authorization-widened Capability fetch, even
   when `LANGFLOW_AUTHZ_ENABLED` and an authorization plugin are active.
7. Do not add Capability actions, shares, roles, or guards to the current
   Langflow authorization vocabulary in V0.1.

`workspace_id` is a nullable stored field for compatibility. It is omitted from
all V0.1 request schemas and is written as null. A later trusted server-side
workspace context may populate it through a separately approved change.

### 3.2 Flow authorization is independent

When `primary_flow_id` is set or changed, call the existing
`get_authorized_flow_for_read` logic with the authenticated user. A missing or
unreadable Flow returns `404`; do not distinguish those cases.

Clearing `primary_flow_id` is always allowed for the Capability owner and does
not require current read access to the formerly linked Flow. An unrelated
Capability update may retain an unavailable link; only an explicitly supplied
non-null link value is revalidated.

A link grants no new Flow permission. Phase 1 exposes no execution control. Any
future run action must use Langflow's existing Flow execution endpoint and
execute authorization rather than trusting the Capability record.

When serializing an existing link:

- return `available` and the minimal `{id, name}` projection only after a fresh
  Flow read check;
- return `unavailable` and no Flow name or other Flow metadata when the Flow ID
  remains stored but is no longer readable;
- return `not_linked` when `primary_flow_id` is null.

The Capability itself remains readable in all three cases.
`primary_flow_id` remains in the response because it is a value stored on the
owner's Capability; no Flow-derived data accompanies it when unavailable.

### 3.3 Mutation safety

- Use a transaction for hierarchy checks and the write.
- Serialize hierarchy-affecting mutations for one owner by locking the current
  user row on databases that support `FOR UPDATE`, then re-read and validate
  the relevant Capability and parent chain. SQLite's write transaction provides
  its corresponding serialization; correctness must not rely on a no-op row
  lock there.
- Translate expected integrity races into stable `409` or `422` API responses,
  not raw database errors.
- Never accept `created_at`, `updated_at`, `assessed_at`, or `assessed_by` as
  authoritative client values.
- Reject a PATCH with no supplied fields. If supplied normalized values produce
  no effective change, return the current record without advancing timestamps.
- Do not add a hard-delete endpoint.

## 4. Persistence contract

### 4.1 Table and model

Create one singular `capability` table and one SQLModel table class named
`Capability`. Keep request/response models separate from the table model so
server-owned fields cannot accidentally become writable.

Recommended modules:

```text
src/backend/base/langflow/services/database/models/capability/
├── __init__.py
├── crud.py
├── model.py
└── schema.py
```

`model.py` owns the table, string enums, constants, and JSON type variant.
`schema.py` owns API-safe create, update, summary, detail, list, and Flow-link
projection schemas. `crud.py` owns explicitly owner-scoped queries and
hierarchy operations; routes should not duplicate them.

### 4.2 Columns

| Column | SQLModel/Python shape | Database rule |
| --- | --- | --- |
| `id` | `UUID` | Primary key; Python UUID default. |
| `name` | `str` | Non-null; bounded string. |
| `description` | nullable `str` | Nullable text. |
| `functional_area` | `str` | Non-null; bounded string; not an enum. |
| `parent_capability_id` | nullable `UUID` | Nullable self-FK; `ON DELETE SET NULL`. |
| `status` | string enum | Non-null; default `active`; check constraint. |
| `user_id` | `UUID` | Non-null FK to `user.id`; indexed; `ON DELETE CASCADE`. |
| `workspace_id` | nullable `UUID` | Nullable, indexed, no FK because no Workspace table exists. |
| `current_maturity` | string enum | Non-null; default `not_assessed`; check constraint. |
| `target_maturity` | string enum or null | Nullable; same maturity allow-list. |
| `human_oversight` | string enum or null | Nullable; check constraint. |
| `oversight_notes` | nullable `str` | Nullable text. |
| `frequency_value` | nullable `float` | Nullable; finite and greater than zero when present. |
| `frequency_period` | string enum or null | Nullable; check constraint and coherence constraint. |
| `baseline_human_effort_minutes_per_run` | nullable `int` | Nullable; check greater than or equal to zero. |
| `business_value` | nullable `int` | Nullable; check from 1 through 5. |
| `ai_feasibility` | nullable `int` | Nullable; check from 1 through 5. |
| `ai_execution_risk` | nullable `int` | Nullable; check from 1 through 5. |
| `assessment_notes` | nullable `str` | Nullable text. |
| `assessed_at` | nullable timezone-aware `datetime` | Nullable; server managed. |
| `assessed_by` | nullable `UUID` | Nullable FK to `user.id`; `ON DELETE SET NULL`. |
| `inputs` | `list[str]` | Non-null JSON/JSONB; default empty array. |
| `outputs` | `list[str]` | Non-null JSON/JSONB; default empty array. |
| `tools` | `list[str]` | Non-null JSON/JSONB; default empty array. |
| `primary_flow_id` | nullable `UUID` | Nullable FK to `flow.id`; indexed; `ON DELETE SET NULL`. |
| `created_at` | timezone-aware `datetime` | Non-null; Python and database current-time defaults. |
| `updated_at` | timezone-aware `datetime` | Non-null; Python/database default; set on every mutation. |

Use the repository's JSON/JSONB variant pattern so SQLite tests use `JSON` and
PostgreSQL uses `JSONB`. Use strings plus explicit check constraints for the
small domain allow-lists; a database-native PostgreSQL enum would add avoidable
cross-database migration complexity.

Use `String(120)` for `name` and `functional_area` and `Text` for the longer
nullable text fields. Mirror `active`, `not_assessed`, and empty-array defaults
in both the application model and migration DDL so non-null invariants also
hold for controlled server-side inserts.

`frequency_value` is a JSON number and database floating-point value in V0.1.
The contract needs fractional cadence, not exact financial arithmetic, and no
annualisation is persisted. Reject NaN and infinities. If exact decimal
arithmetic becomes a real reporting need, migrate it deliberately rather than
silently changing the wire type.

Do not add ORM relationships to `User` or `Flow` in V0.1. Scalar foreign keys
are sufficient and avoid edits to upstream relationship collections and
accidental loading of unauthorized Flow data.

`ON DELETE SET NULL` on the self-reference protects descendants during rare
administrative/database cleanup. It does not create a hard-delete API and has
no bearing on the non-cascading archive rule.

### 4.3 Indexes and constraints

Create named constraints and indexes so migration and model metadata match:

- composite index on `(user_id, status)` for the normal active map query;
- index on `parent_capability_id` for child checks;
- index on `primary_flow_id` for FK cleanup/lookups;
- index on nullable `workspace_id` for future compatibility;
- check constraints for all enum allow-lists;
- check constraints for effort and each 1-5 rating;
- one frequency coherence check:
  - null period requires null value;
  - `ad_hoc` or `unknown` requires null value;
  - dated periods require a non-null value greater than zero.

Text bounds, finite-number checks, array normalization, ownership, hierarchy,
and cycle rules remain application validation. Database constraints are a
defence-in-depth subset, not the only validation layer.

The user foreign key may cascade only when Langflow itself deletes the entire
user account. This is database lifecycle cleanup and does not create a normal
Capability delete operation.

### 4.4 Migration

Generate one additive Alembic revision under:

```text
src/backend/base/langflow/alembic/versions/<revision>_add_capability_table.py
```

At review time the repository head is `d7e9f1a3b5c8`; implementation must
generate from the then-current single head rather than copying that value
blindly. Follow the repository's `Phase: EXPAND` convention and migration
helpers for table/index existence where appropriate.

The upgrade should only create `capability`, its constraints, indexes, and
foreign keys. It must not alter `flow`, `folder`, or `user`. The downgrade drops
only the new table and its owned indexes/constraints. Verify both SQLite and
PostgreSQL-compatible DDL, especially self-reference behaviour, JSON variants,
and `ON DELETE SET NULL`.

## 5. Domain validation contract

### 5.1 Required fields and defaults

Server-generated or server-assigned:

- `id`: UUID
- `user_id`: authenticated user
- `workspace_id`: null in V0.1
- `created_at` and `updated_at`: UTC timestamps

Client-required on create:

- `name`
- `functional_area`

Create defaults:

- `status = active`
- `current_maturity = not_assessed`
- `inputs = []`
- `outputs = []`
- `tools = []`

All other domain fields are nullable. Do not populate ratings, target maturity,
oversight, cadence, effort, notes, or assessment identity with placeholders.

### 5.2 Text

- `name`: trim; 1-120 characters.
- `functional_area`: trim; 1-120 characters.
- `description`: normalize blank to null; maximum 2,000 characters.
- `oversight_notes`: normalize blank to null; maximum 2,000 characters.
- `assessment_notes`: normalize blank to null; maximum 5,000 characters.

These limits match the approved starting contract; no repository convention
requires a deviation.

### 5.3 Enums

- `status`: `active`, `archived`.
- maturity: `not_assessed`, `manual`, `ai_assisted`, `ai_executable`,
  `automated`.
- oversight: `none`, `review_recommended`, `approval_required`, `human_led`.
- frequency period: `day`, `week`, `month`, `quarter`, `year`, `ad_hoc`,
  `unknown`.

### 5.4 Frequency and effort

- Null `frequency_period` requires null `frequency_value`.
- `day`, `week`, `month`, `quarter`, and `year` require a finite positive
  `frequency_value`; fractional values are valid.
- `ad_hoc` and `unknown` require null `frequency_value`.
- Do not persist or return an annualised total.
- `baseline_human_effort_minutes_per_run` is a nullable integer greater than or
  equal to zero and means total human labour, not elapsed duration.
- Do not calculate savings in V0.1.

### 5.5 Assessment

Each score is either null or an integer from 1 through 5. No composite score is
stored or returned.

`assessed_at` and `assessed_by` are server managed. Treat the following as
assessment-bearing fields: `current_maturity`, `target_maturity`,
`human_oversight`, `oversight_notes`, the three scores, and
`assessment_notes`.

- A create request that leaves `current_maturity=not_assessed` and all other
  assessment-bearing fields null leaves `assessed_at` and `assessed_by` null.
- When a create or update establishes or changes substantive assessment data,
  set `assessed_at` to the current UTC time and `assessed_by` to the current
  user.
- If an update explicitly resets the state to `not_assessed` and clears every
  other assessment-bearing field, clear both assessment identity fields.
- Work-economics changes alone do not stamp an AI assessment.

This rule prevents record creation from masquerading as assessment while
keeping provenance useful without accepting forged client values.

### 5.6 Ordered string arrays

Apply this normalization independently to `inputs`, `outputs`, and `tools`:

1. Reject a request containing more than 50 raw entries.
2. Require strings and trim surrounding whitespace.
3. Reject values that become empty or exceed 200 characters after trimming.
4. Remove exact, case-sensitive duplicates after trimming.
5. Preserve the first occurrence and resulting display order.

The values are business-language descriptors, not Flow ports or executable
Langflow Tool objects.

### 5.7 Hierarchy and archival

- A non-null parent must be an owner-scoped Capability that exists.
- A Capability cannot parent itself.
- Walk the proposed parent's ancestor chain before create/update; reject if the
  Capability being updated is encountered.
- There is no maximum depth in V0.1.
- An active Capability cannot be created, re-parented, or restored beneath an
  archived parent.
- Setting a Capability to `archived` returns `409` while it has an active
  owner-scoped child.
- Archiving does not cascade and does not clear child links.
- The API may restore an archived record by setting `status=active`; all normal
  parent and cycle validation applies.
- Functional areas do not participate in hierarchy validation.
- No dependency, sequence, trigger, data-flow, or general relationship edge is
  inferred.

When workspace scoping is introduced later, parent and child must have
compatible workspace scope. Because V0.1 always writes null workspace IDs,
owner equality is the complete current scope check.

## 6. API contract

Use an `APIRouter(prefix="/capabilities", tags=["Capabilities"])` registered
under the existing v1 router. All paths below are therefore under `/api/v1`.

### 6.1 Endpoints

| Method and path | Behaviour | Success |
| --- | --- | --- |
| `GET /capabilities/` | Owner-scoped list; active only by default. Supports `include_archived`, `offset`, and `limit`. | `200 CapabilityListResponse` |
| `POST /capabilities/` | Validate and create for authenticated owner. | `201 CapabilityRead` |
| `GET /capabilities/{capability_id}` | Owner-scoped full record and current Flow-link projection. | `200 CapabilityRead` |
| `PATCH /capabilities/{capability_id}` | Partial owner-scoped update, including archive/restore and clearing nullable fields. | `200 CapabilityRead` |

There is no `DELETE` endpoint and no run/execute endpoint.

List parameters:

- `include_archived: bool = false`
- `offset: int = 0`, minimum zero
- `limit: int = 200`, range 1-200

Order results deterministically by `functional_area`, `name`, then `id`.
`total` is counted within the same owner/status filter before pagination.
Phase 1B's list query retrieves all pages so the map never silently renders a
partial hierarchy.

### 6.2 Request schemas

`CapabilityCreate`:

```text
name: string                                      required
functional_area: string                           required
description: string | null                        default null
parent_capability_id: UUID | null                  default null
status: active | archived                          default active
current_maturity: maturity                         default not_assessed
target_maturity: maturity | null                   default null
human_oversight: oversight | null                  default null
oversight_notes: string | null                     default null
frequency_value: number | null                     default null
frequency_period: frequency period | null          default null
baseline_human_effort_minutes_per_run: int | null  default null
business_value: int | null                         default null
ai_feasibility: int | null                         default null
ai_execution_risk: int | null                      default null
assessment_notes: string | null                    default null
inputs: string[]                                   default []
outputs: string[]                                  default []
tools: string[]                                    default []
primary_flow_id: UUID | null                       default null
```

`CapabilityUpdate` exposes the same mutable fields, all optional. Omission
means no change; explicit null clears a nullable field. Explicit null for
`name`, `functional_area`, `status`, `current_maturity`, or any collection is
invalid. Implement this distinction using Pydantic's fields-set information,
not truthiness.

Use strict integers for effort and the three assessment scores. Serialize UUIDs
as UUID strings and timestamps as ISO 8601 values with an explicit UTC offset.

Neither schema contains `id`, `user_id`, `workspace_id`, `created_at`,
`updated_at`, `assessed_at`, or `assessed_by`.

### 6.3 Response schemas

`FlowLinkAvailability`:

```text
status: not_linked | available | unavailable
flow: { id: UUID, name: string } | null
```

`CapabilitySummary` contains the fields needed to construct and render the
map without a detail request:

```text
id, name, functional_area, parent_capability_id, status,
current_maturity, target_maturity,
business_value, ai_feasibility, ai_execution_risk,
primary_flow_id, primary_flow_link
```

`CapabilityRead` contains every persisted domain field plus
`primary_flow_link`. `CapabilityListResponse` is:

```text
items: CapabilitySummary[]
total: integer
offset: integer
limit: integer
```

Never serialize a SQLModel table row directly as the public contract. Build the
projection deliberately so an inaccessible Flow cannot leak its name,
description, folder, workspace, graph, or authorization state.

For list responses, resolve each distinct non-null Flow ID at most once per
request and reuse that redacted projection for duplicate references. Do not
cache an authorization decision across requests.

### 6.4 Error semantics

- `401`: not authenticated, through existing authentication behaviour.
- `404`: Capability missing or owned by someone else; parent missing or owned
  by someone else; linked Flow missing or unreadable.
- `409`: cycle, attempt to archive with active children, or hierarchy conflict
  caused by a concurrent mutation.
- `422`: invalid field, enum, text, array, score, frequency, effort, self-parent,
  or explicit null for a required field.

Do not include another owner's ID, name, or existence in an error response.

## 7. Phase 1A repository change plan

### 7.1 Files to create

```text
src/backend/base/langflow/services/database/models/capability/__init__.py
src/backend/base/langflow/services/database/models/capability/model.py
src/backend/base/langflow/services/database/models/capability/schema.py
src/backend/base/langflow/services/database/models/capability/crud.py
src/backend/base/langflow/api/v1/capabilities.py
src/backend/base/langflow/alembic/versions/<generated_revision>_add_capability_table.py
src/backend/tests/unit/services/database/models/capability/__init__.py
src/backend/tests/unit/services/database/models/capability/test_model.py
src/backend/tests/unit/services/database/models/capability/test_crud.py
src/backend/tests/unit/api/v1/test_capabilities.py
```

If migration-specific behaviour is not adequately covered by existing
migration suites, also create:

```text
src/backend/tests/unit/services/database/test_capability_migration.py
```

### 7.2 Existing files requiring narrow registration edits

```text
src/backend/base/langflow/services/database/models/__init__.py
src/backend/base/langflow/api/v1/__init__.py
src/backend/base/langflow/api/router.py
```

The model registry imports and exports `Capability`; the v1 package imports and
exports `capabilities_router`; the central router includes it. No User model,
Flow model, Folder model, authorization action, graph engine, or execution
router edit is required.

Use `DbSessionReadOnly` for list/get and `DbSession` for create/patch. The Flow
read helper accepts the same underlying async session when invoked by these
routes.

### 7.3 Backend tests

Model/schema tests cover:

- every default and nullable field;
- trimming and text bounds;
- each enum allow-list;
- fractional cadence and all invalid period/value pairings;
- zero effort, rejected negative/fractional effort;
- score bounds and integers only;
- array trimming, empty rejection, maximums, case-sensitive deduplication, and
  order;
- assessment stamping and clearing.

CRUD/API tests cover:

- authentication on every route;
- owner-scoped list/get/update and identical `404` for another owner;
- server assignment of `user_id`, null `workspace_id`, UUID, and timestamps;
- list pagination, active default, archived inclusion, and deterministic order;
- valid parent creation, cross-owner parent rejection, self-parent, deep cycle,
  archived parent, and unlimited valid depth;
- blocked parent archival with an active child, non-cascade archive, child
  re-parenting, archive, and restore;
- accessible Flow link, missing Flow, unreadable Flow, clearing a link,
  `ON DELETE SET NULL`, and inaccessible-link response redaction;
- DB constraint translation and concurrent hierarchy conflict behaviour;
- absence of `DELETE` and execute routes.

Use the established async API test client and authenticated header fixtures.
Run the model/API tests directly first, then the relevant backend unit suite.

## 8. Phase 1B frontend contract

### 8.1 Route placement

Add a lazy `CapabilitiesPage` import and this route to
`src/frontend/src/routes.tsx`:

```text
ProtectedRoute
└── AppAuthenticatedPage
    └── CustomDashboardWrapperPage
        ├── CollectionPage                 existing pathless flow surface
        ├── CapabilitiesPage               path="capabilities"
        └── SettingsPage                   existing
```

This provides the existing login redirect/protection and dashboard chrome but
avoids `CollectionPage` and `flowsManagerStore`. Do not place the route under
`/flow/:id`, a Project/Folder route, or custom Flow routes.

No global navigation or dashboard-shell redesign is required in Phase 1B.
`/capabilities` can be accessed directly while product navigation placement is
decided separately.

### 8.2 Files to create

```text
src/frontend/src/types/capabilities/index.ts
src/frontend/src/controllers/API/queries/capabilities/index.ts
src/frontend/src/controllers/API/queries/capabilities/use-get-capabilities.ts
src/frontend/src/controllers/API/queries/capabilities/use-get-capability.ts
src/frontend/src/pages/CapabilitiesPage/index.tsx
src/frontend/src/pages/CapabilitiesPage/types.ts
src/frontend/src/pages/CapabilitiesPage/components/CapabilitySkillTree.tsx
src/frontend/src/pages/CapabilitiesPage/components/CapabilityDetailDrawer.tsx
src/frontend/src/pages/CapabilitiesPage/components/CapabilityMapLoadingState.tsx
src/frontend/src/pages/CapabilitiesPage/components/CapabilityMapEmptyState.tsx
src/frontend/src/pages/CapabilitiesPage/components/CapabilityMapErrorState.tsx
src/frontend/src/pages/CapabilitiesPage/components/CapabilityEdge.tsx
src/frontend/src/pages/CapabilitiesPage/components/nodes/CapabilityMapRootNode.tsx
src/frontend/src/pages/CapabilitiesPage/components/nodes/FunctionalAreaNode.tsx
src/frontend/src/pages/CapabilitiesPage/components/nodes/CapabilityNode.tsx
src/frontend/src/pages/CapabilitiesPage/layout/build-capability-graph.ts
src/frontend/src/pages/CapabilitiesPage/layout/layout-capability-tree.ts
src/frontend/src/pages/CapabilitiesPage/__fixtures__/initial-capabilities.ts
src/frontend/src/pages/CapabilitiesPage/components/CapabilitySkillTree.stories.tsx
```

The repository already has a Storybook runner. Keep the story focused on the
pure SkillTree component and provide its required React Flow/query context in
the story rather than adding a production fallback-data path.

### 8.3 Existing files requiring narrow edits

```text
src/frontend/src/routes.tsx
src/frontend/src/controllers/API/helpers/constants.ts
src/frontend/src/locales/en.json
src/frontend/src/locales/de.json
src/frontend/src/locales/es.json
src/frontend/src/locales/fr.json
src/frontend/src/locales/ja.json
src/frontend/src/locales/pt.json
src/frontend/src/locales/zh-Hans.json
scripts/a11y/a11y_routes.json
```

Add `CAPABILITIES: "capabilities"` to the URL constants. Add equivalent keys to
every locale so the locale-parity checks remain valid; use reviewed translations
where available and the English source text as the explicit fallback where they
are not. Register `/capabilities` as a static protected accessibility surface
with a stable main-content readiness marker.

Do not edit `GenericNode`, `NoteNode`, `DefaultEdge`, workflow node registries,
`flowStore`, `flowsManagerStore`, `CollectionPage`, Flow autosave, or
`src/frontend/package.json`.

### 8.4 Type and query structure

`src/frontend/src/types/capabilities/index.ts` mirrors the public API enums and
response schemas. It must not import workflow `AllNodeType`, `NodeDataType`, or
Flow graph shapes.

The query hooks use the existing Axios client and `useQuery` request processor:

- `useGetCapabilities`: one cache key rooted at `capabilities`; retrieves all
  active pages in chunks of 200 until `total` is satisfied; merges without
  reordering; does not use `flowsManagerStore`.
- `useGetCapability(id, enabled)`: fetches the full detail only when an actual
  node is selected and the drawer is open.

Keep server records in the TanStack Query cache. Keep selected Capability ID,
drawer open state, and current derived graph local to `CapabilitiesPage` or
`CapabilitySkillTree`. Phase 1B does not justify a global Zustand store.

### 8.5 Derived graph model

Define a feature-local discriminated union in `CapabilitiesPage/types.ts`:

- `CapabilityMapRootNode`: presentation node.
- `FunctionalAreaNode`: presentation node carrying only the area label.
- `CapabilityNode`: persisted Capability summary data.
- `CapabilityEdge`: feature-local edge data and semantic kind.

Use collision-safe IDs:

```text
presentation:root
presentation:functional-area:<encoded functional area>
capability:<Capability UUID>
edge:root:<functional-area node ID>
edge:group:<functional-area node ID>:<Capability UUID>
edge:parent:<parent UUID>:<child UUID>
```

Build the graph as follows:

1. Exclude archived records from the default SkillTree query.
2. Add one `My Capability Map` presentation root.
3. Derive distinct grouping nodes from active top-level Capabilities'
   `functional_area` values.
4. Attach each grouping node to the root.
5. Attach each active top-level Capability to its own grouping node.
6. Attach each descendant only to its persisted parent, never to a second
   functional-area group.
7. Sort areas and siblings by a pinned, case-insensitive label comparison and
   UUID tie-break so input/API order cannot change the layout.

Backend integrity should make cycles and missing parents impossible. The graph
builder should still fail safely: place an orphan under the group for its own
functional area, record a development warning, and never recurse forever.

Presentation nodes are non-selectable. Only persisted Capability nodes open
the detail drawer.

### 8.6 Layout

Use the installed `elkjs/lib/elk.bundled.js` in the new
`layout-capability-tree.ts`. Recommended ELK settings:

- layered algorithm;
- direction `DOWN`;
- fixed dimensions per role, initially root `240 x 64`, functional area
  `240 x 56`, and Capability `280 x 120`;
- explicit, Capability-specific layer and sibling spacing;
- stable sorted nodes and edges before invoking ELK.

The layout function accepts only Capability feature node/edge types and returns
new positioned nodes. Do not import or adapt the existing workflow
`layoutUtils.ts`.

ELK is asynchronous. Guard layout results with a monotonically increasing
request token or equivalent cancellation check so a slow previous layout
cannot overwrite newer query data. Until the current layout resolves, retain
the loading state or last complete layout; do not flash unpositioned nodes.

Do not persist `position`, viewport, zoom, pan, or user drag results. Recompute
from capability data on load/change. Configure the canvas read-only:

- `nodesDraggable={false}`
- `nodesConnectable={false}`
- no delete key behaviour
- no connection creation
- pan, zoom, fit-view, and keyboard navigation may remain available

Use feature-local, non-interactive source/target anchors built from
`@xyflow/react` primitives if edge routing requires handles. These are not
Langflow workflow component handles.

### 8.7 Node and edge presentation

Capability nodes prioritise:

1. Capability name.
2. Current maturity, always as a visible text label.

Compact secondary indicators may show target maturity, Flow availability, and
the three assessment values. They must remain subordinate and may be omitted
at narrow sizes rather than overloading the node.

Maturity uses five categorical treatments with both text and non-colour cues.
Do not use progress bars, completion percentages, ordinal levels, arrows that
imply improvement, or game language. `automated` must not be styled as a
victory state. When present, target maturity is labelled `Target` and never
visually replaces current maturity.

Functional-area and root nodes use different shapes/typography from Capability
nodes so a viewer cannot mistake presentation structure for stored business
work. The feature-local `CapabilityEdge` may use `BaseEdge` primitives from
`@xyflow/react`, but must not reuse Langflow's workflow `DefaultEdge` or imply
process flow/direction beyond hierarchy.

### 8.8 Read-only detail drawer

Selecting a Capability ID opens `CapabilityDetailDrawer` and enables the detail
query. The drawer displays:

- Identity: name, description, functional area, status.
- AI transformation: current maturity, target maturity, human oversight,
  oversight notes.
- Work economics: human-readable frequency and baseline total human effort.
- Assessment: the three directional scores and assessment notes.
- Execution context: ordered inputs, outputs, and tools.
- Langflow: primary Flow ID and `not linked`, `available`, or `unavailable`
  state; Flow name only when available.

Reuse the repository's accessible Radix-based primitives from
`src/frontend/src/components/ui/dialog.tsx`, styled as a right-side drawer. The
`MemoryDocumentPanel` is a useful interaction pattern; do not reuse its
business component. Provide a dialog title, close control, Escape handling,
focus trap, and focus restoration.

Show explicit `Not assessed`, `Not set`, or empty-list copy for null data. Do
not convert null scores to zero. There are no inputs, edit controls, archive
buttons, Flow run buttons, or automatic navigation to an inaccessible Flow in
this slice.

### 8.9 Loading, empty, and error states

- Loading: page skeleton plus stable main-content landmark.
- Empty: explain what Capabilities are; no automatic sample insertion. Because
  Phase 1B has no editor, the primary action may be omitted or labelled as a
  future capability rather than linking to unrelated Flow creation.
- Error: accessible alert with a retry action that refetches Capability data.
- Detail error: keep the map usable, close or show an inline drawer error, and
  never fall back to cached Flow metadata that is no longer authorized.

### 8.10 Development/demo data

The safest V0.1 strategy is a frontend-only explicit fixture used by Storybook,
unit tests, and API-mocked Playwright tests:

| Capability | Functional area |
| --- | --- |
| Proposal Builder | Clients |
| Workshop Architect | Programmes |
| Talking-Head Script Writer | Marketing & Content |
| Market Research | Research |
| Meeting Synthesiser | Operations |

Give fixture records deterministic fixture UUIDs and null `primary_flow_id`.
Never activate the fixture as a runtime fallback and never match a Flow by
name. Production builds always use authenticated API data, so this strategy
cannot create duplicate database rows or mutate users.

For a manual integrated demo, use a disposable development database and make
explicit authenticated POST requests. Do not add startup seeding or a hidden
production seed path.

### 8.11 Frontend tests to create

```text
src/frontend/src/controllers/API/queries/capabilities/__tests__/use-get-capabilities.test.tsx
src/frontend/src/controllers/API/queries/capabilities/__tests__/use-get-capability.test.tsx
src/frontend/src/pages/CapabilitiesPage/__tests__/CapabilitiesPage.test.tsx
src/frontend/src/pages/CapabilitiesPage/components/__tests__/CapabilitySkillTree.test.tsx
src/frontend/src/pages/CapabilitiesPage/components/__tests__/CapabilityDetailDrawer.test.tsx
src/frontend/src/pages/CapabilitiesPage/layout/__tests__/build-capability-graph.test.ts
src/frontend/src/pages/CapabilitiesPage/layout/__tests__/layout-capability-tree.test.ts
src/frontend/tests/core/features/capabilities-route.spec.ts
```

Tests cover:

- authentication redirects for `/capabilities` and access when authenticated;
- loading, empty, retryable error, and successful states;
- retrieval and merge of all API pages;
- the five fixture branches and the root/group/capability distinction;
- real parent hierarchy, cross-area descendant policy, deterministic order,
  orphan fallback, and cycle safety;
- deterministic top-down ELK positions and stale-result protection;
- categorical maturity labels, target treatment, scores, and Flow status;
- keyboard selection of a Capability node;
- drawer content, null display, focus behaviour, Escape, and unavailable Flow
  redaction;
- no drag, connect, delete, or workflow-store interaction;
- the route's inclusion in the static accessibility scan.

Mock network boundaries in frontend unit/E2E tests; backend authorization and
foreign-key behaviour remain backend test responsibilities.

## 9. Explicit no-touch list

Phase 1 must not change:

- `Flow.data`, Flow identifiers, Flow table semantics, or Flow API contracts;
- `Folder`/Project semantics or hierarchy;
- `src/lfx/` execution primitives;
- `src/backend/base/langflow/graph/` or processing/build internals;
- v2 workflow execution routes, background jobs, streaming, or history;
- agents, providers, tools, bundles, and component class identifiers;
- workflow `GenericNode`, `NoteNode`, `DefaultEdge`, handles, stores, layout,
  selection, or autosave;
- existing Flow authorization semantics;
- global React Flow state or provider behaviour.

Narrow shared-file registration edits listed in Sections 7 and 8 are the only
expected upstream touch points.

## 10. Out of scope

V0.1 does not include:

- a `CapabilityMap` database model;
- shared/team maps or Capability RBAC;
- multiple Flow links or `CapabilityFlowLink`;
- an AI Opportunity Score;
- scheduling or automatic execution;
- Capability run history;
- general relationship edges or process sequence;
- saved coordinates, viewport, drag persistence, or map versions;
- editing UI in the first vertical slice;
- collaboration, client organisations, or external publication;
- replacement of any Langflow workflow semantic.

## 11. Conflicts and resolved integration choices

No approved product decision conflicts with the current repository in a way
that blocks Phase 1. The following integration tensions are resolved here:

1. **No Workspace model:** keep `workspace_id` nullable and server-controlled;
   owner `user_id` is the V0.1 boundary.
2. **Pluggable cross-user Flow authorization:** Capability fetches remain
   owner-only, while Flow-link checks reuse the existing share-aware Flow read
   guard. The two access decisions stay separate.
3. **Global React Flow provider:** mount a nested feature-local provider and
   controlled Capability graph state.
4. **Existing workflow ELK utility:** reuse the installed `elkjs` package, not
   the workflow-specific utility or types.
5. **Flow deletion:** a nullable FK with `ON DELETE SET NULL` preserves the
   Capability and is compatible with current migration patterns.
6. **Presentation hierarchy versus persisted hierarchy:** root and grouping
   nodes are derived, namespaced client objects; only Capability nodes persist.

There are no unresolved blockers for Phase 1A. Phase 1B should begin only after
the Phase 1A API contract and tests are merged or otherwise stable. Navigation
placement beyond direct `/capabilities` access and editing UX are future product
decisions, not blockers for the approved read-only slice.

## 12. Required implementation order

### Phase 1A — Backend foundation

1. Add enums, normalization helpers, API schemas, and focused validation tests.
2. Add the `Capability` table model with constraints/FKs and model tests.
3. Register the model in SQLModel metadata.
4. Generate and inspect the additive migration from the then-current Alembic
   head; verify upgrade/downgrade and both supported database dialects.
5. Add owner-scoped CRUD functions and hierarchy/archive transaction logic.
6. Add Flow-link authorization and response projection logic using the existing
   Flow read guard.
7. Add the v1 router and its four endpoints.
8. Make the two narrow API router registrations.
9. Add complete API security, validation, hierarchy, archive, and Flow-link
   tests.
10. Run formatting, targeted backend tests, migration checks, then the relevant
    backend unit suite.

### Phase 1B — Read-only SkillTree vertical slice

1. Add frontend API types, URL constant, paginated list query, detail query,
   and query tests.
2. Add the explicit five-record development/test fixture.
3. Implement and test the pure Capability-to-presentation-graph transform.
4. Implement and test the feature-local deterministic ELK layout.
5. Build distinct root, functional-area, Capability, and edge components.
6. Compose the read-only SkillTree under a feature-local
   `ReactFlowProvider`, including selection and stale-layout protection.
7. Build the accessible read-only detail drawer.
8. Add loading, empty, and error states and page-level tests.
9. Add locale keys, then register the protected sibling route in
   `routes.tsx`.
10. Add the authenticated Playwright route test and static accessibility route
    manifest entry.
11. Run formatting, targeted frontend tests, locale checks, route E2E, and the
    scoped accessibility scan.

Stop after Phase 1B verification. Workflow execution and editing require
separate approval.
