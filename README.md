# Uptime Monitor

This is a simplified website uptime monitoring application used to showcase Nuon's capabilities.

## Architecture

### Tech Stack

- **Backend**: Python, FastAPI
- **Frontend**: JavaScript
- **Database**: PostgreSQL
- **Storage**: AWS S3

### Services

- **UI**: Nginx serving static HTML
- **API**: FastAPI application with background workers
- **Database**: PostgreSQL with automatic migrations
- **Storage**: LocalStack (S3 emulation for local dev)

## Local Development

1. Clone the repository:
```bash
git clone https://github.com/nuonco/uptime-monitor.git
cd uptime-monitor
```

2. Start all services:
```bash
docker compose up
```

3. Access the application:
   - UI: http://localhost:3000
   - API: http://localhost:8000
   - API Health Check: http://localhost:8000/livez
