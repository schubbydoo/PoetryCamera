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
            # iwgetid (wireless-tools) is not installed on the Pi; ask NetworkManager (no rescan) instead
            result = subprocess.run(
                ["nmcli", "-t", "-f", "ACTIVE,SSID", "device", "wifi", "list", "--rescan", "no"],
                capture_output=True,
                text=True,
                timeout=self.CMD_TIMEOUT_SHORT
            )
            ssid = None
            for line in result.stdout.splitlines():
                if line.startswith("yes:"):
                    ssid = line[4:].replace("\\:", ":") or None
                    break
            
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
            # NAME goes last so names containing ':' or spaces split cleanly
            result = subprocess.run(
                ["nmcli", "-t", "-f", "TYPE,AUTOCONNECT,NAME", "connection", "show"],
                capture_output=True,
                text=True,
                timeout=self.CMD_TIMEOUT_MEDIUM
            )
            
            for line in result.stdout.strip().split('\n'):
                parts = line.split(':', 2)
                if len(parts) == 3 and parts[0] == "802-11-wireless":
                    name = parts[2].replace('\\:', ':')
                    # Skip the AP mode connection
                    if name != self.ap_connection_name:
                        networks.append({
                            "name": name,
                            "autoconnect": parts[1] == "yes"
                        })
                            
        except Exception as e:
            logger.error(f"Error getting saved networks: {e}")
        
        return networks
    
    def _find_profile(self, ssid):
        """Return the saved profile name for an SSID (handles older underscore-style names)."""
        saved = {n["name"] for n in self.get_saved_networks()}
        for candidate in (ssid, ssid.replace(' ', '_')):
            if candidate in saved:
                return candidate
        return None
    
    def get_network_details(self, name):
        """Return details of a saved network (the password itself is never returned)."""
        profile = self._find_profile(name)
        if not profile:
            return None
        fields = ["connection.id", "connection.autoconnect", "connection.autoconnect-priority",
                  "connection.interface-name", "802-11-wireless.ssid", "802-11-wireless.hidden",
                  "802-11-wireless-security.key-mgmt", "ipv4.method"]
        out = subprocess.run(
            ["sudo", "nmcli", "-g", ",".join(fields), "connection", "show", "id", profile],
            capture_output=True, text=True, timeout=self.CMD_TIMEOUT_MEDIUM
        )
        # -g with several fields prints one value per line, empty values included
        values = out.stdout.split('\n')
        values += [''] * len(fields)
        d = dict(zip(fields, values))
        
        psk = subprocess.run(
            ["sudo", "nmcli", "-s", "-g", "802-11-wireless-security.psk", "connection", "show", "id", profile],
            capture_output=True, text=True, timeout=self.CMD_TIMEOUT_MEDIUM
        ).stdout.strip()
        key_mgmt = d["802-11-wireless-security.key-mgmt"]
        ssid = d["802-11-wireless.ssid"] or profile
        
        active = subprocess.run(
            ["nmcli", "-t", "-f", "NAME", "connection", "show", "--active"],
            capture_output=True, text=True, timeout=self.CMD_TIMEOUT_SHORT
        ).stdout.replace('\\:', ':').split('\n')
        
        signal = None
        scan = subprocess.run(
            ["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL", "device", "wifi", "list"],
            capture_output=True, text=True, encoding='utf-8', errors='ignore',
            timeout=self.CMD_TIMEOUT_MEDIUM
        ).stdout
        connected_ssid = False
        for line in scan.split('\n'):
            if ':' in line:
                head, _, sig = line.rpartition(':')
                is_active, _, scan_ssid = head.partition(':')
                if scan_ssid.replace('\\:', ':') == ssid and sig.isdigit():
                    signal = max(signal or 0, int(sig))
                    connected_ssid = connected_ssid or is_active == "yes"
        
        if profile in active or connected_ssid:
            status = "Connected"
        elif signal is not None:
            status = f"In range (signal {signal}%)"
        else:
            status = "Not in range"
        
        return {
            "Name": d["connection.id"],
            "SSID": ssid,
            "Status": status,
            "Security": "WPA-PSK" if key_mgmt == "wpa-psk" else (key_mgmt.upper() if key_mgmt else "Open"),
            "Password": "Stored" if psk else ("None (open network)" if not key_mgmt else "Not stored"),
            "Auto-connect": "Yes" if d["connection.autoconnect"] == "yes" else "No",
            "Priority": d["connection.autoconnect-priority"] or "0",
            "Interface": d["connection.interface-name"] or "any",
            "Hidden network": "Yes" if d["802-11-wireless.hidden"] == "yes" else "No",
            "IP": "Automatic (DHCP)" if d["ipv4.method"] == "auto" else d["ipv4.method"],
        }
    
    def connect_network(self, ssid, password, autoconnect=True, connect_now=True):
        """Save a WiFi network profile and optionally connect to it.
        
        The profile is created directly (not via 'device wifi connect'), so networks
        that are out of range, or whose names contain spaces, can be preprogrammed.
        An empty password saves an open network.
        """
        try:
            ssid = ssid.strip()
            profile = self._find_profile(ssid)
            auto = "yes" if autoconnect else "no"
            
            if profile:
                modify = ["sudo", "nmcli", "connection", "modify", "id", profile,
                          "connection.autoconnect", auto]
                if password:
                    modify += ["wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password]
                subprocess.run(modify, check=True, capture_output=True, text=True,
                               timeout=self.CMD_TIMEOUT_MEDIUM)
            else:
                profile = ssid
                add = ["sudo", "nmcli", "connection", "add", "type", "wifi",
                       "ifname", self.interface, "con-name", profile, "ssid", ssid,
                       "connection.autoconnect", auto]
                if password:
                    add += ["wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password]
                result = subprocess.run(add, capture_output=True, text=True,
                                        timeout=self.CMD_TIMEOUT_MEDIUM)
                if result.returncode != 0:
                    error_msg = (result.stderr or result.stdout or "Failed to save network").strip()
                    logger.error(f"Failed to save {ssid}: {error_msg}")
                    return {"success": False, "error": error_msg}
            
            logger.info(f"Saved network profile: {ssid}")
            if not connect_now:
                return {"success": True, "saved": True, "connected": False,
                        "message": f"Saved {ssid}. It will connect automatically when in range."}
            
            result = subprocess.run(
                ["sudo", "nmcli", "connection", "up", "id", profile],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                logger.info(f"Successfully connected to {ssid}")
                return {"success": True, "saved": True, "connected": True,
                        "message": f"Connected to {ssid}"}
            
            error_msg = (result.stderr or "Connection failed").strip()
            logger.warning(f"Saved {ssid} but could not connect now: {error_msg}")
            return {"success": True, "saved": True, "connected": False,
                    "message": f"Saved {ssid}, but could not connect right now "
                               f"(it may be out of range). It will connect automatically when in range."}
                
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": (e.stderr or str(e)).strip()}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Connection timed out"}
        except Exception as e:
            logger.error(f"Error connecting to network: {e}")
            return {"success": False, "error": str(e)}
    
    def forget_network(self, ssid):
        """Remove a saved WiFi network (ssid is the saved profile name)."""
        try:
            connection_name = self._find_profile(ssid) or ssid
            
            result = subprocess.run(
                ["sudo", "nmcli", "connection", "delete", "id", connection_name],
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
