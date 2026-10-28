# WasteWise Deployment Guide

## Local development

Use `setup_guide.md`. Run backend and frontend in separate terminals. Use seeded demo data and set `DEMO_MODE=true` only for local/demo environments.

## Docker Compose target

The repository should eventually provide:
- `frontend`: production static build served by a web server
- `api`: FastAPI application
- `db`: PostgreSQL with PostGIS where needed

Example `docker-compose.yml` starter (adjust image tags and health checks after implementation):

```yaml
services:
  db:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_DB: wastewise
      POSTGRES_USER: wastewise
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U wastewise -d wastewise"]
      interval: 5s
      timeout: 5s
      retries: 10

  api:
    build: ./backend
    env_file: .env
    environment:
      DATABASE_URL: ${DATABASE_URL}
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

This is a starter configuration, not a complete production hardening profile. Do not expose the database port publicly in production.

## Environment variables

- `APP_ENV`: development / test / production
- `APP_SECRET_KEY`: random secret for signing/session features if used
- `DATABASE_URL`: database connection
- `CORS_ORIGINS`: comma-separated allowed frontend origins
- `DEMO_MODE`: enable simulation-only endpoints
- `LOG_LEVEL`
- `ROUTING_PROVIDER`: local / configured provider
- `ROUTING_API_KEY`: optional secret; never returned by settings endpoint
- `FUEL_PRICE_PER_LITRE`: configurable assumption
- `FUEL_CONSUMPTION_L_PER_100KM`: configured vehicle default
- `LLM_PROVIDER`, `LLM_API_KEY`: optional; not required for core MVP

## Production checklist

- Use TLS and a trusted reverse proxy/load balancer.
- Use strong secret values from a secret manager.
- Restrict CORS to known origins.
- Disable demo simulator endpoints.
- Add authentication, roles, rate limits, and audit logging.
- Run Alembic migrations as a controlled release step.
- Back up PostgreSQL and test restore procedures.
- Configure database connection limits and timeouts.
- Configure health checks, structured logs, metrics, and error reporting.
- Pin dependencies and scan for vulnerabilities.
- Apply upload size/type limits if image uploads are enabled.
- Confirm map tile and routing provider terms, quotas, and attribution.
- Do not advertise actual fuel savings or forecast accuracy without measured evaluation.
