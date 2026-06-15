# Deploying online (Supabase + Streamlit Cloud)

This app is wired for a **public URL** with your data living in **Supabase
Postgres** so nothing is lost between deploys. The architecture works around the
one hard constraint — **Garmin blocks logins from datacenter IPs** — by splitting
the work:

```
        ┌─────────────────────────┐         ┌──────────────────────┐
        │  Streamlit Community     │  reads/ │   Supabase Postgres  │
        │  Cloud (public URL)      │◀──────▶│   (your data)         │
        │  • weight entry          │  writes │   garmin_daily        │
        │  • dashboard / charts    │         │   weight              │
        └─────────────────────────┘         └──────────▲───────────┘
                                                        │ writes
                                            ┌───────────┴───────────┐
                                            │  sync_job.py on your   │
                                            │  home PC (residential  │
                                            │  IP → Garmin works)    │
                                            └────────────────────────┘
```

- The **cloud app** does everything that doesn't need Garmin: logging weight and
  showing trends/recovery. It reads and writes Supabase.
- A tiny **local job** (`sync_job.py`) pulls Garmin on your home PC and writes the
  same Supabase DB. Scheduled a few times a day, your cloud dashboard always has
  fresh Garmin data.

The Supabase project, schema, and your 90-day history are **already set up** —
your `DATABASE_URL` is in your local `.env` and saved in
`.supabase_database_url.txt` (both git-ignored).

---

## Step 1 — Deploy the app to Streamlit Community Cloud (~2 min, your click)

Streamlit Cloud has no API for creating a deployment — it needs a GitHub OAuth
click in your browser. This is the only manual step.

1. Go to **https://share.streamlit.io** and sign in with the **same GitHub
   account that owns the repo** (`jorgesanh`).
2. **Create app → Deploy a public app from GitHub.**
3. Pick:
   - **Repository:** `jorgesanh/fitness-dashboard`
   - **Branch:** `master`
   - **Main file path:** `app.py`
4. Click **Advanced settings → Secrets** and paste (the real value is in your
   local `.supabase_database_url.txt`):
   ```toml
   DATABASE_URL = "postgresql://postgres.pbukfofybkxfnbtsbbox:<db-password>@aws-1-us-east-1.pooler.supabase.com:5432/postgres"
   ```
5. **Deploy.** Your public URL will be something like
   `https://fitness-dashboard-<random>.streamlit.app` (you can rename it in app
   settings). Open it on any device — weight logging and the dashboard work
   immediately against Supabase.

> The repo is **private**. Streamlit Cloud's free tier can still deploy it because
> you authorize it via GitHub OAuth. If it ever can't see the repo, grant Streamlit
> access to private repos in the GitHub authorization prompt.

---

## Step 2 — Keep Garmin data fresh from your home PC

The cloud app can't log into Garmin. Run the sync job locally instead.

**One-off:**
```powershell
cd C:\Users\josah\fitness-dashboard
.venv\Scripts\python.exe sync_job.py            # incremental
.venv\Scripts\python.exe sync_job.py --backfill # force 90-day refill
```

**Scheduled (set-and-forget) — Windows Task Scheduler:**
1. Create Task → **Trigger:** Daily, repeat every 6 hours.
2. **Action:** Start a program
   - Program: `C:\Users\josah\fitness-dashboard\.venv\Scripts\python.exe`
   - Arguments: `sync_job.py`
   - Start in: `C:\Users\josah\fitness-dashboard`
3. It reads `DATABASE_URL` + Garmin creds from `.env` and writes to Supabase.

The first Garmin login (and any MFA) is handled once when you run the app or the
job locally; the cached token in `~/.garminconnect` is reused after that.

---

## Notes & caveats (honest)

- **Garmin from the cloud:** the in-app "Sync Garmin now" button will usually fail
  on Streamlit Cloud with a rate-limit message — that's expected; it's why
  `sync_job.py` exists. The app catches it and keeps showing Supabase data.
- **Why the pooler URL:** Supabase's direct host (`db.<ref>.supabase.co`) is
  IPv6-only; Streamlit Cloud needs IPv4, so we use the session pooler
  (`...pooler.supabase.com:5432`).
- **One database everywhere:** your local app, the sync job, and the cloud app all
  point at the same Supabase via `DATABASE_URL`, so there's a single source of
  truth. Remove `DATABASE_URL` from `.env` if you ever want the local app to fall
  back to the standalone SQLite file.
- **Rotating the DB password:** Supabase dashboard → Project Settings → Database →
  Reset password, then update `DATABASE_URL` in `.env` and in Streamlit secrets.

## Alternative: keep it fully local

If you'd rather not use the cloud at all, see **Option A** in the project history:
run `start.bat`, auto-start via Task Scheduler, and use Tailscale for phone access.
Remove `DATABASE_URL` from `.env` to use the local SQLite database.
