"""
Poem statistics for Poetry Camera.

Every generated poem is appended as one JSON line to poem_log.jsonl, so counts
survive reboots and power loss. The dashboard reads it to show event totals.
"""

import json
import os
import threading
from datetime import datetime, timedelta

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "poem_log.jsonl")
SESSION_GAP = timedelta(minutes=45)  # a longer quiet spell starts a new "event"
MIN_EVENT = 5  # runs shorter than this are treated as test shots, not events

_lock = threading.Lock()


def record_poem(provider, model, seconds, fallback=False, when=None):
    """Append one poem to the log. Never raises: stats must not break the camera."""
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


def _load():
    entries = []
    try:
        with open(LOG_PATH) as f:
            for line in f:
                try:
                    e = json.loads(line)
                    e["dt"] = datetime.fromisoformat(e["time"])
                    entries.append(e)
                except Exception:
                    continue
    except FileNotFoundError:
        pass
    entries.sort(key=lambda e: e["dt"])
    return entries


def get_summary(now=None):
    """Counts for the dashboard: all time, today, last 24h, and the latest event."""
    now = now or datetime.now()
    entries = _load()
    summary = {
        "total": len(entries),
        "today": sum(1 for e in entries if e["dt"].date() == now.date()),
        "last_24h": sum(1 for e in entries if now - e["dt"] <= timedelta(hours=24)),
        "fallbacks": sum(1 for e in entries if e["fallback"]),
        "event": None,
    }
    if entries:
        # Split into events: runs of poems with no gap longer than SESSION_GAP
        events = [[entries[0]]]
        for prev, cur in zip(entries, entries[1:]):
            if cur["dt"] - prev["dt"] <= SESSION_GAP:
                events[-1].append(cur)
            else:
                events.append([cur])
        # Latest real event: ignore stray test shots (fewer than MIN_EVENT poems)
        real = [ev for ev in events if len(ev) >= MIN_EVENT]
        event = (real or events)[-1]
        hours = {}
        for e in event:
            hours[e["dt"].strftime("%-I %p")] = hours.get(e["dt"].strftime("%-I %p"), 0) + 1
        busiest = max(hours.items(), key=lambda kv: kv[1]) if hours else None
        times = [e["seconds"] for e in event if e["seconds"] is not None]
        summary["event"] = {
            "count": len(event),
            "start": event[0]["dt"].strftime("%a %b %-d, %-I:%M %p"),
            "end": event[-1]["dt"].strftime("%-I:%M %p"),
            "busiest_hour": busiest[0] if busiest else None,
            "busiest_count": busiest[1] if busiest else 0,
            "avg_seconds": round(sum(times) / len(times), 1) if times else None,
            "hours": list(hours.items()),
        }
    return summary
