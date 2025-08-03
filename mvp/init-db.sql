-- Database initialization script for Smart Home MVP
-- This script creates the necessary databases for the system

-- Create management database for device-management service
CREATE DATABASE management_db;

-- Grant permissions to postgres user (already the owner)
GRANT ALL PRIVILEGES ON DATABASE management_db TO postgres; 