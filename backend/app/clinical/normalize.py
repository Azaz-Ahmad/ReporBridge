"""Lossless metadata normalization and bounded inline document extraction."""
import base64
import binascii
import hashlib
import json
import re
import textwrap
from datetime import UTC, datetime

from app.clinical.access import fail
from app.fhir import STATUSES, structure_errors
from app.rules import DEMO_TAG, SYSTEM

DOCUMENT_TYPES = {"clinical-note", "assessment-summary", "referral-note", "discharge-summary", "diagnostic-report"}
CONTRACT_STATUSES = {
    **STATUSES,
    "MedicationRequest": {"active", "on-hold", "cancelled", "completed", "entered-in-error", "stopped", "draft", "unknown"},
    "MedicationStatement": {"active", "completed", "entered-in-error", "intended", "stopped", "on-hold", "unknown", "not-taken"},
}
KNOWN_CODES = DOCUMENT_TYPES | {
    "follow-up-flag", "pregnancy-registration", "follow-up-reconciled", "pregnancy-handoff-reconciled",
    "synthetic", "metabolic-assessment", "synthetic-medication",
    "tsp-lmp", "tsp-ultrasound-edd",  # Explicit synthetic dating vocabulary; no clinical terminology mapping.
}
UCUM = "http://unitsofmeasure.org"
KNOWN_UNITS = {"g", "mg", "kg", "mmol/L", "mg/dL"}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def stamp(value):
    if isinstance(value, str):
        if len(value) == 10:
            value = value + "T00:00:00+00:00"
        value = datetime.fromisoformat(value)
    if value.utcoffset() is None:
        raise ValueError("Missing offset")
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def nested(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nested(child)
    elif isinstance(value, list):
        for child in value:
            yield from nested(child)


def source_status(resource):
    if "status" in resource:
        return resource["status"]
    if resource["resourceType"] == "Patient" and isinstance(resource.get("active"), bool):
        return "active" if resource["active"] else "inactive"
    if resource["resourceType"] == "Condition":
        codings = (resource.get("clinicalStatus") or {}).get("coding", [])
        return next((coding["code"] for coding in codings if coding.get("code")), "unknown")
    return "unknown"


def normalize(resource, received, event_time=None):
    kind = resource["resourceType"]
    candidates = (resource.get("effectiveDateTime"), resource.get("effectiveInstant"), resource.get("onsetDateTime"),
                  (resource.get("effectivePeriod") or {}).get("start"), (resource.get("period") or {}).get("start"),
                  ((resource.get("context") or {}).get("period") or {}).get("start")
                  if isinstance(resource.get("context"), dict) else None,
                  resource.get("authoredOn"), resource.get("dateAsserted"), resource.get("issued"),
                  resource.get("recordedDate"), resource.get("date"))
    original = (((resource.get("context") or {}).get("period") or {}).get("start") if kind == "DocumentReference"
                else next((value for value in candidates if value is not None), None))
    warnings = set()
    clinical = None
    if original is not None:
        try:
            clinical = stamp(original)
        except (TypeError, ValueError, OverflowError):
            warnings.add("unresolved_clinical_timestamp")
    elif kind != "Patient":
        warnings.add("missing_clinical_timestamp")
    if (clinical and clinical > stamp(received)) or (event_time and event_time > stamp(received)):
        warnings.add("timestamp_after_receipt")

    coding = []
    units = []
    for item in nested(resource):
        if isinstance(item.get("code"), str) and isinstance(item.get("system"), str):
            system, code = item["system"], item["code"]
            if "value" not in item and system != UCUM:
                verified = system == SYSTEM and code in KNOWN_CODES
                coding.append({"system": system, "code": code, "terminology": "recognized" if verified else "unresolved"})
                if not verified:
                    warnings.add("unknown_terminology")
        if "value" in item and ("unit" in item or item.get("system") == UCUM):
            known = item.get("system") == UCUM and item.get("code") in KNOWN_UNITS
            units.append({"value": item["value"], "unit": item.get("unit"), "system": item.get("system"),
                          "code": item.get("code"), "resolution": "recognized" if known else "unresolved"})
            if not known:
                warnings.add("unknown_unit")
    return clinical, {"original_clinical_time": original, "original_status": resource.get("status"),
                      "source_version": (resource.get("meta") or {}).get("versionId"),
                      "codings": coding, "units": units, "warnings": sorted(warnings)}


def validate(resource, patient_id, version, kind):
    pending = [(resource, 0)]
    visited = 0
    while pending:
        node, depth = pending.pop()
        visited += 1
        if depth > 32 or visited > 8000:
            fail(422, "resource_size", "Clinical resource exceeds the supported complexity.")
        if isinstance(node, (dict, list)):
            children = node.values() if isinstance(node, dict) else node
            if len(children) > 8000:
                fail(422, "resource_size", "Clinical resource exceeds the supported complexity.")
            pending.extend((child, depth + 1) for child in children)
    try:
        if len(json.dumps(resource, ensure_ascii=True, allow_nan=False)) > 96000:
            fail(422, "resource_size", "Clinical resource exceeds the supported size.")
    except (ValueError, TypeError):
        fail(422, "invalid_json", "The resource contains unsupported JSON values.")
    status = resource.get("status")
    if kind in CONTRACT_STATUSES and (not isinstance(status, str) or status not in CONTRACT_STATUSES[kind]):
        fail(422, "invalid_status", "Resource status is outside the supported R4 values.")
    if kind != resource.get("resourceType") or structure_errors(resource):
        fail(422, "invalid_fhir", "Resource did not pass the bundled FHIR R4 structural schema.")
    meta = resource.get("meta") or {}
    if DEMO_TAG not in meta.get("tag", []) or (meta.get("versionId") and meta["versionId"] != str(version)):
        fail(422, "invalid_source_metadata", "Synthetic tag and consistent source version are required.")
    if kind == "Patient":
        if resource["id"] != patient_id:
            fail(422, "invalid_subject", "Patient must match the granted canonical identifier.")
    elif (resource.get("subject") or {}).get("reference") != f"Patient/{patient_id}":
        fail(422, "invalid_subject", "Resource subject must match the granted canonical patient.")
    for item in nested(resource):
        if isinstance(item.get("identifier"), dict) and not item.get("reference"):
            fail(422, "logical_reference", "Use a canonical literal reference in this scope.")


def extract_document(resource):
    code = (resource.get("type") or {}).get("coding", [])
    kind = next((item.get("code") for item in code if item.get("system") == SYSTEM), None)
    if kind not in DOCUMENT_TYPES or resource.get("status") not in {"current", "superseded", "entered-in-error"}:
        fail(422, "invalid_document", "A supported synthetic document type and status are required.")
    content = resource.get("content", [])
    if len(content) != 1 or not resource.get("date"):
        fail(422, "invalid_document", "Provide a creation instant and one inline attachment.")
    attachment = content[0].get("attachment")
    if not isinstance(attachment, dict):
        fail(422, "invalid_document", "The document attachment is required.")
    media = attachment.get("contentType")
    if media not in {"text/plain", "text/markdown"} or attachment.get("url"):
        fail(422, "unsafe_attachment", "Only inline UTF-8 text or Markdown is supported.")
    try:
        stamp(resource["date"])
        created = attachment.get("creation") or resource["date"]
        stamp(created)
        encoded = attachment.get("data", "")
        if len(encoded) > 43692:
            raise ValueError("Attachment too large")
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) > 32768:
            raise ValueError("Attachment too large")
        body = raw.decode("utf-8")
        if any(ord(char) < 32 and char not in "\r\n\t" for char in body):
            raise ValueError("Control character")
    except (ValueError, binascii.Error, UnicodeError):
        fail(422, "invalid_attachment", "Attachment is invalid UTF-8, base64 or exceeds the size limit.")
    metadata = {
        "type": kind, "author": [item.get("display") for item in resource.get("author", []) if item.get("display")],
        "created": created, "indexed": resource["date"], "content_ref": "urn:sha256:" + hashlib.sha256(raw).hexdigest() if raw else None,
        "attachment_type": media, "available": bool(body.strip()),
    }
    return metadata, section_chunks(body)


def section_chunks(body):
    groups = [("Document", [])]
    for line in body.splitlines():
        heading = re.fullmatch(r"(?:#{1,6}\s+(.{1,140})|([A-Za-z][A-Za-z /-]{1,75}):)", line.strip())
        if heading:
            groups.append((heading.group(1) or heading.group(2), []))
        else:
            groups[-1][1].append(line)
    return [(section, part) for section, lines in groups for part in
            textwrap.wrap("\n".join(lines).strip(), width=1000, replace_whitespace=False)]
