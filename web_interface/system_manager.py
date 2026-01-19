"""
System Management Module for Poetry Camera

Handles system operations like version checking, git updates, and reboot.
"""

import subprocess
import os
import threading
import time
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent


class SystemManager:
    """Manages system operations for Poetry Camera."""
    
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
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
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
                timeout=10
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
        except Exception as e:
            logger.error(f"Error getting last updated: {e}")
            return "unknown"
    
    def check_for_updates(self):
        """Check if updates are available from git remote."""
        try:
            # Fetch from remote
            fetch_result = subprocess.run(
                ["git", "fetch", self.git_remote],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if fetch_result.returncode != 0:
                return {
                    "success": False,
                    "error": "Failed to check for updates. Check your internet connection."
                }
            
            # Compare local and remote
            result = subprocess.run(
                ["git", "rev-list", f"HEAD..{self.git_remote}/{self.git_branch}", "--count"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": "Failed to compare versions."
                }
            
            commits_behind = int(result.stdout.strip())
            updates_available = commits_behind > 0
            
            # Get commit messages if updates available
            commits = []
            if updates_available:
                log_result = subprocess.run(
                    ["git", "log", f"HEAD..{self.git_remote}/{self.git_branch}",
                     "--oneline", "--no-decorate"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if log_result.returncode == 0:
                    commits = log_result.stdout.strip().split('\n')
            
            return {
                "success": True,
                "updates_available": updates_available,
                "commits_behind": commits_behind,
                "commits": commits,
                "message": f"{commits_behind} update(s) available" if updates_available else "You're up to date!"
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Update check timed out. Check your internet connection."
            }
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def apply_updates(self):
        """Apply updates from git remote."""
        try:
            # Stash any local changes
            subprocess.run(
                ["git", "stash"],
                cwd=self.project_root,
                capture_output=True,
                timeout=30
            )
            
            # Pull updates
            result = subprocess.run(
                ["git", "pull", self.git_remote, self.git_branch],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                # Try to restore stashed changes
                subprocess.run(
                    ["git", "stash", "pop"],
                    cwd=self.project_root,
                    capture_output=True,
                    timeout=30
                )
                
                logger.info("Updates applied successfully")
                return {
                    "success": True,
                    "message": "Updates applied successfully. Please reboot to complete the update.",
                    "output": result.stdout
                }
            else:
                error_msg = result.stderr or "Failed to apply updates"
                logger.error(f"Failed to apply updates: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }
                
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Update timed out."
            }
        except Exception as e:
            logger.error(f"Error applying updates: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def reboot(self, delay=2):
        """Schedule a system reboot."""
        try:
            def do_reboot():
                time.sleep(delay)
                os.system("sudo reboot")
            
            thread = threading.Thread(target=do_reboot)
            thread.daemon = True
            thread.start()
            
            logger.info("Reboot scheduled")
            return {
                "success": True,
                "message": "Device is rebooting..."
            }
        except Exception as e:
            logger.error(f"Error scheduling reboot: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_system_info(self):
        """Get system information."""
        info = {
            "version": self.get_version(),
            "git_commit": self.get_git_commit(),
            "last_updated": self.get_last_updated(),
        }
        
        # Get hostname
        try:
            result = subprocess.run(["hostname"], capture_output=True, text=True, timeout=5)
            info["hostname"] = result.stdout.strip() if result.returncode == 0 else "unknown"
        except:
            info["hostname"] = "unknown"
        
        # Get uptime
        try:
            result = subprocess.run(["uptime", "-p"], capture_output=True, text=True, timeout=5)
            info["uptime"] = result.stdout.strip() if result.returncode == 0 else "unknown"
        except:
            info["uptime"] = "unknown"
        
        return info


# Singleton instance
system_manager = SystemManager()
