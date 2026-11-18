# Clinical Evidence Agent architecture

Sprint 2 adds one Clinical Evidence Agent under `backend/app/investigation`. The established deterministic graph in `app/agent.py` remains independently callable.

## Actual graph

`START → validate_request → investigate → authorized_tools → investigate → validate_grounding → prepare_review_packet → human_review_queue → END`

The investigate node conditionally routes to tools when the model emits function calls. It routes to grounding when a structured draft or failure arrives. Tool execution loops until the model finishes or the configured step, tool or elapsed-time guard stops it. The last permitted model step requests a final structured output with tool choice disabled. A malicious extra tool call still encounters backend budget enforcement.

The final graph node persists a ready or abstained packet. Explicit coordinator submission places it into the persisted pending-review queue. Reviewer decisions use a separate table and endpoint.

## Typed state

InvestigationState carries backend run/patient/actor/question, allowed tools, ephemeral provider messages, calls, tool metadata, retrieved evidence, draft, validation, packet, status, error, steps, usage and graph trace. PatientAccess is created from authenticated role grants outside model arguments.

The official provider adapter implements a small provider-independent invoke interface. Actual OpenAI requests use Responses with function tools and strict JSON schema. Deterministic test doubles exist exclusively in tests.

## Persistence and recovery

Migration 0005 adds clinical_investigation_runs and clinical_investigation_reviews. Existing migrations remain unchanged. Metadata, configuration version, timestamps, usage, invocation metadata, citations, grounding and review packets are persisted after each graph node. Network calls occur outside database transactions.

A unique patient/actor/request-ID reservation prevents duplicate execution and duplicate charges from application request replay. Changed payload under the same request ID returns 409. In-flight duplicates return the existing run. Interrupted runs retain checkpoints and cannot publish a new result after interruption. A stale running record is marked interrupted on a subsequent read after 240 seconds without checkpoint activity. Recovery uses a new explicit request ID. There is no automatic replay of uncertain remote completions.

## Data integrity

Every tool reauthorizes scope and uses real M08 retrieval. A catalog fingerprint captures source IDs, hashes, status and correction lineage before invocation. Grounding rechecks catalog and retrieved records after investigation. Submission and review also recheck current evidence, including newly added records. Source changes require a fresh investigation.

The additive migration was applied after a PostgreSQL backup. All 20 existing workflow and M08 tables matched their pre-migration count and content hashes. Amira remained at pregnancy.
