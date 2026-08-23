-- 03_security.sql

-- Create a new user specifically for the AI agent
CREATE ROLE ai_analyst WITH LOGIN PASSWORD 'ai_secure_pass_123';

-- Grant access to connect to the database
GRANT CONNECT ON DATABASE enterprise_db TO ai_analyst;

-- Grant usage on the default 'public' schema
GRANT USAGE ON SCHEMA public TO ai_analyst;

-- Grant SELECT (read-only) permission on all existing tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ai_analyst;

-- Ensure that if we add new tables later, this user automatically gets SELECT access
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO ai_analyst;