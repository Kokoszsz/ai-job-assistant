-- ==============================================================================
-- AI-Powered Job Search Assistant - Database Initialization Script
-- ==============================================================================
-- This script runs automatically when the PostgreSQL container is first created.
-- It creates the database and sets up any initial configuration.

-- Create database if it doesn't exist (handled by POSTGRES_DB env var)
-- This file is for additional initialization if needed

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pg_trgm for text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE jobassistant TO postgres;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Database initialization completed at %', NOW();
END $$;
