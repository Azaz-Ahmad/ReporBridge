# Sprint 2 tool contracts

The `ClinicalTools` binder accepts a trusted database context and authenticated, grant-checked patient scope. The patient and role belong to server-side context. Request models reject extra fields, including caller-supplied identity or role.

| Tool | Validated input | Output |
| --- | --- | --- |
| `get_patient_clinical_context` | Filters | EvidencePage |
| `search_patient_observations` | Search | Patient-local Observation matches |
| `search_patient_encounters` | Search | Patient-local Encounter matches |
| `search_patient_documents` | Search | Cited and section-labeled document excerpts |
| `get_evidence_provenance` | EvidenceId | Exact scoped result and provenance |
| `check_evidence_quality` | EvidenceId | Exact scoped quality state, warnings and configured policy reference |
| `get_related_obligations` | RelatedRequest | Bounded authorized obligations, optionally filtered by a verified evidence ID |

These methods share the HTTP retrieval implementation and access audit. Missing collections have a `not_found` outcome. Missing or foreign detail IDs produce a scoped 404. Supersession, insufficiency, conflicts and unavailable source content are explicit. Source text is data with an untrusted indicator and never enters the existing LangGraph workflow as an instruction. The prototype wires no LLM or new agent to these interfaces.
