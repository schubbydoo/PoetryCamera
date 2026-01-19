import os
import time
import threading
from gpiozero import LED
import requests
import subprocess

# Initialize the LEDs
wifi_led = LED(5)
internet_led = LED(27)

def check_wifi_connection():
    # Check WiFi connection by running iwgetid and checking its return value
    result = os.system("iwgetid -r > /dev/null 2>&1")
    return result == 0

def check_http_connection(url, timeout=5):
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except:
        return False

def check_internet_connection():
    # Check HTTP connection to two known reliable URLs
    if check_http_connection('https://www.google.com') or check_http_connection('https://www.example.com'):
        return True
    return False

def ping_host(host, ping_count=5):
    try:
        # Ping the specified host multiple times
        result = subprocess.run(['ping', '-c', str(ping_count), host], stdout=subprocess.DEVNULL)
        return result.returncode == 0
    except:
        return False

def stable_check_internet():
    # Perform both HTTP check and ping check for better reliability
    http_check = check_internet_connection()
    ping_check_google = ping_host('www.google.com')
    ping_check_example = ping_host('www.example.com')
    
    if http_check and (ping_check_google or ping_check_example):
        return True
    return False

def wifi_check():
    while True:
        if check_wifi_connection():
            wifi_led.on()
        else:
            wifi_led.blink(on_time=1, off_time=1)
        time.sleep(10)

def internet_check():
    while True:
        if check_wifi_connection():
            internet_led.blink(on_time=1, off_time=1)
            if stable_check_internet():
                internet_led.on()
                while True:
                    # Retry mechanism for ping checks
                    success = False
                    for _ in range(3):
                        ping_success = ping_host('www.google.com') or ping_host('www.example.com')
                        if ping_success:
                            success = True
                            break
                        time.sleep(3)  # Short delay before retrying
                    if success:
                        internet_led.on()
                    else:
                        internet_led.blink(on_time=1, off_time=1)
                    time.sleep(10)
            else:
                internet_led.blink(on_time=1, off_time=1)
        else:
            internet_led.off()  # Turn off internet LED if WiFi is not connected
        time.sleep(10)

if __name__ == "__main__":
    wifi_thread = threading.Thread(target=wifi_check)
    internet_thread = threading.Thread(target=internet_check)

    wifi_thread.start()
    internet_thread.start()

    wifi_thread.join()
    internet_thread.join()
