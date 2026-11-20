# Ajyra AI - ReproBridge v0.2 FHIR validation

The validation target is HL7 FHIR R4 4.0.1. Ajyra AI - ReproBridge uses python-jsonschema 4.26.0 with Draft 6 against the official HL7 R4 JSON schema stored in `backend/app/schema/fhir-r4-schema.zip`. Imports add bounded synthetic identity, vocabularies, and reference checks. Export uses `application/fhir+json` and validates the collection before serving it. [HL7 R4 JSON schema](https://hl7.org/fhir/R4/fhir.schema.json.zip)

| Scope | Method |
| --- | --- |
| Patient, Condition, Observation, Encounter, DiagnosticReport, ServiceRequest, CarePlan | Structural validation, supported IDs and required demo fields, and round-trip tests |
| Task | Proposal intent, requested or completed status from obligation state, patient and source references, rule version, and verified output only while closed |
| Provenance | In-bundle Task target, UTC recorded instant, acting role and evidence entities linked to stored audit actions |
| Bundle | Collection structure, generated full URLs, same-patient references, selected allowed target types, and serialized JSON validation |

The automated browser runner independently validates the downloaded Amira bundle after each PostgreSQL journey. API tests cover malformed resources, dangling and foreign-patient references, incorrect Encounter targets, and omission of completion outputs on reopened Tasks. Full FHIR conformance is unestablished. The audit covers structure and the local reference contract. It does not run a full HL7 terminology, profile or FHIRPath validation server. [HL7 R4 Bundle](https://hl7.org/fhir/R4/bundle.html) · [Task](https://hl7.org/fhir/R4/task.html) · [Provenance](https://hl7.org/fhir/R4/provenance.html)
