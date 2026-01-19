"""
AP Mode Activation Script for Poetry Camera

Activates the PoetCam access point mode when the user holds the shutter button
for more than 9 seconds. The web interface (running on port 8000) will
automatically detect AP mode and display the appropriate banner.
"""

import subprocess
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def activate_ap_mode():
    """Activate the PoetCam access point for WiFi configuration."""
    try:
        # Attempt to bring up the PoetCam connection
        result = subprocess.run(
            ["sudo", "nmcli", "connection", "up", "PoetCam"], 
            check=True, 
            capture_output=True, 
            text=True
        )
        logging.info(result.stdout)
        
        # Check if the connection is up
        check_result = subprocess.run(
            ["nmcli", "-t", "-f", "active", "connection", "show", "--active"], 
            capture_output=True, 
            text=True
        )
        logging.info("Active connections check result: %s", check_result.stdout)
        
        if "PoetCam" in check_result.stdout or "Connection successfully activated" in result.stdout:
            logging.info("PoetCam AP mode activated successfully")
            logging.info("Web interface is available at http://10.42.0.1:8000")
            logging.info("Users can configure WiFi via the web interface")
            
            # The web interface is already running (started by startup.sh)
            # It will automatically detect AP mode and show the appropriate UI
            # No need to start wifi_config.py separately anymore
            
        else:
            logging.error("Failed to start WiFi Setup")
            
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to start WiFi Setup: {e}")
        logging.error(e.stderr)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")


def deactivate_ap_mode():
    """Deactivate the PoetCam access point."""
    try:
        result = subprocess.run(
            ["sudo", "nmcli", "connection", "down", "PoetCam"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logging.info("PoetCam AP mode deactivated")
        else:
            logging.error(f"Failed to deactivate AP mode: {result.stderr}")
    except Exception as e:
        logging.error(f"Error deactivating AP mode: {e}")


if __name__ == "__main__":
    activate_ap_mode()
