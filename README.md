# Uptime Monitor

This is a simplified website uptime monitoring application used to showcase Nuon's capabilities.

## Architecture

### Tech Stack

- **Backend**: Python, FastAPI
- **Frontend**: JavaScript
- **Database**: PostgreSQL
- **Storage**: AWS S3

## Local Development

1. Clone the repository:

```bash
git clone https://github.com/nuonco/uptime-monitor.git
cd uptime-monitor
```

2. Start all services:

```bash
docker compose up -d
```

3. Access the application:
   - UI: http://localhost:3000
   - API: http://localhost:8000
   - API Health Check: http://localhost:8000/livez
