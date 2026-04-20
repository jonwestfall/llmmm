# Getting Started: Capturing Useful Memories for LLMMM

This guide helps you prompt LLMs to produce high-value memories in JSON so you can store them in LLMMM with minimal cleanup.

## What Belongs in LLMMM

Store durable information that improves future sessions:

- Stable preferences (tone, formatting, coding style)
- Reusable constraints (tech stack limits, compliance rules)
- Project conventions (naming rules, release process)
- Recurring context (client preferences, audience expectations)

Do not store low-value noise:

- One-off chat chatter
- Temporary guesses
- Secrets unless absolutely required

## Recommended Memory JSON Shape

Use this target shape for each memory object:

```json
{
  "title": "Short memory title",
  "body": "Durable instruction or fact in plain language.",
  "tags": ["style", "coding"],
  "source_model": "chatgpt",
  "importance": 4,
  "pinned": false,
  "metadata": {
    "project": "alpha",
    "confidence": "high"
  }
}
```

Compatible with:

- `POST /api/v1/memories` (single object)
- `POST /api/v1/memories/bulk-import` (array of objects)

## Prompt Pattern That Produces Clean JSON

Use this base instruction with any LLM:

```text
Extract durable memories from the conversation.
Only include facts or preferences likely to be useful in future sessions.
Return ONLY valid JSON (no markdown, no commentary).
Return an array of objects using this schema:
[
  {
    "title": string,
    "body": string,
    "tags": string[],
    "source_model": string,
    "importance": 1-5,
    "pinned": boolean,
    "metadata": object
  }
]
```

Tip: include `If no durable memories are found, return []` to avoid junk entries.

## Scenarios + Example Prompts

### Scenario 1: Writing and Tone Preferences

Use when the user defines writing style or brand voice.

Prompt:

```text
From the text below, extract durable writing preferences that should be remembered for future content generation.
Ignore temporary requests.
Set tags from ["writing", "tone", "audience", "formatting"].
Set importance=5 for strict rules, otherwise 3-4.
Return ONLY valid JSON array.
If nothing durable exists, return [].

SOURCE_TEXT:
{{paste conversation or notes}}
```

### Scenario 2: Coding Standards and Team Practices

Use when discussing architecture/coding conventions.

Prompt:

```text
Identify stable engineering preferences and constraints from this discussion.
Keep only durable guidance that should influence future code sessions.
Use tags from ["coding", "testing", "architecture", "devops"].
Each memory body should be explicit and actionable.
Return ONLY valid JSON array matching the schema.

SOURCE_TEXT:
{{paste conversation or PR summary}}
```

### Scenario 3: Client Profile Memory Pack

Use for agencies/consulting where each client has recurring preferences.

Prompt:

```text
Create LLMMM memory entries for this client profile.
Prioritize recurring preferences, forbidden phrases, audience details, and delivery constraints.
Add metadata.client_id="acme" and metadata.owner="jon" on every item.
Tag all items with "client-acme" plus relevant topic tags.
Return ONLY valid JSON array.

CLIENT_NOTES:
{{paste notes}}
```

### Scenario 4: Meeting-to-Memory Conversion

Use after planning calls or retros.

Prompt:

```text
Convert meeting notes into durable LLMMM memories.
Exclude tentative ideas unless the notes mark them as decided.
Use importance=5 for hard constraints, 4 for strong preferences, 3 for defaults.
Set pinned=true only for rules that should always be pulled into context.
Return ONLY valid JSON array.

MEETING_NOTES:
{{paste notes}}
```

### Scenario 5: Build a Daily Memory Digest

Use for periodic capture from multiple model sessions.

Prompt:

```text
You are consolidating today's AI session outputs into LLMMM memories.
Deduplicate overlapping items and keep the most precise version.
Each memory should stand alone and be understandable without prior chat context.
Return ONLY valid JSON array.

SESSION_LOGS:
{{paste multiple summaries}}
```

## Example Output (Bulk Import Ready)

```json
[
  {
    "title": "Use concise technical writing",
    "body": "Prefer direct technical wording with short paragraphs and minimal fluff in engineering docs.",
    "tags": ["writing", "engineering"],
    "source_model": "claude",
    "importance": 4,
    "pinned": false,
    "metadata": {
      "project": "llmmm",
      "captured_from": "doc-review"
    }
  },
  {
    "title": "Always include rollback steps in deployment plans",
    "body": "Deployment instructions must include explicit rollback commands and validation checks.",
    "tags": ["devops", "release"],
    "source_model": "codex",
    "importance": 5,
    "pinned": true,
    "metadata": {
      "project": "llmmm",
      "captured_from": "release-retro"
    }
  }
]
```

## Load JSON Into LLMMM

```bash
curl -sS "$LLMMM_URL/api/v1/memories/bulk-import" \
  -H "X-API-Key: $LLMMM_API_KEY" \
  -H "Content-Type: application/json" \
  -d @memories.json
```

## Quality Checklist Before Import

- Is each memory durable (useful beyond one session)?
- Is each body explicit and unambiguous?
- Are tags consistent with existing conventions?
- Is importance calibrated (3 default, 5 only for strict constraints)?
- Are pinned memories truly global/high-priority?

## Fast Workflow

1. Ask your LLM to extract memories using one of the scenario prompts.
2. Save output as `memories.json`.
3. Run bulk import.
4. Spot-check in LLMMM web UI.
5. Pin or edit only the highest-signal entries.
