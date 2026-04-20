# Integrating LLMMM with Your LLM Stack

This guide focuses on practical integration paths for:

- ChatGPT
- Codex
- Google Gemini
- Claude
- NotebookLM

## Recommended Shared Pattern

For each tool:

1. Create a dedicated API key in `/keys`.
2. On session start, call `GET /api/v1/context/pull?profile=default`.
3. When a durable preference/fact appears, call `POST /api/v1/memories`.
4. For long references (PDF/DOCX), use LLMMM share links.

This gives you lightweight periodic reference plus easy write-back.

## Easy Memory Ingestion Options

### Option A: API call (best)

Use `POST /api/v1/memories` with a tool-specific API key.

### Option B: Web UI inbox

Paste memory manually in `/` when an LLM cannot make API calls.

### Option C: CLI helper

Use `scripts/llmmm_push.sh` from terminals, cron jobs, or wrappers.

## ChatGPT

### Practical path

- Use a custom GPT action (OpenAPI import from your LLMMM endpoint).
- Configure API-key auth in the action.
- Add two actions:
  - `pull_context`
  - `save_memory`

### Prompt policy snippet

"At conversation start, call LLMMM context pull. When the user states a durable preference or reusable fact, call save_memory."

## Codex

### Practical path

- Add shell aliases or scripts around `scripts/llmmm_push.sh` and `scripts/llmmm_pull.sh`.
- Optionally load pull context into your local workflow before each coding session.

Example:

```bash
./scripts/llmmm_pull.sh "$LLMMM_URL" "$CODEX_KEY" default
```

## Google Gemini

### Practical path

Gemini integration depends on which product variant you use.

- If your Gemini environment supports external tool calls/webhooks: call LLMMM API directly.
- Otherwise: use a tiny wrapper (Apps Script/Cloud Function/local script) to push/pull memory.

Minimum workflow:

- Pull context from LLMMM before opening Gemini session.
- Paste context block into system instructions.
- Push durable output back via wrapper script.

## Claude

### Practical path

- If your Claude setup supports MCP/tooling, map LLMMM endpoints as tools.
- Otherwise use the same wrapper/script pattern as Gemini.

Recommended:

- Pull LLMMM context at session start.
- Save final decisions/constraints into LLMMM at session end.

## NotebookLM

NotebookLM typically behaves differently than tool-calling chat models.

Best practice:

- Use LLMMM share links for source files.
- Use LLMMM exports (`jsonl`/`csv`) to maintain memory snapshots outside NotebookLM.
- Manual copy/paste may still be required for memory sync depending on NotebookLM capabilities in your environment.

## Periodic Memory Reference Strategies

### Session-start pull (simple)

Call `GET /api/v1/context/pull?profile=default` at the beginning of each chat.

### Time-based pull (automation)

Run periodic pull in cron and attach summary to your LLM launcher prompt.

### Profile-based pull (advanced)

Define multiple pull profiles:

- `default`
- `coding`
- `writing`
- `client-a`

Then call the profile that matches context.

## Suggested Memory Capture Heuristics

Capture only durable/high-signal information:

- User writing/style preferences
- Stable project constraints
- Reusable business rules
- Long-lived technical decisions

Avoid storing:

- One-off transient conversation filler
- Secrets unless strictly required and encrypted upstream
- Unverified claims
