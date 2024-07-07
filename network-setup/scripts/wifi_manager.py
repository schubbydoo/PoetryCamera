# wifi_manager.py
import subprocess

def change_wifi(ssid, password):
    try:
        subprocess.run(["nmcli", "dev", "wifi", "connect", ssid, "password", password], check=True)
        return "Wi-Fi settings updated successfully"
    except subprocess.CalledProcessError as e:
        return f"Failed to update Wi-Fi settings: {e}"
