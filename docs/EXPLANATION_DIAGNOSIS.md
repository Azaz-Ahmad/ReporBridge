# Preserved explanation failures

All five original live attempts and the hardening-v1 tag remain untouched. `scripts/analyze_explanation_failures.py` regenerates the exact read-only trace analysis in `test-reports/explanation/five-causes.json`.

| Case | Recorded cause |
|---|---|
| Initial TSP | Ninth requested tool call exceeds the eight-call budget; eight executed, no final Draft. |
| Initial history | Provider response was not completed on turn 3; adapter rejected it (`incomplete_response`), 2,393 output tokens on that turn. |
| Uncertain dating | Provider response was not completed on turn 6; adapter rejected it, 2,385 output tokens on that turn. |
| Repeat TSP | Summary exactly matches the server. Three narrative findings add source dates; missing-information/review text adds window W1. Those fields are outside the exact allowed summary/literal value and trigger `tsp_window_or_policy_mismatch`. |
| Repeat history | Provider response was not completed on turn 5; adapter rejected it, 2,393 output tokens on that turn. |

The incomplete calls approached the 2,400-token output cap. Their raw `incomplete_details` and reasoning-token split were not persisted; the precise upstream reason cannot honestly be inferred beyond the recorded non-completed response. The new path removes iterative tools/free narrative and bounds the model's fields instead of weakening that guard.

Read-only authenticated model discovery on this task returned the canonical permitted IDs `anthropic/claude-sonnet-5.5-20260928`, `google/gemini-3.8-flash-20260902`, `openai/gpt-6-luna-20260922`. The API's reported intelligence indices were 54.5, 30.8 and 27.9 respectively; Claude is selected explicitly for these explanations. This is a catalog ranking criterion, not a claim of clinical validation. Source: [OpenRouter model catalog](https://openrouter.ai/docs/api/api-reference/models/get-models). Private key/account fields were not saved.
