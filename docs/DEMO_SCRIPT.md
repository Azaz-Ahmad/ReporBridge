# Hackathon demonstration

Use the preconception fixture with one open obligation and no pregnancy event. On an empty database, sign in as coordinator and select **Load demo patient**. Keep the coordinator and reviewer tokens available locally.

1. Open Amira Haddad’s workspace. Show the final synthetic follow-up flag. Open the preconception passport and identify the owner, source, and illustrative rule version.
2. Return to the workspace and select **Register pregnancy**. Open the preconception passport again. Show the same obligation ID and the configured edge to pregnancy coordination.
3. Select **Verify closure** without completion evidence. Show the blocked response, then select **Run care-resolution agent**. Open the care-resolution center and show the missing-evidence finding and queued coordination action.
4. Open **Evidence & audit**. Choose the preconception obligation and select **Add verified evidence**.
5. Sign out and sign in with the reviewer token. Open the care-resolution center, read the current evidence, and select **Approve**. Reject and Request additional evidence are alternate paths that keep the obligation open.
6. Sign back in as coordinator. Select the preconception passport and choose **Verify closure**. Show the closed status and then open **Evidence & audit**. Show both closure outcomes, the actor and time, evidence references, and rule version. Download the FHIR bundle.
7. To show contradictory evidence separately, select the open pregnancy obligation in **Evidence & audit**. Add verified and conflicting evidence, then attempt closure from its passport. The records remain visible and the closure attempt is blocked.

For repeated demos, point `DATABASE_URL` at a new empty database, apply migrations, and reload the fixture. The original database retains its lifecycle and audit records.
