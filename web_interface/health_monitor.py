"""
Background health monitor for Poetry Camera.

Records wifi / internet transitions and restarts into the event log so the
dashboard can summarise what went wrong during an event. Every check is
wrapped so the monitor can never affect taking or printing photos.
"""

import json
import logging
import os
import signal
import socket
import subprocess
import threading
import time
from datetime import datetime

from .poem_stats import record_event

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "health_state.json")
CHECK_EVERY = 10  # seconds
INTERNET_HOST = ("api.anthropic.com", 443)


def _write_state(clean):
    try:
        with open(STATE_PATH, "w") as f:
            json.dump({"last_seen": datetime.now().isoformat(timespec="seconds"), "clean": clean}, f)
    except Exception:
        pass


def _clock_synced():
    try:
        out = subprocess.run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"],
                             capture_output=True, text=True, timeout=5).stdout.strip()
        return out == "yes"
    except Exception:
        return False


def _wifi_ssid():
    """Network name (SSID) of the wifi we are connected to, or None."""
    try:
        out = subprocess.run(["nmcli", "-t", "-f", "ACTIVE,SSID", "device", "wifi", "list"],
                             capture_output=True, text=True, timeout=8).stdout
        for line in out.splitlines():
            if line.startswith("yes:"):
                return line[4:].replace("\\:", ":") or None
        return None
    except Exception:
        return None


def _internet_ok():
    try:
        socket.create_connection(INTERNET_HOST, timeout=3).close()
        return True
    except Exception:
        return False


def _note_restart():
    """Compare with the last heartbeat to tell clean restarts from power loss."""
    try:
        with open(STATE_PATH) as f:
            state = json.load(f)
        last_seen = datetime.fromisoformat(state["last_seen"])
        downtime = max((datetime.now() - last_seen).total_seconds(), 0)
        record_event("restart", {"clean": bool(state.get("clean")), "downtime_s": int(downtime)})
    except FileNotFoundError:
        pass  # first run
    except Exception:
        record_event("restart", {"clean": False, "downtime_s": None})


def _monitor():
    # No battery clock: wait for the network time so timestamps and downtime make sense
    for _ in range(36):
        if _clock_synced():
            break
        time.sleep(5)
    _note_restart()

    UNKNOWN = object()
    current_ssid = UNKNOWN
    internet_up = None
    internet_fails = 0
    while True:
        try:
            _write_state(clean=False)

            ssid = _wifi_ssid()
            if ssid != current_ssid:
                if ssid:
                    record_event("wifi_up", {"ssid": ssid})  # joined, or switched networks
                else:
                    record_event("wifi_down")
                current_ssid = ssid

            if ssid:
                if _internet_ok():
                    internet_fails = 0
                    if internet_up is False:
                        record_event("internet_up")
                    internet_up = True
                else:
                    internet_fails += 1
                    if internet_fails >= 2 and internet_up is not False:  # 20 s of failures
                        record_event("internet_down")
                        internet_up = False
        except Exception:
            logging.exception("health monitor check failed")
        time.sleep(CHECK_EVERY)


def start_health_monitor():
    """Start the monitor and mark clean shutdowns (SIGTERM from systemd/reboot)."""
    def on_term(signum, frame):
        _write_state(clean=True)
        os._exit(0)

    try:
        signal.signal(signal.SIGTERM, on_term)
    except Exception:
        pass
    threading.Thread(target=_monitor, daemon=True).start()
