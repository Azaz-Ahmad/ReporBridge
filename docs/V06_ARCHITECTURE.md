# v0.6 prevention architecture

Increment 1 extends the five existing screens and existing authentication, M08 retrieval and Clinical Evidence Agent. The deterministic clinical care-resolution graph and the six original innovations retain their entry points.

## Domain and storage

Migration 0006 adds five independent tables.

| Table | Purpose |
|---|---|
| prevention_decisions | Patient/obligation link, owner, rationale, lifecycle, rule/policy, snapshot, revision and archive marker |
| prevention_prerequisites | Versioned required evidence categories, definitions, availability, source IDs, issues and evaluation time |
| prevention_timing_policies | Immutable illustrative definition/version/source and active/retired/superseded state |
| prevention_decision_records | One immutable reviewer outcome per decision, rationale, source references, snapshot and follow-up |
| prevention_decision_audit | Append-only creation, evaluation, review, recording, investigation, follow-up and archive events |

Historical obligation/patient identifiers are stored without deletion-cascading foreign keys. Canonical demo reset archives decision rows and preserves their audit and reviewer records before the original workflow is reset. Unrelated patients, the independent M08 feed and illustrative timing scenario are preserved.

The migration was backed up and applied live. All 22 existing workflow, M08 and investigation tables retained identical before/after row counts and content hashes.

## Derived evaluation

The prevention service uses the existing patient authorization and M08 ClinicalRetrieval gateway. Current source versions and source integrity are checked. The illustrative metabolic registry applies only to preconception review obligations.

A technical prerequisite can be missing, unavailable, conflicting, requires_reconciliation or available_for_review. Availability never constitutes clinical sufficiency. A reviewer decides the outcome.

Source snapshots include source IDs, versions, hashes, quality, structured values, citations, clinical times, prerequisite definitions/status, linked-obligation status, life-stage events, owner and policy. Changes invalidate an in-progress review through an incremented revision. Recorded decisions retain their original snapshot and expose a changed-context indicator.

Existing serialized write transactions synchronize decision evaluations after events. Decision snapshot reads also synchronize derived state. Timing labels are evaluated against current server UTC time, so passing a deadline updates the read result without a scheduled job.

## Five-screen integration

Population adds backend queue counts and patient links. Workspace adds a chronological Decision Timeline. Passport adds rationale, owner, provenance, prerequisites, timing and reviewer controls. Care-resolution adds a decision-bound investigation using the existing agent panel. Evidence & audit adds persisted Decision History.

General investigations and decision-readiness investigations have separate panel filters. They share the same provider, six-node graph and seven authorized tools.

## Transaction boundaries

Creation, transitions, policy changes, recording and follow-up use existing serialized database writes. Revision checks and a unique decision-record constraint prevent duplicate clinical outcomes. Network model calls remain outside database transactions. Decision-bound run reservation includes trusted decision context in its replay fingerprint. Concurrent duplicate investigations finalize once.

The gateway catalog is local and evaluated synchronously. Production-scale paging and background scheduling remain future work.
