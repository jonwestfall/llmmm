# Operations Guide

## Setup Checklist

1. Configure `.env` from `.env.example`.
2. Start service with `docker compose up -d --build`.
3. Log in at `/login`.
4. Create API keys for each tool.
5. Validate:
   - `GET /api/v1/health`
   - `GET /api/v1/context/pull?profile=default`

## Loading Memories In

### Single item

- Web UI: `POST /memories` form.
- API: `POST /api/v1/memories`.

### Bulk import

- API: `POST /api/v1/memories/bulk-import` with JSON list.

Recommended pre-import shape:

```json
[
  {
    "title": "Client A Style",
    "body": "Use formal tone and avoid contractions.",
    "tags": ["client-a", "style"],
    "source_model": "manual",
    "importance": 4,
    "pinned": true,
    "metadata": {"owner": "jon"}
  }
]
```

## Loading Memories Out

### Pull context

- `GET /api/v1/context/pull?profile=default`

### Full export

- `GET /api/v1/memories/export?fmt=jsonl`
- `GET /api/v1/memories/export?fmt=csv`

## File Reference Lifecycle

1. Upload file at `/files` or `/api/v1/files/upload`.
2. Create share link with expiry/password policy.
3. Give link to the target LLM flow.
4. Disable share after use.

## Backup

Create backup archive:

```bash
./scripts/backup.sh
```

This includes the entire `data/` directory:

- SQLite DB
- uploaded files
- prior backups

## Restore

```bash
./scripts/restore.sh <backup.tar.gz> --yes
```

After restore:

1. Restart container.
2. Validate health and memory counts.
3. Test one share link and one API call.

## Retention Strategy

Suggested:

- Daily backups (7 days)
- Weekly backups (8 weeks)
- Monthly backups (12 months)
- One offsite encrypted copy

## Routine Maintenance

- Weekly: review stale memories; delete low-value entries.
- Weekly: review active share links.
- Monthly: rotate API keys.
- Monthly: dependency updates and image rebuild.
