# Hackathon demonstration

Start with Amira Haddad at preconception with one open obligation. On an empty demo database, sign in with the coordinator token and select **Load demo patient**. Keep the separate reviewer token available locally.

1. Open Amira’s workspace. Show the preconception event and the synthetic follow-up flag. Open the obligation passport and identify its owner, source Observation, and illustrative rule version.
2. Register pregnancy from the workspace. Return to the same passport and show the preserved obligation ID and typed dependency on the pregnancy obligation.
3. Run the care-resolution agent. In the care-resolution center, show the missing-evidence finding and the proposal to obtain completion evidence.
4. Sign out and sign in as reviewer. Approve the coordination proposal. Return as coordinator and select **Verify closure**. The service records a blocked attempt because there is no qualifying completion evidence.
5. In **Evidence & audit**, choose the preconception obligation and add verified synthetic evidence. Try closure again to show that the earlier coordination approval is insufficient.
6. Open the passport and run the agent again. Show **Evidence available** in the care-resolution center. Sign in as reviewer and approve the new proposal against its evidence. Reject and Request additional evidence are alternate paths that leave the obligation open.
7. Sign back in as coordinator. Verify closure from the passport. Inspect the blocked and verified decisions, their actors, timestamps, rule versions, and evidence references under **Evidence & audit**. Download Amira’s FHIR R4 bundle.
8. For the conflict branch, choose the pregnancy obligation and add verified and conflicting evidence. Try closure and show that the conflict leaves it open.

Run `& .\scripts\Test-Demo.ps1 -PostgreSQL` from the repository root for two complete Edge journeys. Each run creates and migrates a fresh PostgreSQL schema, reseeds Amira through the application, independently validates its downloaded bundle, and removes only its disposable schema. For a repeated manual walkthrough, select a separate empty demo database in the local configuration and migrate it. Keep the original database for its lifecycle history.
