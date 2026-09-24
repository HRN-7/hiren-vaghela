-- Initial schema for a NEW PostgreSQL database. Review before running.

CREATE TABLE users (
	id VARCHAR(128) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	location VARCHAR(150) NOT NULL, 
	language VARCHAR(5) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE markets (
	id VARCHAR(180) NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	state VARCHAR(60) NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE market_prices (
	id VARCHAR(36) NOT NULL, 
	market VARCHAR(180) NOT NULL, 
	crop VARCHAR(30) NOT NULL, 
	variety VARCHAR(100) NOT NULL, 
	grade VARCHAR(30) NOT NULL, 
	date DATE NOT NULL, 
	price FLOAT NOT NULL, 
	arrivals FLOAT, 
	source VARCHAR(100) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (market, crop, variety, grade, date, source)
);

CREATE INDEX ix_market_prices_date ON market_prices (date);

CREATE INDEX ix_market_prices_market ON market_prices (market);

CREATE INDEX ix_market_prices_crop ON market_prices (crop);

CREATE TABLE service_records (
	id VARCHAR(100) NOT NULL, 
	kind VARCHAR(20) NOT NULL, 
	data JSON NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_service_records_kind ON service_records (kind);

CREATE TABLE crops (
	id VARCHAR(36) NOT NULL, 
	owner_id VARCHAR(128) NOT NULL, 
	name VARCHAR(30) NOT NULL, 
	variety VARCHAR(100) NOT NULL, 
	quantity FLOAT NOT NULL, 
	grade VARCHAR(1) NOT NULL, 
	parameters JSON NOT NULL, 
	location VARCHAR(150) NOT NULL, 
	sell_date DATE NOT NULL, 
	preferred_market VARCHAR(150) NOT NULL, 
	notes VARCHAR(2000) NOT NULL, 
	public BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(owner_id) REFERENCES users (id)
);

CREATE INDEX ix_crops_owner_id ON crops (owner_id);

CREATE TABLE buyer_demands (
	id VARCHAR(36) NOT NULL, 
	owner_id VARCHAR(128) NOT NULL, 
	company VARCHAR(160) NOT NULL, 
	crop VARCHAR(30) NOT NULL, 
	grade VARCHAR(1) NOT NULL, 
	quantity FLOAT NOT NULL, 
	price FLOAT NOT NULL, 
	location VARCHAR(150) NOT NULL, 
	required_by DATE NOT NULL, 
	contact VARCHAR(150) NOT NULL, 
	verified BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(owner_id) REFERENCES users (id)
);

CREATE INDEX ix_buyer_demands_owner_id ON buyer_demands (owner_id);

CREATE TABLE fpos (
	id VARCHAR(36) NOT NULL, 
	owner_id VARCHAR(128) NOT NULL, 
	name VARCHAR(180) NOT NULL, 
	location VARCHAR(150) NOT NULL, 
	members INTEGER NOT NULL, 
	capacity FLOAT NOT NULL, 
	services JSON NOT NULL, 
	contact VARCHAR(150) NOT NULL, 
	verified BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (owner_id), 
	FOREIGN KEY(owner_id) REFERENCES users (id)
);

CREATE TABLE recommendations (
	id VARCHAR(36) NOT NULL, 
	owner_id VARCHAR(128) NOT NULL, 
	data JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(owner_id) REFERENCES users (id)
);

CREATE INDEX ix_recommendations_owner_id ON recommendations (owner_id);

CREATE TABLE notifications (
	id VARCHAR(36) NOT NULL, 
	owner_id VARCHAR(128) NOT NULL, 
	text VARCHAR(300) NOT NULL, 
	read BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(owner_id) REFERENCES users (id)
);

CREATE INDEX ix_notifications_owner_id ON notifications (owner_id);

CREATE TABLE push_tokens (
	token VARCHAR(500) NOT NULL, 
	owner_id VARCHAR(128) NOT NULL, 
	PRIMARY KEY (token), 
	FOREIGN KEY(owner_id) REFERENCES users (id)
);

CREATE INDEX ix_push_tokens_owner_id ON push_tokens (owner_id);

CREATE TABLE crop_photos (
	id VARCHAR(36) NOT NULL, 
	crop_id VARCHAR(36) NOT NULL, 
	content BYTEA NOT NULL, 
	mime VARCHAR(30) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(crop_id) REFERENCES crops (id) ON DELETE CASCADE
);

CREATE INDEX ix_crop_photos_crop_id ON crop_photos (crop_id);

CREATE TABLE fpo_contributions (
	id VARCHAR(36) NOT NULL, 
	fpo_id VARCHAR(36) NOT NULL, 
	crop_id VARCHAR(36) NOT NULL, 
	owner_id VARCHAR(128) NOT NULL, 
	accepted BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (fpo_id, crop_id), 
	FOREIGN KEY(fpo_id) REFERENCES fpos (id), 
	FOREIGN KEY(crop_id) REFERENCES crops (id), 
	FOREIGN KEY(owner_id) REFERENCES users (id)
);

CREATE TABLE connections (
	id VARCHAR(36) NOT NULL, 
	owner_id VARCHAR(128) NOT NULL, 
	demand_id VARCHAR(36) NOT NULL, 
	message VARCHAR(1000) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (owner_id, demand_id), 
	FOREIGN KEY(owner_id) REFERENCES users (id), 
	FOREIGN KEY(demand_id) REFERENCES buyer_demands (id)
);

CREATE TABLE purchases (
	id VARCHAR(36) NOT NULL, 
	crop_id VARCHAR(36) NOT NULL, 
	buyer_id VARCHAR(128) NOT NULL, 
	seller_id VARCHAR(128) NOT NULL, 
	quantity FLOAT NOT NULL, 
	price FLOAT NOT NULL, 
	buyer_contact VARCHAR(150) NOT NULL, 
	seller_contact VARCHAR(150) NOT NULL, 
	message VARCHAR(1000) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(crop_id) REFERENCES crops (id), 
	FOREIGN KEY(buyer_id) REFERENCES users (id), 
	FOREIGN KEY(seller_id) REFERENCES users (id)
);

CREATE INDEX ix_purchases_seller_id ON purchases (seller_id);

CREATE INDEX ix_purchases_crop_id ON purchases (crop_id);

CREATE INDEX ix_purchases_buyer_id ON purchases (buyer_id);
