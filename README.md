# Fat-loss & Recovery Dashboard

A local, single-file-runnable Streamlit dashboard that combines **Garmin Connect**
data with a **manual daily weight entry** to make your weekly fat-loss trend and
recovery state obvious at a glance.

- 7-day moving-average weight trend (the real signal; daily numbers are noise)
- Headline panel: 7-day avg weight, weekly rate (kg/wk), live maintenance
  **estimate**, and the implied daily deficit
- Status read on your rate: *on target / too aggressive / stalled*
- Recovery row: resting HR, sleep, Body Battery — flags under-recovery when
  resting HR rises while sleep and Body Battery fall
- 2w / 4w / 8w / all range selector
- Two-second weight logging, plus past-date backfill
- Manual "Sync Garmin now" button; shows cached data if Garmin is unreachable

Everything is stored locally in `fitness.db` (SQLite). Nothing leaves your machine
except the calls to Garmin Connect.

## Setup

Requires Python 3.10+.

```bash
cd fitness-dashboard

# (recommended) a virtual environment
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
```

### Credentials (`.env`)

Copy the example and fill in your Garmin Connect login:

```bash
cp .env.example .env
```

`.env` format:

```
GARMIN_EMAIL=you@example.com
GARMIN_PASSWORD=your-garmin-password
```

`.env` is git-ignored. Credentials are never hardcoded. After the first
successful login, Garmin's auth token is cached at `~/.garminconnect` so the app
doesn't re-login every run.

**MFA:** if your account uses multi-factor auth, the app won't crash — it shows a
field in the sidebar to enter your code and completes the login.

## Run

```bash
streamlit run app.py
```

On first launch it backfills the last 90 days from Garmin; on later launches it
syncs only the days missing since the last pull (and re-fetches today, since
today's numbers are still accumulating).

### Use it from your phone

Streamlit serves on your local network. Run:

```bash
streamlit run app.py --server.address 0.0.0.0
```

Then open `http://<your-computer-ip>:8501` from your phone on the same Wi-Fi.

## How the numbers work

- **Weekly rate** is the slope of the 7-day moving average over the trailing
  14 days, scaled to kg/week. Negative = losing.
- **Maintenance estimate** is your average daily Garmin expenditure over the same
  window — a live *estimate*, not ground truth.
- **Implied daily deficit** comes from the weight trend using ≈7700 kcal per kg.
- **Status:** on target = 0.4–0.7 kg/wk loss, too aggressive = >0.8 kg/wk,
  stalled = moving average flat for 2+ weeks.

## Files

| File | Purpose |
|------|---------|
| `app.py` | Streamlit UI |
| `garmin_sync.py` | Garmin login (native SSO + MFA), per-day metric pull, sync |
| `db.py` | SQLite storage (`garmin_daily`, `weight`) |
| `metrics.py` | Moving average, rate, status read, recovery flags |
| `config.py` | Paths, targets, constants |

## Notes

- Uses `python-garminconnect`'s native auth engine (the official Connect mobile
  SSO flow). It does not use `garth` directly.
- If Garmin is unreachable, sync fails gracefully and the dashboard shows the
  last cached data.
- **Recovery metrics depend on your device.** Resting HR and Body Battery only
  appear if your Garmin records wrist heart rate. On devices without an optical
  HR sensor (or with HR tracking off) those panels stay empty and the recovery
  read falls back to a **sleep-only** signal — this is expected, not an error.
- Hosting / "always-on" / phone-from-anywhere options are in
  [DEPLOY.md](DEPLOY.md).
