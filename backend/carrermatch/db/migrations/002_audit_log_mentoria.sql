-- =============================================================================
-- 002 — sprint 3: trilha de auditoria (LGPD) + regra de mentoria
-- =============================================================================

BEGIN;
SET search_path = app, public;

-- trilha de auditoria ANONIMIZADA: registra que algo aconteceu, nunca de quem.
-- (exclusão de conta precisa ser comprovável sem manter o dado excluído)
CREATE TABLE audit_log (
    id           BIGSERIAL PRIMARY KEY,
    event_type   TEXT NOT NULL CHECK (event_type IN ('account_deleted', 'data_exported', 'auth_revocation_failed')),
    occurred_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    details      JSONB NOT NULL DEFAULT '{}'   -- só contagens/flags; nunca ids, e-mail ou texto do usuário
);
CREATE INDEX audit_log_type_idx ON audit_log (event_type, occurred_at DESC);
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;  -- sem policy: só o backend (dono) acessa

-- no máximo UMA solicitação pendente por par mentorado→mentor (anti-spam, 409 na API)
CREATE UNIQUE INDEX mentor_matches_one_pending
    ON mentor_matches (mentee_id, mentor_id) WHERE status = 'requested';

REVOKE ALL ON audit_log FROM PUBLIC;
REVOKE ALL ON SEQUENCE audit_log_id_seq FROM PUBLIC;
DO $$
DECLARE r TEXT;
BEGIN
    FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
            EXECUTE format('REVOKE ALL ON app.audit_log FROM %I', r);
            EXECUTE format('REVOKE ALL ON SEQUENCE app.audit_log_id_seq FROM %I', r);
        END IF;
    END LOOP;
END;
$$;

COMMIT;
