# M08 Sprint 1 implementation

The eight M08 submodules share the existing synthetic patient and authorization workflow. The database migration adds grants, exact identity claims, evidence versions, chunks, event receipts, change notices and access audit. The gateway loads real stored resources. The patient workspace adds a small, paginated evidence explorer for Amira and other authorized synthetic patients.

The reproducible Amira set covers a visit, metabolic assessment, a corrected version and same-time conflict, diagnostic report, neutral chart concern, coordination drafts, two medication-shaped records, all five document categories and an unavailable note. The existing outstanding assessment remains the workflow decision source. Tests add a wrong-patient note, reference tampering, identity ambiguity and concurrent event replay.

**Release decision: GO for the local synthetic Sprint 1 scope.** Patient isolation, evidence integrity, correction lineage, workflow safety and the full demonstration passed. The live update preserved the original pregnancy-stage workflow and loaded 16 supplemental source events.

The original preconception-to-pregnancy workflow continues independently of the supplemental clinical feed. Corrections to workflow observations trigger evidence re-evaluation and use the established closure reopening mechanism. See the [module matrix](V05_S1_ARCHITECTURE.md), [test report](V05_S1_TEST_REPORT.md) and [security review](V05_S1_SECURITY_REVIEW.md).
