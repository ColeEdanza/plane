"""
CSFD Plane audit-consumer
==========================

A tiny webhook receiver that turns Plane outbound webhooks into rows in the
plane_audit Postgres database. Sibling-container to the Plane stack on the
office Synology; not part of the Plane API process.

Why this exists
---------------
The in-fork AuditMiddleware records ONE row per HTTP request — which is
enough to satisfy HIPAA "who-touched-when" auditing for read events and
auth events, but lacks the model-level "what changed" detail (Plane's
viewsets perform multi-step updates that don't always 1:1 map to a single
request). The webhook consumer fills that gap by listening to Plane's
existing webhook stream and writing model-level rows for the PHI-bearing
models listed in PHI_MODELS.

Webhook envelope (from Plane source — plane/bgtasks/webhook_task.py):
    {
      "event": "issue" | "issue_comment" | "project" | ...,
      "action": "create" | "update" | "delete" | "publish",
      "data":   <serialized model>,
      "webhook_id": "<uuid>",
      "workspace_id": "<uuid>",
      ...
    }
A signature header "X-Plane-Signature" carries an HMAC-SHA256 over the body
with the webhook's secret (also from webhook_task.py).

We accept any "event" but ONLY persist payload digests for events whose
"event" key is in PHI_MODELS (config-overridable). Anything else is
ack'd-and-dropped so this stays low-noise.

Operational stance
------------------
* Listens on PORT (default 8088). Reverse-proxy this behind Caddy / DSM /
  whatever on the office Synology; do NOT expose to the public internet.
* Fail-open posture matches the in-fork middleware: a DB write failure
  is logged but the 200 is still returned to Plane so Plane doesn't
  drown its retry queue.
* No payload-stripping is done beyond keeping a fixed allowlist of
  fields per model. Adjust DIGEST_FIELDS to taste; the default is the
  minimum set to make a row useful (ids + timestamps + state names).
"""

import hashlib
import hmac
import json
import logging
import os
import sys
from datetime import datetime

import psycopg2
from flask import Flask, request, jsonify


PHI_MODELS = set(
    os.environ.get(
        "PHI_MODELS",
        "issue,issue_comment,issue_activity,project,workspace,user,"
        "issue_reaction,comment_reaction,issue_activity_reaction",
    )
    .replace(" ", "")
    .split(",")
)

DIGEST_FIELDS = {
    "issue":               ["id", "sequence_id", "name", "state_id", "priority", "assignees", "created_by", "updated_by"],
    "issue_comment":       ["id", "issue", "actor", "created_by", "updated_by"],
    "issue_activity":      ["id", "issue", "actor", "field", "verb"],
    "project":             ["id", "name", "identifier", "workspace"],
    "workspace":           ["id", "name", "slug"],
    "user":                ["id", "email"],
    "issue_reaction":      ["id", "issue", "actor", "reaction"],
    "comment_reaction":    ["id", "comment", "actor", "reaction"],
    "issue_activity_reaction": ["id", "activity", "actor", "reaction"],
}

WEBHOOK_SECRET = os.environ.get("PLANE_WEBHOOK_SECRET", "")

DB_DSN = os.environ.get(
    "AUDIT_DATABASE_URL",
    "postgresql://plane:plane@plane-db:5432/plane_audit",
)

PORT = int(os.environ.get("PORT", "8088"))

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("audit-consumer")


def _conn():
    return psycopg2.connect(DB_DSN)


def _record(event_name, action, data):
    """Insert one audit_events row. Returns False on any DB failure (fail-open)."""
    obj_id = str(data.get("id", "")) if isinstance(data, dict) else ""
    fields = DIGEST_FIELDS.get(event_name, ["id"])
    digest = {k: data.get(k) for k in fields if isinstance(data, dict)}

    try:
        with _conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit_events (
                    id, timestamp, event_type, model_name, object_id, action, payload
                ) VALUES (
                    gen_random_uuid(), %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    datetime.utcnow(),
                    "webhook",
                    event_name[:64],
                    obj_id[:64],
                    (action or "")[:32],
                    json.dumps(digest, default=str),
                ),
            )
        return True
    except Exception as e:
        log.warning("audit insert failed event=%s action=%s err=%s", event_name, action, e)
        return False


app = Flask(__name__)


def _verify_signature(raw_body: bytes, signature_header: str) -> bool:
    if not WEBHOOK_SECRET:
        log.warning("PLANE_WEBHOOK_SECRET unset; accepting unsigned webhooks (DEV ONLY)")
        return True
    if not signature_header:
        return False
    mac = hmac.new(WEBHOOK_SECRET.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, signature_header)


@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify(status="ok"), 200


@app.route("/webhook", methods=["POST"])
def webhook():
    raw = request.get_data(cache=False)
    sig = request.headers.get("X-Plane-Signature", "")
    if not _verify_signature(raw, sig):
        return jsonify(error="bad signature"), 401

    try:
        body = json.loads(raw.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return jsonify(error="bad json"), 400

    event_name = (body.get("event") or "").strip().lower()
    action = (body.get("action") or "").strip().lower()
    data = body.get("data") or {}

    if event_name not in PHI_MODELS:
        return jsonify(status="ignored", reason=f"event {event_name!r} not in PHI_MODELS"), 200

    ok = _record(event_name, action, data)
    return jsonify(status="ok" if ok else "logged_error"), 200


if __name__ == "__main__":
    log.info("audit-consumer starting on :%d; PHI_MODELS=%s", PORT, sorted(PHI_MODELS))
    if not WEBHOOK_SECRET:
        print("WARNING: PLANE_WEBHOOK_SECRET is unset — signature verification disabled", file=sys.stderr)
    app.run(host="0.0.0.0", port=PORT)
