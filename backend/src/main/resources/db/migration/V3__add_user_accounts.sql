CREATE TABLE app_users (
    id UUID PRIMARY KEY,
    username VARCHAR(64) NOT NULL,
    password_hash VARCHAR(100) NOT NULL,
    role VARCHAR(16) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT uk_app_users_username UNIQUE (username),
    CONSTRAINT chk_app_users_username_lowercase CHECK (username = LOWER(username)),
    CONSTRAINT chk_app_users_role CHECK (role IN ('VIEWER', 'OPERATOR'))
);

CREATE INDEX idx_app_users_enabled ON app_users(enabled);
