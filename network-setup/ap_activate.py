import subprocess
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def activate_ap_mode():
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
            # Print environment variables for debugging
            logging.info("Environment variables:")
            for key, value in os.environ.items():
                logging.info(f"{key}: {value}")
            
            # Activate virtual environment and run wifi_config.py
            venv_activate = "/home/shschubert/PoetryCamera/poetrycamera-env/bin/activate"
            command = f"source {venv_activate} && python3 /home/shschubert/PoetryCamera/network-setup/wifi_config.py"
            wifi_result = subprocess.run(command, shell=True, capture_output=True, text=True, executable='/bin/bash')
            
            logging.info("wifi_config.py output: %s", wifi_result.stdout)
            logging.info("wifi_config.py error (if any): %s", wifi_result.stderr)
        else:
            logging.error("Failed to start Wifi Setup")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to start Wifi Setup: {e}")
        logging.error(e.stderr)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    activate_ap_mode()
