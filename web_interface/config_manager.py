"""
Configuration Management Module for Poetry Camera

Handles persistent storage of settings including:
- AI provider and model settings (OpenAI, Anthropic)
- Printer configuration
- User credentials
"""

import copy
import fcntl
import json
import os
import hashlib
import secrets
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))
from atomic_io import write_json  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_FILE = PROJECT_ROOT / "poetry_camera_config.json"

# Default configuration values
DEFAULT_CONFIG = {
    "demo_context": "",
    "openai": {
        "provider": "anthropic",  # Options: "openai", "anthropic"
        "model": "claude-sonnet-4-6",
        "poem_prompt": "You are a poet with a camera's eye. You will receive an image and a poetry format.\nStudy the image closely. Notice the people first \u2014 their expressions, posture, what they might be feeling or doing together. Then take in the setting, the light, the colors, the objects, the mood of the moment.\nWrite a single poem in the specified format that brings this scene to life. Weave in specific details you actually see \u2014 don't be generic. If there are people, make them the heart of the poem. Give them warmth, humor, or tenderness depending on what the moment calls for.\nBe playful when the scene is playful. Be quiet when the scene is quiet. Match the energy of what you see. Aim for something the people in the photo would want to keep.\nDo not describe the image before the poem. Do not explain the poem after. Just the poem.\nFormat: {format_variable}",
        "poem_format": "rhyming couplets"
    },
    "printer": {
        "type": "cat_printer",  # Options: "cat_printer", "network_printer", "both"
        "cat_printer": {
            "enabled": True,
            "name": "MX06",
            "mac_address": "A7:09:08:1B:58:69"
        },
        "network_printer": {
            "enabled": False,
            "address": "192.168.0.100",
            "port": 9100
        }
    },
    "auth": {
        "username": "poeteer",
        "password_hash": None,  # Will be set on first run
        "secret_key": None  # Will be generated on first run
    }
}


_MISSING = object()


def _apply_changes(base: dict, old: dict, new: dict):
    """Apply to `base` only what differs between `old` (as last loaded/saved) and `new` (this process's edits)."""
    for k in set(old) | set(new):
        o, n = old.get(k, _MISSING), new.get(k, _MISSING)
        if o == n:
            continue
        if n is _MISSING:
            base.pop(k, None)
        elif isinstance(o, dict) and isinstance(n, dict) and isinstance(base.get(k), dict):
            _apply_changes(base[k], o, n)
        else:
            base[k] = copy.deepcopy(n)


class ConfigManager:
    """Manages Poetry Camera configuration."""
    
    def __init__(self):
        self.config_file = CONFIG_FILE
        self.config = self._load_config(retries=3)
        if self.config is None:
            logger.error("Config unreadable at start-up; using defaults WITHOUT saving them over the file")
            self.config = {}
            self._read_failed = True
        else:
            self._read_failed = False
        self._disk = copy.deepcopy(self.config) if not self._read_failed else None
        self._ensure_defaults()
    
    def _load_config(self, retries: int = 0) -> Optional[Dict[str, Any]]:
        """Load configuration from file. {} if the file does not exist; None if it is empty or unparseable."""
        import time
        for attempt in range(retries + 1):
            try:
                if not self.config_file.exists():
                    return {}
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
                raise ValueError("config is not a JSON object")
            except Exception as e:
                logger.error(f"Error loading config: {e}")
                if attempt < retries:
                    time.sleep(0.2)
        return None

    def reload(self):
        """Reload configuration from disk. Call this to pick up changes made by other processes.
        If the file cannot be read right now, keep the config already in memory."""
        data = self._load_config(retries=2)
        if data is None:
            logger.error("Config unreadable; keeping the previous settings")
            return
        self.config = data
        self._read_failed = False
        self._disk = copy.deepcopy(data)
        self._ensure_defaults()
    
    def _save_config(self):
        """Save configuration to file."""
        try:
            if getattr(self, "_read_failed", False):
                logger.error("Not saving: the config file could not be read, so it is not overwritten")
                return
            # Read-modify-write under a lock: apply only this process's own edits on top of the file as it is now,
            # so a save from a stale copy cannot undo a change another process made meanwhile.
            lock_path = str(self.config_file) + ".lock"
            with open(lock_path, 'a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                disk = self._load_config(retries=2)
                if disk is None:
                    logger.error("Not saving: the config file could not be read, so it is not overwritten")
                    return
                base = getattr(self, "_disk", None)
                if base is None or not disk:
                    merged = copy.deepcopy(self.config)
                else:
                    merged = copy.deepcopy(disk)
                    _apply_changes(merged, base, self.config)
                write_json(self.config_file, merged, indent=2)
                self.config = merged
                self._disk = copy.deepcopy(merged)
            logger.info("Configuration saved")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def _ensure_defaults(self):
        """Ensure all default values exist in config."""
        changed = False
        
        def merge_defaults(current: dict, defaults: dict) -> bool:
            nonlocal changed
            for key, value in defaults.items():
                if key not in current:
                    current[key] = value
                    changed = True
                elif isinstance(value, dict) and isinstance(current.get(key), dict):
                    merge_defaults(current[key], value)
            return changed
        
        merge_defaults(self.config, DEFAULT_CONFIG)
        
        # Generate secret key if not exists
        if not self.config["auth"].get("secret_key"):
            self.config["auth"]["secret_key"] = secrets.token_hex(32)
            changed = True
        
        # Set default password hash if not exists
        if not self.config["auth"].get("password_hash"):
            self.config["auth"]["password_hash"] = self._hash_password("poeteer")
            changed = True
        
        if changed:
            self._save_config()
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    # ==================== Auth Methods ====================
    
    def get_secret_key(self) -> str:
        """Get the Flask secret key."""
        return self.config["auth"]["secret_key"]
    
    def verify_credentials(self, username: str, password: str) -> bool:
        """Verify login credentials."""
        stored_username = self.config["auth"]["username"]
        stored_hash = self.config["auth"]["password_hash"]
        return username == stored_username and self._hash_password(password) == stored_hash
    
    def change_password(self, current_password: str, new_password: str) -> Dict[str, Any]:
        """Change the user password."""
        if not self.verify_credentials(self.config["auth"]["username"], current_password):
            return {"success": False, "error": "Current password is incorrect"}
        
        self.config["auth"]["password_hash"] = self._hash_password(new_password)
        self._save_config()
        return {"success": True, "message": "Password changed successfully"}
    
    def get_username(self) -> str:
        """Get the current username."""
        return self.config["auth"]["username"]
    
    # ==================== Demo Context Methods ====================

    def get_demo_context(self) -> str:
        """Get the current demo context."""
        return self.config.get("demo_context", "")

    def set_demo_context(self, context: str):
        """Set the demo context."""
        self.config["demo_context"] = context
        self._save_config()

    def clear_demo_context(self):
        """Clear the demo context."""
        self.config["demo_context"] = ""
        self._save_config()

    # ==================== AI Methods ====================

    def get_openai_config(self) -> Dict[str, Any]:
        """Get AI configuration (stored under 'openai' key for backward compat)."""
        return self.config.get("openai", DEFAULT_CONFIG["openai"]).copy()

    def get_ai_provider(self) -> str:
        """Get the current AI provider ('openai' or 'anthropic')."""
        return self.config["openai"].get("provider", "openai")

    def set_ai_provider(self, provider: str):
        """Set the AI provider."""
        valid_providers = ["openai", "anthropic"]
        if provider in valid_providers:
            self.config["openai"]["provider"] = provider
            self._save_config()

    def get_openai_model(self) -> str:
        """Get the current model name."""
        return self.config["openai"]["model"]

    def set_openai_model(self, model: str):
        """Set the model name."""
        self.config["openai"]["model"] = model
        self._save_config()

    def get_poem_prompt(self) -> str:
        """Get the poem prompt."""
        return self.config["openai"]["poem_prompt"]
    
    def set_poem_prompt(self, prompt: str):
        """Set the poem prompt."""
        self.config["openai"]["poem_prompt"] = prompt
        self._save_config()
    
    def get_poem_format(self) -> str:
        """Get the poem format."""
        return self.config["openai"]["poem_format"]
    
    def set_poem_format(self, format: str):
        """Set the poem format."""
        self.config["openai"]["poem_format"] = format
        self._save_config()
    
    def update_openai_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update multiple AI settings at once."""
        try:
            if "provider" in config:
                valid_providers = ["openai", "anthropic"]
                if config["provider"] not in valid_providers:
                    return {"success": False, "error": f"Invalid provider: {config['provider']}"}
                self.config["openai"]["provider"] = config["provider"]
            if "model" in config:
                self.config["openai"]["model"] = config["model"]
            if "poem_prompt" in config:
                self.config["openai"]["poem_prompt"] = config["poem_prompt"]
            if "poem_format" in config:
                self.config["openai"]["poem_format"] = config["poem_format"]

            self._save_config()
            return {"success": True, "message": "AI settings updated"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ==================== Printer Methods ====================
    
    def get_printer_config(self) -> Dict[str, Any]:
        """Get printer configuration."""
        return self.config.get("printer", DEFAULT_CONFIG["printer"]).copy()
    
    def get_printer_type(self) -> str:
        """Get the current printer type."""
        return self.config["printer"]["type"]
    
    def set_printer_type(self, printer_type: str):
        """Set the printer type."""
        valid_types = ["cat_printer", "network_printer", "both"]
        if printer_type in valid_types:
            self.config["printer"]["type"] = printer_type
            self._save_config()
    
    def get_cat_printer_config(self) -> Dict[str, Any]:
        """Get Cat Printer configuration."""
        return self.config["printer"]["cat_printer"].copy()
    
    def update_cat_printer_config(self, config: Dict[str, Any]):
        """Update Cat Printer configuration."""
        if "enabled" in config:
            self.config["printer"]["cat_printer"]["enabled"] = config["enabled"]
        if "name" in config:
            self.config["printer"]["cat_printer"]["name"] = config["name"]
        if "mac_address" in config:
            self.config["printer"]["cat_printer"]["mac_address"] = config["mac_address"]
        self._save_config()
    
    def get_network_printer_config(self) -> Dict[str, Any]:
        """Get Network Printer configuration."""
        return self.config["printer"]["network_printer"].copy()
    
    def update_network_printer_config(self, config: Dict[str, Any]):
        """Update Network Printer configuration."""
        if "enabled" in config:
            self.config["printer"]["network_printer"]["enabled"] = config["enabled"]
        if "address" in config:
            self.config["printer"]["network_printer"]["address"] = config["address"]
        if "port" in config:
            self.config["printer"]["network_printer"]["port"] = config["port"]
        self._save_config()
    
    def update_printer_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update printer configuration."""
        try:
            if "type" in config:
                self.set_printer_type(config["type"])
            if "cat_printer" in config:
                self.update_cat_printer_config(config["cat_printer"])
            if "network_printer" in config:
                self.update_network_printer_config(config["network_printer"])
            return {"success": True, "message": "Printer settings updated"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ==================== General Methods ====================
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration (excluding sensitive data)."""
        config = self.config.copy()
        # Remove sensitive auth data
        if "auth" in config:
            config["auth"] = {
                "username": config["auth"]["username"]
            }
        return config
    
    def reset_to_defaults(self, section: Optional[str] = None) -> Dict[str, Any]:
        """Reset configuration to defaults."""
        try:
            if section:
                if section in DEFAULT_CONFIG:
                    # Keep auth secret key and password
                    if section == "auth":
                        secret_key = self.config["auth"]["secret_key"]
                        password_hash = self.config["auth"]["password_hash"]
                        self.config[section] = DEFAULT_CONFIG[section].copy()
                        self.config["auth"]["secret_key"] = secret_key
                        self.config["auth"]["password_hash"] = password_hash
                    else:
                        self.config[section] = DEFAULT_CONFIG[section].copy()
                else:
                    return {"success": False, "error": f"Unknown section: {section}"}
            else:
                # Reset all except auth credentials
                secret_key = self.config["auth"]["secret_key"]
                password_hash = self.config["auth"]["password_hash"]
                self.config = DEFAULT_CONFIG.copy()
                self.config["auth"]["secret_key"] = secret_key
                self.config["auth"]["password_hash"] = password_hash
            
            self._save_config()
            return {"success": True, "message": f"Reset {section or 'all'} to defaults"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton instance
config_manager = ConfigManager()
