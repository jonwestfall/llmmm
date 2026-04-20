# Security Hardening Guide

LLMMM is intended to be internet-exposed only when hardened behind TLS and strict key management.

## Threat Model

Primary risks:

- API key leakage
- Unintended public file exposure via share links
- Prompt-injected memory poisoning
- Brute force login attempts
- Data loss without backups

## Baseline Controls

- HTTPS-only ingress via reverse proxy.
- Strong random values for:
  - `LLMMM_ADMIN_PASSWORD`
  - `LLMMM_SESSION_SECRET`
  - `LLMMM_SECRET_KEY`
- Per-tool API keys with minimal scopes.
- Fast key revocation when compromise is suspected.
- CORS restricted to known origins (not `*` in production).

## Recommended Deployment Pattern

1. Run LLMMM in Docker on private interface.
2. Put Nginx/Caddy/Traefik in front for TLS termination.
3. Force HTTP -> HTTPS redirect.
4. Add request rate limiting at reverse proxy.
5. Enforce firewall allowlist where possible.

## API Key Policy

- One key per integration (ChatGPT, Codex, Claude, etc.).
- Use scope minimization.
- Rotate on schedule (e.g., monthly).
- Revoke immediately if copied into logs/chats/screenshots.

## File Share Link Policy

- Always set expiry.
- Use password for sensitive files.
- Set max download count for single-purpose shares.
- Disable links after usage window.

## Data-at-Rest

- Protect `./data` volume with host-level encryption.
- Restrict filesystem permissions.
- Include data volume in encrypted backups.

## Monitoring Suggestions

- Reverse proxy access logs + fail2ban.
- Alert on repeated 401/403/429 spikes.
- Alert when high-volume downloads happen on share links.

## Recovery Plan

- Keep daily backups and periodic restore tests.
- Document key revocation + replacement runbook.
- Practice restoring to a staging VPS quarterly.
