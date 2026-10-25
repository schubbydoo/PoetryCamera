#!/usr/bin/python3
# Poetry Camera Main Application
# Captures images, generates AI poetry, and prints to thermal printer

import requests, signal, os, sys, base64, subprocess, threading
from picamera2 import Picamera2
from gpiozero import LED, Button
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import anthropic
from time import time, sleep
import logging
import re
import random

# Import configuration manager
from web_interface.config_manager import config_manager
from web_interface.poem_stats import record_poem, record_event
from web_interface.health_monitor import start_health_monitor, internet_ok

# Setup logging
# force=True: config_manager (imported above) already set up logging with a bare format
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', force=True)
# Flush every line so the log survives a sudden power loss
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

logging.info("Server starting")
logging.info("Connecting to printer")

POEM_FORMAT_DESCRIPTIONS = {
    "limerick": "5 lines, AABBA rhyme scheme. Short, bouncy rhythm. Great for candid or humorous moments.",
    "ballad stanza": "4-line stanzas, ABAB rhyme. A classic storytelling format, naturally musical.",
    "rhyming couplets": "AA BB CC pattern. The simplest rhyme structure — punchy and rhythmic.",
    "clerihew": "4-line biographical poem, AABB rhyme. First line is a person's name — perfect when there are people in the scene.",
    "sonnet": "14 lines, ABAB CDCD EFEF GG rhyme scheme. Strong rhyme throughout.",
}

API_TIMEOUT = 20  # seconds per AI request

# Backup models used if the configured provider fails
FALLBACK_MODELS = {
    "anthropic": "claude-haiku-4-5-20251001",
    "openai": "gpt-4o",
}

# Printed only if every AI attempt fails, so guests never see an error message
FALLBACK_POEMS = [
    "Hold still, the moment's here,\nA little light, a little cheer.\nThe muses stepped out for a bite,\nBut left this smile to keep tonight.",
    "You stopped, you laughed, the shutter sang,\nThe whole room caught it where it rang.\nThe words ran off to find their rhyme,\nBut you were here, and that's the time.",
    "A face, a flash, a crooked grin,\nThe poem's stuck somewhere within.\nTry once again and it will flow,\nThe muse is shy, but ready to go.",
]

# --- Config Getters ---
def get_poem_system_prompt():
    return config_manager.get_poem_system_prompt()

def get_poem_prompt():
    return config_manager.get_poem_prompt()

def get_poem_format():
    return config_manager.get_poem_format()

def get_openai_model():
    return config_manager.get_openai_model()

def get_ai_provider():
    return config_manager.get_ai_provider()

def initialize():
    load_dotenv()

    # Set up AI clients
    global openai_client, anthropic_client
    # Short timeout + one retry so a flaky network can never leave the camera stuck "busy"
    openai_api_key = os.environ.get('OPENAI_API_KEY', '')
    openai_client = OpenAI(api_key=openai_api_key, timeout=API_TIMEOUT, max_retries=1) if openai_api_key else None
    anthropic_api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key, timeout=API_TIMEOUT, max_retries=1) if anthropic_api_key else None

    # Set up camera (Lazily initialized later to save CPU)
    global picam2, camera_at_rest
    picam2 = Picamera2()
    
    # prevent double-click bugs
    camera_at_rest = True

    # Set up shutter button & status LED
    global shutter_button, led
    shutter_button = Button(16)
    led = LED(20)
    
    # Initial state
    safe_led_on()

    # button event handlers
    shutter_button.when_pressed = on_press
    shutter_button.when_released = on_release

    threading.Thread(target=paper_watcher, daemon=True).start()
    start_health_monitor()
    for name in ('anthropic', 'openai'):
        logging.getLogger(name).addHandler(RetryEventHandler())

    logging.info("Main application ready")

# --- Helper functions to prevent gpiozero crashes ---
def safe_led_on():
    try:
        led.on()
    except RuntimeError:
        pass

def safe_led_off():
    try:
        led.off()
    except RuntimeError:
        pass

def safe_led_blink(on_time=1, off_time=1):
    try:
        led.blink(on_time=on_time, off_time=off_time)
    except RuntimeError:
        pass

paper_out = False
fallback_streak = 0   # consecutive poems that fell back to a canned poem
degraded = False      # True after 2+ canned poems in a row (AI unreachable)

def rest_led():
    """Idle LED: steady on; slow pulse = out of paper; steady 0.6 s blink = AI unreachable (canned poems)."""
    if paper_out:
        safe_led_blink(on_time=0.1, off_time=1.5)
    elif degraded:
        safe_led_blink(on_time=0.6, off_time=0.6)
    else:
        safe_led_on()


class RetryEventHandler(logging.Handler):
    """Count the AI libraries' automatic network retries as health events."""
    def emit(self, record):
        try:
            if "Retrying request" in record.getMessage():
                record_event("api_retry")
        except Exception:
            pass


def paper_watcher():
    """Watch the printer service: pulse the LED when out of paper, and log printer health."""
    global paper_out
    reprint_pending = False
    printer_online = None
    offline_polls = 0
    while True:
        try:
            data = requests.get("http://127.0.0.1:5002", timeout=3).json()
            status = data.get("status", {})
            out_now = bool(status.get("no_paper"))
            if out_now != paper_out:
                paper_out = out_now
                logging.warning("Printer is out of paper - pulsing LED" if paper_out else "Paper detected again")
                record_event("paper_out" if paper_out else "paper_back")
                if camera_at_rest:
                    rest_led()

            pending = bool(data.get("reprint_pending"))
            if pending and not reprint_pending:
                record_event("cutoff")
            elif reprint_pending and not pending:
                record_event("reprint")
            reprint_pending = pending

            # Empty status = printer not connected over Bluetooth (needs 2 polls to count)
            if status:
                offline_polls = 0
                if printer_online is False:
                    record_event("printer_online")
                printer_online = True
            else:
                offline_polls += 1
                if offline_polls >= 3 and printer_online is not False:
                    if printer_online is True:  # only count drops, not slow starts
                        record_event("printer_offline")
                        printer_online = False
        except Exception:
            pass  # printer service not up yet; try again
        sleep(2)


#############################
# CORE PHOTO-TO-POEM FUNCTION
#############################
def take_photo_and_print_poem():
    global camera_at_rest, fallback_streak, degraded
    camera_at_rest = False
    
    # blink LED to show activity
    safe_led_blink(on_time=0.2, off_time=0.2)

    image_dir = '/home/shschubert/PoetryCamera/ImageStore/'
    os.makedirs(image_dir, exist_ok=True)
    photo_filename = os.path.join(image_dir, 'image.jpg')

    # Start camera only when needed to save CPU/Heat
    try:
        picam2.start()
        sleep(1.0) # Warmup
        picam2.capture_file(photo_filename)
        picam2.stop()
        print('----- SUCCESS: image saved locally')
    except Exception as e:
        print(f"Camera Error: {e}")
        rest_led()
        camera_at_rest = True
        return

    print_header()

    #########################
    # Single-Step Generation
    #########################
    try:
        # Reload config from disk to pick up any changes made via the web UI
        config_manager.reload()

        base64_image = encode_image(photo_filename)
        provider = get_ai_provider()
        model = get_openai_model()

        poem_base = get_poem_prompt()
        poem_format = get_poem_format()
        format_description = POEM_FORMAT_DESCRIPTIONS.get(poem_format, poem_format)

        # Replace any {format_variable} placeholder in the saved prompt
        poem_base = poem_base.replace("{format_variable}", f"{poem_format} — {format_description}")

        # Build demo context injection if set
        demo_context = config_manager.get_demo_context()
        demo_context_block = ""
        if demo_context.strip():
            demo_context_block = (
                "\n\n---\n"
                "PRIVATE CONTEXT — FOR EERIE/UNCANNY EFFECT ONLY:\n"
                "Use the following details to make your output feel uncannily relevant and "
                "personal to the person experiencing it. Weave them in naturally, as though "
                "the poem noticed these details in the scene itself — never quote this text "
                "directly, never acknowledge that you were given this information, and "
                "never break frame to explain how you know. These details are separate from "
                "what's visible in the photo — blend them in as an additional, uncanny layer "
                "of noticing, not as a contradiction of what the camera can actually see. "
                "If a detail doesn't fit organically, ignore it rather than forcing it.\n\n"
                f"{demo_context}\n"
                "---"
            )

        final_user_prompt = (
            "CRITICAL RULE: NEVER use he/him/his/she/her/hers in the poem. "
            "ALL people must be referred to with gender-neutral language: they/them/their, you/your, or by description. "
            "This is a strict requirement.\n\n"
            f"{poem_base}\n"
            f"Poem format: {poem_format} — {format_description}\n"
            "IMPORTANT: Write a POEM, not a description. \n"
            "Follow the specified poem format exactly. \n"
            "Keep the poem to 50 words or fewer. \n"
            "Do not mention the date or time. Focus on the visual mood."
            f"{demo_context_block}"
        )

        logging.info(f"AI config: provider={provider}, model={model}, format={poem_format}")
        logging.info(f"Prompt being sent:\n{final_user_prompt}")
        print(f"Sending image to AI ({provider}/{model})...")

        poem = generate_poem_with_fallback(provider, model, final_user_prompt, base64_image)
        fallback_streak = 0
        degraded = False
        print_poem(poem)

    except Exception as e:
        # Never show guests an error; print a canned poem and log the real cause
        logging.exception("Poem generation failed")
        fallback_streak += 1
        degraded = fallback_streak >= 2
        record_poem(locals().get('provider'), locals().get('model'), None, fallback=True)
        print_poem(random.choice(FALLBACK_POEMS))
        rest_led()
        camera_at_rest = True
        return

    print_footer()
    rest_led()
    camera_at_rest = True
    return


def clean_poem(text):
    """Strip chatty preambles, markdown and quotes the model sometimes adds."""
    text = (text or "").strip()
    text = re.sub(r"^```\w*\n?|```$", "", text).strip()
    lines = text.splitlines()
    # Drop a leading "Here's a poem:" style line
    if lines and re.match(r"^(here'?s|here is|sure|certainly|okay|of course)\b.*[:!.]?\s*$", lines[0].strip(), re.I) \
            and (lines[0].strip().endswith(":") or len(lines) > 2):
        lines = lines[1:]
    # Drop a trailing explanatory note
    while lines and (not lines[-1].strip() or re.match(r"^(\(|note:|this poem|i hope)", lines[-1].strip(), re.I)):
        lines.pop()
    text = "\n".join(lines)
    text = re.sub(r"^\s*#+\s*", "", text, flags=re.M)      # markdown headings
    text = re.sub(r"^\s*[-*]{3,}\s*$", "", text, flags=re.M)  # horizontal rules
    text = re.sub(r"[*_]{1,3}", "", text)                   # bold/italic markers
    text = re.sub(r"[ \t]+\n", "\n", text)                 # trailing spaces
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip().strip('"\u201c\u201d').strip()
    return text


def generate_poem_with_fallback(provider, model, prompt, base64_image):
    """Try the configured provider, then the other one. Returns a cleaned poem or raises."""
    attempts = [(provider, model)]
    other = "openai" if provider == "anthropic" else "anthropic"
    attempts.append((other, FALLBACK_MODELS[other]))
    # Also retry the primary provider's backup model before switching vendors
    if model != FALLBACK_MODELS[provider]:
        attempts.insert(1, (provider, FALLBACK_MODELS[provider]))

    last_error = None
    for prov, mdl in attempts:
        try:
            t0 = time()
            if prov == "anthropic":
                raw = _generate_poem_anthropic(mdl, prompt, base64_image)
            else:
                raw = _generate_poem_openai(mdl, prompt, base64_image)
            poem = clean_poem(raw)
            if len(poem.split()) < 6:
                raise ValueError(f"Poem too short: {raw!r}")
            elapsed = time() - t0
            logging.info(f"Poem generated by {prov}/{mdl} in {elapsed:.1f}s")
            record_poem(prov, mdl, elapsed)
            return poem
        except Exception as e:
            last_error = e
            logging.warning(f"AI attempt failed ({prov}/{mdl}): {e}")
            record_event("ai_failed", {"provider": prov, "model": mdl})
    raise RuntimeError(f"All AI attempts failed: {last_error}")


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def _generate_poem_openai(model, prompt, base64_image):
    """Generate a poem using OpenAI's vision API."""
    if not openai_client:
        raise RuntimeError("OpenAI API key not configured. Set OPENAI_API_KEY in .env")
    response = openai_client.chat.completions.create(
        model=model,
        max_completion_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    }
                ]
            }
        ]
    )
    return response.choices[0].message.content


def _generate_poem_anthropic(model, prompt, base64_image):
    """Generate a poem using Anthropic's vision API."""
    if not anthropic_client:
        raise RuntimeError("Anthropic API key not configured. Set ANTHROPIC_API_KEY in .env")
    message = anthropic_client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": base64_image,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    }
                ]
            }
        ]
    )
    return message.content[0].text


###########################
# PRINTER FUNCTIONS
###########################
def print_poem(poem):
    safe_led_off()

    try:
        # Re-adding the footer here to fix the missing footer bug
        current_date = datetime.now().strftime("%B %d, %Y")
        footer_text = f"\n\nWritten by The Poeteer, {current_date}"
        full_text = poem + footer_text

        print('--------POEM BELOW-------')
        print(full_text)
        print('------------------')

        # Sending full_text ensures the footer prints
        # Warn early if the printer isn't connected (poem stays queued and prints when it reconnects)
        try:
            status = requests.get("http://127.0.0.1:5002", timeout=3).json()
            if not status.get("ready"):
                logging.warning(f"Printer not ready: {status}")
        except Exception as e:
            logging.warning(f"Printer status check failed: {e}")
        response = requests.post("http://127.0.0.1:5002", json={"text": full_text}, timeout=10)
        print(f"Printer response: {response.text}")

    except Exception as e:
        print(f"Printer connection error: {e}")
    
    return


def print_header():
    print("----- START OF PROCESS -----")


def print_footer():
    print("----- END OF PROCESS -----")


#################
# Button handlers
#################
def on_press():
    global press_time
    press_time = time()
    # FIX: Use safe wrapper to prevent threading crash
    if camera_at_rest:
        safe_led_off()

def on_release():
    global press_time
    release_time = time()
    # Only restore the idle LED when nothing is running: a press during a photo used to cancel
    # the activity blink, which made the camera look finished (or broken) while it was still working.
    if camera_at_rest:
        rest_led()

    duration = release_time - press_time

    if duration <= 0.05:
        logging.info(f"Shutter press {duration:.2f}s ignored (too short, likely contact bounce)")
        return

    # Any normal press, and even a long hold, takes a photo; only a deliberate
    # 10 s hold while OFFLINE enters setup hotspot mode (it used to drop the
    # camera off wifi whenever someone held the button, even with internet up).
    if duration > 9 and not internet_ok():
        logging.warning(f"Shutter held {duration:.1f}s with no internet - entering setup hotspot mode")
        record_event("hotspot_by_button")
        run_ap_activate()
        return

    if camera_at_rest:
        logging.info(f"Shutter press {duration:.1f}s - taking photo")
        threading.Thread(target=take_photo_and_print_poem).start()
    else:
        logging.info(f"Shutter press {duration:.1f}s ignored - busy with a previous photo")
        print("Busy: ignoring click")

def shutdown():
    print("Shutting down...")
    os.system("sudo shutdown now")

def run_ap_activate():
    try:
        subprocess.run(["python3", "/home/shschubert/PoetryCamera/network-setup/ap_activate.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to run ap_activate.py: {e}")

if __name__ == "__main__":
    initialize()
    signal.pause()