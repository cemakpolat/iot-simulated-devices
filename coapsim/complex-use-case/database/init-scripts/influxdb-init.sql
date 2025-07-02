-- database/init-scripts/influxdb-init.sql
-- This script runs automatically when the InfluxDB Docker container starts for the first time
-- due to `volumes: - ./database/init-scripts:/docker-entrypoint-initdb.d`.

-- For InfluxDB 2.x, the DOCKER_INFLUXDB_INIT_* environment variables in docker-compose.yml
-- usually handle the initial setup of organization, bucket, user, and admin token.
-- This SQL script is more typically used for granular permissions or additional buckets
-- after the initial setup.

-- Example: You could create another bucket or user here if your init vars didn't cover it.
-- CREATE BUCKET another_bucket WITH ORGANIZATION thermostat-org;
-- CREATE USER another_user WITH PASSWORD 'another_password';
-- GRANT READ ON another_bucket TO another_user;
-- GRANT WRITE ON another_bucket TO another_user;

-- For this project, the docker-compose.yml environment variables handle the basic setup.
-- This file exists to satisfy the directory structure and for future expansion.