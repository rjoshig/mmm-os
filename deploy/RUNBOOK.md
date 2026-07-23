# Deployment & Operations Runbook (Phase 11)

Concrete operational guidance for running `mmm-os` in dev/stage/prod. This
complements the design in [`docs/phases/phase-11-deployment-infrastructure.md`](../docs/phases/phase-11-deployment-infrastructure.md)
and the two-database strategy in [`docs/architecture.md`](../docs/architecture.md) §2.

> **Golden rules that constrain deployment**
> - Config comes from the **environment** (12-factor). Never bake secrets into
>   images. All secrets flow through the `SecretStore` (CC-12).
> - The backend and UI have **independent databases**; both are SQLite in dev and
>   Postgres in stage/prod, selected by URL only.
> - Migrations are applied by the app image (`entrypoint.sh migrate`) — never by
>   hand-editing schema.

---

## 1. Images

| Image | Build context | Serves |
|---|---|---|
| API/worker | `./Dockerfile` | FastAPI (`uvicorn`), migrations, in-process scheduler |
| Front-end | `./front-end/Dockerfile` | Next.js standalone server |

Build locally:

```bash
docker build -t mmm-os-api:local .
docker build -t mmm-os-web:local ./front-end
```

The API entrypoint takes a role: `api` (migrate + serve, the default), `migrate`
(one-shot), or any command (escape hatch). Run migrations as a **pre-deploy job**
before rolling new app pods:

```bash
docker run --rm -e BACKEND_DATABASE_URL=… -e SECRET_MASTER_KEY=… mmm-os-api:local migrate
```

## 2. Environments & promotion

| Env | Backend DB | UI DB | Auth | Notes |
|---|---|---|---|---|
| dev | SQLite file | SQLite file | off | local, `uvicorn --reload` + `next dev` |
| stage | Postgres (managed) | Postgres (managed) | on | parity with prod; smoke + load runs here |
| prod | Postgres (managed, HA) | Postgres (managed) | on | per-region; enterprise silos as needed |

Promotion is **image-based**: the exact image that passed stage is promoted to
prod. Schema changes ship as migrations that run before the new image serves
traffic (expand/contract for zero-downtime — add columns nullable/`server_default`
first, backfill, then tighten in a later release; this repo already uses
`server_default` backfills for NOT NULL adds).

## 3. Required configuration (env)

| Variable | Purpose |
|---|---|
| `BACKEND_DATABASE_URL` | Backend Postgres URL (`postgresql+psycopg://…`). |
| `SECRET_MASTER_KEY` | Master key for the local `SecretStore` backend (or configure a managed KMS backend). |
| `AUTH_ENABLED` | `true` in stage/prod. |
| `SCHEDULER_ENABLED` | `true` on exactly one API replica (or a dedicated worker) to avoid duplicate scheduling. |
| `MULTI_DB_ROUTING_ENABLED` | `true` to enable per-customer silo routing (§5). |
| `CORS_ALLOW_ORIGINS` | The front-end origin(s). |
| `MMM_OS_WORKERS` | uvicorn worker processes per pod. |
| UI: `DATABASE_URL`, `MMM_OS_API_URL` | UI database + backend base URL for the Next rewrite. |

## 4. Secret injection (CC-12)

- Secrets are injected as env vars **at deploy time** from the platform secret
  manager — never committed, never in an image layer, never logged.
- `SECRET_MASTER_KEY` gates the local encrypted `SecretStore`; a managed KMS/vault
  backend plugs in at `secrets/factory.py` without changing callers (OQ-00.6-2).
- Partner tokens + silo DB URLs live **inside** the `SecretStore` (only a
  `secret_ref` is in the database).

## 5. Enterprise silo provisioning (ties to Slice 7.2)

To move an enterprise customer onto a dedicated database:

1. Provision a dedicated Postgres database for the customer (managed instance or
   schema, per isolation requirements).
2. Ensure `MULTI_DB_ROUTING_ENABLED=true` on the API.
3. Set the customer to **enterprise** tier, then call
   `PUT /api/v1/customers/{id}/isolation` with `{"mode":"silo","database_url":"…"}`.
   This stores the URL in the `SecretStore`, provisions the schema
   (`create_all`), and seeds the customer's tenant + user rows. (For Postgres,
   pre-run `alembic upgrade head` against the dedicated URL instead of relying on
   `create_all`.)
4. Verify: a request to `/api/v1/tenants/{id}/…` reads/writes the dedicated DB and
   the pool has none of that customer's business data.
5. To roll back to the shared pool: `{"mode":"pool"}` (clears the stored URL).

Control-plane (auth/sessions/customer registry) always stays on the pool; only
tenant-scoped business queries route. See architecture §3.1.

## 6. Autoscaling & workers (ADR-007)

- The API is stateless behind a load balancer → scale horizontally on CPU/RTT.
- The batch queue provides **per-tenant round-robin fairness** (Phase 7). In prod
  the queue backend is Celery + Redis; scale worker replicas on queue depth.
- **The in-process scheduler must run on exactly one replica** (or a dedicated
  worker) to avoid double-firing due syncs. With silos enabled, the scheduler
  routes each silo customer to its own engine (Slice 7.6).

## 7. Health & rollout

- Liveness/readiness probe: `GET /health` (returns env + status).
- Roll out new images after the migration job succeeds; roll back by redeploying
  the previous image (migrations are expand/contract, so the prior image keeps
  working against the new schema).

## 8. Local prod-like stack

`docker compose up --build` starts Postgres + API + front-end wired together
(see `docker-compose.yml`) for parity testing before shipping.
