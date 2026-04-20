# Potential Pitfalls and How to Avoid Them

## 1) Memory Poisoning

If an LLM stores incorrect or prompt-injected content, later sessions may treat it as truth.

Mitigation:

- Keep `importance` low by default and pin only vetted memories.
- Require manual review for critical memories.
- Add metadata fields like `verified_by` and `verified_at`.

## 2) Context Bloat

Too many low-value memories degrade retrieval quality and token efficiency.

Mitigation:

- Keep pull profiles tight.
- Use tags and source filters.
- Archive or delete stale entries regularly.

## 3) Cross-Model Drift

Different LLMs may phrase or interpret facts differently, causing inconsistent memory writes.

Mitigation:

- Normalize memory schema (`title`, `body`, `tags`, `metadata`).
- Use source-specific tags and periodic cleanup.

## 4) Key Sprawl and Leakage

Many integrations mean many keys, increasing operational risk.

Mitigation:

- One key per tool/environment.
- Rotate on schedule.
- Revoke on any suspicion.

## 5) Overexposed Share Links

Long-lived or unprotected links can leak sensitive files.

Mitigation:

- Always set expiry.
- Add password for sensitive files.
- Use low max-download limits.
- Disable links post-use.

## 6) NotebookLM Capability Mismatch

NotebookLM may not support direct API write-back in your exact workflow.

Mitigation:

- Use periodic export/import pattern.
- Keep a manual fallback ingestion path.

## 7) Backup Gaps

Without routine backups and restore tests, one incident can wipe all shared memory.

Mitigation:

- Automate backups.
- Test restoration in staging.
- Keep encrypted offsite copies.

## 8) Compliance and Privacy Oversight

Memories can include sensitive user/client data that may need legal handling controls.

Mitigation:

- Define allowed data classes.
- Avoid storing secrets when possible.
- Encrypt storage and constrain access.
