from operator import add
from typing import Annotated, TypedDict
from langgraph.graph import END, START, StateGraph
from app.rules import code_matches, matches


class Resolution(TypedDict, total=False):
    authorized_records: list[dict]
    closure_code: str
    source_qualified: bool
    proposal_context: str
    evidence_refs: list[str]
    finding: str
    action: str
    route: str
    trace: Annotated[list[str], add]


def retrieve(state: Resolution):
    return {"evidence_refs": [f"{record['resourceType']}/{record['id']}" for record in state["authorized_records"]], "trace": ["retrieve"]}


def reconcile(state: Resolution):
    candidates = [record for record in state["authorized_records"] if code_matches(record, state["closure_code"])]
    if not state["source_qualified"] or any(not matches(record, state["closure_code"], "verified")
                                            for record in candidates):
        return {"finding": "conflicting_or_unqualified_evidence", "trace": ["reconcile"]}
    return {"finding": "evidence_available" if candidates else "missing_closure_evidence", "trace": ["reconcile"]}


def prepare(state: Resolution):
    actions = {
        "conflicting_or_unqualified_evidence": "Ask the demo reviewer to reconcile conflicting or unqualified records.",
        "missing_closure_evidence": "Ask the demo coordinator to obtain a synthetic follow-up completion record.",
        "evidence_available": "Ask the demo reviewer to verify the submitted completion record.",
    }
    action = actions[state["finding"]]
    if context := state.get("proposal_context"):
        action = f"{context} {action}"
    return {"action": action, "trace": ["prepare"]}


def route(_: Resolution):
    return {"route": "human_review", "trace": ["route"]}


workflow = StateGraph(Resolution)
NODES = (retrieve, reconcile, prepare, route)
for node in NODES:
    workflow.add_node(node.__name__, node)
workflow.add_edge(START, "retrieve")
workflow.add_edge("retrieve", "reconcile")
workflow.add_edge("reconcile", "prepare")
workflow.add_edge("prepare", "route")
workflow.add_edge("route", END)
graph = workflow.compile()
