#!/bin/sh
# Runs once when the Postgres volume is first created.
#
# The API connects as `hr_app`: a LOGIN role that owns no tables and is not a superuser,
# so Row-Level Security policies always apply to it. Table ownership stays with the
# migration role (POSTGRES_USER). Grants are issued by the Alembic migrations.
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE hr_app LOGIN PASSWORD '${APP_DB_PASSWORD}' NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
    GRANT CONNECT ON DATABASE "${POSTGRES_DB}" TO hr_app;
    GRANT USAGE ON SCHEMA public TO hr_app;
    CREATE EXTENSION IF NOT EXISTS vector;
EOSQL
