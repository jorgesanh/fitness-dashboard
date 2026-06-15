# Getting it online

You asked to not have to start this from the console and to have it "online."
There are two honest paths, with a real trade-off between **reliability** and a
**public URL**. Read this before picking one.

## The two constraints that shape everything

1. **Garmin rate-limits / blocks datacenter IPs.** Logging in from your home
   (residential) IP works. Logging in from a cloud host (Streamlit Cloud, a VPS,
   etc.) frequently returns HTTP 429 or gets bot-challenged. We already saw 429s
   even from your home IP during testing — from a datacenter it's worse.
2. **Your data lives in local files** (`fitness.db` and the cached token in
   `~/.garminconnect`). Most free cloud hosts have an **ephemeral** filesystem
   that resets on every redeploy/sleep — which would wipe your weight history,
   the whole point of the app.

So "always-on public cloud URL" fights the design. Here's how to get what you
actually want.

---

## Option A — Run locally, always-on (recommended)

Reliable Garmin sync, data persists, reachable from your phone. This is the
right default for a personal health app.

**1. Launch without the console:** double-click **`start.bat`**. It activates the
venv and serves on your network. Open `http://<your-PC-ip>:8501` on your phone
(same Wi-Fi). Your PC's network IP during setup was `192.168.1.36`, so
`http://192.168.1.36:8501`.

**2. Auto-start on login (so you never start it manually):** Windows Task
Scheduler →
- Create Task → *Trigger:* "At log on" →
- *Action:* Start a program → `C:\Users\josah\fitness-dashboard\start.bat` →
- (optional) check "Run whether user is logged on or not."

Now it's running whenever your PC is on; just open the URL on your phone.

**3. Reach it from anywhere (not just home Wi-Fi):** install
[Tailscale](https://tailscale.com) on your PC and phone (free personal tier).
You get a private IP that works from any network — `http://<tailscale-ip>:8501` —
with no port-forwarding and without exposing the app to the public internet.

---

## Option B — Streamlit Community Cloud (public URL)

A genuine `https://...streamlit.app` URL, deployed straight from the GitHub repo.
Free. **But** mind the two constraints above:

- **Garmin login may fail from Streamlit's IP** (429 / bot challenge). If it does,
  there's no fix from your side except retrying — it's Garmin's anti-automation.
- **The filesystem is ephemeral.** `fitness.db` and the token cache reset on each
  redeploy and after the app sleeps. Without a persistent database, **you lose
  your weight history and re-do MFA constantly.** This makes plain Streamlit Cloud
  a poor fit as-is.

To make Option B viable you'd swap the local SQLite for a hosted Postgres. You
already use **Supabase** (there's a `.supabase` dir in your home folder), so that's
the natural choice — a small change to `db.py` to talk to Supabase Postgres
instead of SQLite, plus storing the Garmin token in the DB.

**If you want Option B, tell me and I'll wire up Supabase persistence.** I didn't
do it pre-emptively because it's a real change beyond the original local-app scope.

### If you still want to deploy as-is (accepting the caveats)

1. Push to GitHub (already done — see README).
2. Go to https://share.streamlit.io → "New app" → pick this repo → `app.py`.
3. In *Advanced settings → Secrets*, add:
   ```toml
   GARMIN_EMAIL = "you@example.com"
   GARMIN_PASSWORD = "your-garmin-password"
   ```
   (The app reads these via `os.getenv`, so Streamlit secrets work directly.)
4. Deploy. Expect possible Garmin 429s and data resets per the caveats above.

---

## My recommendation

**Option A** (local always-on + Tailscale) for a personal tracker: Garmin sync is
reliable from your home IP, your weight history is safe, and Tailscale gives you
phone access from anywhere without making your health data public.

Reach for **Option B + Supabase** only if you specifically want a public URL and
are OK with me migrating the storage layer — say the word and I'll do it.
