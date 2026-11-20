# Accepted single-call synthetic explanation recordings

These two successful live Responses calls used the explicitly selected key-visible strongest model, with no tools, no retries and one model request per explanation. Every returned field matched the authoritative server packet exactly and the original source/window/history grounding checks passed. Text is rendered by the server from validated fields; it is not generated prose or a clinical approval.

The model was selected explicitly through EXPLANATION_MODEL. Both requested and provider-reported model IDs, response IDs, actual token usage, latency and original validation are retained. Keys, role tokens and headers are excluded; both files passed local-secret scanning before inclusion.

Replay revalidates the exact current source references, versions, digests, excerpts, calculator fields and policy/rule identifiers. It runs the original graph and grounding again, with zero live model calls. Unavailable or changed context causes a logged abstention and a separately labelled authoritative rule fallback when context remains fresh. There is no successful-recording substitution for a failed response.

The five older failed hardening investigations remain preserved in their original directories and tag; they are not used by this explanation replay path. No accepted uncertain-dating live capture is claimed: the demo intentionally shows its labelled rule fallback without spending another live call.
