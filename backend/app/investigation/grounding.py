"""Deterministic source checks. Narrative inference always requires human interpretation."""
import json
import re

from app.investigation.contracts import ClinicalEvidenceReviewPacket, Source
from app.clinical.normalize import digest


def validate(draft, snapshots):
    from app.history_guard import risk_errors
    errors = list(risk_errors(draft))
    interpretation = False
    source_map = {item["id"]: item for item in snapshots}
    cited = set()
    for finding in draft.findings:
        if not finding.supporting_sources:
            errors.append("missing_citation")
        for support in finding.supporting_sources:
            source = source_map.get(support.evidence_id)
            if source is None:
                errors.append("unknown_citation")
                continue
            cited.add(source["id"])
            if source["version"] != support.version:
                errors.append("version_mismatch")
            if source["quality"]["state"] == "unavailable":
                errors.append("unavailable_source")
            if support.excerpt and support.excerpt not in (source.get("content") or ""):
                errors.append("excerpt_mismatch")
            if support.value_key:
                values = source["normalized"].get("values", {})
                try:
                    claimed = json.loads(support.value_json)
                    if support.value_key not in values or digest(claimed) != digest(values[support.value_key]):
                        errors.append("structured_value_mismatch")
                except ValueError:
                    errors.append("structured_value_mismatch")
            elif support.value_json:
                errors.append("value_key_missing")
            if not support.excerpt and not support.value_key:
                interpretation = True
            if source["quality"]["state"] == "superseded" and finding.evidence_status != "historical":
                errors.append("historical_status_missing")
            exact = finding.statement == support.excerpt and bool(support.excerpt)
            if support.value_key and support.value_key in source["normalized"].get("values", {}):
                exact = exact or finding.statement == str(source["normalized"]["values"][support.value_key])
            if finding.requires_clinical_interpretation or not exact:
                interpretation = True
                finding.requires_clinical_interpretation = True
    conflict_ids = [item["id"] for item in snapshots if item["quality"]["state"] == "conflicting"]
    if conflict_ids and (not draft.conflicting_evidence or not draft.abstained):
        errors.append("conflict_not_acknowledged")
    if draft.scope == "outside_scope" and not draft.abstained:
        errors.append("scope_not_abstained")
    if not draft.findings and not draft.abstained:
        errors.append("unsupported_summary")
    narrative = " ".join([draft.summary, *draft.recommended_review_actions,
                          *(finding.statement for finding in draft.findings
                            if finding.requires_clinical_interpretation)])
    unsafe = (r"\b(diagnos(?:e|ed|is)|prescrib\w*|increase (?:the )?dose|start medication|clinically verified)\b"
              r"|\bobligation\s+(?:(?:is|was)\s+)?(?:complete|closed)\b")
    if re.search(unsafe, narrative, re.IGNORECASE):
        errors.append("clinical_scope_violation")
    if errors:
        status = "validation_failed"
    elif conflict_ids:
        status = "conflicting_evidence"
    elif not snapshots or draft.abstained:
        status = "insufficient_evidence"
    else:
        # Free narrative summary, missing-information claims and review actions remain unverified.
        status = "partially_grounded"
    return {"status": status, "errors": sorted(set(errors)),
            "claim_checks": "Exact excerpts and structured values checked. Narrative requires human review.",
            "interpretation_required": interpretation, "conflicting_evidence_ids": conflict_ids,
            "cited_ids": sorted(cited)}


def packet(run, draft, snapshots, validation, error=None):
    failed = error or validation["errors"]
    safe = draft is not None and not failed
    uncertainty = list(draft.uncertainty) if safe else []
    uncertainty.append("Narrative claims require clinical review. Accessible records may be incomplete.")
    if error:
        uncertainty.append(error)
    if validation["errors"]:
        uncertainty.append("Grounding checks rejected the generated output.")
    return ClinicalEvidenceReviewPacket(
        run_id=run["id"], patient_id=run["patient_id"], clinical_question=run["detail"]["question"],
        summary=draft.summary if safe else "The investigation abstained. Review the evidence and run status.",
        findings=draft.findings if safe else [],
        missing_information=draft.missing_information if safe else [],
        conflicting_evidence=draft.conflicting_evidence if safe else validation.get("conflicting_evidence_ids", []),
        uncertainty=uncertainty,
        recommended_review_actions=draft.recommended_review_actions if safe else ["Inspect source records and reconcile with a clinician."],
        source_references=[Source(evidence_id=item["id"], version=item["version"], digest=item["digest"],
                                 citation=item["citation"], quality_state=item["quality"]["state"])
                           for item in {row["id"]: row for row in snapshots}.values()],
        earlier_record_context=((run["detail"].get("window_context") or {}).get("history")),
        prevention_window=(run["detail"].get("window_context") or {}).get("result"),
        grounding_status=validation["status"], requires_human_review=True,
        abstained=not safe or draft.abstained, origin="model" if safe else "system_abstention",
        model_name=run["detail"]["configuration"]["model"], created_at=run["created"])
