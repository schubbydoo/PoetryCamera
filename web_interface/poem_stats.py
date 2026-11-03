"""
Activity and health records for Poetry Camera.

Every poem is recorded as a standard propkit activity event (logs/events.jsonl), which feeds the shared Dashboard.
It is also appended to poem_log.jsonl, the older plain log that the backfill below reads.
Health events (paper, wifi, internet, printer, restarts, AI trouble) go to event_log.jsonl; they are recorded
only, not displayed (outages are shown on the System tab from netguard's log).

Nothing here may ever raise or slow down taking and printing a photo.
"""

import json
import os
import threading
from datetime import datetime

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
LOG_PATH = os.path.join(BASE, "poem_log.jsonl")
EVENTS_PATH = os.path.join(BASE, "event_log.jsonl")
EVENTS_DIR = os.environ.get("POETRYCAMERA_EVENTS_DIR") or os.path.abspath(os.path.join(BASE, "logs"))  # propkit activity events (gitignored)

_lock = threading.Lock()
_recorder = None


def _rec():
    global _recorder
    if _recorder is None:
        from propkit.stats import Recorder
        _recorder = Recorder(EVENTS_DIR)
    return _recorder


def record_poem(provider, model, seconds, fallback=False, when=None):
    """Record one poem. Never raises: stats must not break the camera."""
    try:
        entry = {
            "time": (when or datetime.now()).isoformat(timespec="seconds"),
            "provider": provider,
            "model": model,
            "seconds": round(seconds, 1) if seconds is not None else None,
            "fallback": bool(fallback),  # True = canned poem, AI failed
        }
        with _lock, open(LOG_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
            f.flush()
            os.fsync(f.fileno())
    except Exception:
        pass
    try:
        _rec().record("poem", "fallback" if fallback else "ok", seconds=seconds,
                      detail=f"{provider}/{model}" if provider and model else None, when=when)
    except Exception:
        pass


def backfill_events():
    """Copy poems from poem_log.jsonl into the activity events. Safe to run any number of times
    (a poem whose time is already recorded is skipped). Returns how many were added. Never raises."""
    added = 0
    try:
        from propkit.stats import read_events
        have = {e["ts"] for e in read_events(EVENTS_DIR, kinds=["poem"])}
        with open(LOG_PATH) as f:
            lines = f.read().splitlines()
        for line in lines:
            try:
                e = json.loads(line)
                when = datetime.fromisoformat(e["time"])
            except Exception:
                continue
            if e["time"] in have:
                continue
            fb = bool(e.get("fallback"))
            prov, mdl = e.get("provider"), e.get("model")
            if _rec().record("poem", "fallback" if fb else "ok", seconds=e.get("seconds"),
                             detail=f"{prov}/{mdl}" if prov and mdl else None, when=when):
                have.add(e["time"])
                added += 1
    except Exception:
        pass
    return added


def record_event(kind, detail=None, when=None):
    """Append one health event. Never raises."""
    try:
        entry = {"time": (when or datetime.now()).isoformat(timespec="seconds"), "kind": kind}
        if detail is not None:
            entry["detail"] = detail
        with _lock, open(EVENTS_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
            f.flush()
            os.fsync(f.fileno())
    except Exception:
        pass
