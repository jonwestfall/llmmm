# LLMMM API Reference

Base path: `/api/v1`

Authentication:

- Header `X-API-Key: <key>` or `Authorization: Bearer <key>`
- Keys are scoped; endpoint access depends on scope.

## Scopes

- `read`: list/get/export memories, context pull
- `write`: create/update/delete/import memories
- `files`: upload/list files, create/revoke share links
- `admin`: key management, pull profile updates

## Endpoints

### Health

- `GET /health`

### Memories

- `POST /memories` (`write`)
- `GET /memories` (`read`)
  - Query: `q`, `tags[]`, `source_model`, `pinned`, `since`, `limit`, `offset`
- `GET /memories/{memory_id}` (`read`)
- `PUT /memories/{memory_id}` (`write`)
- `DELETE /memories/{memory_id}` (`write`)
- `POST /memories/bulk-import` (`write`)
- `GET /memories/export?fmt=jsonl|csv` (`read`)

### Context Pull

- `GET /context/pull?profile=default` (`read`)

### Pull Profiles

- `POST /pull-profiles` (`admin`) create/update by profile name
- `GET /pull-profiles/default` (`read`)

### API Keys

- `POST /keys` (`admin`) create key (returns plaintext once)
- `GET /keys` (`admin`) list keys
- `DELETE /keys/{key_id}` (`admin`) revoke key

### Files

- `POST /files/upload` (`files`) multipart upload
- `GET /files` (`files`) list files
- `POST /files/{file_id}/share-links` (`files`) create public link
- `GET /files/{file_id}/share-links` (`files`) list links (token not recoverable)
- `POST /files/{file_id}/share-links/{share_id}/disable` (`files`) disable link

### Public Share

- `GET /share/{token}`
  - Optional query: `password=<value>` for password-protected links

## Response Notes

- Times are UTC ISO timestamps.
- Memory metadata is arbitrary JSON object.
- API key values are never stored plaintext.
- Share link raw token is only returned at creation time.
