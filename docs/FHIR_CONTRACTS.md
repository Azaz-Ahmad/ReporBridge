# FHIR R4 contracts

The API uses a bounded application contract built on HL7 FHIR 4.0.1. The checked-in archive is the [official HL7 FHIR R4 JSON schema](https://hl7.org/fhir/R4/fhir.schema.json.zip). The import path validates resource structure with JSON Schema Draft 6 and applies additional demo validation.

`POST /api/fhir/import` accepts a JSON object with a `resources` array of 1–50 resources. The coordinator supplies `demo-` IDs and the `synthetic` tag in the `https://reprobridge.example/fhir/CodeSystem/demo` system. Resources are immutable by ID within each storage group. Submit the patient in the same batch or import it first.

| Resource | Demo contract |
| --- | --- |
| Patient | Synthetic identity, name, administrative gender and full birth date |
| Observation | Local Patient reference, coded finding, status, and valueString |
| Condition, DiagnosticReport, Encounter, ServiceRequest, CarePlan | Structural and bounded status or intent validation, stored and exported as supporting records |
| Task | Generated from an obligation with subject, owner, source, rule version and verified output where applicable |
| Provenance | Generated from obligation audit history with task target, actor, timestamp and source references |
| Bundle | Patient collection export with absolute synthetic fullUrl values |

`GET /api/fhir/patients/{patient_id}` produces the collection for authenticated demo roles. Import is an application endpoint with a bounded resource array. Planned integration profiles, external reference resolution, terminology services, full FHIRPath invariant checks, and live connectivity are future work. See [Task](https://hl7.org/fhir/R4/task.html) and [Provenance](https://hl7.org/fhir/R4/provenance.html).
