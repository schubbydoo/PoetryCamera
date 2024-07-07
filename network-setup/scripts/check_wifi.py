# check_wifi.py
import subprocess

def is_connected():
    try:
        # Check if wlan0 has an IP address
        result = subprocess.run(['ip', 'addr', 'show', 'wlan0'], capture_output=True, text=True)
        return 'inet ' in result.stdout
    except Exception as e:
        print(f"Error checking Wi-Fi connection: {e}")
        return False

def start_access_point():
    subprocess.run(["sudo", "systemctl", "start", "hostapd"])
    subprocess.run(["sudo", "systemctl", "start", "dnsmasq"])
    print("Access point started")

if __name__ == "__main__":
    if not is_connected():
        start_access_point()
