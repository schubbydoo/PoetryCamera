# web_server.py
from flask import Flask, request, jsonify, render_template_string
import wifi_manager

app = Flask(__name__)

@app.route("/")
def index():
    return render_template_string('''
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <title>Change Wi-Fi Settings</title>
      </head>
      <body>
        <div class="container">
          <h1 class="mt-5">Change Wi-Fi Settings</h1>
          <form method="post" action="/wifi">
            <div class="form-group">
              <label for="ssid">SSID</label>
              <input type="text" class="form-control" id="ssid" name="ssid" required>
            </div>
            <div class="form-group">
              <label for="password">Password</label>
              <input type="password" class="form-control" id="password" name="password" required>
            </div>
            <button type="submit" class="btn btn-primary">Submit</button>
          </form>
        </div>
      </body>
    </html>
    ''')

@app.route("/wifi", methods=['POST'])
def update_wifi():
    ssid = request.form.get("ssid")
    password = request.form.get("password")
    if ssid and password:
        result = wifi_manager.change_wifi(ssid, password)
        return jsonify({"result": result})
    else:
        return jsonify({"error": "SSID and password are required"}), 400

def start_flask_server():
    app.run(port=5002, use_reloader=False)
