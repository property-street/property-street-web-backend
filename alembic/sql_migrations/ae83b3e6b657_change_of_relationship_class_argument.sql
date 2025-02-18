BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 57fefa726641

DROP TYPE IF EXISTS email_management_reason_choice;;

DROP TYPE IF EXISTS client_type_choice;;

CREATE TABLE cloud_image_details (
    id SERIAL NOT NULL, 
    created_at VARCHAR NOT NULL, 
    format VARCHAR NOT NULL, 
    bytes INTEGER NOT NULL, 
    height INTEGER NOT NULL, 
    public_id VARCHAR NOT NULL, 
    secure_url VARCHAR NOT NULL, 
    width INTEGER NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (public_id)
);

CREATE INDEX ix_cloud_image_details_id ON cloud_image_details (id);

CREATE TYPE email_management_reason_choice AS ENUM ('email_verification', 'password_change', 'verified');

CREATE TABLE email_management_model (
    id VARCHAR NOT NULL, 
    email_address VARCHAR, 
    email_code VARCHAR(255), 
    email_code_time TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    email_link VARCHAR, 
    email_link_time TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    reason email_management_reason_choice, 
    PRIMARY KEY (id), 
    UNIQUE (email_code)
);

CREATE INDEX ix_email_management_model_id ON email_management_model (id);

CREATE TABLE tags (
    id SERIAL NOT NULL, 
    name VARCHAR NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (name)
);

CREATE INDEX ix_tags_id ON tags (id);

CREATE TYPE client_type_choice AS ENUM ('client', 'agent');

CREATE TABLE users (
    id SERIAL NOT NULL, 
    email VARCHAR, 
    username VARCHAR, 
    password_hash VARCHAR NOT NULL, 
    first_name VARCHAR, 
    last_name VARCHAR, 
    other_names VARCHAR, 
    date_of_birth DATE, 
    country_of_origin VARCHAR, 
    account_status VARCHAR, 
    misc JSON, 
    client_type client_type_choice, 
    is_active BOOLEAN, 
    is_admin BOOLEAN, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    profile_avatar_id INTEGER, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE INDEX ix_users_id ON users (id);

CREATE UNIQUE INDEX ix_users_username ON users (username);

CREATE TABLE agents (
    id INTEGER NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT fk_agents_user_id FOREIGN KEY(id) REFERENCES users (id)
);

CREATE INDEX ix_agents_id ON agents (id);

CREATE TABLE assets (
    id SERIAL NOT NULL, 
    title VARCHAR NOT NULL, 
    country VARCHAR NOT NULL, 
    address VARCHAR NOT NULL, 
    currency VARCHAR NOT NULL, 
    status VARCHAR NOT NULL, 
    amount NUMERIC NOT NULL, 
    description TEXT, 
    has_features BOOLEAN, 
    availability BOOLEAN, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    category VARCHAR NOT NULL, 
    agent_id INTEGER, 
    cover_image_id INTEGER, 
    PRIMARY KEY (id), 
    CONSTRAINT fk_assets_agent_id FOREIGN KEY(agent_id) REFERENCES agents (id) ON DELETE CASCADE
);

CREATE INDEX ix_assets_id ON assets (id);

CREATE TABLE asset_tag_association (
    asset_id INTEGER NOT NULL, 
    tag_id INTEGER NOT NULL, 
    PRIMARY KEY (asset_id, tag_id), 
    FOREIGN KEY(asset_id) REFERENCES assets (id), 
    FOREIGN KEY(tag_id) REFERENCES tags (id)
);

INSERT INTO alembic_version (version_num) VALUES ('57fefa726641') RETURNING alembic_version.version_num;

-- Running upgrade 57fefa726641 -> 5313a33a1bfa

CREATE TABLE asset_cloud_image (
    id SERIAL NOT NULL, 
    asset_id INTEGER, 
    asset_feature_id INTEGER, 
    created_at VARCHAR NOT NULL, 
    format VARCHAR NOT NULL, 
    bytes INTEGER NOT NULL, 
    height INTEGER NOT NULL, 
    public_id VARCHAR NOT NULL, 
    secure_url VARCHAR NOT NULL, 
    width INTEGER NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (public_id)
);

CREATE INDEX ix_asset_cloud_image_id ON asset_cloud_image (id);

CREATE TABLE asset_features (
    id SERIAL NOT NULL, 
    title VARCHAR NOT NULL, 
    asset_id INTEGER, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_asset_features_id ON asset_features (id);

ALTER TABLE agents DROP CONSTRAINT fk_agents_user_id;

ALTER TABLE assets ADD CONSTRAINT fk_assets_cover_image_id FOREIGN KEY(cover_image_id) REFERENCES cloud_image_details (id) ON DELETE SET NULL;

ALTER TABLE users ADD COLUMN agent_profile_id INTEGER;

ALTER TABLE users ADD UNIQUE (agent_profile_id);

ALTER TABLE users ADD CONSTRAINT fk_user_profile_avatar_id FOREIGN KEY(profile_avatar_id) REFERENCES cloud_image_details (id) ON DELETE SET NULL;

ALTER TABLE users ADD CONSTRAINT fk_users_agent_profile_id FOREIGN KEY(agent_profile_id) REFERENCES agents (id) ON DELETE SET NULL;

UPDATE alembic_version SET version_num='5313a33a1bfa' WHERE alembic_version.version_num = '57fefa726641';

-- Running upgrade 5313a33a1bfa -> 201ffaf12eac

ALTER TABLE asset_cloud_image ADD CONSTRAINT fk_asset_cloud_image_asset_feature_id FOREIGN KEY(asset_feature_id) REFERENCES asset_features (id) ON DELETE CASCADE;

ALTER TABLE asset_cloud_image ADD CONSTRAINT fk_asset_cloud_image_asset_id FOREIGN KEY(asset_id) REFERENCES assets (id) ON DELETE CASCADE;

ALTER TABLE asset_features ADD CONSTRAINT fk_asset_features_asset_id FOREIGN KEY(asset_id) REFERENCES assets (id) ON DELETE CASCADE;

UPDATE alembic_version SET version_num='201ffaf12eac' WHERE alembic_version.version_num = '5313a33a1bfa';

-- Running upgrade 201ffaf12eac -> 5947634d0334

CREATE TABLE asset_cloud_images (
    id SERIAL NOT NULL, 
    asset_id INTEGER, 
    asset_feature_id INTEGER, 
    created_at VARCHAR NOT NULL, 
    format VARCHAR NOT NULL, 
    bytes INTEGER NOT NULL, 
    height INTEGER NOT NULL, 
    public_id VARCHAR NOT NULL, 
    secure_url VARCHAR NOT NULL, 
    width INTEGER NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (public_id)
);

CREATE INDEX ix_asset_cloud_images_id ON asset_cloud_images (id);

DROP INDEX ix_asset_cloud_image_id;

DROP TABLE asset_cloud_image;

UPDATE alembic_version SET version_num='5947634d0334' WHERE alembic_version.version_num = '201ffaf12eac';

-- Running upgrade 5947634d0334 -> dad4a73567aa

CREATE TYPE asset_category_choice AS ENUM ('house', 'hotel', 'land', 'estate', 'fabricated_homes', 'peng_house', 'office_complex', 'oriental_suite');

ALTER TABLE asset_cloud_images ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT now();

ALTER TABLE asset_cloud_images ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at::timestamp with time zone;

ALTER TABLE asset_cloud_images ALTER COLUMN created_at DROP NOT NULL;

ALTER TABLE asset_cloud_images ADD CONSTRAINT fk_asset_cloud_images_asset_feature_id FOREIGN KEY(asset_feature_id) REFERENCES asset_features (id) ON DELETE CASCADE;

ALTER TABLE asset_cloud_images ADD CONSTRAINT fk_asset_cloud_images_asset_id FOREIGN KEY(asset_id) REFERENCES assets (id) ON DELETE CASCADE;

ALTER TABLE assets ALTER COLUMN category TYPE asset_category_choice USING category::asset_category_choice;

ALTER TABLE assets ALTER COLUMN category DROP NOT NULL;

ALTER TABLE cloud_image_details ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT now();

ALTER TABLE cloud_image_details ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at::timestamp with time zone;

ALTER TABLE cloud_image_details ALTER COLUMN created_at DROP NOT NULL;

UPDATE alembic_version SET version_num='dad4a73567aa' WHERE alembic_version.version_num = '5947634d0334';

-- Running upgrade dad4a73567aa -> 46bc2e062333

ALTER TABLE cloud_image_details ADD COLUMN asset_id VARCHAR NOT NULL;

UPDATE alembic_version SET version_num='46bc2e062333' WHERE alembic_version.version_num = 'dad4a73567aa';

-- Running upgrade 46bc2e062333 -> e0404e8dccd8

ALTER TABLE asset_cloud_images ADD COLUMN cloud_asset_id VARCHAR NOT NULL;

ALTER TABLE asset_tag_association DROP CONSTRAINT asset_tag_association_tag_id_fkey;

ALTER TABLE asset_tag_association DROP CONSTRAINT asset_tag_association_asset_id_fkey;

ALTER TABLE asset_tag_association ADD CONSTRAINT fk_asset_tag_association_tag_id FOREIGN KEY(tag_id) REFERENCES tags (id) ON DELETE RESTRICT;

ALTER TABLE asset_tag_association ADD CONSTRAINT fk_asset_tag_association_asset_id FOREIGN KEY(asset_id) REFERENCES assets (id) ON DELETE CASCADE;

ALTER TABLE cloud_image_details ADD COLUMN cloud_asset_id VARCHAR NOT NULL;

ALTER TABLE cloud_image_details DROP COLUMN asset_id;

UPDATE alembic_version SET version_num='e0404e8dccd8' WHERE alembic_version.version_num = '46bc2e062333';

-- Running upgrade e0404e8dccd8 -> 23ab00bb47af

ALTER TABLE assets ALTER COLUMN category TYPE VARCHAR;

ALTER TABLE assets ALTER COLUMN category SET NOT NULL;

UPDATE alembic_version SET version_num='23ab00bb47af' WHERE alembic_version.version_num = 'e0404e8dccd8';

-- Running upgrade 23ab00bb47af -> 52db608125a9

ALTER TABLE assets ADD COLUMN lease_duration VARCHAR;

UPDATE alembic_version SET version_num='52db608125a9' WHERE alembic_version.version_num = '23ab00bb47af';

-- Running upgrade 52db608125a9 -> 7d5af4d25535

ALTER TABLE assets ALTER COLUMN availability TYPE TEXT;

ALTER TABLE assets ALTER COLUMN availability SET NOT NULL;

UPDATE alembic_version SET version_num='7d5af4d25535' WHERE alembic_version.version_num = '52db608125a9';

-- Running upgrade 7d5af4d25535 -> 0200b703001e

CREATE TABLE add_ons (
    id SERIAL NOT NULL, 
    tag_list VARCHAR[], 
    PRIMARY KEY (id)
);

CREATE INDEX ix_add_ons_id ON add_ons (id);

UPDATE alembic_version SET version_num='0200b703001e' WHERE alembic_version.version_num = '7d5af4d25535';

-- Running upgrade 0200b703001e -> 440ab6100f42

CREATE TABLE threads (
    id SERIAL NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id)
);

CREATE INDEX ix_threads_id ON threads (id);

CREATE TABLE chat_sessions (
    id SERIAL NOT NULL, 
    user_id INTEGER, 
    PRIMARY KEY (id), 
    CONSTRAINT fk_chat_sessions_user_id FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_chat_sessions_id ON chat_sessions (id);

CREATE TABLE messages (
    id SERIAL NOT NULL, 
    text_content VARCHAR, 
    status VARCHAR NOT NULL, 
    timestamp INTEGER NOT NULL, 
    updated_timestamp INTEGER, 
    thread_id INTEGER, 
    sender_id INTEGER, 
    recipient_id INTEGER, 
    PRIMARY KEY (id), 
    CONSTRAINT fk_messages_recipient_id FOREIGN KEY(recipient_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT fk_messages_sender_id FOREIGN KEY(sender_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT fk_messages_thread_id FOREIGN KEY(thread_id) REFERENCES threads (id) ON DELETE CASCADE
);

CREATE INDEX ix_messages_id ON messages (id);

CREATE TABLE thread_participants_association (
    thread_id INTEGER NOT NULL, 
    user_id INTEGER NOT NULL, 
    PRIMARY KEY (thread_id, user_id), 
    CONSTRAINT fk_thread_participants_association_thread_id FOREIGN KEY(thread_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT fk_thread_participants_association_user_id FOREIGN KEY(user_id) REFERENCES threads (id) ON DELETE RESTRICT
);

CREATE TABLE thread_chat_session_association (
    thread_id INTEGER NOT NULL, 
    chat_session_id INTEGER NOT NULL, 
    PRIMARY KEY (thread_id, chat_session_id), 
    CONSTRAINT fk_thread_chat_session_association_chat_session_id FOREIGN KEY(chat_session_id) REFERENCES chat_sessions (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_thread_chat_session_association_thread_id FOREIGN KEY(thread_id) REFERENCES threads (id) ON DELETE RESTRICT
);

UPDATE alembic_version SET version_num='440ab6100f42' WHERE alembic_version.version_num = '0200b703001e';

-- Running upgrade 440ab6100f42 -> 9a34da851371

CREATE TABLE threads_participants_association (
    thread_id INTEGER NOT NULL, 
    user_id INTEGER NOT NULL, 
    PRIMARY KEY (thread_id, user_id), 
    CONSTRAINT fk_threads_participants_association_thread_id FOREIGN KEY(thread_id) REFERENCES threads (id) ON DELETE CASCADE, 
    CONSTRAINT fk_threads_participants_association_user_id FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT
);

DROP TABLE thread_participants_association;

UPDATE alembic_version SET version_num='9a34da851371' WHERE alembic_version.version_num = '440ab6100f42';

-- Running upgrade 9a34da851371 -> ae83b3e6b657

UPDATE alembic_version SET version_num='ae83b3e6b657' WHERE alembic_version.version_num = '9a34da851371';

COMMIT;

