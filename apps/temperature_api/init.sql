-- Initial setup for IoT Gateway PostgreSQL database
-- This file is automatically executed when the PostgreSQL container starts

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- The tables will be created automatically by SQLAlchemy when the Flask app starts
-- This file is mainly for any additional setup or initial data that might be needed

-- You can add custom functions, triggers, or additional setup here
-- For example, creating indexes for better performance:

-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sensor_location ON sensor(location);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sensor_type ON sensor(type);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sensor_status ON sensor(status); 