# Deterministic timing policy

Amira's prevention decision has no clinical deadline. It displays **Timing not established.**

No approved clinical timing rule was present in the baseline. Increment 1 therefore accepts explicitly illustrative policies only. The policy API requires illustrative=true. The stored source states that it has no clinical timing approval.

## Stored policy

A policy has a unique ID, immutable version, source, actor, creation time, lifecycle state and definition. The definition contains an offset-aware due_at, due_soon_seconds and illustrative marker. A new policy version needs a new ID. Existing definitions cannot be overwritten.

| Condition | Result |
|---|---|
| No policy | not_established |
| Retired or superseded policy | not_established |
| Active deadline beyond the configured threshold | scheduled |
| Active deadline at or inside the threshold | due_soon |
| Current server time strictly after deadline | overdue |

At the deadline instant the result is due_soon. Evaluation uses server UTC and accepts an explicit clock for deterministic tests. Due dates are never derived from LLM text.

Source/life-stage changes refresh decision snapshots. Policy assignment, retirement and supersession also refresh snapshots and invalidate an in-progress review. The policy version and source remain attached to the decision and immutable reviewer record.

## Separate illustrative scenario

The explicit Load illustrative timing scenario action creates demo-prevention-timing, separate from Amira. Two decisions use policies created with a deadline one hour after first load and one hour before first load, with a two-hour due-soon display window. These values demonstrate software states and have no clinical authority.

The scenario is idempotent. Its deadlines continue to age normally after first load. A future policy version can be created and assigned through the policy API. Amira reset preserves this unrelated scenario.

The dashboard's due-soon and overdue counts are calculated from authorized active decisions. No client or model supplies urgency counts, and no timing policy is silently assigned to Amira.
