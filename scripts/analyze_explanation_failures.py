"""Read-only analysis of the five preserved hardening investigations."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CASES=[("tsp-amira","initial"),("history-amira","initial"),("tsp-uncertain","initial"),("tsp-amira","repeat"),("history-amira","repeat")]

def analyze():
    result=[]
    for case,attempt in CASES:
        folder=ROOT/"backend/demo-replays"/("hardening-v1-repeat" if attempt=="repeat" else "")
        row=json.loads((folder/(case+"-result.json")).read_text(encoding="utf-8"))
        source=("history-" if case.startswith("history") else "tsp-")+("demo-tsp-uncertain" if case.endswith("uncertain") else "demo-amira")
        record=json.loads((folder/(source+".json")).read_text(encoding="utf-8"))
        item={"case":case,"attempt":attempt,"error":row["error"],"validation":row["grounding"],"model_calls":row["usage"]["model_calls"],"tool_calls_executed":row["tool_count"],"reported_usage":row["usage"]}
        if row["error"]=="tool_budget_exhausted":
            item["exact_cause"]="Nine tool calls requested; eight executed. authorized_tools rejects the ninth and routes to grounding without a final Draft (finalize_on_budget is false)."
        elif row["error"]=="incomplete_response":
            item["exact_cause"]="Responses SDK adapter rejected a provider response whose status was not completed; no final Draft accepted."
            item["last_output_tokens"]=row["model_history"][-1]["output_tokens"]
            item["configured_output_cap"]=2400
            item["evidence_limit"]="Original incomplete_details and reasoning-token split were not recorded. Near-cap output suggests token exhaustion, but the exact upstream incomplete reason cannot be proved from these stored fields."
        else:
            draft=record["frames"][-1]["turn"]["draft"]
            expected=record["context_descriptor"]["context"]["window"]["allowed_explanation"]
            item["summary_matches_server"]=draft["summary"]==expected
            item["exact_cause"]="Summary matches. Additional narrative contains dates and window W1 outside the exact allowed explanation/literal structured value, so the original window guard rejects it."
            item["offending_fields"]={"findings":[f["statement"] for f in draft["findings"]],"missing_information":draft["missing_information"],"recommended_review_actions":draft["recommended_review_actions"]}
        result.append(item)
    return result
if __name__=="__main__":print(json.dumps(analyze(),indent=2))
