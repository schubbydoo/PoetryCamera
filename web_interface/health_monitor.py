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


def internet_ok():
    try:
        socket.create_connection(INTERNET_HOST, timeout=3).close()
        return True
    except Exception:
        return False


AP_NAME = "PoetCam"
AP_GRACE = 180        # seconds in setup hotspot with nobody connected before we leave it
OFFLINE_GRACE = 90    # seconds without wifi before we try to reconnect
NO_INTERNET_GRACE = 120
HEAL_COOLDOWN = 300


def _ap_active():
    try:
        out = subprocess.run(["nmcli", "-t", "-f", "NAME", "connection", "show", "--active"],
                             capture_output=True, text=True, timeout=8).stdout
        return AP_NAME in out.splitlines()
    except Exception:
        return False


def _ap_has_clients():
    """True if any device is connected to our hotspot."""
    try:
        out = subprocess.run(["ip", "-4", "neigh", "show", "dev", "wlan0"],
                             capture_output=True, text=True, timeout=5).stdout
        return any(l.split()[-1] in ("REACHABLE", "STALE", "DELAY", "PROBE") for l in out.splitlines() if l.strip())
    except Exception:
        return False


def _saved_networks():
    """Saved wifi profiles we may auto-join, best priority first (never the hotspot)."""
    try:
        out = subprocess.run(["nmcli", "-t", "-f", "TYPE,AUTOCONNECT,AUTOCONNECT-PRIORITY,NAME", "connection", "show"],
                             capture_output=True, text=True, timeout=8).stdout
        nets = []
        for line in out.splitlines():
            parts = line.split(":", 3)
            if len(parts) == 4 and parts[0] == "802-11-wireless" and parts[1] == "yes" and parts[3] != AP_NAME:
                try:
                    prio = int(parts[2])
                except ValueError:
                    prio = 0
                nets.append((prio, parts[3].replace("\\:", ":")))
        return [name for _, name in sorted(nets, key=lambda n: -n[0])]
    except Exception:
        return []


def _profile_ssid(name):
    try:
        return subprocess.run(["sudo", "nmcli", "-g", "802-11-wireless.ssid", "connection", "show", "id", name],
                              capture_output=True, text=True, timeout=8).stdout.strip() or name
    except Exception:
        return name


def _visible_ssids():
    try:
        subprocess.run(["sudo", "nmcli", "device", "wifi", "rescan"], capture_output=True, timeout=10)
        time.sleep(3)
        out = subprocess.run(["nmcli", "-t", "-f", "SSID", "device", "wifi", "list"],
                             capture_output=True, text=True, timeout=10).stdout
        return {l.replace("\\:", ":") for l in out.splitlines() if l}
    except Exception:
        return set()


def _self_heal(reason, was_ap):
    """Try saved networks that are in range (best priority first). Restore the hotspot if we left it and failed."""
    logging.warning(f"Self-heal ({reason}): looking for a saved network")
    names = _saved_networks()
    visible = _visible_ssids()
    candidates = [n for n in names if _profile_ssid(n) in visible] if visible else names
    for name in (candidates or names)[:6]:
        try:
            r = subprocess.run(["sudo", "nmcli", "connection", "up", "id", name],
                               capture_output=True, text=True, timeout=30)
            if r.returncode == 0 and internet_ok():
                record_event("self_heal", {"reason": reason, "network": _profile_ssid(name)})
                logging.warning(f"Self-heal: back online via {name}")
                return True
        except Exception:
            continue
    record_event("self_heal_failed", {"reason": reason})
    if was_ap:
        subprocess.run(["sudo", "nmcli", "connection", "up", AP_NAME], capture_output=True, timeout=30)
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
    ap_since = offline_since = no_net_since = None
    last_heal = 0
    while True:
        try:
            _write_state(clean=False)
            now = time.time()

            ap = _ap_active()
            ssid = _wifi_ssid()
            if ssid != current_ssid:
                if ssid:
                    record_event("wifi_up", {"ssid": ssid})  # joined, or switched networks
                else:
                    record_event("wifi_down")
                current_ssid = ssid

            if ssid and not ap:
                if internet_ok():
                    internet_fails = 0
                    if internet_up is False:
                        record_event("internet_up")
                    internet_up = True
                else:
                    internet_fails += 1
                    if internet_fails >= 2 and internet_up is not False:  # 20 s of failures
                        record_event("internet_down")
                        internet_up = False

            # --- self-heal: leave a forgotten hotspot, rejoin lost wifi ---
            ap_since = (ap_since or now) if (ap and not _ap_has_clients()) else None
            offline_since = (offline_since or now) if (not ap and not ssid) else None
            no_net_since = (no_net_since or now) if (not ap and ssid and internet_up is False) else None

            reason = None
            if ap_since and now - ap_since > AP_GRACE:
                reason = "hotspot with nobody connected"
            elif offline_since and now - offline_since > OFFLINE_GRACE:
                reason = "wifi lost"
            elif no_net_since and now - no_net_since > NO_INTERNET_GRACE:
                reason = "no internet"
            if reason and now - last_heal > HEAL_COOLDOWN:
                last_heal = now
                healed = _self_heal(reason, was_ap=ap)
                if not healed and ap:
                    last_heal = now + 900  # someone may be using the hotspot to set up wifi: back off 15 min
                ap_since = offline_since = no_net_since = None
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
