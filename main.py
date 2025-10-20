"""PassGuard - Secure Password Manager
Main application entry point with automatic dependency installation
"""

# Auto-install dependencies if missing
def check_dependencies():
    """Check and install missing dependencies automatically"""
    missing = []
    
    try:
        import customtkinter
    except ImportError:
        missing.append('customtkinter==5.2.1')
    
    try:
        import pyperclip
    except ImportError:
        missing.append('pyperclip==1.8.2')
    
    try:
        import argon2
    except ImportError:
        missing.append('argon2-cffi==23.1.0')
    
    try:
        from Crypto.Cipher import AES
    except ImportError:
        missing.append('pycryptodome==3.20.0')
    
    try:
        import cryptography
    except ImportError:
        missing.append('cryptography==41.0.7')
    
    try:
        import reportlab
    except ImportError:
        missing.append('reportlab==4.0.7')
    
    try:
        import requests
    except ImportError:
        missing.append('requests==2.31.0')
    
    try:
        import flask
    except ImportError:
        missing.append('flask==3.0.0')
    
    try:
        import flask_cors
    except ImportError:
        missing.append('flask-cors==4.0.0')
    
    if missing:
        print("=" * 60)
        print("PassGuard - Installing Missing Dependencies")
        print("=" * 60)
        print()
        print(f"Found {len(missing)} missing package(s). Installing...")
        print()
        
        import subprocess
        for package in missing:
            pkg_name = package.split('==')[0]
            print(f"Installing {pkg_name}...", end=' ')
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", package, "--quiet"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print("✓")
            except:
                print("✗")
                print(f"\nERROR: Failed to install {pkg_name}")
                print("Please run: pip install -r requirements.txt")
                input("\nPress Enter to exit...")
                sys.exit(1)
        
        print()
        print("✓ All dependencies installed successfully!")
        print("=" * 60)
        print()

# Check dependencies before importing
check_dependencies()

import customtkinter as ctk
import os
import sys
import threading
import time
import pyperclip
from typing import Optional
from ui.unlock_dialog import UnlockDialog
from ui.main_window import MainWindow
from core.vault import unlock_vault, create_vault, load_vault_labels
from core.usb_watch import is_removable_path, start_watch, stop_watch, get_drive_info


class PassGuardApp:
    """Main application class managing vault lifecycle"""
    
    # Constants
    INACTIVITY_LIMIT = 3 * 60  # 3 minutes
    CHANGE_INACTIVITY_LIMIT = 3 * 60  # 3 minutes without credential changes
    
    def __init__(self, tray_app=None):
        """Initialize PassGuard application
        
        Args:
            tray_app: Optional system tray application instance
        """
        self.tray_app = tray_app
        self.main_window: Optional[MainWindow] = None
        self.unlock_ui: Optional[UnlockDialog] = None
        self.usb_watcher_thread: Optional[threading.Thread] = None
        
        # Session management
        self.last_activity_time = time.time()
        self.last_change_time = time.time()
        self.current_session_id = 0
        self.failed_attempts = 0
        
        # Vault state
        self.selected_vault_path = ""
        self.selected_vault_label = ""
        
        # Resource paths
        self.icon_path = self._get_resource_path("assets", "icon.ico")
    
    @staticmethod
    def _get_resource_path(*path_parts) -> str:
        """Get absolute path to resource (works for dev and PyInstaller)"""
        try:
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, *path_parts)
    
    @staticmethod
    def center_window(win):
        """Center window on screen with smooth positioning"""
        try:
            win.update_idletasks()
            w, h = win.winfo_width(), win.winfo_height()
            
            # Fallback to requested size if current size is not yet realized
            if w <= 1 or h <= 1:
                w, h = win.winfo_reqwidth(), win.winfo_reqheight()
            
            sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
            x = (sw // 2) - (w // 2)
            y = (sh // 2) - (h // 2)
            
            win.geometry(f"+{x}+{y}")
            win.attributes("-topmost", True)
            
            # Drop topmost after a tick to avoid sticking above everything
            win.after(200, lambda: win.attributes("-topmost", False))
            # Re-center once more to handle late layout changes
            win.after(220, lambda: PassGuardApp._recenter(win))
        except Exception as e:
            print(f"[App] Failed to center window: {e}")
    
    @staticmethod
    def _recenter(win):
        """Internal recenter helper"""
        try:
            win.update_idletasks()
            w, h = win.winfo_width(), win.winfo_height()
            if w <= 1 or h <= 1:
                w, h = win.winfo_reqwidth(), win.winfo_reqheight()
            
            sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
            x = (sw // 2) - (w // 2)
            y = (sh // 2) - (h // 2)
            win.geometry(f"+{x}+{y}")
        except Exception as e:
            print(f"[App] Failed to recenter: {e}")
    
    def monitor_inactivity(self):
        """Monitor for inactivity and auto-lock"""
        session_id = self.current_session_id
        
        def check():
            while True:
                time.sleep(10)
                # Exit if there is no active main window
                if self.main_window is None:
                    break
                # Lock if there have been no credential changes for CHANGE_INACTIVITY_LIMIT
                if time.time() - self.last_change_time > self.CHANGE_INACTIVITY_LIMIT:
                    try:
                        if self.main_window is not None and session_id == self.current_session_id:
                            self.main_window.after(0, lambda sid=session_id: self.lock_due_to_inactivity(sid))
                            break
                    except Exception as e:
                        print(f"[App] Inactivity monitor error: {e}")
        
        threading.Thread(target=check, daemon=True).start()
    
    def lock_vault(self):
        """Lock the vault and return to unlock screen"""
        if self.main_window:
            try:
                # Stop USB watcher if running
                if self.usb_watcher_thread and self.usb_watcher_thread.is_alive():
                    print("[Auto-Lock] Stopping USB watcher...")
                    stop_watch(self.usb_watcher_thread)
                    self.usb_watcher_thread = None
                
                # Clear clipboard for security
                try:
                    pyperclip.copy("")
                    print("[Auto-Lock] Clipboard cleared")
                except Exception as e:
                    print(f"[Auto-Lock] Failed to clear clipboard: {e}")
                
                self.main_window.destroy()
            finally:
                self.main_window = None
                # Invalidate any pending monitor callbacks from this session
                self.current_session_id += 1
                # Reset timers to prevent stale triggers
                self.last_change_time = time.time()
                
                # Update tray state
                if self.tray_app:
                    self.tray_app.vault_unlocked = False
                
                # Show unlock dialog if it exists
                if self.unlock_ui:
                    try:
                        # Clear password box for security BEFORE showing
                        try:
                            self.unlock_ui.password_entry.delete(0, "end")
                        except Exception:
                            pass
                        self.unlock_ui.deiconify()
                        # Recenter and raise unlock window
                        self.center_window(self.unlock_ui)
                    except Exception as e:
                        print(f"[App] Failed to show unlock dialog: {e}")
    
    def lock_due_to_inactivity(self, session_id: int):
        """Lock due to inactivity (keeps API running)"""
        # Only post a message if vault is currently open; otherwise ignore stale callbacks
        if self.main_window is None or session_id != self.current_session_id:
            return
        
        # Lock UI but keep API running for browser autofill
        if self.main_window:
            self.main_window.lock_vault(stop_api=False)
        
        try:
            if self.unlock_ui:
                self.unlock_ui.status_label.configure(
                    text="Locked due to inactivity. Browser autofill still active."
                )
        except Exception as e:
            print(f"[App] Failed to update status: {e}")
    
    def launch_main_window(self, credentials, password, label):
        """Launch the main vault window"""
        def on_cred_change():
            self.last_change_time = time.time()
        
        self.main_window = MainWindow(
            credentials, password, self.selected_vault_path, label,
            parent=self.unlock_ui,
            on_change=on_cred_change,
            change_timeout_sec=self.CHANGE_INACTIVITY_LIMIT,
            app=self  # Pass app instance for tray integration
        )
        
        if os.path.exists(self.icon_path):
            try:
                self.main_window.iconbitmap(self.icon_path)
            except Exception as e:
                print(f"[App] Failed to set icon: {e}")
        
        # Start USB watcher if vault is on removable drive
        if self.selected_vault_path and is_removable_path(self.selected_vault_path):
            print(f"[Auto-Lock] Vault on removable drive detected")
            drive_info = get_drive_info(self.selected_vault_path)
            print(f"[Auto-Lock] Drive: {drive_info['drive']} | Type: {drive_info['type']}")
            
            def on_usb_removed():
                """Callback when USB drive is removed"""
                print(f"[Auto-Lock] USB drive removed! Triggering auto-lock...")
                try:
                    # Schedule lock on main thread
                    if self.main_window:
                        self.main_window.after(0, self.lock_vault)
                except Exception as e:
                    print(f"[Auto-Lock] Error triggering lock: {e}")
            
            self.usb_watcher_thread = start_watch(self.selected_vault_path, on_usb_removed, poll_interval=1.0)
            print(f"[Auto-Lock] USB watcher started for: {self.selected_vault_path}")
        else:
            print(f"[Auto-Lock] Vault on fixed drive - USB watcher not needed")
        
        # Start inactivity monitor
        self.monitor_inactivity()
        
        # Update tray state
        if self.tray_app:
            self.tray_app.vault_unlocked = True
        
        # Position and show window
        try:
            self.main_window.withdraw()
            self.center_window(self.main_window)
            self.main_window.deiconify()
            self.main_window.lift()
            self.main_window.focus_force()
        except Exception as e:
            print(f"[App] Failed to show main window: {e}")
    
    def handle_unlock(self, password, status_label, vault_path):
        """Handle vault unlock attempt"""
        try:
            if not vault_path or not os.path.exists(vault_path):
                status_label.configure(text="Please select a vault.")
                return
            
            self.selected_vault_path = vault_path
            labels = load_vault_labels()
            filename = os.path.basename(vault_path)
            self.selected_vault_label = labels.get(filename, "Unknown")
            
            vault = unlock_vault(password, self.selected_vault_path)
            status_label.configure(text="Vault unlocked ✔")
            self.failed_attempts = 0
            status_label.after(500, lambda: self.open_main(vault["credentials"], password))
        except FileNotFoundError:
            status_label.configure(text="Vault not found.")
        except Exception as e:
            self.failed_attempts += 1
            remaining_to_lock = max(0, 3 - self.failed_attempts)
            
            if self.failed_attempts < 3:
                status_label.configure(
                    text=f"Invalid password ❌  ({self.failed_attempts}/3). {remaining_to_lock} more before vault is locked."
                )
            elif self.failed_attempts == 3:
                # Ensure any open vault is closed
                try:
                    self.lock_vault()
                except Exception:
                    pass
                status_label.configure(
                    text="Too many attempts. Vault locked. One more wrong attempt will suspend the app."
                )
            else:
                # 4th wrong attempt => suspend application
                try:
                    self.show_splash_and_suspend("Too many failed attempts. Suspending application…")
                except Exception:
                    # fallback: close app forcefully
                    try:
                        if self.unlock_ui:
                            self.unlock_ui.destroy()
                    except Exception:
                        pass
    
    def show_splash_and_suspend(self, message: str):
        """Show splash message and suspend app"""
        try:
            if self.unlock_ui:
                self.unlock_ui.attributes("-disabled", True)
        except Exception:
            pass
        
        splash = ctk.CTkLabel(
            self.unlock_ui,
            text=message,
            text_color="white",
            fg_color="#AA0000",
            font=ctk.CTkFont(size=16, weight="bold"),
            corner_radius=10,
            padx=15,
            pady=10,
            wraplength=260,
            justify="center",
        )
        # Center it in the unlock window
        splash.place(relx=0.5, rely=0.5, anchor="center")
        # Exit shortly after to ensure user sees the message
        if self.unlock_ui:
            self.unlock_ui.after(1800, lambda: self.unlock_ui.destroy())
    
    def handle_create(self, name, password, path, status_label, refresh_callback):
        """Handle vault creation"""
        try:
            create_vault(password, path)
            status_label.configure(text="Vault created ✔")
            status_label.after(800, refresh_callback)
        except Exception as e:
            status_label.configure(text=f"Error: {e}")
    
    def open_main(self, credentials, password):
        """Open main vault window"""
        try:
            if self.unlock_ui and hasattr(self.unlock_ui, '_focus_after_id'):
                self.unlock_ui.after_cancel(self.unlock_ui._focus_after_id)
        except Exception:
            pass
        
        if self.unlock_ui:
            self.unlock_ui.withdraw()
            self.unlock_ui.update()
        
        # Start change inactivity window from now
        self.last_change_time = time.time()
        self.current_session_id += 1
        
        try:
            if self.unlock_ui:
                self.unlock_ui.status_label.configure(text="")
        except Exception:
            pass
        
        self.launch_main_window(credentials, password, self.selected_vault_label)
    
    def show_unlock_dialog(self):
        """Show the unlock dialog"""
        if self.unlock_ui:
            try:
                self.unlock_ui.deiconify()
                self.center_window(self.unlock_ui)
                self.unlock_ui.lift()
                self.unlock_ui.focus_force()
            except Exception as e:
                print(f"[App] Failed to show unlock dialog: {e}")
    
    def cleanup(self):
        """Cleanup resources before exit"""
        try:
            if self.usb_watcher_thread and self.usb_watcher_thread.is_alive():
                stop_watch(self.usb_watcher_thread)
            
            if self.main_window:
                self.main_window.destroy()
            
            if self.unlock_ui:
                self.unlock_ui.destroy()
        except Exception as e:
            print(f"[App] Cleanup error: {e}")
    
    def run(self):
        """Run the application"""
        # Create unlock dialog
        self.unlock_ui = UnlockDialog(self.handle_unlock, self.handle_create, app=self)
        
        if os.path.exists(self.icon_path):
            try:
                self.unlock_ui.iconbitmap(self.icon_path)
            except Exception as e:
                print(f"[App] Failed to set icon: {e}")
        
        # Center and show unlock window
        self.center_window(self.unlock_ui)
        
        # Handle close button for tray
        if self.tray_app:
            self.unlock_ui.protocol("WM_DELETE_WINDOW", self._minimize_to_tray)
        
        # Start main loop
        self.unlock_ui.mainloop()
    
    def _minimize_to_tray(self):
        """Minimize to system tray instead of closing"""
        # Clear password field for security
        if self.unlock_ui:
            try:
                self.unlock_ui.password_entry.delete(0, "end")
            except Exception:
                pass
            self.unlock_ui.withdraw()
        if self.main_window:
            self.main_window.withdraw()


class TrayApp:
    """System tray application manager"""
    
    def __init__(self):
        self.icon = None
        self.main_app = None
        self.vault_unlocked = False
        
    def create_icon_image(self):
        """Create or load tray icon image"""
        icon_path = os.path.join("assets", "icon.ico")
        if os.path.exists(icon_path):
            try:
                from PIL import Image
                return Image.open(icon_path)
            except:
                pass
        
        # Fallback: create simple icon
        try:
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (64, 64), color='#2c3e50')
            draw = ImageDraw.Draw(img)
            draw.rectangle([20, 25, 44, 50], fill='#3498db', outline='#2980b9')
            draw.ellipse([24, 15, 40, 30], outline='#3498db', width=3)
            return img
        except:
            return None
    
    def show_vault(self, icon=None, item=None):
        """Show/unlock the vault window"""
        if self.main_app and self.main_app.unlock_ui:
            try:
                self.main_app.unlock_ui.deiconify()
                self.main_app.unlock_ui.lift()
                self.main_app.unlock_ui.focus_force()
            except:
                pass
    
    def lock_vault(self, icon=None, item=None):
        """Lock the vault"""
        if self.main_app:
            try:
                self.main_app.lock_vault()
                self.vault_unlocked = False
            except:
                pass
    
    def exit_app(self, icon=None, item=None):
        """Exit the application immediately"""
        try:
            # Stop tray icon first
            if self.icon:
                self.icon.visible = False
                self.icon.stop()
        except:
            pass
        finally:
            # Force immediate exit - no cleanup, no errors
            os._exit(0)
    
    def create_menu(self):
        """Create tray icon menu"""
        try:
            import pystray
            from pystray import MenuItem as item
            return pystray.Menu(
                item('🔓 Show Vault', self.show_vault, default=True),
                item('🔒 Lock Vault', self.lock_vault, enabled=lambda item: self.vault_unlocked),
                item('❌ Exit', self.exit_app)
            )
        except ImportError:
            return None
    
    def run(self):
        """Start the system tray application"""
        # Set appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Create main app
        self.main_app = PassGuardApp(tray_app=self)
        
        # Try to create tray icon
        try:
            import pystray
            icon_image = self.create_icon_image()
            if icon_image:
                self.icon = pystray.Icon(
                    "PassGuard",
                    icon_image,
                    "PassGuard Password Manager",
                    menu=self.create_menu()
                )
                
                # Start app in thread
                app_thread = threading.Thread(target=self.main_app.run, daemon=False)
                app_thread.start()
                
                # Run tray icon (blocks)
                print("[PassGuard] Starting with system tray...")
                self.icon.run()
            else:
                # No icon, run normally
                print("[PassGuard] Starting without tray (icon not available)...")
                self.main_app.run()
        except ImportError:
            # pystray not available, run without tray
            print("[PassGuard] Starting without tray (pystray not installed)...")
            self.main_app.run()


def main():
    """Entry point - runs with system tray by default"""
    tray = TrayApp()
    tray.run()


if __name__ == "__main__":
    main()
