# Standard WebUI Specification

This specification defines the standard patterns, components, and features for building consistent web interfaces across Raspberry Pi-based projects.

---

## Table of Contents

1. [Overview](#overview)
2. [Technology Stack](#technology-stack)
3. [Project Structure](#project-structure)
4. [Base Template](#base-template)
5. [Navigation](#navigation)
6. [Required Pages](#required-pages)
7. [Optional Pages](#optional-pages)
8. [Common Components](#common-components)
9. [API Endpoints](#api-endpoints)
10. [Styling Guidelines](#styling-guidelines)
11. [JavaScript Patterns](#javascript-patterns)
12. [Implementation Checklist](#implementation-checklist)

---

## Overview

This spec ensures all projects share:
- Consistent look and feel
- Common system management features (WiFi, updates, reboot)
- Standardized API patterns
- Reusable components and templates

---

## Technology Stack

| Component | Technology | Version/Notes |
|-----------|------------|---------------|
| Backend | Python Flask | Latest stable |
| CSS Framework | Bulma | 0.9.4+ (via CDN) |
| Icons | Font Awesome | 6.x (via CDN) |
| Templating | Jinja2 | (included with Flask) |
| JavaScript | Vanilla JS | No framework required |

### CDN Links

```html
<!-- Bulma CSS -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@0.9.4/css/bulma.min.css">

<!-- Font Awesome -->
<script src="https://kit.fontawesome.com/YOUR_KIT_ID.js" crossorigin="anonymous"></script>
```

---

## Project Structure

```
project_name/
├── web_interface/
│   ├── __init__.py
│   ├── app.py                 # Flask application
│   ├── routes/                # Route blueprints (optional for larger apps)
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── wifi.py
│   │   └── system.py
│   ├── static/
│   │   ├── styles.css         # Custom styles
│   │   ├── main.js            # Main JavaScript
│   │   └── wifi.js            # WiFi-specific JavaScript
│   └── templates/
│       ├── base.html          # Base template
│       ├── index.html         # Home/dashboard
│       ├── login.html         # Login page (if auth enabled)
│       ├── wifi.html          # WiFi management
│       ├── system.html        # System updates/info
│       └── [feature].html     # Project-specific pages
├── wifi_management/
│   ├── __init__.py
│   └── network_manager.py     # WiFi operations
├── system_management.py       # System operations (reboot, updates)
├── VERSION                    # Version file
├── config.json               # Configuration
└── requirements.txt
```

---

## Base Template

All pages extend `base.html`. The base template includes:

### Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Project Name{% endblock %}</title>
    
    <!-- Bulma CSS -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@0.9.4/css/bulma.min.css">
    
    <!-- Custom Styles -->
    <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
    
    {% block extra_head %}{% endblock %}
</head>
<body>
    <!-- AP Mode Warning Banner (conditional) -->
    {% if is_in_ap_mode %}
    <div class="notification is-warning has-text-centered is-light" style="border-radius: 0; margin-bottom: 0;">
        <strong>Device is in Access Point (AP) Mode.</strong> 
        Connect to your home Wi-Fi via the <a href="{{ url_for('wifi') }}">WiFi Setup</a> page.
    </div>
    {% endif %}

    <!-- Header -->
    <nav class="navbar is-primary" role="navigation" aria-label="main navigation">
        <div class="navbar-brand">
            <a class="navbar-item" href="{{ url_for('home') }}">
                <strong>Project Name</strong>
            </a>
            <a role="button" class="navbar-burger" aria-label="menu" aria-expanded="false" data-target="mainNavbar">
                <span aria-hidden="true"></span>
                <span aria-hidden="true"></span>
                <span aria-hidden="true"></span>
            </a>
        </div>
        <div id="mainNavbar" class="navbar-menu">
            <div class="navbar-start">
                {% block nav_items %}{% endblock %}
            </div>
            <div class="navbar-end">
                <div class="navbar-item">
                    <div class="buttons">
                        {% if request.endpoint != 'home' %}
                        <a href="{{ url_for('home') }}" class="button is-light">Home</a>
                        {% endif %}
                        {% if current_user and current_user.is_authenticated %}
                        <a href="{{ url_for('logout') }}" class="button is-light">Logout</a>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
    </nav>

    <!-- Flash Messages -->
    <section class="section py-3">
        <div class="container">
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                    <div class="notification is-{{ category }} is-light">
                        <button class="delete"></button>
                        {{ message }}
                    </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
        </div>
    </section>

    <!-- Main Content -->
    <section class="section">
        <div class="container">
            {% block content %}{% endblock %}
        </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
        <div class="content has-text-centered">
            <p>
                &copy; {{ current_year }} Project Name
                {% if version %}
                <span class="tag is-dark is-small ml-2">v{{ version }}</span>
                {% endif %}
            </p>
        </div>
    </footer>

    <!-- Navbar burger toggle script -->
    <script>
    document.addEventListener('DOMContentLoaded', () => {
        const $navbarBurgers = Array.prototype.slice.call(document.querySelectorAll('.navbar-burger'), 0);
        $navbarBurgers.forEach(el => {
            el.addEventListener('click', () => {
                const target = el.dataset.target;
                const $target = document.getElementById(target);
                el.classList.toggle('is-active');
                $target.classList.toggle('is-active');
            });
        });
        
        // Auto-dismiss notifications
        document.querySelectorAll('.notification .delete').forEach(btn => {
            btn.addEventListener('click', () => {
                btn.parentNode.remove();
            });
        });
    });
    </script>
    
    {% block scripts %}{% endblock %}
</body>
</html>
```

### Context Variables

The base template expects these variables in the Flask context:

| Variable | Type | Description |
|----------|------|-------------|
| `is_in_ap_mode` | bool | Whether device is in AP mode |
| `version` | string | Application version from VERSION file |
| `current_year` | int | Current year for copyright |

**Flask Implementation:**

```python
@app.context_processor
def inject_globals():
    version = None
    version_file = Path(__file__).parent.parent / 'VERSION'
    if version_file.exists():
        version = version_file.read_text().strip()
    
    return {
        'version': version,
        'current_year': datetime.now().year,
        'is_in_ap_mode': check_ap_mode()  # Implement based on your wifi manager
    }
```

---

## Navigation

### Navigation Patterns

**Option A: Navbar with Hamburger Menu (Recommended)**

For projects with 3+ pages, use a hamburger menu that collapses on mobile:

```html
{% block nav_items %}
<a class="navbar-item" href="{{ url_for('home') }}">Dashboard</a>
<a class="navbar-item" href="{{ url_for('wifi') }}">WiFi</a>
<a class="navbar-item" href="{{ url_for('system') }}">System</a>
<a class="navbar-item" href="{{ url_for('settings') }}">Settings</a>
{% endblock %}
```

**Option B: Hero Header with Buttons**

For simpler projects with few pages:

```html
<section class="hero is-primary">
    <div class="hero-body">
        <div class="container">
            <div class="level">
                <div class="level-left">
                    <h1 class="title">Project Name</h1>
                </div>
                <div class="level-right">
                    <a href="{{ url_for('home') }}" class="button is-primary is-inverted">Home</a>
                    <a href="{{ url_for('wifi') }}" class="button is-primary is-inverted">WiFi</a>
                    <a href="{{ url_for('system') }}" class="button is-primary is-inverted">System</a>
                </div>
            </div>
        </div>
    </div>
</section>
```

---

## Required Pages

Every project MUST implement these pages:

### 1. Home/Dashboard (`/`)

The landing page showing device status and quick access to features.

**Required Elements:**
- Device status card (IP address, current network, key metrics)
- Quick links to main features
- Project-specific status information

**Template Structure:**

```html
{% extends "base.html" %}
{% block title %}Project Name - Dashboard{% endblock %}

{% block content %}
<!-- Welcome/Description Box -->
<div class="box mb-5">
    <p class="subtitle">Brief description of what this device does.</p>
</div>

<!-- Feature Cards -->
<div class="columns is-multiline">
    <div class="column is-4">
        <div class="box has-text-centered">
            <p class="title is-5">Feature Name</p>
            <p class="subtitle is-6">Brief description</p>
            <a href="{{ url_for('feature') }}" class="button is-primary">Configure</a>
        </div>
    </div>
    <!-- More feature cards... -->
</div>

<!-- Device Status -->
<div class="box">
    <h2 class="title is-5">Device Status</h2>
    <table class="table is-fullwidth is-striped">
        <tbody>
            <tr>
                <td class="has-text-weight-bold" style="width: 200px;">IP Address:</td>
                <td><code>{{ status.ip_address }}</code></td>
            </tr>
            <tr>
                <td class="has-text-weight-bold">Network:</td>
                <td>{{ status.network }}</td>
            </tr>
            <!-- More status rows... -->
        </tbody>
    </table>
</div>
{% endblock %}
```

---

### 2. WiFi Management (`/wifi`)

Network configuration page for connecting to WiFi networks.

**Required Elements:**
- Current connection status (network name, IP)
- Available networks list with scan button
- Saved/known networks list
- Add new network form
- Connect/disconnect/forget actions

**Template Structure:**

```html
{% extends "base.html" %}
{% block title %}WiFi Management{% endblock %}

{% block content %}
<h1 class="title">WiFi Management</h1>

<!-- Current Status -->
<div class="box">
    <h2 class="title is-5">Current Status</h2>
    <p><strong>Connected Network:</strong> <span id="current-network">{{ current_network or 'Not connected' }}</span></p>
    <p><strong>IP Address:</strong> <code id="current-ip">{{ ip_address or 'N/A' }}</code></p>
</div>

<div class="columns">
    <!-- Available Networks -->
    <div class="column">
        <div class="box">
            <h2 class="title is-5">
                Available Networks
                <button class="button is-small is-primary is-pulled-right" id="btn-scan">
                    <span class="icon"><i class="fas fa-sync-alt"></i></span>
                    <span>Scan</span>
                </button>
            </h2>
            <table class="table is-fullwidth" id="available-networks">
                <thead>
                    <tr>
                        <th>SSID</th>
                        <th>Signal</th>
                        <th>Security</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    <!-- Populated by JavaScript -->
                </tbody>
            </table>
        </div>
    </div>

    <!-- Add Network / Saved Networks -->
    <div class="column">
        <div class="box">
            <h2 class="title is-5">Add New Network</h2>
            <div class="field">
                <label class="label">Network Name (SSID)</label>
                <input class="input" type="text" id="new-ssid" placeholder="Enter network name">
            </div>
            <div class="field">
                <label class="label">Password</label>
                <input class="input" type="password" id="new-password" placeholder="Enter password">
            </div>
            <div class="field">
                <label class="checkbox">
                    <input type="checkbox" id="new-autoconnect" checked>
                    Auto-connect when available
                </label>
            </div>
            <button class="button is-primary" id="btn-add-network">Save & Connect</button>
        </div>

        <div class="box">
            <h2 class="title is-5">Saved Networks</h2>
            <table class="table is-fullwidth" id="saved-networks">
                <tbody>
                    <!-- Populated by JavaScript -->
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script src="{{ url_for('static', filename='wifi.js') }}"></script>
{% endblock %}
```

---

### 3. System Management (`/system`)

System updates, version info, and device management.

**Required Elements:**
- Current version information (version number, git commit, last updated)
- Check for updates button
- Apply updates button (shown when updates available)
- Reboot button
- Update instructions/help text

**Template Structure:**

```html
{% extends "base.html" %}
{% block title %}System Management{% endblock %}

{% block extra_head %}
<style>
    .version-badge {
        font-family: monospace;
        background-color: #363636;
        color: #fff;
        padding: 0.25em 0.5em;
        border-radius: 4px;
    }
    .commit-list {
        max-height: 300px;
        overflow-y: auto;
        font-family: monospace;
        font-size: 0.9em;
        background: #f5f5f5;
        padding: 1em;
        border-radius: 4px;
    }
    .spinner {
        display: inline-block;
        width: 1em;
        height: 1em;
        border: 2px solid #f3f3f3;
        border-top: 2px solid #3498db;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
</style>
{% endblock %}

{% block content %}
<h1 class="title">System Management</h1>

<!-- Current Version -->
<div class="box">
    <h2 class="title is-5">Current Version</h2>
    <table class="table is-fullwidth">
        <tbody>
            <tr>
                <td class="has-text-weight-bold" style="width: 150px;">Version:</td>
                <td><span class="version-badge">{{ version }}</span></td>
            </tr>
            <tr>
                <td class="has-text-weight-bold">Git Commit:</td>
                <td><span class="version-badge">{{ git_commit }}</span></td>
            </tr>
            <tr>
                <td class="has-text-weight-bold">Last Updated:</td>
                <td>{{ last_updated }}</td>
            </tr>
        </tbody>
    </table>
</div>

<!-- Update Check -->
<div class="box">
    <h2 class="title is-5">Software Updates</h2>
    <div id="update-status" class="mb-4">
        <p class="has-text-grey">Click below to check for available updates.</p>
    </div>
    <div class="buttons">
        <button id="btn-check-updates" class="button is-info">
            <span class="icon"><i class="fas fa-sync-alt"></i></span>
            <span>Check for Updates</span>
        </button>
        <button id="btn-apply-updates" class="button is-success" style="display: none;">
            <span class="icon"><i class="fas fa-download"></i></span>
            <span>Apply Updates</span>
        </button>
    </div>
</div>

<!-- Device Actions -->
<div class="box">
    <h2 class="title is-5">Device Actions</h2>
    <div class="buttons">
        <button id="btn-reboot" class="button is-danger">
            <span class="icon"><i class="fas fa-power-off"></i></span>
            <span>Reboot Device</span>
        </button>
    </div>
    <p class="help">Rebooting will temporarily disconnect you from this interface.</p>
</div>

<!-- How Updates Work -->
<div class="box has-background-info-light">
    <h2 class="title is-5">How Updates Work</h2>
    <div class="content">
        <ol>
            <li><strong>Check for Updates</strong> - Connects to GitHub to check for new code</li>
            <li><strong>Review Changes</strong> - See what will be updated</li>
            <li><strong>Apply Updates</strong> - Downloads and installs new code</li>
            <li><strong>Reboot</strong> - Restart the device to complete the update</li>
        </ol>
        <p class="has-text-weight-bold">
            <span class="icon has-text-success"><i class="fas fa-shield-alt"></i></span>
            Your settings and data are preserved during updates.
        </p>
    </div>
</div>

<!-- Reboot Confirmation Modal -->
<div id="reboot-modal" class="modal">
    <div class="modal-background"></div>
    <div class="modal-card">
        <header class="modal-card-head">
            <p class="modal-card-title">Confirm Reboot</p>
            <button class="delete" aria-label="close"></button>
        </header>
        <section class="modal-card-body">
            <p>Are you sure you want to reboot the device? You will be temporarily disconnected.</p>
        </section>
        <footer class="modal-card-foot">
            <button id="btn-confirm-reboot" class="button is-danger">Reboot Now</button>
            <button class="button btn-cancel">Cancel</button>
        </footer>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script src="{{ url_for('static', filename='system.js') }}"></script>
{% endblock %}
```

---

## Optional Pages

Implement these based on project requirements:

### Login Page (`/login`)

Required if authentication is enabled.

```html
{% extends "base.html" %}
{% block title %}Login{% endblock %}

{% block content %}
<div class="columns is-centered">
    <div class="column is-one-third">
        <div class="box">
            <h2 class="title is-4">Login</h2>
            <form method="POST" action="{{ url_for('login') }}">
                <div class="field">
                    <label class="label">Username</label>
                    <div class="control has-icons-left">
                        <input class="input" type="text" name="username" required>
                        <span class="icon is-small is-left">
                            <i class="fas fa-user"></i>
                        </span>
                    </div>
                </div>
                <div class="field">
                    <label class="label">Password</label>
                    <div class="control has-icons-left">
                        <input class="input" type="password" name="password" required>
                        <span class="icon is-small is-left">
                            <i class="fas fa-lock"></i>
                        </span>
                    </div>
                </div>
                <div class="field">
                    <button class="button is-primary is-fullwidth" type="submit">Login</button>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}
```

### Settings/Account Page (`/settings`)

For password changes and account management.

### User Manual (`/manual`)

Built-in documentation for the device.

---

## Common Components

### Status Card

```html
<div class="box">
    <h2 class="title is-5">
        <span class="icon"><i class="fas fa-info-circle"></i></span>
        Status
    </h2>
    <div class="columns is-multiline">
        <div class="column is-6">
            <p><strong>Label:</strong> {{ value }}</p>
        </div>
        <!-- More status items -->
    </div>
</div>
```

### Feature Card (Dashboard)

```html
<div class="column is-3">
    <div class="box has-text-centered has-background-light">
        <span class="icon is-large has-text-primary">
            <i class="fas fa-2x fa-wifi"></i>
        </span>
        <p class="title is-5 mt-3">Feature Name</p>
        <p class="subtitle is-6">Brief description</p>
        <a href="{{ url_for('feature') }}" class="button is-primary mt-3">Configure</a>
    </div>
</div>
```

### Form Box

```html
<div class="box">
    <h2 class="title is-5">Form Title</h2>
    <div class="field">
        <label class="label">Field Label</label>
        <div class="control">
            <input class="input" type="text" placeholder="Placeholder text">
        </div>
        <p class="help">Help text explaining the field</p>
    </div>
    <div class="field">
        <div class="control">
            <button class="button is-primary">Submit</button>
        </div>
    </div>
</div>
```

### Notification/Alert

```html
<!-- Success -->
<div class="notification is-success is-light">
    <button class="delete"></button>
    <strong>Success!</strong> Your changes have been saved.
</div>

<!-- Warning -->
<div class="notification is-warning is-light">
    <strong>Warning:</strong> Please review before proceeding.
</div>

<!-- Error -->
<div class="notification is-danger is-light">
    <strong>Error:</strong> Something went wrong.
</div>

<!-- Info -->
<div class="notification is-info is-light">
    <strong>Note:</strong> Additional information here.
</div>
```

### Confirmation Modal

```html
<div id="confirm-modal" class="modal">
    <div class="modal-background"></div>
    <div class="modal-card">
        <header class="modal-card-head">
            <p class="modal-card-title">Confirm Action</p>
            <button class="delete" aria-label="close"></button>
        </header>
        <section class="modal-card-body">
            <p>Are you sure you want to proceed?</p>
        </section>
        <footer class="modal-card-foot">
            <button class="button is-danger" id="btn-confirm">Confirm</button>
            <button class="button" id="btn-cancel">Cancel</button>
        </footer>
    </div>
</div>
```

### Loading Spinner

```html
<button class="button is-loading">Loading</button>

<!-- Or inline -->
<span class="spinner"></span> Loading...
```

---

## API Endpoints

### Required Endpoints

| Endpoint | Method | Description | Response |
|----------|--------|-------------|----------|
| `/api/status` | GET | Get device status | `{ ip, network, ... }` |
| `/api/wifi/status` | GET | Get WiFi status | `{ connected, ssid, ip }` |
| `/api/wifi/scan` | GET | Scan for networks | `{ networks: [...] }` |
| `/api/wifi/networks` | GET | Get saved networks | `{ networks: [...] }` |
| `/api/wifi/connect` | POST | Connect to network | `{ success, message }` |
| `/api/wifi/forget` | POST | Forget a network | `{ success, message }` |
| `/api/check_updates` | GET | Check for updates | `{ updates_available, commits, ... }` |
| `/api/apply_updates` | POST | Apply updates | `{ success, message }` |
| `/api/reboot` | POST | Reboot device | `{ success, message }` |

### Response Format

All API responses follow this format:

**Success:**
```json
{
    "success": true,
    "data": { ... },
    "message": "Optional success message"
}
```

**Error:**
```json
{
    "success": false,
    "error": "Error description"
}
```

### Flask API Implementation Example

```python
from flask import jsonify, request

@app.route('/api/wifi/scan')
def api_wifi_scan():
    try:
        networks = wifi_manager.scan_networks()
        return jsonify({
            'success': True,
            'networks': networks
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/reboot', methods=['POST'])
def api_reboot():
    try:
        # Schedule reboot after response is sent
        import threading
        def do_reboot():
            import time
            time.sleep(1)
            os.system('sudo reboot')
        
        threading.Thread(target=do_reboot).start()
        return jsonify({
            'success': True,
            'message': 'Device is rebooting...'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

---

## Styling Guidelines

### Custom CSS (`static/styles.css`)

```css
/* Custom styles extending Bulma */

/* Version badge */
.version-badge {
    font-family: monospace;
    background-color: #363636;
    color: #fff;
    padding: 0.25em 0.5em;
    border-radius: 4px;
}

/* Loading spinner */
.spinner {
    display: inline-block;
    width: 1em;
    height: 1em;
    border: 2px solid #f3f3f3;
    border-top: 2px solid #3498db;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-right: 0.5em;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* Status indicator */
.status-dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-right: 0.5em;
}

.status-dot.is-success { background-color: #48c774; }
.status-dot.is-warning { background-color: #ffdd57; }
.status-dot.is-danger { background-color: #f14668; }

/* Card hover effect */
.box.is-clickable:hover {
    box-shadow: 0 0.5em 1em -0.125em rgba(10, 10, 10, 0.2);
    cursor: pointer;
}

/* Monospace code display */
code {
    background-color: #f5f5f5;
    padding: 0.25em 0.5em;
    border-radius: 4px;
    font-size: 0.9em;
}

/* Table improvements */
.table td {
    vertical-align: middle;
}

/* Footer spacing */
.footer {
    padding: 1.5rem;
}
```

### Color Scheme

Use Bulma's built-in color classes:

| Purpose | Class | Usage |
|---------|-------|-------|
| Primary actions | `is-primary` | Main CTAs, brand elements |
| Success/Confirm | `is-success` | Successful operations |
| Warning | `is-warning` | Caution states |
| Danger/Delete | `is-danger` | Destructive actions |
| Info | `is-info` | Informational elements |
| Light/Secondary | `is-light` | Secondary actions |

---

## JavaScript Patterns

### API Call Helper

```javascript
// static/main.js

async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
        }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(endpoint, options);
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Request failed');
        }
        
        return result;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Usage
async function checkUpdates() {
    try {
        const result = await apiCall('/api/check_updates');
        if (result.updates_available) {
            showNotification('Updates available!', 'warning');
        }
    } catch (error) {
        showNotification(error.message, 'danger');
    }
}
```

### Notification Helper

```javascript
function showNotification(message, type = 'info', duration = 5000) {
    const container = document.querySelector('.section.py-3 .container');
    const notification = document.createElement('div');
    notification.className = `notification is-${type} is-light`;
    notification.innerHTML = `
        <button class="delete"></button>
        ${message}
    `;
    
    container.appendChild(notification);
    
    notification.querySelector('.delete').addEventListener('click', () => {
        notification.remove();
    });
    
    if (duration > 0) {
        setTimeout(() => notification.remove(), duration);
    }
}
```

### Button Loading State

```javascript
function setButtonLoading(button, loading) {
    if (loading) {
        button.classList.add('is-loading');
        button.disabled = true;
    } else {
        button.classList.remove('is-loading');
        button.disabled = false;
    }
}

// Usage
const btn = document.getElementById('btn-save');
setButtonLoading(btn, true);
await saveData();
setButtonLoading(btn, false);
```

### Modal Management

```javascript
function openModal(modalId) {
    document.getElementById(modalId).classList.add('is-active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('is-active');
}

// Close on background click
document.querySelectorAll('.modal-background, .modal .delete, .btn-cancel').forEach(el => {
    el.addEventListener('click', () => {
        el.closest('.modal').classList.remove('is-active');
    });
});
```

---

## Implementation Checklist

Use this checklist when implementing a new webUI:

### Setup
- [ ] Create `web_interface/` directory structure
- [ ] Install Flask: `pip install flask`
- [ ] Create `app.py` with Flask app
- [ ] Create `static/` folder with `styles.css`
- [ ] Create `templates/` folder

### Base Template
- [ ] Create `base.html` with standard structure
- [ ] Add Bulma CSS CDN link
- [ ] Add Font Awesome CDN link
- [ ] Implement navbar with hamburger menu
- [ ] Add flash message display
- [ ] Add footer with version
- [ ] Implement AP mode banner (if applicable)

### Required Pages
- [ ] Home/Dashboard (`/`) - status display, feature links
- [ ] WiFi Management (`/wifi`) - scan, connect, manage networks
- [ ] System Management (`/system`) - version, updates, reboot

### API Endpoints
- [ ] `/api/status` - device status
- [ ] `/api/wifi/status` - WiFi status
- [ ] `/api/wifi/scan` - scan networks
- [ ] `/api/wifi/connect` - connect to network
- [ ] `/api/wifi/forget` - forget network
- [ ] `/api/check_updates` - check for updates
- [ ] `/api/apply_updates` - apply updates
- [ ] `/api/reboot` - reboot device

### Backend
- [ ] Create `VERSION` file
- [ ] Implement `system_management.py` (git operations, reboot)
- [ ] Implement `wifi_management/` (network operations)
- [ ] Add context processor for global template variables

### Testing
- [ ] Test on desktop browser
- [ ] Test on mobile browser (responsive)
- [ ] Test WiFi operations
- [ ] Test update check/apply
- [ ] Test reboot functionality

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-19 | Initial specification |

---

## References

- [Bulma Documentation](https://bulma.io/documentation/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Font Awesome Icons](https://fontawesome.com/icons)
