#!/bin/bash

# Arguments
connection_name=$1
config=$2

# Path to save the configuration
config_path="/etc/NetworkManager/system-connections/${connection_name}.nmconnection"

# Write configuration to file
echo "$config" | sudo tee $config_path > /dev/null

# Set the correct permissions
sudo chmod 600 $config_path

# Reload and activate the connection
sudo nmcli connection reload
sudo nmcli connection up $connection_name

