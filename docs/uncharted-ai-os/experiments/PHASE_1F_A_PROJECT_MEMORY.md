# Phase 1F-A Project Memory

Last updated: 2026-09-16

## Purpose

Concise navigation and working memory for future Phase 1F-A editorial-
evaluation sessions. This is not a second source of truth. Canonical
documents always override this file; follow the links below for detail.

Update this file only when an approved decision or materially changed,
verified implementation status needs to be indexed.

## Authoritative documents

Read these before changing Phase 1F-A behavior:

1. `docs/uncharted-ai-os/experiments/PHASE_1F_A_EDITORIAL_EVAL_PROTOCOL.md`
2. `docs/uncharted-ai-os/capabilities/TALKING_HEAD_CONTENT_DEVELOPMENT.md`
3. `docs/uncharted-ai-os/roles/EDITORIAL_CONTENT_DIRECTOR.md`
4. `docs/uncharted-ai-os/DOMAIN_MODEL.md`
5. `docs/uncharted-ai-os/ARCHITECTURE.md`

## Repository baseline

- Branch: `uncharted-v0.1`
- Relevant commit: `4f28e25692d902175fee5dae29b5f229c2280472`
- Commit: `feat: add Phase 1F-A editorial evaluation harness`
- Harness: `scripts/uncharted_ai_os/editorial_eval/`
- Focused tests: `src/backend/tests/unit/scripts/uncharted_ai_os/editorial_eval/`

## Current / ephemeral status

The following describes the state recorded at the relevant commit and may
become stale. It is operational status, not architectural truth.

- Harness implementation is committed and reviewed.
- Reported focused-test result at that commit: 94 passed; Ruff and Python
  compilation passed; one unrelated Starlette/httpx deprecation warning was
  reported.
- The first real provider-backed contaminated development rehearsal has not
  run.
- Provider pre-flight stopped before an external call because no supported
  provider credential was available in the then-current environment.
- No provider/model was selected, provider output or private trace was
  created, blind bundle/reveal mapping was created, or tuning was performed.

Do not record credential values, private reveal mappings, holdout material,
confidential client content, raw provider outputs, or hidden reasoning here.

## Currently implemented development topology

creator
→ deterministic validation
→ independent evaluator
→ bounded revision/evaluation

The canonical Phase 1F-A design also includes conditional fact-checking where
required. It remains deferred until before holdout freeze unless a development
finding requires it earlier; this memory file does not imply it is implemented.

The harness remains experiment-owned and disposable. It does not add a
generalized Agent framework, production orchestration, persistence, UI,
database/schema/migrations, or publication authority.

## Exact next step

Using the committed Phase 1F-A harness, run exactly one real provider-backed
case that is explicitly:

**CONTAMINATED / DEVELOPMENT ONLY / NOT HOLDOUT**

Case: **“AI tools before work redesign”** (`case_dev_tools_before_redesign`)

Use an explicitly supported provider and model configured through the
provider's external environment/secret mechanism. Never guess an identifier,
and record only safe configuration metadata.

After the run, keep it development-only; complete the normal blind bundle and
sequential Stage 1 review; do not reveal identities or begin Stage 2 until all
three Stage 1 judgments are locked; do not tune from the resulting outputs.

## Deferred until before holdout freeze

- Fresh protected holdout workflow and data
- Full Stage 1 and Stage 2 human-review questionnaires
- Timed edit capture and integrated repeatability execution
- Conditional fact checker (unless required earlier by development findings)
- Instagram or Langflow integration
- Database, schema, migrations, frontend/UI, or production persistence
- Playbook learning and experiment freeze

## Standing engineering principle

Reuse before build:

- check the existing repository first
- check upstream/current dependencies
- search mature maintained open-source/GitHub solutions where appropriate
- integrate/extend before rebuilding
- custom-build only the differentiated gap

## Update discipline

- Record only approved decisions or verified status.
- Label ephemeral status with its date or relevant commit.
- Keep canonical definitions and decisions in the authoritative documents.
- Include the relevant commit hash when implementation status changes.
- Keep confidential artifacts and reveal material in their approved private
  custody boundary.
- Never reinterpret development results as holdout or pilot evidence.
