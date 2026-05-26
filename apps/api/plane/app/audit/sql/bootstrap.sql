-- =====================================================================
-- CSFD Plane fork — audit DB + role bootstrap
-- =====================================================================
--
-- Run this ONCE against the office Synology Postgres instance (as a
-- superuser, e.g. the "postgres" role) before pointing Plane at the
-- audit DB. Local-dev deployments can skip this entirely — they use the
-- existing plane user (see "Local-dev convenience" section at the bottom).
--
-- See Business/plane-fork/DECISIONS.md (2026-05-25 audit log operational
-- decisions) for the rationale behind the same-instance / separate-DB /
-- role-based-append-only design.
--
-- Roles created:
--   plane_audit_admin   — DDL owner. Used only to run Django migrations
--                         against the audit DB; Plane runtime never connects
--                         as this role. Revoke after each migration if you
--                         want maximum strictness.
--   plane_writer        — INSERT-only on audit_events. The role Plane API
--                         connects as in production (POSTGRES_AUDIT_USER).
--   audit_consumer      — INSERT-only on audit_events. The role the
--                         external webhook consumer uses.
--   audit_pruner        — SELECT + DELETE on audit_events. Used by the
--                         weekly retention cron and the weekly summary
--                         mailer. No INSERT/UPDATE.
--
-- After running this you MUST set passwords on each role (or use peer
-- auth in pg_hba.conf) — the role passwords are intentionally left as
-- placeholders below. Do NOT commit real passwords to git.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Database
-- ---------------------------------------------------------------------
CREATE DATABASE plane_audit
    WITH ENCODING = "UTF8"
         LC_COLLATE = "en_US.UTF-8"
         LC_CTYPE = "en_US.UTF-8"
         TEMPLATE = template0;

COMMENT ON DATABASE plane_audit IS
    "CSFD Plane HIPAA audit log. Append-only via role grants. Retention 73 months.";

-- ---------------------------------------------------------------------
-- 2. Roles — set real passwords before use
-- ---------------------------------------------------------------------
CREATE ROLE plane_audit_admin WITH LOGIN PASSWORD "CHANGE_ME_admin";
CREATE ROLE plane_writer      WITH LOGIN PASSWORD "CHANGE_ME_writer";
CREATE ROLE audit_consumer    WITH LOGIN PASSWORD "CHANGE_ME_consumer";
CREATE ROLE audit_pruner      WITH LOGIN PASSWORD "CHANGE_ME_pruner";

GRANT CONNECT ON DATABASE plane_audit TO plane_writer, audit_consumer, audit_pruner, plane_audit_admin;

-- ---------------------------------------------------------------------
-- 3. Switch to the new DB to grant schema-level perms
-- ---------------------------------------------------------------------
\connect plane_audit

-- plane_audit_admin owns public schema; everyone else only has USAGE.
ALTER SCHEMA public OWNER TO plane_audit_admin;
GRANT USAGE ON SCHEMA public TO plane_writer, audit_consumer, audit_pruner;

-- Default privileges for objects created LATER by plane_audit_admin:
ALTER DEFAULT PRIVILEGES FOR ROLE plane_audit_admin IN SCHEMA public
    GRANT INSERT ON TABLES TO plane_writer;
ALTER DEFAULT PRIVILEGES FOR ROLE plane_audit_admin IN SCHEMA public
    GRANT INSERT ON TABLES TO audit_consumer;
ALTER DEFAULT PRIVILEGES FOR ROLE plane_audit_admin IN SCHEMA public
    GRANT SELECT, DELETE ON TABLES TO audit_pruner;

-- Sequences (auto-id, etc.) — writers need USAGE, pruner needs SELECT only.
ALTER DEFAULT PRIVILEGES FOR ROLE plane_audit_admin IN SCHEMA public
    GRANT USAGE ON SEQUENCES TO plane_writer, audit_consumer;
ALTER DEFAULT PRIVILEGES FOR ROLE plane_audit_admin IN SCHEMA public
    GRANT SELECT ON SEQUENCES TO audit_pruner;

-- ---------------------------------------------------------------------
-- 4. Post-migration retroactive grants (run this AFTER Django migrate
--    if you ran migrate before this script, or any time you add a new
--    table to the audit DB).
-- ---------------------------------------------------------------------
-- GRANT INSERT  ON ALL TABLES    IN SCHEMA public TO plane_writer, audit_consumer;
-- GRANT SELECT, DELETE ON ALL TABLES IN SCHEMA public TO audit_pruner;
-- GRANT USAGE   ON ALL SEQUENCES IN SCHEMA public TO plane_writer, audit_consumer;
-- GRANT SELECT  ON ALL SEQUENCES IN SCHEMA public TO audit_pruner;

-- ---------------------------------------------------------------------
-- 5. (Optional) Belt-and-braces: revoke any superuser-y defaults that
--    the public schema gives the PUBLIC role pre-PG15.
-- ---------------------------------------------------------------------
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO plane_writer, audit_consumer, audit_pruner;

-- =====================================================================
-- Local-dev convenience
-- =====================================================================
-- For docker-compose-local.yml the audit DB lives on the same plane-db
-- container as Plane itself, and the existing "plane" superuser is reused
-- for everything. The plane_writer / audit_consumer / audit_pruner roles
-- are NOT required locally because nothing enforces them — local dev is
-- not the trust boundary. Just run:
--
--     CREATE DATABASE plane_audit;
--
-- from psql against the plane-db container, set the AUDIT_* env vars
-- (see apps/api/.env / docker-compose-local.yml), and run
-- `python manage.py migrate --database=audit`.
-- =====================================================================
