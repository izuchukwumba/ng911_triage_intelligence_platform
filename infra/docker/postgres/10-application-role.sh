#!/bin/sh
# Runs once, when the PostgreSQL volume is first initialised. Creates the login
# role the API connects as: a member of ntip_app, which migration 0006 grants
# read and append access only. Migrations keep running as the table owner.
# (The entrypoint may source this file, so it does not change shell options.)
psql -v ON_ERROR_STOP=1 -v pw="$NTIP_API_DB_PASSWORD" \
     --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
CREATE ROLE ntip_app NOLOGIN;
CREATE ROLE ntip_api LOGIN PASSWORD :'pw' IN ROLE ntip_app;
SQL
