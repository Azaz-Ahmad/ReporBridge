# Ajyra AI - ReproBridge v0.5 Sprint 2 implementation

## Release decision

The initial delivery was CONDITIONAL GO pending credentials. The current Gemini integration has passed all three real investigations. See V05_S2_GEMINI_VERIFICATION.md for the current regression results and release decision.

The starting commit is 737f7ceb4bd81a5b137dbbfaf3801e4b47ff6cc7. The verified implementation is committed after the final test run. The ending commit is reported in the delivery message and available through git log -1.

## Delivered implementation

Official OpenAI SDK 2.54.0 supports a reusable Responses provider adapter. The configurable default is gpt-4.1-mini. Current verified Gemini model calls total 17 in the final three-case gate, with actual tool traces, source checks and human-review routing recorded. Invocation, strict structured parsing, bounded retries, classified failures, usage tracking and provider status are implemented. Dollar cost estimates are unavailable and configuring a dollar ceiling prevents execution.

The dedicated graph contains validate_request, investigate, authorized_tools, validate_grounding, prepare_review_packet and human_review_queue. The model chooses function calls. The backend supplies trusted scope and enforces tools, schemas, access and budgets. The deterministic care-resolution graph continues independently.

All seven existing M08 methods are connected through thin adapters. Context listing, Observation/Encounter/document search, provenance, quality and related-obligation reads reuse the persisted M08 services.

ClinicalEvidenceReviewPacket contains typed findings, versioned supporting sources, excerpts or JSON values, uncertainty, missing information, conflicts, grounding and mandatory human review. Backend-owned identifiers prevent model identity forgery. Drafts failing grounding are withheld and replaced with labeled system abstention.

Migration 0005 adds two independent tables for runs and summary reviews. Old migrations remain unchanged. An ignored PostgreSQL backup precedes live upgrade. All 20 existing workflow and M08 tables retained identical counts and hashes. Amira's pregnancy-stage records remained intact.

## New HTTP endpoints

| Method | Path under /api/v1/agents/clinical-evidence | Role |
|---|---|---|
| GET | /status | Authenticated reader |
| POST | /runs | Coordinator |
| GET | /runs?patient_id=demo-amira | Patient-scoped reader |
| GET | /runs/{run_id} | Patient-scoped reader |
| GET | /runs/{run_id}/trace | Patient-scoped reader |
| GET | /runs/{run_id}/review-packet | Patient-scoped reader |
| POST | /runs/{run_id}/submit | Coordinator |
| POST | /runs/{run_id}/review | Reviewer |

## UI and human review

The existing Care-resolution center gains a Clinical Evidence Investigation section. It shows provider status, a bounded synthetic question, persisted execution metadata, source citations, findings, missing/conflicting information, grounding, uncertainty and immutable reviewer decisions. Every action uses a backend endpoint.

The running app displays the active Gemini provider configuration. The five existing screens remain. Desktop and 390-pixel screenshots were inspected, UTF-8 rendering was corrected, and the mobile panel fits.

Summary review uses its own records. Existing clinical approval and closure tables remain independent. Source snapshots are revalidated at generation, submission and review.

## Verification and safety

See V05_S2_TEST_REPORT.md for the final complete regression run and V05_S2_EVALUATION_REPORT.md for 28 agent checks and 16 labeled scenarios.

Actual tool invocation metadata, evidence IDs, versions, hashes, usage, graph steps and grounding results are persisted. Raw prompts and tool documents remain ephemeral. Clinical question and bounded packet support are retained for the reviewer.

Executed tests found no remaining critical scope, write-tool or clinical-closure defect. Semantic narrative validation and live model behavior remain verification limits.

## Deliberate prototype decisions

The LLM feature is scoped to canonical synthetic Amira with explicit synthetic-question attestation. It executes synchronously, checkpoints node results and marks stale workers interrupted on read. Recovery requires a new request ID. Dollar estimates and automatic remote-completion replay are unavailable.

The existing patient grants, identity ambiguity handling, FHIR/document gateway, corrections, event idempotency, deterministic rules and closure safeguards remain the data and clinical-control foundation.

## Documentation

The ten V05_S2 documents cover baseline, architecture, OpenAI integration, tool security, grounding/abstention, evaluations, tests, implementation, limitations and demonstration. Screenshots are in docs/screenshots/v05-s2. Reproducible raw reports and the database backup are under ignored test-reports.
