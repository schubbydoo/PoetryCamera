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
EVENTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "event_log.jsonl")
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
        "recent_fallbacks": 0,
        "event": None,
    }
    # Canned poems in a row at the end, within the last 6 hours = AI is currently unreachable
    streak = 0
    for e in reversed(entries):
        if not e["fallback"] or now - e["dt"] > timedelta(hours=6):
            break
        streak += 1
    summary["recent_fallbacks"] = streak if streak >= 2 else 0
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
        peak10 = 0
        j = 0
        for i, e in enumerate(event):
            while e["dt"] - event[j]["dt"] > timedelta(minutes=10):
                j += 1
            peak10 = max(peak10, i - j + 1)
        summary["event"] = {
            "count": len(event),
            "start": event[0]["dt"].strftime("%a %b %-d, %-I:%M %p"),
            "end": event[-1]["dt"].strftime("%-I:%M %p"),
            "busiest_hour": busiest[0] if busiest else None,
            "busiest_count": busiest[1] if busiest else 0,
            "avg_seconds": round(sum(times) / len(times), 1) if times else None,
            "slowest_seconds": round(max(times), 1) if times else None,
            "peak_10min": peak10,
            "health": get_health(event[0]["dt"] - timedelta(minutes=10), event[-1]["dt"] + timedelta(minutes=10)),
            "hours": list(hours.items()),
        }
    return summary


# ---------------------------------------------------------------------------
# Health events: paper, wifi, internet, printer, restarts, AI trouble
# ---------------------------------------------------------------------------

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


def _load_events():
    events = []
    try:
        with open(EVENTS_PATH) as f:
            for line in f:
                try:
                    e = json.loads(line)
                    e["dt"] = datetime.fromisoformat(e["time"])
                    events.append(e)
                except Exception:
                    continue
    except FileNotFoundError:
        pass
    events.sort(key=lambda e: e["dt"])
    return events


def _outages(events, start_kind, end_kind, lo, hi):
    """Pair start/end events inside [lo, hi]; return (count, total_seconds)."""
    count, total, open_at = 0, 0.0, None
    for e in events:
        if e["kind"] == start_kind and open_at is None:
            open_at = max(e["dt"], lo)
            count += 1
        elif e["kind"] == end_kind and open_at is not None:
            total += (min(e["dt"], hi) - open_at).total_seconds()
            open_at = None
    if open_at is not None:
        total += (hi - open_at).total_seconds()
    return count, max(total, 0)


def _fmt_duration(seconds):
    seconds = int(round(seconds))
    if seconds < 90:
        return f"{seconds}s"
    return f"{round(seconds / 60)} min" if seconds < 3600 else f"{seconds // 3600}h {seconds % 3600 // 60}m"


def get_health(lo, hi):
    """Trouble summary for the window [lo, hi]. Each row: label, count, detail, ok."""
    all_events = _load_events()
    window = [e for e in all_events if lo <= e["dt"] <= hi]
    kinds = lambda k: [e for e in window if e["kind"] == k]
    rows = []

    n, secs = _outages(window, "paper_out", "paper_back", lo, hi)
    cut = len(kinds("cutoff"))
    rows.append(("Paper ran out", n,
                 (f"{_fmt_duration(secs)} without paper; {cut} poem(s) cut off, {len(kinds('reprint'))} reprinted" if n else ""), n == 0))

    n, secs = _outages(window, "wifi_down", "wifi_up", lo, hi)
    ssids = []
    earlier = [e for e in all_events if e["kind"] == "wifi_up" and e["dt"] < lo]
    if earlier and (earlier[-1].get("detail") or {}).get("ssid"):
        ssids.append(earlier[-1]["detail"]["ssid"])  # network in use when the window began
    for e in kinds("wifi_up"):
        ssid = (e.get("detail") or {}).get("ssid")
        if ssid and (not ssids or ssids[-1] != ssid):
            ssids.append(ssid)
    detail = (f"{_fmt_duration(secs)} without wifi" if n else "") + (f"; networks used: {', '.join(ssids)}" if len(ssids) > 1 else "")
    rows.append(("Wi-Fi drops", n, detail.strip("; "), n == 0))

    n, secs = _outages(window, "internet_down", "internet_up", lo, hi)
    rows.append(("Internet outages", n, f"{_fmt_duration(secs)} total" if n else "", n == 0))

    n, secs = _outages(window, "printer_offline", "printer_online", lo, hi)
    rows.append(("Printer offline", n, f"{_fmt_duration(secs)} total" if n else "", n == 0))

    restarts = kinds("restart")
    unclean = [e for e in restarts if not (e.get("detail") or {}).get("clean", True)]
    down = sum((e.get("detail") or {}).get("downtime_s") or 0 for e in restarts)
    rows.append(("Restarts", len(restarts),
                 (f"{len(unclean)} unclean (likely power loss); about {_fmt_duration(down)} down" if restarts else ""),
                 len(unclean) == 0))

    heals = kinds("self_heal")
    rows.append(("Self-recoveries", len(heals),
                 (", ".join(f"{(e.get('detail') or {}).get('reason')} -> {(e.get('detail') or {}).get('network')}" for e in heals)
                  if heals else ""), not heals))

    retries, failed = len(kinds("api_retry")), len(kinds("ai_failed"))
    rows.append(("AI hiccups", retries + failed,
                 (f"{retries} slow-network retries, {failed} failed attempts" if retries + failed else ""),
                 retries + failed == 0))
    return rows
