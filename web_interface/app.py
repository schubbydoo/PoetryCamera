"""
Poetry Camera Web Interface

Flask application providing web-based configuration and management.
"""

import os
import sys
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
from .poem_stats import get_summary as get_poem_stats
from .health_monitor import NETGUARD_STATE_DIR

# Shared UI kit (https://github.com/schubbydoo/propkit), cloned to ~/propkit on the Pi
sys.path.insert(0, os.path.expanduser("~/propkit"))
import propkit
from propkit import flask_app as propkit_flask

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


ACTIVE_TAB = {'home': 'dashboard', 'settings': 'settings', 'account': 'account'}


@app.context_processor
def inject_globals():
    """Inject global variables into all templates."""
    return {
        'version': system_manager.get_version(),
        'current_year': datetime.now().year,
        'is_in_ap_mode': wifi_manager.is_ap_mode(),
        'active_page': ACTIVE_TAB.get(request.endpoint),
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
        printer_status=printer_status,
        poem_stats=get_poem_stats()
    )


@app.route('/settings')
@login_required
def settings():
    """Settings page for prompts and printer configuration."""
    openai_config = config_manager.get_openai_config()
    printer_config = config_manager.get_printer_config()
    demo_context = config_manager.get_demo_context()
    return render_template('settings.html',
        openai_config=openai_config,
        printer_config=printer_config,
        demo_context=demo_context
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


# ==================== API Routes - Demo Context ====================

@app.route('/api/settings/demo_context', methods=['GET', 'POST'])
@login_required
def api_demo_context():
    """Get or update demo context."""
    if request.method == 'GET':
        return jsonify({
            "success": True,
            "demo_context": config_manager.get_demo_context()
        })

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400

    config_manager.set_demo_context(data.get("demo_context", ""))
    return jsonify({"success": True, "message": "Demo context saved"})


@app.route('/api/settings/demo_context/clear', methods=['POST'])
@login_required
def api_clear_demo_context():
    """Clear demo context."""
    config_manager.clear_demo_context()
    return jsonify({"success": True, "message": "Demo context cleared"})


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


# ==================== Shared System tab (propkit) ====================

def _printer_rows():
    """Extra System-tab row: what the printer service reports."""
    try:
        d = requests.get("http://127.0.0.1:5002", timeout=1).json()
        st = d.get("status") or {}
        if st.get("no_paper"):
            return [{"k": "Printer", "v": "Out of paper", "color": "bad"}]
        if st.get("cover_open") or st.get("over_temp"):
            return [{"k": "Printer", "v": "Cover open or too hot", "color": "warn"}]
        return [{"k": "Printer", "v": "Ready" if d.get("ready") else "Connecting", "color": "good" if d.get("ready") else "warn"}]
    except Exception:
        return [{"k": "Printer", "v": "Printer service not responding", "color": "bad"}]


def _software_rows():
    try:
        today = get_poem_stats().get("today", 0)
    except Exception:
        today = "?"
    return [{"k": "Poems today", "v": str(today), "color": None}]


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PROP_CONFIG = propkit.PropConfig(
    name="Poetry Camera", brand=("POETRY", "CAMERA"),
    tabs=[("dashboard", "/", "Dashboard"), ("settings", "/settings", "Settings"),
          ("account", "/settings/account", "Account"),
          ("system", "/system", "System"), ("logout", "/logout", "Logout")],
    service_name="poetrycamera.service", base_dir=BASE_DIR,
    state_dir=os.path.abspath(NETGUARD_STATE_DIR),
    hotspot_profile="PoetCam", auth=login_required,
    allow_repo_change=True,   # every propkit route is behind login_required (cfg.auth)
    extra_health=_printer_rows, extra_software=_software_rows,
)
propkit_flask.install(app, PROP_CONFIG)


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
