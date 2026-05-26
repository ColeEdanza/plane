# audit-consumer

External webhook receiver that turns Plane outbound webhooks into rows in the
`plane_audit` database. Companion to the in-fork `plane.app.audit` Django app.

See [`Business/plane-fork/DECISIONS.md`](../../../Business/plane-fork/DECISIONS.md)
§ "Audit log: hybrid in-fork + external" for the architectural rationale.

## What it does

- Listens on `POST /webhook` for Plane webhook deliveries.
- Verifies `X-Plane-Signature` HMAC against `PLANE_WEBHOOK_SECRET`.
- Filters to events whose `"event"` field is in `PHI_MODELS` (defaults to:
  `issue`, `issue_comment`, `issue_activity`, `project`, `workspace`, `user`,
  `issue_reaction`, `comment_reaction`, `issue_activity_reaction`).
- Persists a payload **digest** (allowlisted fields only — see `DIGEST_FIELDS`
  in [`consumer.py`](consumer.py)) into `audit_events`. PHI bodies (issue
  description, comment HTML) are never stored.
- Returns 200 even on DB write failure (fail-open, matches in-fork middleware
  posture). DB failures are logged at WARNING for ops alerting.

## Local dev

```bash
# From the plane-fork repo root, after creating the plane_audit DB:
docker exec plane-fork-plane-db-1 psql -U plane -c 'CREATE DATABASE plane_audit;'

# Run migrations against the audit DB to create audit_events table:
docker exec plane-fork-api-1 python manage.py migrate --database=audit

# Then bring up the consumer:
docker compose -f docker-compose-local.yml \
               -f services/audit-consumer/docker-compose.yml \
               up -d audit-consumer

# Point a Plane workspace webhook at http://audit-consumer:8088/webhook
# (set the same secret on both sides via PLANE_WEBHOOK_SECRET).
```

## Office Synology deploy

1. Copy `services/audit-consumer/` to the office Synology (rsync or
   git clone the fork).
2. Create `services/audit-consumer/.env` with the real
   `PLANE_WEBHOOK_SECRET` and the production `AUDIT_DATABASE_URL`
   (use the `audit_consumer` role's DSN — see
   [`../../apps/api/plane/app/audit/sql/bootstrap.sql`](../../apps/api/plane/app/audit/sql/bootstrap.sql)).
3. `docker compose --env-file .env up -d --build`.
4. In Plane god-mode → Workspace settings → Webhooks → add
   `http://audit-consumer:8088/webhook` with all relevant model events
   selected. Set the secret to match `PLANE_WEBHOOK_SECRET`.

## NOT for public internet

This service has no authentication beyond the HMAC signature. Bind it to
the Docker network with the Plane stack; do not expose port 8088 to the
LAN or WAN.
