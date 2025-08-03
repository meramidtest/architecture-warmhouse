# Smart Home MVP

This directory contains the minimal viable product (MVP) implementation of the smart home system with the following services:

## Architecture Overview

Based on the C4 container diagram, this MVP implements the core system boundaries with:

- **Device Configuration API** - Manages device registration and configuration
- **Device Management API** - Manages programmable logic, telemetry, and device commands  
- **Device Management Worker** - Processes device events and manages telemetry caching
- **IoT Gateway** - Handles device communication and commands
- **PostgreSQL Database** - Stores device, configuration, and management data
- **Redis Cache** - Caches device status and telemetry for fast access
- **RabbitMQ** - Handles async messaging between services

## Services

### 1. Device Configuration Service (Port 8081)
**Location**: `./device-configuration/`

Python Flask application that implements the Configuration API:
- Device registration and management
- Location (home) management
- Device configuration management
- User access control
- Integration with IoT Gateway
- RabbitMQ event publishing

**API Endpoints**:
- `GET/POST /api/v1/locations` - Location management
- `GET/POST /api/v1/devices` - Device management
- `GET/POST /api/v1/devices/{id}/configurations` - Configuration management

### 2. Device Management Service (Port 8082)
**Location**: `./device-management/api/`

Python Flask application that implements the Management API:
- Programmable logic CRUD operations for device automation
- Historical telemetry data retrieval and management
- Device command forwarding to IoT Gateway
- PostgreSQL integration with separate database

**API Endpoints**:
- `GET/POST /api/v1/devices/{id}/logic` - Programmable logic management
- `PUT/DELETE /api/v1/devices/{id}/logic/{logic_id}` - Logic update/delete
- `GET /api/v1/devices/{id}/telemetry` - Telemetry retrieval
- `POST /api/v1/devices/{id}/commands` - Device command sending

**Key Features**:
- Uses separate `management_db` PostgreSQL database
- Implements tables: Device, DeviceCustomLogic, Telemetry
- Forwards commands to IoT Gateway via HTTP API
- User context via `User-ID` header

### 3. Device Management Worker
**Location**: `./device-management/worker/`

Go worker that processes device events from RabbitMQ:
- Consumes device registered/updated events from "devices" topic  
- Stores/updates devices in management database
- Fetches device status from IoT Gateway
- Caches device status and telemetry in Redis
- Provides fast data access for management API

**Key Features**:
- Event-driven processing via RabbitMQ
- Redis caching with TTL (5min status, 1hr telemetry)
- IoT Gateway integration for real-time status
- Automatic database synchronization

### 4. IoT Gateway (Port 8080)
**Location**: `./iotgateway/`

Existing IoT Gateway service for device communication.

### 5. Supporting Infrastructure
- **PostgreSQL** (Port 5432) - Primary database for device and management data
- **Redis** (Port 6379) - High-speed cache for device status and telemetry
- **RabbitMQ** (Port 5672, Management 15672) - Message broker for event-driven communication

## Quick Start

### 1. Start All Services
```bash
cd architecture-pro-warmhouse/mvp
docker-compose up -d
```

### 2. Check Service Health
```bash
# Device Configuration API
curl http://localhost:8081/health

# Device Management API
curl http://localhost:8082/health

# IoT Gateway
curl http://localhost:8080/health
```

### 3. Run Integration Tests
```bash
# Test Device Configuration API
./test-device-config.sh

# Test Device Management API
./test-device-management.sh

# Test Device Management Worker
./test-worker-simple.sh
```

## Service URLs

- **Device Configuration API**: http://localhost:8081
- **Device Management API**: http://localhost:8082
- **IoT Gateway**: http://localhost:8080
- **Redis**: localhost:6379
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)
- **PostgreSQL**: localhost:5432 (postgres/postgres)
  - Database: `device_config` (Configuration service)
  - Database: `management_db` (Management service)

## Example Workflow

1. **Create a Location**:
   ```bash
   curl -X POST http://localhost:8081/api/v1/locations \
     -H "Content-Type: application/json" \
     -H "User-ID: $(uuidgen)" \
     -d '{"name": "My Home"}'
   ```

2. **Register a Device**:
   ```bash
   curl -X POST http://localhost:8081/api/v1/devices \
     -H "Content-Type: application/json" \
     -H "User-ID: your-user-id" \
     -d '{
       "location_id": "location-uuid",
       "serial_id": "SN123456789",
       "name": "Living Room Thermostat",
       "type": "thermostat"
     }'
   ```

3. **Configure Device**:
   ```bash
   curl -X POST http://localhost:8081/api/v1/devices/{device-id}/configurations \
     -H "Content-Type: application/json" \
     -H "User-ID: your-user-id" \
     -d '{
       "config_name": "temperature_threshold",
       "config_value": "22.5",
       "config_type": "number"
     }'
   ```

## Authentication

All API requests require a `User-ID` header with a UUID identifying the user.

## Database Schema

The system uses the following main tables:
- `locations` - Homes/locations where devices are installed
- `devices` - Registered IoT devices
- `device_configurations` - Configuration parameters for devices
- `location_to_device` - User access control for devices

## Messaging

Device events are published to RabbitMQ `devices` queue with:
- Device registration events
- Device update events

These events are consumed by other services in the system (like the Management Worker in the full architecture).

## Development

### Adding New Features
1. Update the Flask app in `device-configuration/app.py`
2. Update database schema in `database.py`
3. Rebuild and restart: `docker-compose up --build device-configuration`

### Debugging
- View logs: `docker-compose logs -f device-configuration`
- Connect to database: `psql -h localhost -U postgres -d device_config`
- Check RabbitMQ queues: http://localhost:15672

## Production Considerations

This is a minimal MVP. For production, consider:
- Add proper authentication/authorization (JWT, OAuth)
- Add input validation and sanitization
- Add comprehensive error handling
- Add monitoring and logging
- Add API rate limiting
- Use connection pooling for database
- Add database migrations
- Add comprehensive tests
- Add API documentation (Swagger UI)
- Use environment-specific configurations
- Add security headers and HTTPS 