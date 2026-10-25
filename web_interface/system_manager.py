"""
System Management Module for Poetry Camera

Reports the camera's version and basic system info (updates and reboot live in propkit's System tab).
"""

import subprocess
import os
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent


class SystemManager:
    """Manages system operations for Poetry Camera."""
    
    # Shorter timeouts for Pi Zero 2W performance
    CMD_TIMEOUT_SHORT = 3
    CMD_TIMEOUT_MEDIUM = 5
    CMD_TIMEOUT_LONG = 30
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.version_file = self.project_root / "VERSION"
        self.git_remote = "origin"
        self.git_branch = "main"
    
    def get_version(self):
        """Get the current version from VERSION file."""
        try:
            if self.version_file.exists():
                return self.version_file.read_text().strip()
            return "unknown"
        except Exception as e:
            logger.error(f"Error reading version: {e}")
            return "unknown"
    
    def get_git_commit(self):
        """Get the current git commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=self.CMD_TIMEOUT_SHORT
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return "unknown"
        except subprocess.TimeoutExpired:
            return "unknown"
        except Exception as e:
            logger.error(f"Error getting git commit: {e}")
            return "unknown"
    
    def get_last_updated(self):
        """Get the date of the last git commit."""
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%ci"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=self.CMD_TIMEOUT_SHORT
            )
            if result.returncode == 0:
                # Parse and format the date
                date_str = result.stdout.strip()
                try:
                    dt = datetime.strptime(date_str[:19], "%Y-%m-%d %H:%M:%S")
                    return dt.strftime("%B %d, %Y at %H:%M")
                except:
                    return date_str
            return "unknown"
        except subprocess.TimeoutExpired:
            return "unknown"
        except Exception as e:
            logger.error(f"Error getting last updated: {e}")
            return "unknown"
    
    def get_system_info(self):
        """Get system information."""
        info = {
            "version": self.get_version(),
            "git_commit": self.get_git_commit(),
            "last_updated": self.get_last_updated(),
        }
        
        # Get hostname
        try:
            result = subprocess.run(["hostname"], capture_output=True, text=True, timeout=self.CMD_TIMEOUT_SHORT)
            info["hostname"] = result.stdout.strip() if result.returncode == 0 else "unknown"
        except:
            info["hostname"] = "unknown"
        
        # Get uptime
        try:
            result = subprocess.run(["uptime", "-p"], capture_output=True, text=True, timeout=self.CMD_TIMEOUT_SHORT)
            info["uptime"] = result.stdout.strip() if result.returncode == 0 else "unknown"
        except:
            info["uptime"] = "unknown"
        
        return info


# Singleton instance
system_manager = SystemManager()
