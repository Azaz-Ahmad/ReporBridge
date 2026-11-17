"""FHIR provider boundary and patient-scoped local retrieval."""
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import func, literal_column, or_, select

from app import db
from app.clinical.access import PatientAccess, audit_access, authorize, fail
from app.clinical.contracts import EvidencePage, EvidenceResult, Filters, ResourcePage, ResourceResult, Search
from app.clinical.normalize import digest, extract_document, normalize, source_status, stamp
from app.clinical.schema_v1 import chunks, receipts, registry
from app.fhir import references, structure_errors


class FHIRProvider(Protocol):
    def catalog(self, context: PatientAccess) -> list[dict]: ...
    def document_matches(self, evidence_ids: list[str], query: str, limit: int) -> list[dict]: ...


def workflow_scope(connection, patient_id):
    return connection.execute(select(db.events.c.id).where(
        db.events.c.patient_id == patient_id, db.events.c.stage == "preconception")).scalar_one_or_none() or patient_id


def local_record(patient_id, resource, scope, received, actor):
    kind, identifier = resource["resourceType"], resource["id"]
    clinical_time, normalized = normalize(resource, received)
    return dict(id=uuid5(NAMESPACE_URL, f"reprobridge/workflow/{patient_id}/{scope}/{kind}/{identifier}").hex,
        patient_id=patient_id, source="workflow", scope=scope, kind=kind, resource_id=identifier, version=1,
        event_time=None, clinical_time=clinical_time, received=stamp(received), status=source_status(resource),
        digest=digest(resource), actor=actor, supersedes=None, resource=resource, normalized=normalized)


class LocalFHIRProvider:
    def __init__(self, connection):
        self.connection = connection

    def catalog(self, context):
        patient_id = context.patient_id
        scope = workflow_scope(self.connection, patient_id)
        patient = self.connection.execute(select(db.patients.c.resource).where(
            db.patients.c.id == patient_id)).scalar_one_or_none()
        if not patient:
            fail(404, "patient_unavailable", "Patient is unavailable in this authorization scope.")
        versions = [dict(row) for row in self.connection.execute(select(registry).where(
            registry.c.patient_id == patient_id,
            (registry.c.source != "workflow") | (registry.c.scope == scope))).mappings()]
        materialized = {version["id"] for version in versions}
        original_records = [patient, *self.connection.execute(select(db.evidence.c.resource).where(
            db.evidence.c.patient_id == patient_id)).scalars()]
        # Original workflow import timestamps are persisted in the v0.4 audit log.
        recorded = {}
        for row in self.connection.execute(select(db.audit.c.recorded, db.audit.c.actor, db.audit.c.evidence_refs).where(
                db.audit.c.patient_id == patient_id, db.audit.c.action == "resource_imported"
        ).order_by(db.audit.c.sequence)).mappings():
            for reference in row["evidence_refs"]:
                recorded.setdefault(reference, (row["recorded"], row["actor"]))
        for resource in original_records:
            reference = f"{resource['resourceType']}/{resource['id']}"
            receipt = recorded.get(reference)
            if receipt is None:
                continue
            row = local_record(patient_id, resource, scope, *receipt)
            if row["id"] not in materialized:
                versions.append(row)
        return versions

    def document_matches(self, evidence_ids, query, limit):
        if not evidence_ids:
            return []
        request = select(chunks).where(chunks.c.evidence_id.in_(evidence_ids))
        if self.connection.dialect.name == "postgresql":
            dictionary = literal_column("'simple'")
            vector = func.to_tsvector(dictionary, chunks.c.body)
            if query:
                terms = func.plainto_tsquery(dictionary, query)
                rank = func.ts_rank(vector, terms).label("score")
                request = request.add_columns(rank).where(vector.op("@@")(terms)).order_by(rank.desc())
        else:
            for term in re.findall(r"\w+", query.casefold()):
                request = request.where(func.lower(chunks.c.body).contains(term, autoescape=True))
        return [dict(row) for row in self.connection.execute(
            request.order_by(chunks.c.evidence_id, chunks.c.position).limit(limit)).mappings()]


@dataclass(frozen=True)
class FreshnessPolicy:
    """Deploy only with the approved policy or pathway reference configured by the server."""
    approved_reference: str
    maximum_age: timedelta


def reference_key(row):
    return f"{row['kind']}/{row['resource_id']}"


def paginate(items, filters):
    start = filters.offset
    end = start + filters.limit
    return {"items": items[start:end], "next_offset": end if end < len(items) and end <= 1000 else None,
            "outcome": "found" if items[start:end] else "not_found"}


def quality(row, superseded, conflicting, policy=None):
    warnings = set(row["normalized"]["warnings"])
    if policy and not policy.approved_reference:
        raise ValueError("A freshness policy requires an approval reference.")
    clinical_time = row["clinical_time"]
    if policy and clinical_time and datetime.now(UTC) - datetime.fromisoformat(clinical_time) > policy.maximum_age:
        warnings.add("potentially_stale")
    if row["status"] in {"invalidated", "entered-in-error", "cancelled"}:
        state = "unavailable"
    elif superseded or row["status"] == "superseded":
        state = "superseded"
    elif conflicting or ("conflicting_document_status" in warnings):
        state = "conflicting"
    elif not row["normalized"].get("document", {}).get("available", True):
        state = "unavailable"
    elif warnings:
        state = "insufficient"
    else:
        state = "valid"
    return {"state": state, "warnings": sorted(warnings), "policy": policy.approved_reference if policy else None}


class ClinicalRetrieval:
    def __init__(self, connection, context: PatientAccess, provider: FHIRProvider | None = None,
                 policy: FreshnessPolicy | None = None):
        self.connection = connection
        self.context = authorize(connection, context.role, context.patient_id)
        self.provider = provider or LocalFHIRProvider(connection)
        self.policy = policy

    def prepare(self, filters):
        rows = self.provider.catalog(self.context)
        if any(row["patient_id"] != self.context.patient_id for row in rows):
            fail(409, "invalid_provider_scope", "Provider returned a record outside its authorized scope.")
        superseded = {row["supersedes"] for row in rows if row["supersedes"]}
        available = {reference_key(row) for row in rows}
        current = [row for row in rows if row["id"] not in superseded and row["status"] not in
                   {"superseded", "invalidated", "entered-in-error", "cancelled"}]
        observed_values = {}
        for row in current:
            key, value = self.observed_value(row)
            if key is not None:
                observed_values.setdefault(key, set()).add(value)
        conflicts = {key for key, values in observed_values.items() if len(values) > 1}
        content_refs = {}
        for row in current:
            content_ref = row["normalized"].get("document", {}).get("content_ref")
            if content_ref:
                content_refs.setdefault(content_ref, set()).add(row["resource_id"])
        duplicates = {key for key, identifiers in content_refs.items() if len(identifiers) > 1}
        filtered = [row for row in rows if
            (filters.history or row["id"] not in superseded)
            and (not filters.kind or row["kind"] == filters.kind)
            and (not filters.status or row["status"] == filters.status)
            and (not filters.start or row["clinical_time"] and row["clinical_time"] >= stamp(filters.start))
            and (not filters.end or row["clinical_time"] and row["clinical_time"] <= stamp(filters.end))]
        filtered.sort(key=lambda row: (row["clinical_time"] or "", row["id"]), reverse=True)
        return filtered, superseded, available, conflicts, duplicates

    @staticmethod
    def observed_value(row):
        record = row["resource"]
        if row["kind"] != "Observation" or not row["clinical_time"] or row["status"] != "final":
            return None, None
        codings = record.get("code", {}).get("coding", [])
        system_codes = tuple(sorted((value.get("system", ""), value.get("code", "")) for value in codings))
        value = record.get("valueString", record.get("valueQuantity"))
        return ((system_codes, row["clinical_time"]), digest(value)) if system_codes and value is not None else (None, None)

    def checked(self, row, available):
        record = row["resource"]
        subject = (record.get("subject") or {}).get("reference")
        patient = self.context.patient_id
        if (record.get("resourceType") != row["kind"] or record.get("id") != row["resource_id"]
                or (row["kind"] == "Patient" and record["id"] != patient)
                or (row["kind"] != "Patient" and subject != f"Patient/{patient}")
                or record.get("contained") or not set(references(record)) <= available):
            fail(409, "invalid_reference", "Stored evidence has invalid patient-local references.")
        if structure_errors(record) or digest(record) != row["digest"]:
            fail(409, "integrity_conflict", "Stored evidence failed structural or content-integrity checks.")

    def result(self, row, superseded, available, conflicts, duplicates, match=None):
        self.checked(row, available)
        ref = reference_key(row)
        record = row["resource"]
        normalized = dict(row["normalized"])
        if normalized.get("document", {}).get("content_ref") in duplicates:
            normalized["warnings"] = [*normalized["warnings"], "duplicate_document_content"]
        freshness = quality({**row, "normalized": normalized}, row["id"] in superseded,
                            self.observed_value(row)[0] in conflicts, self.policy)
        normalized["values"] = {key: value for key, value in record.items() if key.startswith("value")
                                and freshness["state"] != "unavailable"}
        event_id = self.connection.execute(select(receipts.c.event_id).where(
            receipts.c.evidence_id == row["id"]).order_by(receipts.c.received, receipts.c.event_id).limit(1)).scalar_one_or_none()
        obligation_ids = []
        if row["source"] == "workflow":
            recorded = select(db.closures.c.obligation_id).where(db.closures.c.evidence_id == row["resource_id"])
            obligation_ids = sorted(self.connection.execute(select(db.obligations.c.id).where(
                db.obligations.c.patient_id == self.context.patient_id, or_(
                    db.obligations.c.source_id == row["resource_id"], db.obligations.c.id.in_(recorded)))).scalars())
        if match:
            _, parts = extract_document(record)
            position = match["position"]
            if not 0 <= position < len(parts) or parts[position] != (match["section"], match["body"]):
                fail(409, "integrity_conflict", "Document excerpt does not match its source attachment.")
        options = {"method": "document", "content": match["body"], "section": match["section"],
                   "position": match["position"], "score": match.get("score")} if match else {}
        return EvidenceResult(
            **{key: row[key] for key in ("id", "patient_id", "source", "kind", "resource_id", "version",
                "event_time", "clinical_time", "received", "status", "digest", "supersedes")},
            normalized=normalized, quality=freshness, related_obligation_ids=obligation_ids,
            citation=f"{row['source']} / {ref} / version {row['version']}",
            provenance={"resource_reference": ref, "authorization_role": row["actor"],
                        "source_system": row["source"], "scope": row["scope"], "evidence_id": row["id"],
                        "content_trust": "untrusted_data", "event_id": event_id,
                        "patient_local_references": sorted(set(references(record)))}, **options)

    def list(self, filters, raw=False):
        rows, *context = self.prepare(filters)
        page = paginate(rows, filters)
        items = [self.result(row, *context) for row in page["items"]]
        audit_access(self.connection, self.context, "resource_list" if raw else "evidence_list", page["outcome"])
        if raw:
            return ResourcePage(**{**page, "items": [
                ResourceResult(evidence=result, resource=row["resource"] if result.quality["state"] != "unavailable" else None)
                for row, result in zip(page["items"], items)]})
        return EvidencePage(**{**page, "items": items})

    def get(self, *, evidence_id=None, kind=None, resource_id=None, version=None):
        rows, superseded, available, conflicts, duplicates = self.prepare(Filters(kind=kind, history=True))
        candidates = [row for row in rows if (row["id"] == evidence_id if evidence_id else
            row["resource_id"] == resource_id and (row["version"] == version if version else row["id"] not in superseded))]
        if len(candidates) != 1:
            fail(404, "evidence_not_found", "Evidence is not available in this scope.")
        row = candidates[0]
        result = self.result(row, superseded, available, conflicts, duplicates)
        audit_access(self.connection, self.context, "evidence_read")
        return ResourceResult(evidence=result, resource=row["resource"] if result.quality["state"] != "unavailable" else None)

    def search(self, search: Search):
        rows, *context = self.prepare(search)
        selected = []
        if search.mode in {"structured", "hybrid"}:
            terms = re.findall(r"[\w-]+", search.query.casefold())
            selected.extend((row, None) for row in rows if row["kind"] != "DocumentReference" and all(
                term in digestible_structure(row) for term in terms))
        if search.mode in {"document", "hybrid"}:
            documents = {row["id"]: row for row in rows if row["kind"] == "DocumentReference" and
                         row["status"] not in {"invalidated", "entered-in-error", "cancelled"}}
            matches = self.provider.document_matches(list(documents), search.query, search.offset + search.limit + 1)
            selected.extend((documents[match["evidence_id"]], match) for match in matches)
        page = paginate(selected, search)
        audit_access(self.connection, self.context, "clinical_search", page["outcome"])
        return EvidencePage(**{**page, "items": [self.result(row, *context, match) for row, match in page["items"]]})


def digestible_structure(row):
    import json
    return json.dumps({key: value for key, value in row["resource"].items()
                       if key in {"resourceType", "id", "code", "status"} or key.startswith("value")},
                      ensure_ascii=False).casefold()
