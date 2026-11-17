SYSTEM = "https://reprobridge.example/fhir/CodeSystem/demo"
DEMO_TAG = {"system": SYSTEM, "code": "synthetic"}
PRE = "preconception-follow-up@1.0.0"
PREG = "pregnancy-coordination@1.0.0"
DEPENDENCY_RULES = {PREG: (PRE, "requires_verified_closure")}
PATHS = {"preconception": "Preconception", "pregnancy": "Pregnancy"}
RULES = {
    PRE: {
        "pathway": "preconception", "trigger": "follow-up-flag", "value": "outstanding",
        "closure": "follow-up-reconciled", "description": "Reconcile the documented synthetic follow-up flag.",
        "source": "docs/CLINICAL_RULES.md#preconception-follow-up",
    },
    PREG: {
        "pathway": "pregnancy", "trigger": "pregnancy-registration", "value": "registered",
        "closure": "pregnancy-handoff-reconciled", "description": "Review the synthetic handoff and linked follow-up.",
        "source": "docs/CLINICAL_RULES.md#pregnancy-coordination",
    },
}


# Presentation is version-keyed but separate from the immutable decision definitions.
RULE_PRESENTATION = {
    PRE: {
        "title": "Preconception metabolic assessment review",
        "finding": "Documented preconception metabolic assessment requiring clinician reconciliation",
        "rationale": "A documented assessment remained outstanding at preconception. The rule records a review obligation so the assessment stays visible if care moves into pregnancy.",
        "next_action": "Ask the responsible clinician to reconcile the documented preconception metabolic assessment.",
        "completion": "A final synthetic record confirming reconciliation of the metabolic assessment.",
    },
    PREG: {
        "title": "Pregnancy handoff review",
        "finding": "Pregnancy registration recorded",
        "rationale": "Pregnancy registration triggers a handoff review in this illustrative workflow. The linked assessment, when present, remains visible to the receiving care team.",
        "next_action": "Review the pregnancy handoff and the linked preconception assessment.",
        "completion": "A final synthetic record confirming reconciliation of the pregnancy handoff.",
    },
}


def observation(patient: str, identifier: str, code: str, value: str):
    return {
        "resourceType": "Observation", "id": identifier, "meta": {"tag": [DEMO_TAG]},
        "status": "final", "code": {"coding": [{"system": SYSTEM, "code": code}]},
        "subject": {"reference": f"Patient/{patient}"}, "valueString": value,
    }


def seed_records(*, legacy=False):
    patient = {
        "resourceType": "Patient", "id": "demo-amira", "meta": {"tag": [DEMO_TAG]},
        "name": [{"given": ["Amira"], "family": "Haddad"}], "gender": "female", "birthDate": "1995-04-12",
    }
    assessment = observation(patient["id"], "demo-initial-flag", "follow-up-flag", "outstanding")
    if not legacy:
        assessment["code"]["text"] = RULE_PRESENTATION[PRE]["finding"]
    return [patient, assessment]


def code_matches(resource, code):
    return resource.get("resourceType") == "Observation" and any(
        coding.get("system") == SYSTEM and coding.get("code") == code
        for coding in resource.get("code", {}).get("coding", [])
    )


def matches(resource, code, value):
    return (
        code_matches(resource, code) and len(resource["code"]["coding"]) == 1
        and not any(field in resource for field in ("modifierExtension", "component", "dataAbsentReason"))
        and resource.get("status") == "final" and resource.get("valueString") == value
    )
