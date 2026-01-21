#!/usr/bin/python3
# Poetry Camera Main Application
# Captures images, generates AI poetry, and prints to thermal printer

import requests, signal, os, base64, subprocess, threading
from picamera2 import Picamera2
from gpiozero import LED, Button
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from time import time, sleep
import logging

# Import configuration manager
from web_interface.config_manager import config_manager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logging.info("Server starting")
logging.info("Connecting to printer")

# --- Config Getters ---
def get_poem_system_prompt():
    return config_manager.get_poem_system_prompt()

def get_poem_prompt():
    return config_manager.get_poem_prompt()

def get_poem_format():
    return config_manager.get_poem_format()

def get_openai_model():
    return config_manager.get_openai_model()

def initialize():
    load_dotenv()

    # Set up OpenAI client
    global openai_client
    openai_client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

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

#############################
# CORE PHOTO-TO-POEM FUNCTION
#############################
def take_photo_and_print_poem():
    global camera_at_rest
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
        safe_led_on()
        camera_at_rest = True
        return

    print_header()

    #########################
    # Single-Step Generation
    #########################
    try:
        base64_image = encode_image(photo_filename)
        model = get_openai_model()
        
        poem_base = get_poem_prompt()
        poem_format = get_poem_format()
        
        # AGGRESSIVE PROMPT for speed and brevity
        final_user_prompt = (
            f"{poem_base}\n"
            f"Style: {poem_format}\n"
            "IMPORTANT: Write a POEM, not a description. \n"
            "Keep it short (max 8 lines). \n"
            "Do not mention the date or time. Focus on the visual mood."
        )

        print("Sending image to AI...")
        
        # Note: 'max_tokens' is removed to support o1 models
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": final_user_prompt},
                        {
                            "type": "image_url", 
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ]
                }
            ]
        )

        poem = response.choices[0].message.content
        print_poem(poem)

    except Exception as e:
        error_message = str(e)
        print("Error during generation: ", error_message)
        print_poem(f"Alas, the muses are silent.\n(Error: {error_message[:50]}...)")
        safe_led_on()
        camera_at_rest = True
        return

    print_footer()
    safe_led_on()
    camera_at_rest = True
    return


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


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
        response = requests.post("http://127.0.0.1:5002", json={"text": full_text})
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
    # FIX: Use safe wrapper
    safe_led_on() 
    
    duration = release_time - press_time

    if duration > 0.05 and duration < 2:
        if camera_at_rest:
            threading.Thread(target=take_photo_and_print_poem).start()
        else:
            print("Busy: ignoring click")
    elif duration > 9:
        run_ap_activate()

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