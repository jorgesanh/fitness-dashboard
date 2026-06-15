"""Shared configuration and constants for the fitness dashboard."""

import os

# --- Paths ---------------------------------------------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "fitness.db")

# Where the garminconnect library caches its OAuth tokens so it doesn't
# re-login on every run. Keeping it in the user's home (~/.garminconnect)
# matches the library's own convention.
TOKEN_STORE = os.path.expanduser(os.getenv("GARMIN_TOKENSTORE", "~/.garminconnect"))

# --- Profile / reference values -----------------------------------------
# Used only as a fallback reference. The dashboard prefers a *live*
# maintenance estimate derived from Garmin expenditure over the window.
REFERENCE_MAINTENANCE_KCAL = 2850

# Energy density of body-mass change. ~7700 kcal per kg is the standard
# rule-of-thumb for fat mass; used to translate weight trend into an
# implied daily energy deficit.
KCAL_PER_KG = 7700

# --- Sync ----------------------------------------------------------------
BACKFILL_DAYS = 90  # how far back to pull on first run

# --- Fat-loss targets (kg lost per week) ---------------------------------
TARGET_RATE_LOW = 0.4
TARGET_RATE_HIGH = 0.7
AGGRESSIVE_RATE = 0.8

# A 14-day moving-average change smaller than this (kg) counts as "stalled".
STALL_BAND_KG = 0.2

# --- Training -----------------------------------------------------------
# Session types you log. `cat` groups them for the weekly summary; `color`
# drives the training chart. Tweak these to match your plan.
TRAINING_TYPES = [
    {"key": "F1", "label": "F1", "cat": "Lift", "color": "#10b981"},
    {"key": "F2", "label": "F2", "cat": "Lift", "color": "#34d399"},
    {"key": "F3", "label": "F3", "cat": "Lift", "color": "#6ee7b7"},
    {"key": "Ultimate", "label": "Ultimate", "cat": "Sport", "color": "#60a5fa"},
    {"key": "Running", "label": "Run", "cat": "Cardio", "color": "#fbbf24"},
]

# Weekly training target (sessions/week) — shown as context in the summary.
WEEKLY_SESSION_TARGET = 5
