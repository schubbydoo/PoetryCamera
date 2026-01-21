"""
WiFi Management Module for Poetry Camera

Handles WiFi scanning, connection management, and network configuration
using NetworkManager (nmcli).
"""

import subprocess
import uuid
import os
import re
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WiFiManager:
    """Manages WiFi operations using NetworkManager."""
    
    # Shorter timeouts for Pi Zero 2W performance
    CMD_TIMEOUT_SHORT = 3  # Quick commands
    CMD_TIMEOUT_MEDIUM = 5  # Normal commands
    CMD_TIMEOUT_LONG = 15  # Network operations
    
    # Cache for AP mode to avoid repeated slow checks
    _ap_mode_cache = None
    _ap_mode_cache_time = 0
    AP_MODE_CACHE_TTL = 30  # Cache for 30 seconds
    
    def __init__(self):
        self.interface = "wlan0"
        self.ap_connection_name = "PoetCam"
    
    def get_current_connection(self):
        """Get current WiFi connection details."""
        try:
            # Get current SSID
            result = subprocess.run(
                ["iwgetid", "-r"],
                capture_output=True,
                text=True,
                timeout=self.CMD_TIMEOUT_SHORT
            )
            ssid = result.stdout.strip() if result.returncode == 0 else None
            
            # Get IP address
            ip_result = subprocess.run(
                ["hostname", "-I"],
                capture_output=True,
                text=True,
                timeout=self.CMD_TIMEOUT_SHORT
            )
            ip_addresses = ip_result.stdout.strip().split()
            ip_address = ip_addresses[0] if ip_addresses else None
            
            return {
                "connected": ssid is not None and ssid != "",
                "ssid": ssid,
                "ip_address": ip_address
            }
        except subprocess.TimeoutExpired:
            logger.warning("Connection check timed out")
            return {
                "connected": False,
                "ssid": None,
                "ip_address": None
            }
        except Exception as e:
            logger.error(f"Error getting current connection: {e}")
            return {
                "connected": False,
                "ssid": None,
                "ip_address": None
            }
    
    def is_ap_mode(self):
        """Check if device is currently in AP mode (with caching)."""
        # Use cached value if recent enough
        current_time = time.time()
        if (WiFiManager._ap_mode_cache is not None and 
            current_time - WiFiManager._ap_mode_cache_time < WiFiManager.AP_MODE_CACHE_TTL):
            return WiFiManager._ap_mode_cache
        
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "NAME", "connection", "show", "--active"],
                capture_output=True,
                text=True,
                timeout=self.CMD_TIMEOUT_SHORT
            )
            # Check if PoetCam AP connection is active
            is_ap = self.ap_connection_name in result.stdout
            
            # Update cache
            WiFiManager._ap_mode_cache = is_ap
            WiFiManager._ap_mode_cache_time = current_time
            
            return is_ap
        except subprocess.TimeoutExpired:
            # On timeout, assume not in AP mode to keep UI responsive
            logger.warning("AP mode check timed out, assuming not in AP mode")
            WiFiManager._ap_mode_cache = False
            WiFiManager._ap_mode_cache_time = current_time
            return False
        except Exception as e:
            logger.error(f"Error checking AP mode: {e}")
            return False
    
    def scan_networks(self):
        """Scan for available WiFi networks."""
        networks = []
        try:
            # Rescan WiFi (don't wait for it)
            subprocess.run(
                ["sudo", "nmcli", "device", "wifi", "rescan"],
                capture_output=True,
                timeout=self.CMD_TIMEOUT_MEDIUM
            )
            
            # Get list of networks
            result = subprocess.run(
                ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=self.CMD_TIMEOUT_LONG
            )
            
            seen_ssids = set()
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split(':')
                    if len(parts) >= 3:
                        ssid = parts[0].strip()
                        if ssid and ssid not in seen_ssids and ssid != self.ap_connection_name:
                            seen_ssids.add(ssid)
                            networks.append({
                                "ssid": ssid,
                                "signal": int(parts[1]) if parts[1].isdigit() else 0,
                                "security": parts[2] if parts[2] else "Open"
                            })
            
            # Sort by signal strength
            networks.sort(key=lambda x: x["signal"], reverse=True)
            
        except subprocess.TimeoutExpired:
            logger.error("WiFi scan timed out")
        except Exception as e:
            logger.error(f"Error scanning networks: {e}")
        
        return networks
    
    def get_saved_networks(self):
        """Get list of saved WiFi networks."""
        networks = []
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "NAME,TYPE,AUTOCONNECT", "connection", "show"],
                capture_output=True,
                text=True,
                timeout=self.CMD_TIMEOUT_MEDIUM
            )
            
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split(':')
                    if len(parts) >= 3 and parts[1] == "802-11-wireless":
                        name = parts[0]
                        # Skip the AP mode connection
                        if name != self.ap_connection_name:
                            networks.append({
                                "name": name,
                                "autoconnect": parts[2] == "yes"
                            })
                            
        except Exception as e:
            logger.error(f"Error getting saved networks: {e}")
        
        return networks
    
    def connect_network(self, ssid, password, autoconnect=True):
        """Connect to a WiFi network."""
        try:
            connection_name = ssid.replace(' ', '_')
            
            # Check if connection already exists
            existing = subprocess.run(
                ["nmcli", "connection", "show", connection_name],
                capture_output=True,
                timeout=self.CMD_TIMEOUT_SHORT
            )
            
            if existing.returncode == 0:
                # Connection exists, update password and connect
                subprocess.run(
                    ["sudo", "nmcli", "connection", "modify", connection_name,
                     "wifi-sec.psk", password],
                    check=True,
                    timeout=self.CMD_TIMEOUT_MEDIUM
                )
                result = subprocess.run(
                    ["sudo", "nmcli", "connection", "up", connection_name],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            else:
                # Create new connection
                result = subprocess.run(
                    ["sudo", "nmcli", "device", "wifi", "connect", ssid,
                     "password", password, "name", connection_name],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            
            if result.returncode == 0:
                # Set autoconnect
                subprocess.run(
                    ["sudo", "nmcli", "connection", "modify", connection_name,
                     "connection.autoconnect", "yes" if autoconnect else "no"],
                    timeout=self.CMD_TIMEOUT_SHORT
                )
                logger.info(f"Successfully connected to {ssid}")
                return {"success": True, "message": f"Connected to {ssid}"}
            else:
                error_msg = result.stderr or "Connection failed"
                logger.error(f"Failed to connect to {ssid}: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Connection timed out"}
        except Exception as e:
            logger.error(f"Error connecting to network: {e}")
            return {"success": False, "error": str(e)}
    
    def forget_network(self, ssid):
        """Remove a saved WiFi network."""
        try:
            connection_name = ssid.replace(' ', '_')
            
            result = subprocess.run(
                ["sudo", "nmcli", "connection", "delete", connection_name],
                capture_output=True,
                text=True,
                timeout=self.CMD_TIMEOUT_MEDIUM
            )
            
            if result.returncode == 0:
                logger.info(f"Forgot network: {ssid}")
                return {"success": True, "message": f"Removed {ssid}"}
            else:
                error_msg = result.stderr or "Failed to remove network"
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"Error forgetting network: {e}")
            return {"success": False, "error": str(e)}
    
    def activate_ap_mode(self):
        """Activate the PoetCam access point."""
        try:
            # Clear cache when changing AP mode
            WiFiManager._ap_mode_cache = None
            
            result = subprocess.run(
                ["sudo", "nmcli", "connection", "up", self.ap_connection_name],
                capture_output=True,
                text=True,
                timeout=self.CMD_TIMEOUT_LONG
            )
            
            if result.returncode == 0:
                return {"success": True, "message": "AP mode activated"}
            else:
                return {"success": False, "error": result.stderr or "Failed to activate AP"}
                
        except Exception as e:
            logger.error(f"Error activating AP mode: {e}")
            return {"success": False, "error": str(e)}
    
    def deactivate_ap_mode(self):
        """Deactivate the PoetCam access point."""
        try:
            # Clear cache when changing AP mode
            WiFiManager._ap_mode_cache = None
            
            result = subprocess.run(
                ["sudo", "nmcli", "connection", "down", self.ap_connection_name],
                capture_output=True,
                text=True,
                timeout=self.CMD_TIMEOUT_LONG
            )
            
            if result.returncode == 0:
                return {"success": True, "message": "AP mode deactivated"}
            else:
                return {"success": False, "error": result.stderr or "Failed to deactivate AP"}
                
        except Exception as e:
            logger.error(f"Error deactivating AP mode: {e}")
            return {"success": False, "error": str(e)}


# Singleton instance
wifi_manager = WiFiManager()
