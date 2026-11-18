# Remaining limitations

## Release gate

Live OpenAI verification is BLOCKED. No API key was configured and the runtime agent remains disabled. Zero successful live model investigations were claimed. The LLM milestone is CONDITIONAL GO pending three real investigations and review of their tool selection, citations, missing evidence and conflicts.

## Supported scope

The LLM workflow is deliberately limited to canonical synthetic Amira. Requests require synthetic-only attestation and retrieved available resources require synthetic tags. Shared role tokens, application grants and exact demo identity claims support the local prototype. Production identity, individual clinician accounts, consent and organizational authorization are outside this sprint.

## Grounding

Exact quotes, JSON values, source versions, patient scope, integrity, conflicts and catalog changes are checked. Narrative entailment remains a human responsibility. The lexical clinical-scope screen is a bounded supplementary defense. It can overreject harmless wording and miss semantic paraphrases.

The agent sees bounded search pages. It must report retrieval limits and missing accessible evidence without inferring absent care. Current narrative packets receive partially_grounded at best. Source freshness follows existing M08 policy behavior without introducing clinical age thresholds.

## Operations

Runs execute synchronously within bounded server requests. Checkpoints survive failures and stale runs become interrupted on read. Automatic background recovery and distributed job scheduling are deferred. A new explicit request ID is needed after an interrupted run. An unknown remote completion can have consumed tokens.

Token usage is provider-reported when available. Error or timeout usage may be incomplete. Dollar estimates are unavailable. A configured dollar ceiling disables execution. store=False disables response storage for this API invocation, while provider-side data handling still follows the configured account and applicable API terms.

Raw prompts and documents are excluded from default traces. The persisted clinical question and bounded finding excerpts are necessary for review and still require protected storage. Summary review is one immutable decision per run.

## Carried-forward M08 limits

The local catalog remains suitable for small synthetic datasets. Inline text and Markdown are supported. OCR, PDF extraction, remote clinical systems, full FHIR profile/terminology validation and a production outbox dispatcher remain deferred.
