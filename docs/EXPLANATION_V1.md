# Bounded explanation path

The user-facing TSP/history buttons use `/api/v1/tsp/patients/{id}/explanations` and `/api/v1/history-handoff/patients/{id}/explanations`. Legacy `/investigations` endpoints remain for the original bounded evidence agent and its regression coverage.

The server authorizes the patient, prepares calculator output plus versioned/digested source excerpts, and calls Responses once with no tools and a bounded closed JSON schema. Every field is compared exactly, including source/date/status/version/policy/citation/numeric and boolean values. Unknown/free-form fields are forbidden. The server creates literal source findings and renders the text; the original six-node graph, window/history grounding, source freshness and human-review/closure gates still run unchanged. No agent computes clinical timing, eligibility, relevance or closure.

If the agent declines, fails, or differs from any expected field, the packet remains an abstention with its original error/trace. The separate authoritative fallback is labelled **Rule-generated explanation (agent abstained)**. It is not agent output, cannot approve or close work, and is withheld if the source/window context became stale.

## Explicit configuration

- `EXPLANATION_MODEL`: exact allowed model; blank reuses `OPENAI_MODEL`. The generic evidence agent's model is unchanged. This task explicitly selects the strongest key-visible model by the provider's reported intelligence index.
- `EXPLANATION_MAX_OUTPUT_TOKENS=6000`, `EXPLANATION_TIMEOUT_SECONDS=60`, `EXPLANATION_REASONING_EFFORT=low`. Input/output fields have strict size/list bounds; there is no generated prose or iterative tool budget. Only one network attempt per request.
- `LLM_MODE=live|replay` applies explicitly. `EXPLANATION_REPLAY_DIR` defaults to `backend/demo-replays/explanation-v1`. `EXPLANATION_RECORD_DIR` is optional for deliberately recording accepted live calls only.

`python scripts/record_explanations.py` records two real calls against the local authorized synthetic demo, preparing/resetting fixtures through the existing guarded APIs. It refuses overwrite and exports only successful fields as replay files; failures are retained as diagnostics. Restart explicitly in replay mode and use `--replay-check` to validate those same source/version contexts without a model call. The shared key and role tokens remain in ignored `.env`; no credentials are recorded.

Current source versions, status, digest, excerpts, deterministic window fields and policy/hash must match the accepted recording exactly. Extra unrelated source records do not cause rejection because the model is given only the authoritative cited projection; all selected-source grounding and mid-run whole-patient freshness checks remain unchanged. No old failed hardening response is used as a successful replay.
