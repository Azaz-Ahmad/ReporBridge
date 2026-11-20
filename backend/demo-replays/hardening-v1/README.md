# Real synthetic provider captures

These three cassettes contain actual Responses API model/tool turns for canonical synthetic demo patients. Their companion result files retain measured latency, token usage, grounding and errors. Credentials, role tokens, request headers and opaque encrypted reasoning are excluded; files were scanned against the local secrets before inclusion.

They are **real rejected/abstained runs**, not successful explanations: TSP Amira failed `tsp_window_or_policy_mismatch`; historical Amira and uncertain dating ended at `incomplete_response`. Replay reproduces these outcomes with real authorized local tools and unchanged grounding. Do not call this an accepted live or replay explanation.

Both Amira captures are the single explicitly approved repeat; the original attempts remain preserved in ignored local `backend/demo-replays/` and test reports. The uncertain capture is its first/only live attempt. No model was switched. The recorded provider-reported model alias differs from the explicitly requested dated ID; both are retained as metadata.

To replay, explicitly select `LLM_MODE=replay`, enable the synthetic demo/agent, and set `OPENAI_MODEL` to the requested model recorded here. Selection is never automatic. A different model, source, quality, policy or demo date is refused. Equal-date pagination compatibility requires matching the original request hash against the exact fully matched source snapshot; it never injects recorded tool results into grounding.

`context_descriptor.guard_sources` preserves the guard/prompt source used to fingerprint the request; these strings are data and are never executed. New real recordings require an explicitly new output directory; do not overwrite this evidence.
