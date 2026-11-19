"""Specialist claims are checked against original retrieved sources, never another agent's prose."""
import json
import re
from app.investigation import grounding
from app.multi.contracts import ReconciliationDraft, ContextDraft, GapDraft

def validate_output(output, evidence, decision, trusted):
    sources = {x["id"]: x for x in evidence}
    serialization_adjustments = 0
    for finding in output.findings:
        for support in finding.supporting_sources:
            source = sources.get(support.evidence_id)
            values = (source or {}).get("normalized", {}).get("values", {})
            actual = values.get(support.value_key)
            if support.value_key and isinstance(actual, str) and support.value_json == actual:
                # Exact source-string equality permits only a representation repair, never a value change.
                support.value_json = json.dumps(actual)
                serialization_adjustments += 1
    # Withhold metadata-only prose; it cannot establish a clinical fact. Other claims still face full validation.
    supported = [f for f in output.findings if any(s.excerpt or s.value_key for s in f.supporting_sources)
                 or not f.supporting_sources
                 or any(s.evidence_id not in sources or sources[s.evidence_id]["version"] != s.version for s in f.supporting_sources)]
    withheld = len(output.findings) - len(supported)
    output.findings = supported
    if withheld:
        output.uncertainty = [*output.uncertainty[:11], "Metadata-only finding(s) withheld: " + str(withheld)]
        if not supported:
            output.abstained = True
    checks = grounding.validate(output, evidence)
    errors = list(checks["errors"])
    text = " ".join([output.summary, *output.recommended_review_actions, *output.uncertainty,
                     *output.missing_information, *output.conflicting_evidence,
                     *getattr(output, "unresolved_questions", []),
                     *getattr(output, "unresolved_discrepancies", []),
                     *(x.statement for x in output.findings)])
    if re.search(r"\b(within\s+\d+|tomorrow|urgently|urgent|asap|by\s+20\d\d-\d\d-\d\d|start medication|prescrib\w*|diagnos\w*)\b", text, re.I):
        errors.append("unsupported_clinical_or_timing_advice")
    if isinstance(output, ReconciliationDraft):
        conflict = {x["id"] for x in evidence if x["quality"]["state"] == "conflicting"}
        if set(output.conflicting_records) != conflict:
            errors.append("conflict_inventory_mismatch")
        for identifier in output.corrected_records:
            if identifier not in sources or not sources[identifier].get("supersedes"):
                errors.append("correction_lineage_mismatch")
        expected = {(x["supersedes"], x["id"]) for x in evidence if x.get("supersedes") and x["supersedes"] in sources}
        if {(x.previous_id, x.current_id) for x in output.supersession_relationships} != expected:
            errors.append("supersession_lineage_mismatch")
    if isinstance(output, ContextDraft):
        for event in output.timeline_events:
            if event.evidence_id not in sources or event.clinical_time != sources[event.evidence_id]["clinical_time"]:
                errors.append("chronology_mismatch")
        if not set(output.linked_obligations) <= {x["id"] for x in trusted["obligations"]}:
            errors.append("obligation_scope_mismatch")
        if not set(output.life_stage_transition_refs) <= {x["id"] for x in trusted["life_stage_events"]}:
            errors.append("life_stage_scope_mismatch")
    if isinstance(output, GapDraft):
        expected = {x["id"]: x for x in decision["prerequisites"]}
        if {x.prerequisite_id for x in output.prerequisites} != set(expected):
            errors.append("prerequisite_inventory_mismatch")
        for fact in output.prerequisites:
            actual = expected.get(fact.prerequisite_id)
            if not actual or fact.status != actual["status"] or set(fact.evidence_ids) != set(actual["source_refs"]):
                errors.append("prerequisite_state_mismatch")
        if any(x["status"] != "available_for_review" for x in expected.values()) and not output.abstained:
            errors.append("unresolved_prerequisite_not_abstained")
    if isinstance(output, ContextDraft):
        times = [x.clinical_time for x in output.timeline_events]
        if times != sorted(times):
            errors.append("chronology_order_mismatch")
    return {**checks, "serialization_adjustments": serialization_adjustments, "withheld_metadata_findings": withheld, "errors": sorted(set(errors)),
            "status": "validation_failed" if errors else checks["status"]}
