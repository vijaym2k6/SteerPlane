# Running SteerPlane for Several Teams

This guide sets up one SteerPlane server (API, dashboard and Postgres) that
several teams share. Each team gets its own API key. A team's runs are visible
to that team and to the admin, and to nobody else.

It uses `docker-compose.hosted.yml`. For a single-user local setup, use the
regular `docker-compose.yml` instead (see [Getting Started](getting-started.md)).

## What you need

- A Linux server with Docker and Docker Compose v2.
- Two HTTPS addresses that point at the server, for example
  `https://app.example.com` (dashboard) and `https://api.example.com` (API).
- A reverse proxy that terminates HTTPS and forwards to the server's local
  ports. Caddy is the shortest route (it gets certificates automatically):

  ```
  app.example.com {
      reverse_proxy 127.0.0.1:3000
  }
  api.example.com {
      reverse_proxy 127.0.0.1:8000
  }
  ```

## 1. Configure

```bash
cp .env.hosted.example .env.hosted
```

Fill in every value marked REQUIRED:

| Variable | What to put |
|---|---|
| `POSTGRES_PASSWORD` | A long random value |
| `STEERPLANE_ADMIN_TOKEN` | A long random value. This is the admin login |
| `STEERPLANE_DASHBOARD_URL` | The dashboard's HTTPS address |
| `STEERPLANE_PUBLIC_API_URL` | The API's HTTPS address |

Generate the two random values with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

`.env.hosted` is git-ignored. Keep it that way.

## 2. Start

```bash
docker compose -f docker-compose.hosted.yml --env-file .env.hosted up -d --build
```

The API runs database migrations on startup. Check it is up:

```bash
curl https://api.example.com/health
```

Compared with the local compose file, this one always turns run auth on
(`STEERPLANE_REQUIRE_RUN_AUTH=true`), requires the admin token, does not publish
the Postgres port, and binds the API and dashboard to `127.0.0.1` so only the
reverse proxy can reach them.

## 3. Create a key for each team

1. Open the dashboard, click **Sign In**, and paste the admin token.
2. Go to **API Keys** and click **Create Key**. Name it after the team. The
   key's cost and rate limits apply to calls the team makes through the
   gateway. SDK runs use the limits the team sets in code.
3. Copy the key (it starts with `sk_sp_`). It is shown only once.
4. Send it to the team over a private channel.

You can also create keys with the API:

```bash
curl -X POST https://api.example.com/api-keys/ \
  -H "X-SteerPlane-Admin-Token: $STEERPLANE_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "team-acme", "max_cost_usd": 20}'
```

## 4. What each team does

Point the SDK at the server with their key:

```python
from steerplane import guard

@guard(
    api_url="https://api.example.com",
    api_key="sk_sp_...",
    max_cost_usd=10,
    max_steps=100,
)
def run_agent():
    ...
```

Or set `STEERPLANE_API_URL` and `STEERPLANE_API_KEY` in the environment.

To see their runs, a team opens the dashboard, clicks **Sign In** and pastes
their `sk_sp_` key. They see only their own runs. The **API Keys** and
**Policies** screens stay admin-only.

## 5. Check the isolation yourself

With two team keys, `KEY_A` and `KEY_B`:

```bash
# No key: refused
curl -s -o /dev/null -w "%{http_code}\n" https://api.example.com/runs          # 401

# Each team lists only its own runs
curl -s https://api.example.com/runs -H "Authorization: Bearer $KEY_A"

# A team cannot read another team's run
curl -s -o /dev/null -w "%{http_code}\n" \
  https://api.example.com/runs/<a run id owned by team B> \
  -H "Authorization: Bearer $KEY_A"                                             # 403
```

## Notes

- Enforcement on this server is kill mode. The SDK's `enforcement="alert"`
  option needs the human-approval backend, which this stack does not include,
  so alert mode fails closed (the run is terminated) here.
- Back up the `pgdata` volume. It holds every run.
- Keys can be deactivated or deleted from the **API Keys** screen at any time.
