-- init.sql — runs automatically when Postgres container starts for the first time
-- This creates the deployments table (when you swap from in-memory to Postgres)

CREATE TABLE IF NOT EXISTS deployments (
    id           SERIAL PRIMARY KEY,                    -- auto-increment integer ID
    app_name     VARCHAR(255) NOT NULL,
    version      VARCHAR(100) NOT NULL,
    environment  VARCHAR(50)  NOT NULL
                 CHECK (environment IN ('dev','staging','prod')),  -- DB-level constraint
    status       VARCHAR(50)  NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('success','failed','pending')),
    deployed_by  VARCHAR(255) NOT NULL,
    notes        TEXT,                                   -- nullable (optional field)
    deployed_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()    -- always store in UTC
);

-- Index for common queries: "show me all deployments to prod"
CREATE INDEX IF NOT EXISTS idx_deployments_environment ON deployments(environment);
CREATE INDEX IF NOT EXISTS idx_deployments_deployed_at  ON deployments(deployed_at DESC);

-- Insert some seed data so you have something to look at immediately
INSERT INTO deployments (app_name, version, environment, status, deployed_by, notes)
VALUES
    ('payment-service', 'v2.1.0', 'prod',    'success', 'tejas', 'Sprint 14 release'),
    ('order-service',   'v1.5.3', 'staging', 'pending', 'tejas', 'Testing new checkout flow'),
    ('auth-service',    'v3.0.1', 'dev',     'failed',  'ci-bot', 'Unit tests failing on line 42');
