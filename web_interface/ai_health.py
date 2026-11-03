"""
Key and model checks for the AI tab. The shallow check only asks each provider about the configured model
(a read-only call that costs nothing). The result is saved to ai_health.json so every page can show a banner
when a key stops working, and is refreshed once a day by a background thread.
"""

import json
import os
import threading
import time
from datetime import datetime

import requests

import atomic_io
from poem_ai import FALLBACK_MODELS
from .config_manager import config_manager

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUS_PATH = os.path.join(BASE, "ai_health.json")
ENV_PATH = os.path.join(BASE, ".env")
TIMEOUT = 10
RECHECK_EVERY = 24 * 3600
OK, FAIL, UNKNOWN = "ok", "fail", "unknown"

PROVIDERS = {
    "openai": ("OpenAI", "OPENAI_API_KEY"),
    "anthropic": ("Anthropic", "ANTHROPIC_API_KEY"),
}


def _item(name, status, detail, provider=None):
    return {"name": name, "status": status, "detail": detail, "provider": provider}


def _env_keys():
    from propkit import ai
    return ai.EnvFile(ENV_PATH).read()


def _check(provider, key, model, in_use):
    """One key/model check. A provider that isn't the chosen one is only a backup, so a missing key there is not a failure."""
    label, env_var = PROVIDERS[provider]
    name = f"{label} key" if in_use else f"{label} key (backup)"
    if not key:
        if in_use:
            return _item(name, FAIL, f"{env_var} is not set in .env", provider)
        return _item(name, UNKNOWN, f"{env_var} is not set (the backup provider is not available)", provider)
    try:
        if provider == "openai":
            r = requests.get(f"https://api.openai.com/v1/models/{model}",
                             headers={"Authorization": f"Bearer {key}"}, timeout=TIMEOUT)
        else:
            r = requests.get(f"https://api.anthropic.com/v1/models/{model}",
                             headers={"x-api-key": key, "anthropic-version": "2023-06-01"}, timeout=TIMEOUT)
    except requests.exceptions.RequestException as e:
        return _item(name, UNKNOWN, f"Could not reach {label}: {type(e).__name__}", provider)
    if r.status_code == 200:
        return _item(name, OK, f"Key accepted; model {model} available", provider)
    if r.status_code in (401, 403) and "model" not in r.text.lower():
        return _item(name, FAIL if in_use else UNKNOWN, f"{label} key REJECTED (HTTP {r.status_code})", provider)
    if r.status_code in (403, 404):
        return _item(name, FAIL if in_use else UNKNOWN, f"Model '{model}' is not available to this key (HTTP {r.status_code})", provider)
    return _item(name, UNKNOWN, f"{label}: HTTP {r.status_code}", provider)


def run_checks(deep=False, write=True):
    config_manager.reload()  # the page and the camera loop may have changed the file
    keys = _env_keys()
    chosen, model = config_manager.get_ai_provider(), config_manager.get_openai_model()
    backups = FALLBACK_MODELS
    items = []
    for prov in PROVIDERS:
        items.append(_check(prov, keys.get(PROVIDERS[prov][1], ""), model if prov == chosen else backups[prov], prov == chosen))
    statuses = {i["status"] for i in items}
    overall = FAIL if FAIL in statuses else ("warn" if UNKNOWN in statuses else OK)
    result = {"checked_at": datetime.now().isoformat(timespec="seconds"), "deep": bool(deep),
              "overall": overall, "items": items}
    if write:
        try:
            atomic_io.write_json(STATUS_PATH, result)
        except OSError:
            pass
    return result


def read_status():
    try:
        with open(STATUS_PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def start_background():
    """Check shortly after start-up and then once a day. Cheap: two read-only calls."""
    def loop():
        time.sleep(90)  # let the network come up
        while True:
            try:
                run_checks()
            except Exception:
                pass
            time.sleep(RECHECK_EVERY)
    threading.Thread(target=loop, daemon=True).start()
