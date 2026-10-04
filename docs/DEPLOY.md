# Deploying GradGuide Jobs to Render

Production is a single Docker service:

- FastAPI serves the API **and** the built React app (one origin, no CORS setup).
- The scraper can run **inside** the service on a schedule (`GG_SCRAPE_INTERVAL_HOURS`).
  It is **off on the free plan** (`0` in `render.yaml`) and every 24 hours on a paid plan
  with a disk. Render Cron Jobs run as separate services and cannot reach the web
  service's disk, so they are not used.
- SQLite lives at `/data/jobs.db`. On the free plan this is ephemeral and starts from the
  snapshot in `backend/seed/jobs.db`; on a paid plan, mount a disk at `/data` to keep it.

```
Browser ──► Render web service (Docker, 1 instance)
              ├─ /api/*        FastAPI
              ├─ /*            React build (index.html for client routes)
              ├─ scheduler     scrape every N hours → /data/jobs.db (off on the free plan)
              └─ /data         jobs.db (listings, tracker, scrape history)
```

## Cost

`render.yaml` deploys on the **free plan**. The free plan has no persistent disk and sleeps
after about 15 minutes idle (the first request after that takes ~1 minute to wake it). The
image ships a snapshot database (`backend/seed/jobs.db`) that is copied to `/data`
whenever the container starts with no database, so listings are there immediately.

The free deploy **serves that snapshot as it is**: the in-container scrape is turned off,
because a 20–30 minute scrape would be cut short when the instance sleeps and lost on the
next restart. The jobs page shows the snapshot's real age ("updated N days ago"). To
show newer listings, refresh the snapshot (see [Refreshing the snapshot](#refreshing-the-snapshot)).
Tracker entries are lost on every restart.

For a durable database that refreshes itself, switch to **Starter (about $7/month) +
$0.25/GB/month**, add the disk and set `GG_SCRAPE_INTERVAL_HOURS` back to `"24"` (see the
comment in `render.yaml`).

## First deploy

1. **Push the repository to GitHub** (the `render.yaml`, `Dockerfile` and
   `backend/seed/jobs.db` must be on the branch you deploy).
2. In Render: **Dashboard → New → Blueprint**, connect GitHub and pick the repository.
   Render reads `render.yaml` and proposes the `gradguide-jobs` web service (free plan).
3. When asked for `ANTHROPIC_API_KEY`:
   - **Leave it empty** to use the offline matcher and offline resume tips, or
   - **paste a key** from console.anthropic.com to enable AI suggestions. It is stored as a
     secret in Render, never in the repository. Rate limiting (30 resume requests per
     visitor per hour, `GG_RESUME_REQUESTS_PER_HOUR`) caps what strangers can spend.
4. Click **Apply**. The first build takes a few minutes (it builds the frontend, then the
   Python image).
5. The database starts from the bundled snapshot, so jobs show immediately, and the jobs
   page says how old they are. On the free plan nothing is scraped in the container; the
   listings change only when you refresh the snapshot and redeploy.

## Checking it works

| Check | URL | Expect |
|---|---|---|
| Health | `/api/health` | `{"status": "ok", "listings": N, "last_scraped_at": ...}` (on the free plan, the snapshot's date) |
| Scraper health | `/api/meta/sources` | each source with `last_run.status` = `ok` (on the free plan, the runs recorded in the snapshot) |
| App | `/` and a deep link such as `/tracker` | the app loads on both |
| API docs | `/docs` | FastAPI's interactive docs |

A source whose last run is `empty` fetched pages but parsed nothing: its site layout has
probably changed. The jobs page also shows "… could not be refreshed" for it.

## Refreshing the snapshot

The free deploy shows whatever `backend/seed/jobs.db` contains. To update it:

1. Scrape locally (from `backend/`, with the virtual environment active):

   ```bash
   python -m app.scraper.cli run
   python -m app.scraper.cli status     # check every source is ok
   ```

2. Rebuild the seed from `backend/data/jobs.db`. Work on a copy **outside the repository**
   so no `-wal`/`-shm` side files land in `backend/seed/`, then copy the finished file in:

   ```bash
   python - <<'EOF'
   import os, shutil, sqlite3, tempfile

   tmp = os.path.join(tempfile.mkdtemp(), "jobs.db")
   source = sqlite3.connect("data/jobs.db")
   target = sqlite3.connect(tmp)
   source.backup(target)                        # consistent copy, even mid-WAL
   source.close()
   target.execute("DELETE FROM applications")   # never ship anyone's tracker
   target.commit()
   assert target.execute("PRAGMA journal_mode=DELETE").fetchone()[0] == "delete"
   target.execute("VACUUM")
   assert target.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
   target.close()
   shutil.copyfile(tmp, "seed/jobs.db")
   print("seed/jobs.db rebuilt")
   EOF
   ```

   `journal_mode=DELETE` keeps every row in the one `jobs.db` file. A WAL-mode snapshot
   could hold rows in a `-wal` file that is never committed.

3. Commit `backend/seed/jobs.db` (never `backend/data/`) and push; Render redeploys with
   the new snapshot.

## Configuration

Every variable that needs a non-default value is set in `render.yaml`; every variable is
documented here.

| Variable | Default (image) | In `render.yaml` | Purpose |
|---|---|---|---|
| `GG_DATABASE_PATH` | `/data/jobs.db` | `/data/jobs.db` | SQLite file; on a paid plan, keep it on the disk |
| `GG_SCRAPE_INTERVAL_HOURS` | `24` | `0` (free plan) | How often to scrape in the container; `0` turns the scheduler off. Use `24` with a disk |
| `GG_SCRAPE_START_DELAY_SECONDS` | `60` | – | Wait after start-up before the first check |
| `GG_SCRAPER_REFRESH_DAYS` | `3` | – | Detail pages read this recently are not re-downloaded |
| `GG_LISTING_STALE_DAYS` | `30` | – | Listings unseen this long are closed |
| `GG_RESUME_REQUESTS_PER_HOUR` | `30` | `30` | Per-visitor limit on the resume tools |
| `ANTHROPIC_API_KEY` | unset | secret, set in the dashboard | Enables Claude for match and resume suggestions; blank means offline mode |
| `GG_MATCH_MODEL` | `claude-opus-5-5` | – | Claude model for the resume tools |

## Running a scrape by hand

Render dashboard → the service → **Shell**:

```bash
python -m app.scraper.cli status          # last run and open listings per source
python -m app.scraper.cli run             # full scrape now (refuses if one is running)
python -m app.scraper.cli run --source studentjob --limit 20
```

On the free plan the result lasts only until the next restart; refresh the snapshot
instead.

## Run the production image locally

```bash
docker build -t gradguide-jobs .
docker run --rm -p 8000:8000 -v gradguide-data:/data gradguide-jobs
# open http://localhost:8000
```

## Notes and limits

- **One instance only.** SQLite and the in-process scheduler assume a single process; do not
  scale the service horizontally. (Moving to Postgres would be the step for that.)
- **Backups** (paid plan with a disk). Render snapshots disks daily. To download one: Shell →
  `sqlite3 /data/jobs.db ".backup /data/backup.db"`, then copy it out.
- **Trackers are private per browser.** Each browser gets an anonymous id, so visitors never
  see each other's applications; there are no accounts. On the free plan trackers are also
  wiped on every restart.
