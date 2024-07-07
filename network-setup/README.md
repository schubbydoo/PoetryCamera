# Network Setup

This component allows the Raspberry Pi to create a temporary hotspot for configuring local WiFi networks.

## Features
- Temporary hotspot creation.
- Web interface for entering WiFi credentials.
- 5-second button press to initate temporary hotspot for local WiFi network configuration.
- Printer integration for status messages.

## Setup
Instructions for setting up and using this component.

## Usage
Detailed usage instructions.

## Scripts

### bt_agent.py

A script to manage Bluetooth connections for network setup or printer integration.

Usage:
```sh
./bt_agent.py

### check_wifi.py

A script to check the WiFi connection status.

```sh
./check_wifi.py

### reset_ap_mode.sh

A script to reset the Raspberry Pi to Access Point mode

```sh
./reset_ap_mode.sh

### A script to manage WiFi connections and configurations

```sh
./wifi_manager.py

### A web server script for managing network configurations through a web interface.

```sh
./web_server.py
