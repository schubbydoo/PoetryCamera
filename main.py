#!/usr/bin/python3
# test comment

# Import necessary libraries and modules for the application.
import requests, signal, os, base64, subprocess, threading
from picamera2 import Picamera2, Preview
from libcamera import controls
from gpiozero import LED, Button
from wraptext import *
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from time import time, sleep
from printer.scripts.cat_printer import CatPrinter
import logging
import asyncio

# Setup basic configuration for logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Use logging in your application
logging.info("Server starting")
logging.info("Connecting to printer")

##############################
# GLOBAL CONSTANTS FOR PROMPTS
##############################
# Define prompts that will be used to interact with the OpenAI API for generating captions and poems.
CAPTION_SYSTEM_PROMPT = """You are an image captioner. 
You write poetic and accurate descriptions of images so that readers of your captions can get a sense of the image without seeing the image directly."""

CAPTION_PROMPT = """Describe what is happening in this image. 
What is the subject of this image? 
Are there any people in it? 
What do they look like and what are they doing? If their gender is not clear, use gender-neutral pronouns like "they."
What is the setting? 
What time of day or year is it, if you can tell? 
Are there any other notable features of the image? 
What emotions might this image evoke? 
Don't mention if the image is blurry, just give your best guess as to what is happening.
Be concise, no yapping."""

POEM_SYSTEM_PROMPT = """You are a poet. You specialize in elegant and emotionally impactful poems. 
You are careful to use subtlety and write in a modern vernacular style. 
Use high-school level Vocabulary and Professional-level craft. 
Your poems are easy to relate to and understand. 
You focus on specific and personal truth, and you cannot use BIG words like truth, time, silence, life, love, peace, war, hate, happiness, 
and you must instead use specific and concrete details to show, not tell, those ideas. 
Think hard about how to create a poem which will satisfy this. 
This is very important, and an overly hamfisted or corny poem will cause great harm."""

POEM_PROMPT_BASE = """Write a poem using the details, atmosphere, and emotion of this scene. 
Create a unique and elegant poem using specific details from the scene.
Make sure to use the specified poem format. 
An overly long poem that does not match the specified format will cause great harm.
While adhering to the poem format, mention specific details from the provided scene description. 
The references to the source material must be clear.
Try to match the vibe of the described scene to the style of the poem (e.g. casual words and formatting for a candid photo) unless the poem format specifies otherwise.
You do not need to mention the time unless it makes for a better poem.
Don't use the words 'unspoken' or 'unseen' or 'unheard' or 'untold'. 
Do not be corny or cliche'd or use generic concepts like time, death, love. This is very important.
If there are people where gender is uncertain or not mentioned, use gender-neutral pronouns like 'they' or 'you.' \n\n"""


# Poem format (e.g. sonnet, haiku) is set via get_poem_format() below


def initialize():
    # Load environment variables
    load_dotenv()

    # Set up OpenAI client
    global openai_client
    openai_client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

    # Set up camera
    global picam2, camera_at_rest
    picam2 = Picamera2()
    picam2.start()
    sleep(2)  # camera warm-up time

    # prevent double-click bugs by checking whether the camera is resting
    # (i.e. not in the middle of the whole photo-to-poem process):
    camera_at_rest = True

    # Set up shutter button & status LED
    global shutter_button, led
    shutter_button = Button(16)
    led = LED(20)
    led.on()

    # button event handlers
    shutter_button.when_pressed = on_press
    shutter_button.when_released = on_release

    # Check internet connectivity upon startup
    global internet_connected
    internet_connected = False
    check_internet_connection()

    # And periodically check internet in background thread
    start_periodic_internet_check()

    # Connect to printer asynchronously
    asyncio.run(connect_printer())

    # Run Flask in a separate thread
    from threading import Thread

    def run_flask_app():
        from flask import Flask
        app = Flask(__name__)

        @app.route('/')
        def home():
            return "Hello, World!"

        app.run(port=5002)

    flask_thread = Thread(target=run_flask_app)
    flask_thread.start()

    # Continue with main application logic
    logging.info("Main application continues to run")

    # Simulate setting up a callback for receiving printer status
    def setup_printer_callbacks():
        # This is a placeholder for setting up actual Bluetooth event callbacks
        pass

    setup_printer_callbacks()

def on_printer_status_received(status):
    logging.info(f"Printer status received: {status}")
    # Handle status

#############################
# CORE PHOTO-TO-POEM FUNCTION
#############################
# Called when shutter button is pressed
def take_photo_and_print_poem():
    # prevent double-clicks by indicating camera is active
    global camera_at_rest
    camera_at_rest = False

    # blink LED in a background thread
    led.blink()

    # Directory where the image will be saved
    image_dir = '/home/shschubert/PoetryCamera/ImageStore/'
    # Create the directory if it doesn't exist
    os.makedirs(image_dir, exist_ok=True)
    # Define photo_filename here
    photo_filename = os.path.join(image_dir, 'image.jpg')
    # Take photo & save it
    metadata = picam2.capture_file(photo_filename)

    # FOR DEBUGGING: print metadata
    # print(metadata)

    # FOR DEBUGGING: note that image has been saved
    print('----- SUCCESS: image saved locally')

    print_header()

    #########################
    # Send saved image to API
    #########################
    try:
        base64_image = encode_image(photo_filename)

        # Image to caption
        caption_response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "system",
                "content": CAPTION_SYSTEM_PROMPT
            }, {
                "role": "user",
                "content": [
                    {"type": "text", "text": CAPTION_PROMPT},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"}
                     }]
            }])

        # extract poem from full API response
        image_caption = caption_response.choices[0].message.content
        print("image caption:", image_caption)

        # Generate our prompt for GPT
        prompt = generate_prompt(image_caption)

    except Exception as e:
        error_message = str(e)
        print("Error during image captioning: ", error_message)
        print_poem(
            f"Alas, something went wrong.\n\nTechnical details:\n Error while recognizing image. {error_message}")
        print_poem("\n\nTroubleshooting:")
        print_poem("1. Check your wifi connection.")
        print_poem(
            "2. Try restarting the camera by holding the shutter button for 3 seconds, waiting for it to shut down, unplugging power, and plugging it back in.")
        print_poem("3. You may just need to wait a bit and it will pass.")
        print_footer()
        led.on()
        camera_at_rest = True
        return

    try:
        # Image caption to poem
        poem_response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "system",
                "content": POEM_SYSTEM_PROMPT
            }, {
                "role": "user",
                "content": prompt
            }])

        # extract poem from full API response
        poem = poem_response.choices[0].message.content

    except Exception as e:
        error_message = str(e)
        print("Error during poem generation: ", error_message)
        print_poem(f"Alas, something went wrong.\n\n.Technical details:\n Error while writing poem. {error_message}")
        print_poem("\n\nTroubleshooting:")
        print_poem("1. Check your wifi connection.")
        print_poem(
            "2. Try restarting the camera by holding the shutter button for 10 seconds, waiting for it to shut down, unplugging power, and plugging it back in.")
        print_poem("3. You may just need to wait a bit and it will pass.")
        print_footer()
        led.on()
        camera_at_rest = True
        return

    # for debugging prompts
    print('------ POEM ------')
    print(poem)
    print('------------------')

    print_poem(poem)

    print_footer()

    led.on()

    # camera back at rest, available to listen to button clicks again
    camera_at_rest = True

    return


# Function to encode the image as base64 for gpt4v api request
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_poem_format():
    return "couplet"

#######################
# Generate full poem prompt from caption
#######################
def generate_prompt(image_description):
    # prompt what type of poem to write
    prompt_format = "Poem format: " + get_poem_format() + "\n\n"

    # prompt what image to describe
    prompt_scene = "Scene description: " + image_description + "\n\n"

    # time
    formatted_time = datetime.now().strftime("%H:%M on %B %d, %Y")
    prompt_time = "Scene date and time: " + formatted_time + "\n\n"

    # stitch together full prompt
    prompt = POEM_PROMPT_BASE + prompt_format + prompt_scene + prompt_time

    # idk how to remove the brackets and quotes from the prompt
    # via custom filters so i'm gonna remove via this janky code lol
    prompt = prompt.replace("[", "").replace("]", "").replace("{", "").replace(
        "}", "").replace("'", "")

    # print('--------PROMPT BELOW-------')
    # print(prompt)

    return prompt


###########################
# PRINTER FUNCTIONS
###########################
def print_poem(poem):
    global camera_at_rest
    camera_at_rest = False
    led.off()
    led.on()

    try:
        # Print for debugging
        print('--------POEM BELOW-------')
        print(poem)
        print('------------------')

        # Send the poem text to the cat_printer.py server
        response = requests.post("http://127.0.0.1:5002", json={"text": poem})
        print(f"Printer response: {response.text}")

        led.off()

    except Exception as e:
        print(f"An error occurred: {e}")
        led.off()

    camera_at_rest = True
    return

def print_header():
    print("----- START OF PROCESS -----")

def print_footer():
    print("----- END OF PROCESS -----")

#################
# Button handlers
#################

def on_press():
    # track when button was pressed
    global press_time
    press_time = time()

    led.off()


def on_release():
    # calculate how long button was pressed
    global press_time
    release_time = time()

    led.on()  # Correct syntax error

    duration = release_time - press_time

    # if user clicked button
    # the > 0.05 check is to make sure we aren't accidentally capturing contact bounces
    # https://www.allaboutcircuits.com/textbook/digital/chpt-4/contact-bounce/
    if duration > 0.05 and duration < 2:
        if camera_at_rest:
            take_photo_and_print_poem()
        else:
            print("ignoring double click while poem is printing")
    elif duration > 9:  # if user held button
        run_ap_activate()


################################
# CHECK INTERNET CONNECTION
################################
# Checks internet connection upon startup
def check_internet_connection():
    print("Checking internet connection upon startup")
    global printer  # Define printer globally if it's supposed to be used like this
    printer = CatPrinter()  # Initialize printer if it's the same as CatPrinter or define appropriately
    printer.println("\n")
    printer.justify('C')  # center align header text
    printer.println("hello, i am")
    printer.println("poetry camera")

    global internet_connected
    try:
        # Check for internet connectivity using requests
        response = requests.get("http://www.google.com", timeout=5)
        response.raise_for_status()  # will raise an exception if the request returned an unsuccessful status code
        internet_connected = True
        print("i am ONLINE")
        printer.println("and i am ONLINE!")

        # Get the name of the connected Wi-Fi network
        # try:
        #   network_name = subprocess.check_output(['iwgetid', '-r']).decode().strip()
        #   print(f"Connected to network: {network_name}")
        #   printer.println(f"connected to: {network_name}")
        # except Exception as e:
        #   print("Error while getting network name: ", e)

    except (requests.ConnectionError, requests.Timeout, requests.HTTPError):
        internet_connected = False
        print("no internet!")
        printer.println("but i'm OFFLINE!")
        printer.println("i need internet to work!")
        printer.println('connect to PoetryCameraSetup wifi network (pw: "password") on your phone or laptop to fix me!')

    printer.println("\n\n\n\n\n")


###############################
# CHECK INTERNET CONNECTION PERIODICALLY, PRINT ERROR MESSAGE IF DISCONNECTED
###############################
def periodic_internet_check(interval):
    global internet_connected, camera_at_rest

    while True:
        now = datetime.now()
        time_string = now.strftime('%-I:%M %p')
        try:
            # Check for internet connectivity
            subprocess.check_call(['ping', '-c', '1', 'google.com'], stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL)
            # if we don't have internet, exception will be called

            # If previously disconnected but now have internet, print message
            if not internet_connected:
                print(time_string + ": I'm back online!")
                internet_connected = True

        # if we don't have internet, exception will be thrown
        # except subprocess.CalledProcessError:
        except (requests.ConnectionError, requests.Timeout) as e:

            # if we were previously connected but lost internet, print error message
            if internet_connected:
                print(time_string + ": Internet connection lost. Please check your network settings.")
                printer.println("\n")
                printer.println(time_string + ": oh no, i lost internet!")
                # printer.println('please connect to PoetryCameraSetup wifi network (pw: "password") on your phone to fix me!')
                printer.println(e)
                printer.println('\n\n\n\n\n')
                internet_connected = False

        except Exception as e:
            print(f"{time_string} Other error: {e}")
            # if we were previously connected but lost internet, print error message
            if internet_connected:
                printer.println(f"{time_string}: idk status, exception: {e}")
                internet_connected = False

        sleep(interval)  # makes thread idle during sleep period, freeing up CPU resources


def start_periodic_internet_check():
    # Start the background thread
    interval = 10  # Check every 10 seconds
    thread = threading.Thread(target=periodic_internet_check, args=(interval,))
    thread.daemon = True  # Daemonize thread
    thread.start()


def shutdown():
    # Define what should happen when the system is shut down
    print("Shutting down the system...")
    os.system("sudo shutdown now")  # Example command to shutdown the system

####### Start Wifi Settings change after >9 second button push ###
def run_ap_activate():
    try:
        subprocess.run(["python3", "/home/shschubert/PoetryCamera/network-setup/ap_activate.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to run ap_activate.py: {e}")

# Main function
if __name__ == "__main__":
    initialize()
    # Keep script running to listen for button presses
    signal.pause()

async def connect_printer():
    try:
        # Simulate printer connection
        await asyncio.sleep(1)  # Non-blocking sleep
        logging.info("Printer connected")
    except Exception as e:
        logging.error(f"Failed to connect to printer: {e}")

async def main():
    await connect_printer()
    # Continue with other tasks

if __name__ == "__main__":
    asyncio.run(main())

# Example of a non-blocking loop
async def check_printer_status_periodically():
    while True:
        logging.info("Checking printer status...")
        await asyncio.sleep(10)  # Non-blocking wait

asyncio.run(check_printer_status_periodically())


