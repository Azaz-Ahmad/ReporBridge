import json
import re
from pathlib import Path
from zipfile import ZipFile

from jsonschema import Draft6Validator
from datetime import date

from fastapi import HTTPException

from app.rules import DEMO_TAG

TYPES = {"Patient", "Condition", "Observation", "DiagnosticReport", "Encounter", "ServiceRequest", "CarePlan", "Task", "Provenance"}
STATUSES = {
    "Observation": {"registered", "preliminary", "final", "amended", "corrected", "cancelled", "entered-in-error", "unknown"},
    "DiagnosticReport": {"registered", "partial", "preliminary", "final", "amended", "corrected", "appended", "cancelled", "entered-in-error", "unknown"},
    "Encounter": {"planned", "arrived", "triaged", "in-progress", "onleave", "finished", "cancelled", "entered-in-error", "unknown"},
    "ServiceRequest": {"draft", "active", "on-hold", "revoked", "completed", "entered-in-error", "unknown"},
    "CarePlan": {"draft", "active", "on-hold", "revoked", "completed", "entered-in-error", "unknown"},
}


with ZipFile(Path(__file__).with_name("schema") / "fhir-r4-schema.zip") as archive:
    SCHEMA = json.loads(archive.read("fhir.schema.json"))


def structure_errors(resource):
    kind = resource.get("resourceType")
    validator = Draft6Validator({"definitions": SCHEMA["definitions"], "$ref": f"#/definitions/{kind}"})
    return list(validator.iter_errors(resource))


def demand(condition, detail):
    if not condition:
        raise HTTPException(422, detail)


def validate_import(resource):
    kind = resource.get("resourceType")
    demand(isinstance(kind, str) and kind in TYPES - {"Task", "Provenance"}, "Unsupported import resource type")
    errors = structure_errors(resource)
    if errors:
        problem = errors[0]
        location = ".".join(map(str, problem.absolute_path)) or kind
        raise HTTPException(422, f"FHIR R4 structure failed at {location} ({problem.validator})")
    identifier = resource.get("id")
    demand(isinstance(identifier, str) and re.fullmatch(r"demo-[A-Za-z0-9.-]{1,59}", identifier),
           "Resource ids must use the demo- namespace")
    meta = resource.get("meta")
    demand(isinstance(meta, dict) and isinstance(meta.get("tag"), list) and DEMO_TAG in meta["tag"],
           "Each resource must carry the ReproBridge synthetic tag")
    if kind == "Patient":
        names = resource.get("name")
        demand(isinstance(names, list) and bool(names) and all(
            isinstance(name, dict) and isinstance(name.get("family"), str)
            and isinstance(name.get("given"), list) and all(isinstance(given, str) for given in name["given"])
            for name in names
        ), "Patient requires a structured synthetic name")
        try:
            date.fromisoformat(resource.get("birthDate", ""))
        except (TypeError, ValueError) as error:
            raise HTTPException(422, "Patient requires an ISO birth date") from error
        demand(resource.get("gender") in ("male", "female", "other", "unknown"), "Invalid administrative gender")
        return identifier
    subject = resource.get("subject")
    ref = subject.get("reference") if isinstance(subject, dict) else None
    demand(isinstance(ref, str) and re.fullmatch(r"Patient/demo-[A-Za-z0-9.-]{1,59}", ref), "Expected a synthetic Patient subject")
    if kind in STATUSES:
        status = resource.get("status")
        demand(isinstance(status, str) and status in STATUSES[kind], f"Invalid {kind} status")
    if kind in {"Observation", "DiagnosticReport"}:
        code = resource.get("code")
        codings = code.get("coding") if isinstance(code, dict) else None
        demand(isinstance(codings, list) and bool(codings) and all(
            isinstance(coding, dict) and isinstance(coding.get("system"), str) and isinstance(coding.get("code"), str)
            for coding in codings
        ), f"{kind} requires structured coding")
    if kind == "Observation":
        demand(isinstance(resource.get("valueString"), str) and
               [field for field in resource if field.startswith("value")] == ["valueString"],
               "This demo accepts Observation.valueString")
    if kind == "Encounter":
        encounter_class = resource.get("class")
        demand(isinstance(encounter_class, dict) and isinstance(encounter_class.get("code"), str),
               "Encounter.class coding is required")
    if kind == "ServiceRequest":
        demand(resource.get("intent") in ("proposal", "plan", "directive", "order", "original-order",
                                           "reflex-order", "filler-order", "instance-order", "option"),
               "Invalid ServiceRequest intent")
    if kind == "CarePlan":
        demand(resource.get("intent") in ("proposal", "plan", "order", "option"), "Invalid CarePlan intent")
    return ref.split("/", 1)[1]
