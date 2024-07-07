import RPi.GPIO as GPIO
import time
import os
from threading import Thread, Event

# GPIO Pins
BUTTON_PIN = 17
LED_PIN = 27

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(LED_PIN, GPIO.OUT)

# Global variables
camera_running = False
stop_event = Event()

def start_poetry_camera():
    global camera_running
    camera_running = True
    
    # Blink LED while starting
    def blink_led():
        while not stop_event.is_set():
            GPIO.output(LED_PIN, GPIO.HIGH)
            time.sleep(0.5)
            GPIO.output(LED_PIN, GPIO.LOW)
            time.sleep(0.5)
    
    blink_thread = Thread(target=blink_led)
    blink_thread.start()
    
    # Start cat_printer.py
    os.system("python3 cat_printer.py &")
    
    # Wait for the printer to be ready
    def is_printer_ready():
        while not stop_event.is_set():
            status = os.popen("curl -s http://127.0.0.1:5002 | grep -o '\"ready\":true'").read()
            if '"ready":true' in status:
                return True
            time.sleep(1)
        return False

    if is_printer_ready():
        # Start main.py
        os.system("python3 main.py &")
        GPIO.output(LED_PIN, GPIO.HIGH)  # Turn on LED solid when ready
    else:
        print("Stopped waiting for printer to be ready.")

def stop_poetry_camera():
    global camera_running
    camera_running = False
    stop_event.set()
    GPIO.output(LED_PIN, GPIO.LOW)  # Turn off LED
    os.system("pkill -f cat_printer.py")
    os.system("pkill -f main.py")

def button_listener():
    button_pressed_time = None
    debounce_time = 0.2  # Debounce time in seconds
    last_button_state = GPIO.HIGH

    while True:
        button_state = GPIO.input(BUTTON_PIN)
        
        if button_state != last_button_state:
            if button_state == GPIO.LOW:
                if button_pressed_time is None:
                    button_pressed_time = time.time()
                elif time.time() - button_pressed_time >= 5:
                    if camera_running:
                        print("Button held for 5 seconds. Stopping camera...")
                        stop_poetry_camera()
                    button_pressed_time = None
            else:
                if button_pressed_time is not None and time.time() - button_pressed_time < 5:
                    if not camera_running:
                        print("Button pressed. Starting camera...")
                        stop_event.clear()
                        start_poetry_camera()
                button_pressed_time = None
            last_button_state = button_state

        time.sleep(debounce_time)

def main():
    # Start the button listener in a separate thread
    button_thread = Thread(target=button_listener)
    button_thread.start()

    try:
        button_thread.join()
    except KeyboardInterrupt:
        GPIO.cleanup()

if __name__ == "__main__":
    main()
