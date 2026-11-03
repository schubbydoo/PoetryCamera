"""The camera's settings for propkit's shared "AI" tab: what is configurable and how it is stored.

Values stay in poetry_camera_config.json (config_manager), which main.py already reads before every photo.
The page itself, key handling and validation come from propkit.
"""

import base64
import os
import re

from propkit import ai

from poem_ai import POEM_FORMAT_DESCRIPTIONS, build_prompt, clean_poem, generate_anthropic, generate_openai
from . import ai_health
from .config_manager import DEFAULT_CONFIG, config_manager

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE_PATH = os.path.join(BASE_DIR, "ImageStore", "image.jpg")
MODEL_RE = re.compile(r"^[A-Za-z0-9._:-]{2,80}$")
MAX_PROMPT = 4000
PROVIDER_IDS = ("openai", "anthropic")

OPENAI_OPTIONS = [
    ("gpt-4o-mini", "gpt-4o-mini - Budget multimodal"), ("gpt-4o", "gpt-4o - Multimodal"),
    ("gpt-4.1-mini", "gpt-4.1-mini - Fast & affordable"), ("gpt-4.1", "gpt-4.1 - High quality"),
    ("gpt-5.4-mini", "gpt-5.4-mini - Latest, balanced"),
]
ANTHROPIC_OPTIONS = [
    ("claude-sonnet-4-6", "claude-sonnet-4-6 - Balanced (current default)"),
    ("claude-sonnet-5-5", "claude-sonnet-5-5 - Latest, balanced"),
    ("claude-haiku-4-5-20251001", "claude-haiku-4-5 - Fastest & cheapest"),
]
FORMAT_OPTIONS = [(k, "%s - %s" % (k.title(), v)) for k, v in POEM_FORMAT_DESCRIPTIONS.items()]


def defaults(profile=None):
    d = DEFAULT_CONFIG["openai"]
    return {"model_provider": d["provider"], "model": d["model"], "poem_prompt": d["poem_prompt"],
            "poem_format": d["poem_format"], "demo_context": ""}


def load(profile=None):
    config_manager.reload()
    c = config_manager.get_openai_config()
    return {"model_provider": c.get("provider", "openai"), "model": c.get("model", ""),
            "poem_prompt": c.get("poem_prompt", ""), "poem_format": c.get("poem_format", ""),
            "demo_context": config_manager.get_demo_context()}


def _validate(v):
    if v["model_provider"] not in PROVIDER_IDS:
        return "Choose OpenAI or Anthropic."
    if not MODEL_RE.match(v["model"]):
        return "%s is not a valid model name." % v["model"]
    if v["poem_format"] not in POEM_FORMAT_DESCRIPTIONS:
        return "Choose one of the poem formats."
    if not v["poem_prompt"].strip() or len(v["poem_prompt"]) > MAX_PROMPT:
        return "The poem prompt must be filled in (up to %d characters)." % MAX_PROMPT
    if len(v["demo_context"]) > MAX_PROMPT:
        return "The demo context is too long (up to %d characters)." % MAX_PROMPT
    return None


def save(values, profile=None):
    cur = load()
    new = dict(cur, **{k: v for k, v in values.items() if k in cur})
    err = _validate(new)
    if err:
        return False, err
    result = config_manager.update_openai_config({"provider": new["model_provider"], "model": new["model"],
                                                  "poem_prompt": new["poem_prompt"], "poem_format": new["poem_format"]})
    if not result.get("success"):
        return False, result.get("error", "Could not save.")
    config_manager.set_demo_context(new["demo_context"].strip())
    return True, "Saved. The camera uses the new settings for the next photo (a changed key needs a restart)."


# ---- test: one real poem from the most recent photo, with the settings on the page (not yet saved) ---------------
def test(values, profile=None):
    cur = dict(load(), **values)
    err = _validate(cur)
    if err:
        return {"ok": False, "text": "", "detail": err}
    if not os.path.exists(IMAGE_PATH):
        return {"ok": False, "text": "", "detail": "There is no saved photo yet. Take one with the camera button first."}
    keys = ai.EnvFile(ai_health.ENV_PATH).read()
    provider = cur["model_provider"]
    key = keys.get("OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY", "")
    if not key:
        return {"ok": False, "text": "", "detail": "No %s key is set." % ("OpenAI" if provider == "openai" else "Anthropic")}
    with open(IMAGE_PATH, "rb") as f:
        image = base64.b64encode(f.read()).decode()
    prompt = build_prompt(cur["poem_prompt"], cur["poem_format"], cur["demo_context"])
    try:
        if provider == "anthropic":
            import anthropic
            raw = generate_anthropic(anthropic.Anthropic(api_key=key, timeout=30, max_retries=0), cur["model"], prompt, image)
        else:
            import openai
            raw = generate_openai(openai.OpenAI(api_key=key, timeout=30, max_retries=0), cur["model"], prompt, image)
    except Exception as e:
        return {"ok": False, "text": "", "detail": "The AI answered with an error: %s" % str(e)[:200]}
    return {"ok": True, "text": clean_poem(raw),
            "detail": "Written from the most recent saved photo (text only; nothing was printed or sent to Zoltar)."}


# ---- the propkit description -------------------------------------------------------------------------------------
def build():
    return ai.AIConfig(
        providers=[ai.Provider("openai", "OpenAI", "OPENAI_API_KEY"), ai.Provider("anthropic", "Anthropic", "ANTHROPIC_API_KEY")],
        sections=[
            ai.Section("models", "Models", help="Changes apply to the next photo.", fields=[
                ai.Field("model", "", "model", role="see", providers=list(PROVIDER_IDS),
                         options_by_provider={"openai": OPENAI_OPTIONS, "anthropic": ANTHROPIC_OPTIONS},
                         help="Here: looks at the photo and writes the poem in one step.")]),
            ai.Section("prompt", "Prompt", fields=[
                ai.Field("poem_prompt", "Poem prompt", "textarea", rows=10,
                         help="What the poem should be like. {format_variable} is replaced by the poem format below."),
                ai.Field("poem_format", "Poem format", "select", options=FORMAT_OPTIONS)]),
            ai.Section("context", "Demo context", help="Tell the camera about the moment it is part of: where, who is there, "
                       "what is going on. A few phrases are enough. Leave blank for plain poems.", fields=[
                ai.Field("demo_context", "Demo context (optional)", "textarea", rows=4,
                         placeholder='e.g. "Halloween party, the host is dressed as a raven."')])],
        load=load, save=save, defaults=defaults, test=test, test_label="Test: write a poem from the last photo",
        health=ai_health.run_checks, last_health=ai_health.read_status,
        env_file=ai_health.ENV_PATH,
        intro="Which AI looks at the photo and writes the poem, and what it is asked to write. Keys are never shown in full.")
