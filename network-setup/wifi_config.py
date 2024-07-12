from flask import Flask, render_template, request, redirect, url_for, flash
import subprocess
import uuid

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
        print(f"Error scanning WiFi networks: {e}")
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
    config_path = f"/etc/NetworkManager/system-connections/{connection_name}.nmconnection"
    print(f"Writing config to {config_path} with contents:\n{config}")
    try:
        with open(config_path, 'w') as f:
            f.write(config)
        subprocess.run(['sudo', 'chmod', '600', config_path])
        subprocess.run(['sudo', 'nmcli', 'connection', 'reload'])
        subprocess.run(['sudo', 'nmcli', 'connection', 'up', connection_name])
        print(f"Successfully configured {ssid}")
        return True
    except Exception as e:
        print(f"Error configuring WiFi: {e}")
        return False

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
