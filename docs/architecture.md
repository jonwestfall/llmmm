# Architecture Details

## Components

- FastAPI app (`app/main.py`)
- API router (`app/routers/api.py`)
- Web router (`app/routers/web.py`)
- SQLAlchemy models (`app/models.py`)
- Service layer (`app/services.py`)

## Data Model

### `memories`

- identity: `id`
- content: `title`, `body`
- classification: `source_model`, `importance`, `pinned`, tags
- metadata: freeform JSON
- timestamps: `created_at`, `updated_at`

### `tags` and `memory_tags`

- normalized tag catalog with many-to-many relation to memories

### `api_keys`

- hashed key storage
- scoped authorization
- active/revoked state
- usage timestamp

### `file_assets`

- uploaded file metadata
- content hash (SHA-256)
- stored filename pointer

### `file_share_links`

- hashed public token
- optional expiry
- optional max downloads
- optional password hash
- active/revoked state

### `memory_pull_profiles`

- named retrieval templates for periodic pull
- include filters (tags, preferred sources)
- lookback window and max item count

## Request Flow

1. LLM calls API with scoped key.
2. Auth dependency validates key hash and scope.
3. Service layer executes business logic.
4. DB persists memory/file metadata.
5. Context pull endpoint applies profile filters and returns ranked items.

## Filesystem Layout

- `data/llmmm.db` SQLite DB
- `data/files/*` uploaded assets
- `data/backups/*` backup archives

## Scalability Notes

Current design targets a single-container VPS deployment.

To scale:

- move to PostgreSQL
- external object storage for files
- shared cache for distributed rate limits
- centralized logging and metrics
