-- New state/district-aware history. Legacy market_prices is retained untouched.
CREATE TABLE IF NOT EXISTS observed_market_prices (
 id VARCHAR(36) PRIMARY KEY,
 state VARCHAR(60) NOT NULL,
 district VARCHAR(100) NOT NULL DEFAULT '',
 market VARCHAR(180) NOT NULL,
 crop VARCHAR(30) NOT NULL,
 variety VARCHAR(100) NOT NULL DEFAULT '',
 grade VARCHAR(30) NOT NULL DEFAULT '',
 date DATE NOT NULL,
 price FLOAT NOT NULL,
 min_price FLOAT,
 max_price FLOAT,
 source VARCHAR(100) NOT NULL,
 source_url VARCHAR(300) NOT NULL,
 fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CONSTRAINT uq_observed_price_scope UNIQUE (state,district,market,crop,variety,grade,date,source)
);
CREATE INDEX IF NOT EXISTS ix_observed_market_prices_state ON observed_market_prices(state);
CREATE INDEX IF NOT EXISTS ix_observed_market_prices_market ON observed_market_prices(market);
CREATE INDEX IF NOT EXISTS ix_observed_market_prices_crop ON observed_market_prices(crop);
CREATE INDEX IF NOT EXISTS ix_observed_market_prices_date ON observed_market_prices(date);
