"""
Poetry Camera Web Interface

Flask application providing web-based configuration and management.
"""

import os
import requests
from functools import wraps
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for, 
    flash, jsonify, session
)

from .wifi_manager import wifi_manager
from .system_manager import system_manager
from .config_manager import config_manager

# Create Flask app
app = Flask(__name__)
app.secret_key = config_manager.get_secret_key()


# ==================== Authentication ====================

def login_required(f):
    """Decorator to require login for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@app.context_processor
def inject_globals():
    """Inject global variables into all templates."""
    return {
        'version': system_manager.get_version(),
        'current_year': datetime.now().year,
        'is_in_ap_mode': wifi_manager.is_ap_mode(),
        'current_user': {'is_authenticated': session.get('logged_in', False)}
    }


# ==================== Page Routes ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page."""
    if session.get('logged_in'):
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        if config_manager.verify_credentials(username, password):
            session['logged_in'] = True
            session['username'] = username
            flash('Welcome to Poetry Camera!', 'success')
            
            next_url = request.args.get('next')
            if next_url:
                return redirect(next_url)
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout and redirect to login."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/')
@login_required
def home():
    """Dashboard/home page."""
    # Get device status
    wifi_status = wifi_manager.get_current_connection()
    system_info = system_manager.get_system_info()
    printer_config = config_manager.get_printer_config()
    
    # Try to get printer status from cat_printer service
    printer_status = {"connected": False, "ready": False, "status": {}, "service_running": False}
    try:
        response = requests.get("http://127.0.0.1:5002", timeout=1)
        if response.ok:
            data = response.json()
            printer_status = {
                "connected": data.get("ready", False),
                "ready": data.get("ready", False),
                "address": data.get("address"),
                "status": data.get("status", {}),
                "transmit": data.get("transmit", False),
                "service_running": True
            }
    except requests.exceptions.ConnectionError:
        # Service not running
        printer_status["service_running"] = False
    except requests.exceptions.Timeout:
        # Service might be busy
        printer_status["service_running"] = True
    except Exception:
        pass
    
    return render_template('index.html',
        wifi_status=wifi_status,
        system_info=system_info,
        printer_config=printer_config,
        printer_status=printer_status
    )


@app.route('/wifi')
@login_required
def wifi():
    """WiFi management page."""
    wifi_status = wifi_manager.get_current_connection()
    return render_template('wifi.html', wifi_status=wifi_status)


@app.route('/system')
@login_required
def system():
    """System management page."""
    system_info = system_manager.get_system_info()
    return render_template('system.html', system_info=system_info)


@app.route('/settings')
@login_required
def settings():
    """Settings page for prompts and printer configuration."""
    openai_config = config_manager.get_openai_config()
    printer_config = config_manager.get_printer_config()
    return render_template('settings.html',
        openai_config=openai_config,
        printer_config=printer_config
    )


@app.route('/settings/account')
@login_required
def account():
    """Account settings page."""
    return render_template('account.html',
        username=config_manager.get_username()
    )


# ==================== API Routes - Status ====================

@app.route('/api/status')
@login_required
def api_status():
    """Get overall device status."""
    wifi_status = wifi_manager.get_current_connection()
    system_info = system_manager.get_system_info()
    
    # Try to get printer status
    printer_status = {"connected": False}
    try:
        response = requests.get("http://127.0.0.1:5002", timeout=2)
        if response.ok:
            printer_status = response.json()
    except:
        pass
    
    return jsonify({
        "success": True,
        "wifi": wifi_status,
        "system": system_info,
        "printer": printer_status
    })


# ==================== API Routes - WiFi ====================

@app.route('/api/wifi/status')
@login_required
def api_wifi_status():
    """Get current WiFi status."""
    status = wifi_manager.get_current_connection()
    return jsonify({
        "success": True,
        **status
    })


@app.route('/api/wifi/scan')
@login_required
def api_wifi_scan():
    """Scan for available WiFi networks."""
    try:
        networks = wifi_manager.scan_networks()
        return jsonify({
            "success": True,
            "networks": networks
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/wifi/networks')
@login_required
def api_wifi_networks():
    """Get saved WiFi networks."""
    try:
        networks = wifi_manager.get_saved_networks()
        return jsonify({
            "success": True,
            "networks": networks
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/wifi/connect', methods=['POST'])
@login_required
def api_wifi_connect():
    """Connect to a WiFi network."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400
    
    ssid = data.get('ssid')
    password = data.get('password')
    autoconnect = data.get('autoconnect', True)
    
    if not ssid:
        return jsonify({"success": False, "error": "SSID is required"}), 400
    if not password:
        return jsonify({"success": False, "error": "Password is required"}), 400
    
    result = wifi_manager.connect_network(ssid, password, autoconnect)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@app.route('/api/wifi/forget', methods=['POST'])
@login_required
def api_wifi_forget():
    """Forget a saved WiFi network."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400
    
    ssid = data.get('ssid')
    if not ssid:
        return jsonify({"success": False, "error": "SSID is required"}), 400
    
    result = wifi_manager.forget_network(ssid)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


# ==================== API Routes - System ====================

@app.route('/api/check_updates')
@login_required
def api_check_updates():
    """Check for available updates."""
    result = system_manager.check_for_updates()
    status_code = 200 if result.get("success") else 500
    return jsonify(result), status_code


@app.route('/api/apply_updates', methods=['POST'])
@login_required
def api_apply_updates():
    """Apply available updates."""
    result = system_manager.apply_updates()
    status_code = 200 if result.get("success") else 500
    return jsonify(result), status_code


@app.route('/api/reboot', methods=['POST'])
@login_required
def api_reboot():
    """Reboot the device."""
    result = system_manager.reboot()
    return jsonify(result)


# ==================== API Routes - Settings ====================

@app.route('/api/settings/openai', methods=['GET', 'POST'])
@login_required
def api_settings_openai():
    """Get or update OpenAI settings."""
    if request.method == 'GET':
        config = config_manager.get_openai_config()
        return jsonify({
            "success": True,
            "config": config
        })
    
    # POST - update settings
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400
    
    result = config_manager.update_openai_config(data)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@app.route('/api/settings/printer', methods=['GET', 'POST'])
@login_required
def api_settings_printer():
    """Get or update printer settings."""
    if request.method == 'GET':
        config = config_manager.get_printer_config()
        return jsonify({
            "success": True,
            "config": config
        })
    
    # POST - update settings
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400
    
    result = config_manager.update_printer_config(data)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@app.route('/api/settings/reset', methods=['POST'])
@login_required
def api_settings_reset():
    """Reset settings to defaults."""
    data = request.get_json() or {}
    section = data.get('section')  # Optional: 'openai', 'printer', or None for all
    
    result = config_manager.reset_to_defaults(section)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@app.route('/api/settings/password', methods=['POST'])
@login_required
def api_change_password():
    """Change user password."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400
    
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not current_password or not new_password:
        return jsonify({"success": False, "error": "Both current and new password are required"}), 400
    
    if len(new_password) < 4:
        return jsonify({"success": False, "error": "Password must be at least 4 characters"}), 400
    
    result = config_manager.change_password(current_password, new_password)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


# ==================== API Routes - Printer Test ====================

@app.route('/api/printer/test', methods=['POST'])
@login_required
def api_printer_test():
    """Send a test print to the printer."""
    try:
        test_text = "Poetry Camera Test Print\n\nIf you can read this, your printer is working correctly!"
        response = requests.post(
            "http://127.0.0.1:5002",
            json={"text": test_text},
            timeout=10
        )
        if response.ok:
            return jsonify({
                "success": True,
                "message": "Test print sent to printer"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Printer did not respond"
            }), 500
    except requests.exceptions.ConnectionError:
        return jsonify({
            "success": False,
            "error": "Could not connect to printer service"
        }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ==================== Error Handlers ====================

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    if request.path.startswith('/api/'):
        return jsonify({"success": False, "error": "Not found"}), 404
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    if request.path.startswith('/api/'):
        return jsonify({"success": False, "error": "Internal server error"}), 500
    flash('An unexpected error occurred.', 'danger')
    return redirect(url_for('home'))


# ==================== Main ====================

def create_app():
    """Application factory."""
    return app


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
