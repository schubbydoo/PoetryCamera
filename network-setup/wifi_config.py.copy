from flask import Flask, render_template, request, redirect, url_for, flash
import subprocess
import uuid
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__)
app.secret_key = 'vG0U/pWAthcPyG94KOYk+Z3/gGEB9JAg'  # Replace this with your generated key

def scan_wifi():
    networks = []
    try:
        result = subprocess.run(['sudo', 'iwlist', 'wlan0', 'scan'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if "ESSID" in line:
                essid = line.split(':')[1].strip('"')
                if essid not in networks:
                    networks.append(essid)
    except Exception as e:
        logging.error(f"Error scanning WiFi networks: {e}")
    return networks

@app.route('/', methods=['GET', 'POST'])
def index():
    networks = scan_wifi()
    if request.method == 'POST':
        ssid = request.form.get('ssid')
        password = request.form.get('password')
        success = configure_wifi(ssid, password)
        if success:
            flash('Configuration saved successfully! The device will now reboot.')
            # Reboot the system
            reboot_system()
        else:
            flash('Failed to save configuration. Please try again.')
        return redirect(url_for('index'))
    return render_template('index.html', networks=networks)

def configure_wifi(ssid, password):
    connection_name = ssid.replace(' ', '_')
    config = f"""
    [connection]
    id={connection_name}
    uuid={str(uuid.uuid4())}
    type=wifi
    autoconnect=true

    [wifi]
    mode=infrastructure
    ssid={ssid}

    [wifi-security]
    auth-alg=open
    key-mgmt=wpa-psk
    psk={password}

    [ipv4]
    method=auto

    [ipv6]
    addr-gen-mode=stable-privacy
    method=auto
    """
    try:
        # Specify the absolute path to the script
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'write_wifi_config.sh')
        result = subprocess.run(['sudo', script_path, connection_name, config], capture_output=True, text=True)
        if result.returncode != 0:
            logging.error(f"Error configuring WiFi: {result.stderr}")
            return False
        logging.info(f"Successfully configured {ssid}")
        return True
    except Exception as e:
        logging.error(f"Error configuring WiFi: {e}")
        return False

def reboot_system():
    try:
        logging.info("Rebooting system...")
        subprocess.run(["sudo", "reboot"], check=True)
    except Exception as e:
        logging.error(f"Failed to reboot the system: {e}")

if __name__ == '__main__':
    logging.info("Starting WiFi configuration Flask app")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
