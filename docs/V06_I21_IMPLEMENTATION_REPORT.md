# Increment 2.1 implementation report

**GO for the local synthetic optimization release.** Mandatory safety, regression and live-model gates passed. Measured primary input-token and conflict-latency targets were met in the counterbalanced two-repetition sample; limitations below still apply.

Starting commit: da44aea61ea2bf5aabae621b5735ab42fef8f348. Ending commit is supplied in the delivery message and git log -1.

Root causes were unconditional context/gap specialists, repeated shared metadata and tool history, independent serial specialist calls and duplicate checkpoint reads/JSON writes. Historical measurements were verified against actual traces before implementation. Unrecorded historical model timing/context size was not invented.

Implemented selective routing, version-pinned immutable shared context, whole-section bounded excerpts, versioned reuse of identical model tool payloads, request-local source-pinned caching, provenance/quality reuse, bounded correction predecessor retrieval, task-specific specialist context, concise model instructions, independent parallel model reads, deterministic serial merge/persistence, per-agent/per-run accounting and clearer interrupted states. Strict output contracts, ownership/version/value/citation/lineage checks, deterministic timing, mandatory review and all clinical closure controls remain.

The same four agents and seven authoritative M08 tools are retained. The optimized supervisor uses eight nodes with a specialist-execution coordinator around the original six-node evidence graph. An explicit legacy profile preserves the previous ten-node implementation for rollback and matched evaluation; failures never select it automatically. Single-agent creation remains compatible. Provider/model selection and Responses transport are unchanged; no Chat Completions or additional agent was added.

No migration or new endpoint family is necessary. Alembic remains 0006. Existing run/review JSON stores sealed context manifests, routing, actual agent states, token/model/tool accounting, timing and validation. Progress persistence now performs one run read/update rather than two. Existing clinical synchronization/transaction serialization is preserved.

Controlled live means: complete 6→2 calls, 22,806.5→5,322 input tokens, 33.982→9.851 seconds; conflict 7→3, 27,490.5→8,877.5, 38.347→15.402; missing prerequisite 6→4, 20,116.5→9,170, 30.435→15.878. Aggregate input fell 66.8%; conflict latency fell 59.8%. A separate same-routing serial/parallel comparison improved elapsed time by 26.8%. Every one of the 16 controlled live runs passed source/structured-value/abstention/human-review gates. Dollar cost remains unavailable without configured reliable pricing.

Care-Resolution Center now shows a compact persisted execution summary, selected/skipped agents and reasons, actual calls/tokens/timing, grounding, abstention, mandatory review and pinned context. Expandable traces include per-agent accounting. All five screens and seven product innovations remain. Seven inspected screenshots are in docs/screenshots/v06-i21.

Verification: 182 Python tests on each database, 22 React tests, production build, two browser journeys and two FHIR validators passed. A separate retained real run is pending clinician summary review with conflicting evidence and unchanged clinical state. Source/authorization failures and partial specialist output remain fail-closed; no AI can approve clinical decisions or close obligations.

Known scope: synthetic-only prototype, small live sample, lexical longitudinal routing, bounded context that can omit large sections, synchronous non-resumable execution, possible transaction contention and no currency-cost estimator. Full details and actual measurements are in the accompanying evaluation, live, test and limitations reports.
