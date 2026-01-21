"""
Configuration Management Module for Poetry Camera

Handles persistent storage of settings including:
- OpenAI model and prompts
- Printer configuration
- User credentials
"""

import json
import os
import hashlib
import secrets
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_FILE = PROJECT_ROOT / "poetry_camera_config.json"

# Default configuration values
DEFAULT_CONFIG = {
    "openai": {
        "model": "gpt-4o-mini",
        "poem_prompt": """Write a poem using the details, atmosphere, and emotion of this scene.
Create a unique and elegant poem using specific details from the visual.
IMPORTANT: Write a POEM, not a description.
Keep it short (max 8 lines).
Do not mention the date or time. Focus on the visual mood.
Don't use the words 'unspoken' or 'unseen' or 'unheard' or 'untold'.
Do not be corny or cliche'd.
If there are people where gender is uncertain, use gender-neutral pronouns.""",
        "poem_format": "couplet"
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


class ConfigManager:
    """Manages Poetry Camera configuration."""
    
    def __init__(self):
        self.config_file = CONFIG_FILE
        self.config = self._load_config()
        self._ensure_defaults()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
        return {}
    
    def _save_config(self):
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
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
    
    # ==================== OpenAI Methods ====================
    
    def get_openai_config(self) -> Dict[str, Any]:
        """Get OpenAI configuration."""
        return self.config.get("openai", DEFAULT_CONFIG["openai"]).copy()
    
    def get_openai_model(self) -> str:
        """Get the current OpenAI model."""
        return self.config["openai"]["model"]
    
    def set_openai_model(self, model: str):
        """Set the OpenAI model."""
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
        """Update multiple OpenAI settings at once."""
        try:
            if "model" in config:
                self.config["openai"]["model"] = config["model"]
            if "poem_prompt" in config:
                self.config["openai"]["poem_prompt"] = config["poem_prompt"]
            if "poem_format" in config:
                self.config["openai"]["poem_format"] = config["poem_format"]

            self._save_config()
            return {"success": True, "message": "OpenAI settings updated"}
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
