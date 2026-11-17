# M08 API contracts

All routes are under `/api/v1/clinical` and use the existing demo bearer roles. Swagger at `/docs` exposes request and response schemas. Patient selection is exact and grant-checked.

| Method and route | Purpose |
| --- | --- |
| GET `/patients/{patient_id}/resources` | Bounded FHIR resources and evidence metadata |
| GET `/patients/{patient_id}/resources/{kind}/{resource_id}` | Current record or explicit numeric version |
| GET `/patients/{patient_id}/evidence` and `/evidence/{evidence_id}` within the patient path | Read normalized views or an exact evidence ID |
| GET `/patients/{patient_id}/documents` | Document metadata, or scoped section excerpts with `query` |
| POST `/retrieval/search` | Structured, document or hybrid retrieval with exact patient in the request |
| POST `/patients/{patient_id}/events` | Coordinator-only version submission |
| POST `/patients/{patient_id}/identity/claims` and `/identity/resolve` within the patient path | Coordinator-only namespace mapping and exact lookup |
| GET `/patients/{patient_id}/changes` | Patient-local sequence feed with `after` and `limit` |
| POST `/demo/dataset` | Coordinator-only seed and replay of the amended Amira source fixture |

Collections support `kind`, `status`, inclusive clinical `start` and `end` with offsets, `history`, bounded `limit` 1–50 and `offset` 0–1000. The response distinguishes `not_found` collections from evidence quality. Retrieval exposes SHA-256, timestamps, source/version and references, approval role context, predecessor and applicable workflow obligations. Unavailable resources return metadata with a null raw resource. Excerpts are explicitly untrusted data. Failures use a stable `detail.code` and concise message. A scope-denied patient or ID uses the same unavailable response regardless of existence.
