"""Headless Garmin -> database sync.

Run this on a machine with a residential IP (your home PC), where Garmin login
works. It writes into whatever DATABASE_URL points at — your Supabase Postgres —
so the cloud dashboard always has fresh Garmin data even though the cloud app
itself can't log into Garmin (datacenter IPs get rate-limited/blocked).

Usage:
    # one-off / scheduled incremental sync
    python sync_job.py

    # force a full 90-day backfill
    python sync_job.py --backfill

Schedule it (Windows Task Scheduler) to run a few times a day. See DEPLOY.md.
"""

import sys

import db
import garmin_sync


def main():
    full = "--backfill" in sys.argv
    db.init_db()

    result = garmin_sync.login()
    if isinstance(result, garmin_sync.LoginNeedsMFA):
        print("MFA required. Run the Streamlit app once locally to complete MFA "
              "and cache a token, then this job will reuse it.")
        return 1
    if isinstance(result, garmin_sync.LoginFailed):
        print(f"Login failed: {result.message}")
        return 1

    n = garmin_sync.sync(result.client, full_backfill=full,
                         progress=lambda frac, label: print(f"  {label} ({frac:.0%})"))
    print(f"Synced {n} day(s). DB now has {len(db.get_existing_garmin_dates())} "
          f"Garmin dates (latest {db.latest_garmin_date()}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
