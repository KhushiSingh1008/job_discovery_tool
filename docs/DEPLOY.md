# Deploying GradGuide Jobs to Render

Production is a single Docker service:

- FastAPI serves the API **and** the built React app (one origin, no CORS setup).
- The scraper runs **inside** the service every 24 hours. Render Cron Jobs run as separate
  services and cannot reach the web service's disk, so they are not used.
- SQLite lives on a 1 GB persistent disk mounted at `/data`.

```
Browser ──► Render web service (Docker, 1 instance)
              ├─ /api/*        FastAPI
              ├─ /*            React build (index.html for client routes)
              ├─ scheduler     daily scrape → /data/jobs.db
              └─ disk /data    jobs.db (listings, tracker, scrape history)
```

## Cost

`render.yaml` deploys on the **free plan**. The free plan has no persistent disk and sleeps
after about 15 minutes idle (the first request after that takes ~1 minute to wake it). To
keep the app useful anyway, the image ships a snapshot database (`backend/seed/jobs.db`)
that is copied to `/data` whenever the container starts with no database, so listings are
there immediately; the scheduler refreshes them while the service is awake. Tracker entries
are lost on restart.

For a durable database, switch to **Starter (about $7/month) + $0.25/GB/month** and add
the disk (see the comment in `render.yaml`).

## First deploy

1. **Push the repository to GitHub** (the `render.yaml` and `Dockerfile` must be on the
   branch you deploy).
2. In Render: **Dashboard → New → Blueprint**, connect GitHub and pick the repository.
   Render reads `render.yaml` and proposes the `gradguide-jobs` web service with its disk.
3. When asked for `ANTHROPIC_API_KEY`:
   - **Leave it empty** to use the offline matcher and offline resume tips, or
   - **paste a key** from console.anthropic.com to enable AI suggestions. It is stored as a
     secret in Render, never in the repository. Rate limiting (30 resume requests per
     visitor per hour, `GG_RESUME_REQUESTS_PER_HOUR`) caps what strangers can spend.
4. Click **Apply**. The first build takes a few minutes (it builds the frontend, then the
   Python image).
5. The database starts empty. About a minute after the service starts, the scheduler runs
   the first scrape (roughly 20–30 minutes, because the scraper waits 1.5–3.5 s between
   requests to be polite). Jobs appear as each source finishes. Check progress at
   `https://<your-service>.onrender.com/api/meta/sources`.

## Checking it works

| Check | URL | Expect |
|---|---|---|
| Health | `/api/health` | `{"status": "ok", "listings": N, "last_scraped_at": ...}` |
| Scraper health | `/api/meta/sources` | each source with `last_run.status` = `ok` |
| App | `/` and a deep link such as `/tracker` | the app loads on both |
| API docs | `/docs` | FastAPI's interactive docs |

A source whose last run is `empty` fetched pages but parsed nothing: its site layout has
probably changed. The jobs page also shows "… could not be refreshed" for it.

## Configuration

| Variable | Default (image) | Purpose |
|---|---|---|
| `GG_DATABASE_PATH` | `/data/jobs.db` | SQLite file; must be on the disk |
| `GG_SCRAPE_INTERVAL_HOURS` | `24` | How often to scrape; `0` turns the scheduler off |
| `GG_SCRAPE_START_DELAY_SECONDS` | `60` | Wait after start-up before the first check |
| `GG_SCRAPER_REFRESH_DAYS` | `3` | Detail pages read this recently are not re-downloaded |
| `GG_LISTING_STALE_DAYS` | `30` | Listings unseen this long are closed |
| `GG_RESUME_REQUESTS_PER_HOUR` | `30` | Per-visitor limit on the resume tools |
| `ANTHROPIC_API_KEY` | unset | Enables Claude for match and resume suggestions |
| `GG_MATCH_MODEL` | `claude-opus-5-5` | Claude model for the resume tools |

## Running a scrape by hand

Render dashboard → the service → **Shell**:

```bash
python -m app.scraper.cli status          # last run and open listings per source
python -m app.scraper.cli run             # full scrape now (refuses if one is running)
python -m app.scraper.cli run --source studentjob --limit 20
```

## Run the production image locally

```bash
docker build -t gradguide-jobs .
docker run --rm -p 8000:8000 -v gradguide-data:/data gradguide-jobs
# open http://localhost:8000
```

## Notes and limits

- **One instance only.** SQLite and the in-process scheduler assume a single process; do not
  scale the service horizontally. (Moving to Postgres would be the step for that.)
- **Backups.** Render snapshots disks daily. To download one: Shell →
  `sqlite3 /data/jobs.db ".backup /data/backup.db"`, then copy it out.
- **Tracker data is shared.** The tracker has no accounts, so everyone using the deployed
  app shares one tracker. Fine for a demo; real users would need sign-in.
