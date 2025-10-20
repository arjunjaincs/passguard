"""USB/Removable Drive Watcher for Auto-Lock.

Monitors vault files on removable drives and triggers auto-lock when drive is removed.

Platform Support:
- Windows: Full removable drive detection via GetDriveTypeW
- Linux/macOS: Path existence polling (no drive type detection)

Security:
- Immediate lock on drive removal
- Secure memory clearing
- Clipboard auto-clear
"""

import os
import sys
import time
import threading
from typing import Callable, Optional
from pathlib import Path


# Windows drive type constants
DRIVE_UNKNOWN = 0
DRIVE_NO_ROOT_DIR = 1
DRIVE_REMOVABLE = 2
DRIVE_FIXED = 3
DRIVE_REMOTE = 4
DRIVE_CDROM = 5
DRIVE_RAMDISK = 6


def is_removable_path(path: str) -> bool:
    """
    Check if a path is on a removable drive.
    
    Args:
        path: Full path to check (e.g., "E:\\vaults\\vault.dat")
    
    Returns:
        True if path is on removable drive, False otherwise
    
    Platform-specific:
        - Windows: Uses GetDriveTypeW to detect removable drives
        - Linux/macOS: Returns False (no reliable detection without root)
    """
    try:
        # Normalize path
        abs_path = os.path.abspath(path)
        
        # Windows-specific removable drive detection
        if sys.platform == 'win32':
            try:
                import ctypes
                
                # Extract drive letter (e.g., "E:\\vaults\\vault.dat" -> "E:\\")
                drive = os.path.splitdrive(abs_path)[0]
                if not drive:
                    return False
                
                # Ensure drive has trailing backslash
                if not drive.endswith('\\'):
                    drive += '\\'
                
                # Get drive type using Windows API
                drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive)
                
                # DRIVE_REMOVABLE = 2 (USB drives, SD cards, etc.)
                return drive_type == DRIVE_REMOVABLE
                
            except Exception as e:
                print(f"[USB Watch] Failed to detect drive type: {e}")
                return False
        
        # Linux/macOS: No reliable removable detection without root
        # Fall back to False (user can still benefit from path existence polling)
        else:
            return False
            
    except Exception as e:
        print(f"[USB Watch] Error checking removable path: {e}")
        return False


def start_watch(path: str, on_removed: Callable[[], None], poll_interval: float = 1.0) -> threading.Thread:
    """
    Start watching a path for removal (drive disconnect or file deletion).
    
    Args:
        path: Full path to monitor
        on_removed: Callback function to call when path becomes inaccessible
        poll_interval: Seconds between checks (default: 1.0)
    
    Returns:
        Thread object (already started)
    
    Usage:
        >>> def lock_app():
        ...     print("Drive removed! Locking...")
        >>> watcher = start_watch("E:\\vaults\\vault.dat", lock_app)
        >>> # Later...
        >>> stop_watch(watcher)
    """
    stop_flag = threading.Event()
    
    def watch_loop():
        """Background thread that polls path existence."""
        abs_path = os.path.abspath(path)
        
        print(f"[USB Watch] Started monitoring: {abs_path}")
        print(f"[USB Watch] Removable drive: {is_removable_path(abs_path)}")
        
        while not stop_flag.is_set():
            try:
                # Check if path still exists
                if not os.path.exists(abs_path):
                    print(f"[USB Watch] Path no longer accessible: {abs_path}")
                    print(f"[USB Watch] Triggering auto-lock...")
                    
                    # Trigger callback
                    try:
                        on_removed()
                    except Exception as e:
                        print(f"[USB Watch] Error in on_removed callback: {e}")
                    
                    # Stop watching after triggering
                    break
                
                # Wait before next check
                stop_flag.wait(poll_interval)
                
            except Exception as e:
                print(f"[USB Watch] Error in watch loop: {e}")
                # Continue watching even on errors
                stop_flag.wait(poll_interval)
        
        print(f"[USB Watch] Stopped monitoring: {abs_path}")
    
    # Create and start thread
    thread = threading.Thread(target=watch_loop, daemon=True, name="USBWatcher")
    thread._stop_flag = stop_flag  # Store flag for stop_watch()
    thread.start()
    
    return thread


def stop_watch(thread: threading.Thread) -> None:
    """
    Stop a watcher thread.
    
    Args:
        thread: Thread object returned by start_watch()
    
    Usage:
        >>> watcher = start_watch(...)
        >>> stop_watch(watcher)
    """
    try:
        if hasattr(thread, '_stop_flag'):
            thread._stop_flag.set()
            print(f"[USB Watch] Stop signal sent")
        else:
            print(f"[USB Watch] Warning: Thread has no stop flag")
    except Exception as e:
        print(f"[USB Watch] Error stopping watcher: {e}")


def get_drive_info(path: str) -> dict:
    """
    Get detailed drive information for a path.
    
    Args:
        path: Full path to check
    
    Returns:
        Dictionary with drive information:
        - drive: Drive letter (Windows) or mount point
        - type: Drive type name
        - removable: Boolean
        - exists: Boolean
    
    Usage:
        >>> info = get_drive_info("E:\\vaults\\vault.dat")
        >>> print(info['removable'])
        True
    """
    try:
        abs_path = os.path.abspath(path)
        
        info = {
            'path': abs_path,
            'exists': os.path.exists(abs_path),
            'removable': is_removable_path(abs_path),
            'drive': None,
            'type': 'unknown'
        }
        
        # Windows-specific
        if sys.platform == 'win32':
            try:
                import ctypes
                
                drive = os.path.splitdrive(abs_path)[0]
                if drive:
                    if not drive.endswith('\\'):
                        drive += '\\'
                    
                    info['drive'] = drive
                    
                    drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive)
                    
                    type_names = {
                        0: 'unknown',
                        1: 'no_root_dir',
                        2: 'removable',
                        3: 'fixed',
                        4: 'remote',
                        5: 'cdrom',
                        6: 'ramdisk'
                    }
                    
                    info['type'] = type_names.get(drive_type, 'unknown')
            except Exception as e:
                print(f"[USB Watch] Error getting drive info: {e}")
        
        return info
        
    except Exception as e:
        print(f"[USB Watch] Error in get_drive_info: {e}")
        return {
            'path': path,
            'exists': False,
            'removable': False,
            'drive': None,
            'type': 'error'
        }


# Module-level test
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python usb_watch.py <path_to_monitor>")
        print("\nExample:")
        print("  python usb_watch.py E:\\vaults\\test.dat")
        sys.exit(1)
    
    test_path = sys.argv[1]
    
    print("=" * 60)
    print("USB Watch Test")
    print("=" * 60)
    
    # Show drive info
    info = get_drive_info(test_path)
    print(f"\nPath: {info['path']}")
    print(f"Drive: {info['drive']}")
    print(f"Type: {info['type']}")
    print(f"Removable: {info['removable']}")
    print(f"Exists: {info['exists']}")
    
    if not info['exists']:
        print("\n⚠️  Path does not exist!")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("Starting watcher... (Remove drive or delete file to test)")
    print("Press Ctrl+C to stop")
    print("=" * 60 + "\n")
    
    def on_removed():
        print("\n" + "!" * 60)
        print("🚨 DRIVE REMOVED OR FILE DELETED!")
        print("!" * 60)
        print("\nIn real app, this would trigger auto-lock.")
    
    watcher = start_watch(test_path, on_removed, poll_interval=1.0)
    
    try:
        # Keep main thread alive
        while watcher.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n\nStopping watcher...")
        stop_watch(watcher)
        watcher.join(timeout=2)
        print("Done.")
