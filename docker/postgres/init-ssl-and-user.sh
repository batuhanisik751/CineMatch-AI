#!/bin/bash
set -e

# ---------- Self-signed SSL certificate ----------
CERT_DIR="/var/lib/postgresql"
if [ ! -f "$CERT_DIR/server.crt" ]; then
    openssl req -new -x509 -days 3650 -nodes \
        -out "$CERT_DIR/server.crt" \
        -keyout "$CERT_DIR/server.key" \
        -subj "/CN=cinematch-postgres"
    chmod 600 "$CERT_DIR/server.key"
    chown postgres:postgres "$CERT_DIR/server.crt" "$CERT_DIR/server.key"
fi

# ---------- Limited-privilege application user ----------
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'cinematch_app') THEN
            CREATE ROLE cinematch_app WITH LOGIN PASSWORD '${CINEMATCH_APP_DB_PASSWORD:-cinematch_app_dev}';
        END IF;
    END
    \$\$;

    -- DML-only privileges (no DROP, CREATE TABLE, or superuser)
    GRANT CONNECT ON DATABASE cinematch TO cinematch_app;
    GRANT USAGE ON SCHEMA public TO cinematch_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO cinematch_app;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO cinematch_app;
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO cinematch_app;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO cinematch_app;
EOSQL
