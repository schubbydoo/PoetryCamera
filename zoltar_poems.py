"""
Lucky numbers: send each finished poem to Zoltar so guests can hear it read aloud.

Settings (switch, Zoltar's address, shared token) live in zoltar_poems.json and the
numbers used in the last 24 h in zoltar_poem_state.json. Both are kept out of git.
Everything here is best-effort: register() never raises and never takes longer than
the 3 s send timeout, so printing is never blocked by Zoltar.
"""

import json
import logging
import os
import random
import socket
import threading
import time

import requests

BASE = os.path.dirname(os.path.abspath(__file__))
SETTINGS_PATH = os.path.join(BASE, "zoltar_poems.json")
STATE_PATH = os.path.join(BASE, "zoltar_poem_state.json")
RETENTION = 24 * 3600
TIMEOUT = 2
MDNS_HOST = "zoltar.local"
SUBMIT_PATH = "/api/poems/submit"
NUMBERS = [t * 10 + o for t in range(2, 10) for o in range(2, 10)]  # 22..99, no digit 0 or 1
DEFAULTS = {"enabled": False, "address": "http://192.168.128.148:8000", "token": ""}

_lock = threading.Lock()


def get_settings():
    s = dict(DEFAULTS)
    try:
        with open(SETTINGS_PATH) as f:
            s.update({k: v for k, v in json.load(f).items() if k in DEFAULTS})
    except FileNotFoundError:
        pass
    except Exception:
        logging.exception("Zoltar settings unreadable; feature off")
        s["enabled"] = False
    return s


def save_settings(data):
    """Update switch/address; the token only changes when a non-empty one is given."""
    s = get_settings()
    if "enabled" in data:
        s["enabled"] = bool(data["enabled"])
    if "address" in data:
        addr = str(data["address"]).strip().rstrip("/")
        if addr and not addr.startswith(("http://", "https://")):
            addr = "http://" + addr
        s["address"] = addr
    if str(data.get("token") or "").strip():
        s["token"] = str(data["token"]).strip()
    tmp = SETTINGS_PATH + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(s, f)
    os.replace(tmp, SETTINGS_PATH)
    return s


def _load_used(now):
    try:
        with open(STATE_PATH) as f:
            used = json.load(f)
        return {int(n): t for n, t in used.items() if now - t < RETENTION}
    except Exception:
        return {}


def pick_number(now=None, rng=random):
    """Random number not used in the last 24 h; if all are used, the oldest. Records the pick."""
    now = now or time.time()
    with _lock:
        used = _load_used(now)
        free = [n for n in NUMBERS if n not in used]
        n = rng.choice(free) if free else min(used, key=used.get)
        used[n] = now
        try:
            tmp = STATE_PATH + ".tmp"
            with open(tmp, "w") as f:
                json.dump({str(k): v for k, v in used.items()}, f)
            os.replace(tmp, STATE_PATH)
        except Exception:
            logging.exception("Could not save lucky-number state")
        return n


def _mdns_resolves(host, wait=1.0):
    """True if the .local name resolves within `wait` s (a lookup can hang, so it runs in a thread)."""
    ok = []
    def look():
        try:
            socket.gethostbyname(host)
            ok.append(1)
        except Exception:
            pass
    t = threading.Thread(target=look, daemon=True)
    t.start()
    t.join(wait)
    return bool(ok)


def _targets(address):
    """zoltar.local first (same port as the saved address), then the saved address."""
    from urllib.parse import urlsplit
    u = urlsplit(address)
    out = []
    if u.hostname and not u.hostname.endswith(".local") and _mdns_resolves(MDNS_HOST):
        out.append(f"{u.scheme}://{MDNS_HOST}" + (f":{u.port}" if u.port else ""))
    out.append(address)
    return out


def register(poem):
    """Send the poem to Zoltar. Returns the lucky number if Zoltar accepted it, else None."""
    try:
        s = get_settings()
        if not (s["enabled"] and s["address"] and s["token"]):
            return None
        number = pick_number()
        title = next((l.strip() for l in poem.splitlines() if l.strip()), "")[:120]
        for base in _targets(s["address"]):
            try:
                r = requests.post(base + SUBMIT_PATH,
                                  headers={"X-Poem-Token": s["token"]},
                                  json={"number": number, "text": poem, "title": title},
                                  timeout=TIMEOUT)
            except Exception as e:
                logging.warning("Could not reach Zoltar at %s: %s", base, e)
                continue
            if r.status_code == 200 and r.json().get("ok") is True:
                logging.info("Zoltar accepted the poem as lucky number %d", number)
                return number
            logging.warning("Zoltar did not accept the poem (HTTP %s)", r.status_code)
            return None  # reachable but refused (e.g. switched off there): no number
    except Exception as e:
        logging.warning("Could not send the poem to Zoltar: %s", e)
    return None
