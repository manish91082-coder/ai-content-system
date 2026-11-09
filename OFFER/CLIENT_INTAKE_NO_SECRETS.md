# Client Intake — AI Pipeline Reliability Repair

**Do not send API keys, passwords, OAuth refresh tokens, private keys, recovery codes, or personal customer data.**

Please provide only the following non-secret information:

1. Repository URL, or a controlled collaborator invitation with the minimum permissions required.
2. Workflow file path or exported workflow with secrets removed.
3. What should happen when the workflow runs.
4. What actually happens.
5. Approximate time and run identifier of the failure.
6. Sanitized error log with tokens, emails, IDs, customer data and URLs containing credentials removed.
7. Provider names and model IDs (not credentials).
8. Environment variable names used by the application (never their values).
9. Whether a safe test account/test dataset exists.
10. Whether the requested change is limited to a branch/PR or whether production deployment is separately requested.

## Access rules

- Prefer public repository read access or a temporary least-privilege collaborator role.
- Do not request owner/admin access unless a specific documented operation requires it.
- Customer creates and controls all provider secrets.
- Customer performs OAuth consent and KYC in official provider interfaces.
- All tests must avoid sending real messages, publishing posts, charging payments, or modifying production records.
- Production actions require explicit written approval after test evidence is reviewed.
- Remove temporary access after delivery where the platform allows it.
