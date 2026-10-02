-- =============================================================================
-- caminh.ia / carrerMatch — schema v1.0 (PostgreSQL 16)
-- recriado a partir do PRD v2 / TRD v2 / handoff (o arquivo original não foi
-- recuperado). 15 domínios de tabela; tabelas *_i18n contam junto da base.
--
-- convenções:
--   - ids de vocabulário (skills, roles, sectors) são SMALLINT/INT estáveis
--     vindos do seed; ids de usuário e eventos são UUID.
--   - scores normalizados em [0,1] com CHECK; estrelas (1–5) só na API.
--   - RLS habilitado em tabelas com dados de usuário. o backend conecta com o
--     role dono das tabelas (bypass de RLS); policies protegem acesso direto
--     via `app.user_id` (SET LOCAL app.user_id = '<uuid>').
-- =============================================================================

BEGIN;

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gen_random_uuid()

-- -----------------------------------------------------------------------------
-- tipos
-- -----------------------------------------------------------------------------
CREATE TYPE market_trend      AS ENUM ('em_alta', 'estavel', 'emergente');
CREATE TYPE experience_kind   AS ENUM ('professional', 'personal', 'education', 'volunteer');
CREATE TYPE mentor_status     AS ENUM ('available', 'busy', 'inactive');
CREATE TYPE match_status      AS ENUM ('requested', 'accepted', 'declined', 'completed', 'cancelled');
CREATE TYPE rec_source        AS ENUM ('item_based', 'knowledge_graph', 'hybrid', 'own_model');

-- -----------------------------------------------------------------------------
-- utilitário: updated_at automático
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 1. vocabulário controlado
-- =============================================================================
CREATE TABLE sectors (
    id          SMALLINT PRIMARY KEY,
    slug        TEXT NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sectors_i18n (
    sector_id   SMALLINT NOT NULL REFERENCES sectors(id) ON DELETE CASCADE,
    locale      TEXT NOT NULL CHECK (locale IN ('pt-BR', 'en')),
    name        TEXT NOT NULL,
    PRIMARY KEY (sector_id, locale)
);

CREATE TABLE skills (
    id          INT PRIMARY KEY,
    slug        TEXT NOT NULL UNIQUE,
    category    TEXT NOT NULL CHECK (category IN ('technical', 'human', 'business', 'domain', 'creative')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE skills_i18n (
    skill_id    INT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    locale      TEXT NOT NULL CHECK (locale IN ('pt-BR', 'en')),
    name        TEXT NOT NULL,
    -- termos que, encontrados no texto livre, indicam a habilidade (extração TF-IDF)
    aliases     TEXT[] NOT NULL DEFAULT '{}',
    PRIMARY KEY (skill_id, locale)
);
CREATE INDEX skills_i18n_aliases_gin ON skills_i18n USING gin (aliases);
CREATE INDEX skills_i18n_name_trgm   ON skills_i18n USING gin (name gin_trgm_ops);

CREATE TABLE roles (
    id            INT PRIMARY KEY,
    slug          TEXT NOT NULL UNIQUE,
    sector_id     SMALLINT NOT NULL REFERENCES sectors(id),
    market_trend  market_trend NOT NULL DEFAULT 'estavel',
    -- true = cargo "ponte" multidisciplinar (ex.: growth para longevidade)
    is_hybrid     BOOLEAN NOT NULL DEFAULT false,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE roles_i18n (
    role_id     INT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    locale      TEXT NOT NULL CHECK (locale IN ('pt-BR', 'en')),
    title       TEXT NOT NULL,
    PRIMARY KEY (role_id, locale)
);

-- habilidades que caracterizam um cargo. necessário para o item-based (vetor
-- do cargo) — não estava listado no TRD, mas sem ele não há vetor de item.
CREATE TABLE role_skills (
    role_id     INT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    skill_id    INT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    importance  REAL NOT NULL CHECK (importance > 0 AND importance <= 1),
    PRIMARY KEY (role_id, skill_id)
);
CREATE INDEX role_skills_skill_idx ON role_skills (skill_id);

-- setores secundários de um cargo (as "3 indústrias relevantes" do PRD)
CREATE TABLE role_sectors (
    role_id     INT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    sector_id   SMALLINT NOT NULL REFERENCES sectors(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, sector_id)
);

-- =============================================================================
-- 2. usuários e experiências
-- =============================================================================
CREATE TABLE users (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_provider_id  TEXT UNIQUE,              -- sub do Supabase Auth
    email             TEXT UNIQUE,
    display_name      TEXT,
    is_mentor         BOOLEAN NOT NULL DEFAULT false,
    mentor_status     mentor_status,
    mentor_headline   TEXT,
    -- fingerprint comportamental do onboarding (0–1)
    risk_tolerance    REAL CHECK (risk_tolerance BETWEEN 0 AND 1),
    consent_data_at   TIMESTAMPTZ,              -- LGPD: consentimento explícito
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (NOT is_mentor OR mentor_status IS NOT NULL)
);
CREATE INDEX users_mentor_available_idx ON users (id) WHERE is_mentor AND mentor_status = 'available';
CREATE TRIGGER users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE experiences (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    position           SMALLINT NOT NULL CHECK (position BETWEEN 1 AND 5),   -- RN-02
    raw_text           TEXT NOT NULL CHECK (length(trim(raw_text)) > 0),
    kind               experience_kind NOT NULL DEFAULT 'professional',
    -- RN-09: kind NÃO entra na ponderação; os três pesos abaixo sim
    emotional_impact   REAL NOT NULL DEFAULT 0.5 CHECK (emotional_impact BETWEEN 0 AND 1),
    mastery_level      REAL NOT NULL DEFAULT 0.5 CHECK (mastery_level BETWEEN 0 AND 1),
    recognition_score  REAL NOT NULL DEFAULT 0.5 CHECK (recognition_score BETWEEN 0 AND 1),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, position)
);

CREATE TABLE experience_skills (
    experience_id  UUID NOT NULL REFERENCES experiences(id) ON DELETE CASCADE,
    skill_id       INT NOT NULL REFERENCES skills(id),
    weight         REAL NOT NULL CHECK (weight > 0 AND weight <= 1),  -- tf-idf normalizado
    frequency      SMALLINT NOT NULL DEFAULT 1 CHECK (frequency > 0),
    PRIMARY KEY (experience_id, skill_id)
);
CREATE INDEX experience_skills_skill_idx ON experience_skills (skill_id);

CREATE TABLE onboarding_responses (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question_key TEXT NOT NULL,
    answer       JSONB NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, question_key)
);

-- =============================================================================
-- 3. knowledge graph
-- =============================================================================
CREATE TABLE career_transitions (
    id              BIGSERIAL PRIMARY KEY,
    from_role_id    INT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    to_role_id      INT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    observed_count  INT NOT NULL DEFAULT 1 CHECK (observed_count >= 0),
    confidence      REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    avg_years       REAL CHECK (avg_years >= 0),
    bridge_skill_ids INT[] NOT NULL DEFAULT '{}',   -- habilidades que viabilizam a transição
    source          TEXT NOT NULL DEFAULT 'curated' CHECK (source IN ('curated', 'onet', 'rais', 'observed')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (from_role_id <> to_role_id),
    UNIQUE (from_role_id, to_role_id)
);
CREATE INDEX career_transitions_from_idx ON career_transitions (from_role_id, confidence DESC);
CREATE INDEX career_transitions_to_idx   ON career_transitions (to_role_id);
CREATE TRIGGER career_transitions_updated_at BEFORE UPDATE ON career_transitions FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =============================================================================
-- 4. recomendações e feedback
-- =============================================================================
CREATE TABLE career_recommendations (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID REFERENCES users(id) ON DELETE CASCADE,   -- NULL = anônimo (não persistido no beta, RN-07)
    request_id        UUID NOT NULL,                                 -- agrupa uma geração
    role_id           INT NOT NULL REFERENCES roles(id),
    rank              SMALLINT NOT NULL CHECK (rank BETWEEN 1 AND 21),  -- RN-03
    confidence_score  REAL NOT NULL CHECK (confidence_score BETWEEN 0 AND 1),
    source            rec_source NOT NULL,
    description       TEXT,
    key_skill_ids     INT[] NOT NULL DEFAULT '{}',
    model_version     TEXT NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (request_id, rank)
);
CREATE INDEX career_recommendations_user_idx ON career_recommendations (user_id, created_at DESC);

CREATE TABLE recommendation_feedback (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recommendation_id  UUID NOT NULL REFERENCES career_recommendations(id) ON DELETE CASCADE,
    user_id            UUID REFERENCES users(id) ON DELETE SET NULL,
    signal             TEXT NOT NULL CHECK (signal IN (
                           'recommendation_viewed', 'career_expanded', 'career_saved',
                           'mentor_contacted', 'rated_positive', 'rated_negative', 'dismissed')),
    engagement_weight  REAL NOT NULL CHECK (engagement_weight BETWEEN -1 AND 1),  -- TRD §9
    rating             SMALLINT CHECK (rating BETWEEN 1 AND 5),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX recommendation_feedback_rec_idx ON recommendation_feedback (recommendation_id);

-- =============================================================================
-- 5. mentoria
-- =============================================================================
CREATE TABLE mentor_matches (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mentee_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mentor_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id            INT REFERENCES roles(id),
    recommendation_id  UUID REFERENCES career_recommendations(id) ON DELETE SET NULL,
    similarity_score   REAL NOT NULL CHECK (similarity_score BETWEEN 0 AND 1),
    status             match_status NOT NULL DEFAULT 'requested',
    message            TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (mentee_id <> mentor_id)
);
CREATE INDEX mentor_matches_mentor_idx ON mentor_matches (mentor_id, status);
CREATE INDEX mentor_matches_mentee_idx ON mentor_matches (mentee_id, created_at DESC);
CREATE TRIGGER mentor_matches_updated_at BEFORE UPDATE ON mentor_matches FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- cache da matriz cosine user×user (batch diário, ADR-03). par ordenado a < b.
CREATE TABLE user_similarities (
    user_a      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_b      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    similarity  REAL NOT NULL CHECK (similarity BETWEEN -1 AND 1),
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_a, user_b),
    CHECK (user_a < user_b)
);
CREATE INDEX user_similarities_b_idx ON user_similarities (user_b, similarity DESC);

-- =============================================================================
-- 6. eventos comportamentais (particionado por ano — RN-10)
-- =============================================================================
CREATE TABLE behavioral_events (
    id           UUID NOT NULL DEFAULT gen_random_uuid(),
    occurred_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_id      UUID REFERENCES users(id) ON DELETE SET NULL,
    session_id   UUID NOT NULL,                -- anônimo também é rastreado por sessão
    event_type   TEXT NOT NULL,
    request_id   UUID,
    role_id      INT,
    payload      JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (id, occurred_at)
) PARTITION BY RANGE (occurred_at);

CREATE TABLE behavioral_events_2026 PARTITION OF behavioral_events
    FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');
CREATE TABLE behavioral_events_2027 PARTITION OF behavioral_events
    FOR VALUES FROM ('2027-01-01') TO ('2028-01-01');
CREATE TABLE behavioral_events_default PARTITION OF behavioral_events DEFAULT;

CREATE INDEX behavioral_events_type_idx    ON behavioral_events (event_type, occurred_at DESC);
CREATE INDEX behavioral_events_session_idx ON behavioral_events (session_id, occurred_at);
CREATE INDEX behavioral_events_user_idx    ON behavioral_events (user_id, occurred_at DESC) WHERE user_id IS NOT NULL;

-- =============================================================================
-- 7. fase 3 — LTP engine (preparado, inativo no MVP)
-- =============================================================================
CREATE TABLE plasticity_nodes (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill_id         INT NOT NULL REFERENCES skills(id),
    ltp_force        REAL NOT NULL DEFAULT 0 CHECK (ltp_force >= 0),
    maturity_score   REAL NOT NULL DEFAULT 0 CHECK (maturity_score BETWEEN 0 AND 1),
    is_development_window BOOLEAN GENERATED ALWAYS AS (maturity_score > 0.8) STORED,
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, skill_id)
);

CREATE TABLE plasticity_edges (
    from_node_id  UUID NOT NULL REFERENCES plasticity_nodes(id) ON DELETE CASCADE,
    to_node_id    UUID NOT NULL REFERENCES plasticity_nodes(id) ON DELETE CASCADE,
    strength      REAL NOT NULL CHECK (strength BETWEEN 0 AND 1),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (from_node_id, to_node_id),
    CHECK (from_node_id <> to_node_id)
);

CREATE TABLE ltp_predictions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    predicted_class TEXT NOT NULL,
    probability     REAL NOT NULL CHECK (probability BETWEEN 0 AND 1),
    shap_values     JSONB,
    actual_class    TEXT,              -- ground truth quando o usuário confirma
    model_version   TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- 8. views de apoio
-- =============================================================================
CREATE VIEW v_roles_pt AS
SELECT r.id, r.slug, ri.title, r.market_trend, r.is_hybrid, r.sector_id, si.name AS sector_name
FROM roles r
JOIN roles_i18n ri   ON ri.role_id = r.id AND ri.locale = 'pt-BR'
JOIN sectors_i18n si ON si.sector_id = r.sector_id AND si.locale = 'pt-BR';

CREATE VIEW v_available_mentors AS
SELECT id, display_name, mentor_headline
FROM users
WHERE is_mentor AND mentor_status = 'available';

-- =============================================================================
-- 9. RLS (dados de usuário)
-- =============================================================================
CREATE OR REPLACE FUNCTION app_user_id() RETURNS UUID AS $$
    SELECT nullif(current_setting('app.user_id', true), '')::uuid;
$$ LANGUAGE sql STABLE;

ALTER TABLE users                   ENABLE ROW LEVEL SECURITY;
ALTER TABLE experiences             ENABLE ROW LEVEL SECURITY;
ALTER TABLE experience_skills       ENABLE ROW LEVEL SECURITY;
ALTER TABLE onboarding_responses    ENABLE ROW LEVEL SECURITY;
ALTER TABLE career_recommendations  ENABLE ROW LEVEL SECURITY;
ALTER TABLE recommendation_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE mentor_matches          ENABLE ROW LEVEL SECURITY;
ALTER TABLE behavioral_events       ENABLE ROW LEVEL SECURITY;
ALTER TABLE plasticity_nodes        ENABLE ROW LEVEL SECURITY;
ALTER TABLE ltp_predictions         ENABLE ROW LEVEL SECURITY;

CREATE POLICY users_self            ON users                   USING (id = app_user_id());
CREATE POLICY experiences_owner     ON experiences             USING (user_id = app_user_id());
CREATE POLICY exp_skills_owner      ON experience_skills       USING (
    EXISTS (SELECT 1 FROM experiences e WHERE e.id = experience_id AND e.user_id = app_user_id()));
CREATE POLICY onboarding_owner      ON onboarding_responses    USING (user_id = app_user_id());
CREATE POLICY recs_owner            ON career_recommendations  USING (user_id = app_user_id());
CREATE POLICY feedback_owner        ON recommendation_feedback USING (user_id = app_user_id());
CREATE POLICY matches_participant   ON mentor_matches          USING (app_user_id() IN (mentee_id, mentor_id));
CREATE POLICY events_owner          ON behavioral_events       USING (user_id = app_user_id());
CREATE POLICY plasticity_owner      ON plasticity_nodes        USING (user_id = app_user_id());
CREATE POLICY ltp_owner             ON ltp_predictions         USING (user_id = app_user_id());

COMMIT;
