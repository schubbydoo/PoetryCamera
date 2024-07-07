#!/bin/bash

# Stop any existing Wi-Fi connection
sudo systemctl stop dhcpcd
sudo systemctl stop wpa_supplicant

# Start the access point services
sudo systemctl start hostapd
sudo systemctl start dnsmasq

echo "Access point mode activated"
