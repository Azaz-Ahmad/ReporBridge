"""Deterministic clinical data that supplements the canonical Amira demo."""
import base64
from datetime import datetime

from app import db
from app.clinical.access import authorize, claim, fail
from app.clinical.contracts import Event
from app.clinical.events import process
from app.rules import DEMO_TAG, SYSTEM, seed_records

PATIENT = "demo-amira"
SOURCE = "synthetic-m08"
TIME = "2026-10-01T08:00:00+00:00"


def resource(kind, suffix, **values):
    return {"resourceType": kind, "id": f"demo-m08-{suffix}", "meta": {"tag": [DEMO_TAG]},
            "subject": {"reference": f"Patient/{PATIENT}"}, **values}


def coding(code):
    return {"coding": [{"system": SYSTEM, "code": code}]}


def note(suffix, kind, body=None):
    attachment = {"contentType": "text/markdown", "creation": TIME}
    if body:
        attachment["data"] = base64.b64encode(body.encode("utf-8")).decode("ascii")
    return resource("DocumentReference", suffix, status="current", docStatus="final", date=TIME,
                    type=coding(kind), author=[{"display": "Synthetic clinician"}],
                    context={"period": {"start": TIME}}, content=[{"attachment": attachment}])


def dataset():
    encounter = resource("Encounter", "visit", status="finished",
                         **{"class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB"}},
                         period={"start": TIME})
    assessment = resource("Observation", "assessment", status="final", code=coding("metabolic-assessment"),
                          effectiveDateTime=TIME, valueString="Assessment documented for reconciliation",
                          encounter={"reference": "Encounter/demo-m08-visit"})
    corrected = {**assessment, "valueString": "Documentation corrected. Clinician reconciliation remains outstanding."}
    conflict = {**assessment, "id": "demo-m08-conflict", "valueString": "Review documentation conflicts"}
    report = resource("DiagnosticReport", "report", status="final", code=coding("diagnostic-report"),
                      issued=TIME, result=[{"reference": "Observation/demo-m08-assessment"}])
    medication = {"medicationCodeableConcept": coding("synthetic-medication")}
    notes = [
        note("note", "clinical-note", "# Context\nSynthetic metabolic assessment.\n# Follow-up\nClinician reconciliation remains outstanding."),
        note("referral", "referral-note", "# Referral\nCoordinate review with the receiving care team."),
        note("summary", "assessment-summary", "# Assessment\nDocumentation needs reconciliation."),
        note("discharge", "discharge-summary", "# Discharge\nSynthetic transfer context only."),
        note("report-note", "diagnostic-report", "# Findings\nSynthetic report documents the source assessment."),
        note("missing-document", "clinical-note"),
    ]
    for document in notes:
        document["context"]["encounter"] = [{"reference": "Encounter/demo-m08-visit"}]
    return [
        (encounter, 1), (assessment, 1), (corrected, 2), (conflict, 1), (report, 1),
        *((document, 1) for document in notes),
        (resource("Condition", "chart-concern", code={"text": "Synthetic chart concern pending review"},
                  recordedDate=TIME, encounter={"reference": "Encounter/demo-m08-visit"}), 1),
        (resource("ServiceRequest", "review-request", status="draft", intent="proposal",
                  code=coding("metabolic-assessment"), authoredOn=TIME), 1),
        (resource("CarePlan", "review-plan", status="draft", intent="plan", period={"start": TIME},
                  title="Synthetic coordination plan"), 1),
        (resource("MedicationRequest", "medication-request", status="draft", intent="proposal", authoredOn=TIME,
                  **medication), 1),
        (resource("MedicationStatement", "medication-statement", status="unknown", effectiveDateTime=TIME,
                  **medication), 1),
    ]


def seed(connection, actor):
    from app.service import find

    context = authorize(connection, actor, PATIENT)
    if find(connection, db.patients, PATIENT, required=True)["resource"] != seed_records()[0]:
        fail(409, "fixture_mismatch", "The clinical dataset requires the canonical Amira fixture.")
    if claim(connection, context, SOURCE, "amira-m08") == "ambiguous":
        fail(409, "ambiguous_identity", "The synthetic feed mapping requires review.")
    results = []
    for record, version in dataset():
        event = Event(source=SOURCE, event_id=f"{record['id']}-v{version}", event_time=datetime.fromisoformat(TIME),
                      resource=record, version=version, external_id="amira-m08")
        results.append(process(connection, context, event))
    return {"patient_id": PATIENT, "events": len(results), "duplicates": sum(
        result["status"] == "duplicate" for result in results)}
