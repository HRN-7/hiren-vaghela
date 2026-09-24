-- Additive migration; existing notification, crop, demand and account rows remain intact.
CREATE TABLE IF NOT EXISTS push_deliveries (
    id VARCHAR(36) PRIMARY KEY,
    notification_id VARCHAR(36) NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
    token VARCHAR(500) NOT NULL REFERENCES push_tokens(token) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    lease_id VARCHAR(36),
    last_error VARCHAR(100) NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    sent_at TIMESTAMPTZ,
    UNIQUE (notification_id, token)
);
CREATE INDEX IF NOT EXISTS ix_push_deliveries_notification_id ON push_deliveries(notification_id);
CREATE INDEX IF NOT EXISTS ix_push_deliveries_status ON push_deliveries(status);
CREATE INDEX IF NOT EXISTS ix_push_deliveries_next_attempt_at ON push_deliveries(next_attempt_at);
