from core.vault import save_vault
from core.security_audit import run_security_audit
from core.pdf_report import save_report_pdf
from core.strength import classify_strength
from core.export_import import export_vault, import_vault, keypair_exists, save_keypair, get_public_key_fingerprint
from core.autofill_server import AutofillServer
from ui.security_check_dialog import SecurityCheckDialog
from tkinter import messagebox, filedialog
import threading
import time
import customtkinter as ctk
import pyperclip
import string
import random
import os
import sys
from typing import Optional, Callable

class MainWindow(ctk.CTkToplevel):
    def __init__(self, credentials: list, password: str, vault_path: str, label: str, parent: Optional[ctk.CTk] = None, on_change: Optional[Callable[[], None]] = None, change_timeout_sec: int = 180, app=None):
        super().__init__(parent)
        self.title("PassGuard Vault")
        self.geometry("1100x700")
        self.credentials = credentials
        self.password = password
        self.vault_path = vault_path
        self.parent = parent
        self.app = app  # Reference to main app for tray integration
        self._user_on_change = on_change or (lambda: None)
        self.change_inactivity_limit = max(1, int(change_timeout_sec))
        self.change_deadline = time.time() + self.change_inactivity_limit
        self._timer_after_id = None
        self._timer_paused = False
        
        # Autofill server
        self.autofill_server = None
        self._start_autofill_server()
        icon_path = os.path.join("assets", "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(default=icon_path)
            except Exception as e:
                print(f"Failed to set main icon: {e}")
        # Close button: minimize to tray if available, otherwise lock
        try:
            if self.app and hasattr(self.app, 'tray_app') and self.app.tray_app:
                self.protocol("WM_DELETE_WINDOW", self._minimize_to_tray)
            else:
                self.protocol("WM_DELETE_WINDOW", self.lock_vault)
        except Exception as e:
            print(f"[MainWindow] Failed to set close protocol: {e}")

        # Fonts for consistency
        self.font_body = ctk.CTkFont(size=14)
        self.font_bold = ctk.CTkFont(size=14, weight="bold")
        self.font_title = ctk.CTkFont(size=24, weight="bold")

        # Header frame
        header_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=10)
        header_frame.pack(fill="x", padx=20, pady=15)
        
        self.label = ctk.CTkLabel(header_frame, text=f"🔐 {label}", font=self.font_title, text_color="#3498db")
        self.label.pack(pady=15)

        # Countdown label (top-right)
        self.timer_label = ctk.CTkLabel(
            self,
            text="",
            text_color="white",
            fg_color="#2b2b2b",
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=8,
            padx=8,
            pady=4,
        )
        self.timer_label.place(relx=0.98, rely=0.02, anchor="ne")

        # Search bar
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(pady=10)
        
        ctk.CTkLabel(search_frame, text="🔍", font=ctk.CTkFont(size=18)).pack(side="left", padx=(0, 5))
        
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.render_table())
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search by website or username...", textvariable=self.search_var, width=500, font=self.font_body, height=40)
        self.search_entry.pack(side="left")

        # Action buttons - organized in rows
        button_container = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=10)
        button_container.pack(pady=15, padx=20, fill="x")
        
        # Row 1: Primary actions
        row1 = ctk.CTkFrame(button_container, fg_color="transparent")
        row1.pack(pady=10, padx=15)
        
        self.add_btn = ctk.CTkButton(
            row1, 
            text="➕ Add Credential", 
            command=self.open_add_window, 
            font=self.font_bold,
            fg_color="#2ecc71",
            hover_color="#27ae60",
            width=180,
            height=45
        )
        self.add_btn.pack(side="left", padx=5)
        self.create_tooltip(self.add_btn, "Add a new credential to your vault\nShortcut: Ctrl+N")

        self.lock_btn = ctk.CTkButton(
            row1, 
            text="🔒 Lock Vault", 
            command=self.lock_vault, 
            font=self.font_bold,
            fg_color="#95a5a6",
            hover_color="#7f8c8d",
            width=150,
            height=45
        )
        self.lock_btn.pack(side="left", padx=5)
        self.create_tooltip(self.lock_btn, "Lock vault and return to unlock screen\nClears all data from memory")
        
        self.security_btn = ctk.CTkButton(
            row1, 
            text="🛡️ Security Audit", 
            command=self.run_security_test, 
            font=self.font_bold, 
            fg_color="#FF6B35", 
            hover_color="#CC5529",
            width=180,
            height=45
        )
        self.security_btn.pack(side="left", padx=5)
        self.create_tooltip(self.security_btn, "Analyze vault security:\n• Weak passwords\n• Reused passwords\n• PII exposure\n• Generate PDF report")
        
        self.breach_check_btn = ctk.CTkButton(
            row1, 
            text="🔍 Breach Check", 
            command=self.open_breach_check, 
            font=self.font_bold, 
            fg_color="#e74c3c", 
            hover_color="#c0392b", 
            width=180,
            height=45
        )
        self.breach_check_btn.pack(side="left", padx=5)
        self.create_tooltip(self.breach_check_btn, "Check credentials against HIBP database:\n• Password breach check (free)\n• Account breach check (API key required)")
        
        # Row 2: Export/Import/Browser Extension (centered)
        row2 = ctk.CTkFrame(button_container, fg_color="transparent")
        row2.pack(pady=(0, 10), padx=15)
        
        self.export_btn = ctk.CTkButton(
            row2, 
            text="📤 Export Vault", 
            command=self.export_vault_dialog, 
            font=self.font_bold, 
            fg_color="#3498db", 
            hover_color="#2980b9", 
            width=180,
            height=45
        )
        self.export_btn.pack(side="left", padx=5)
        self.create_tooltip(self.export_btn, "Export vault securely:\n• Backup for yourself\n• Share with others (RSA-4096)\n• Digital signatures for authenticity")
        
        self.import_btn = ctk.CTkButton(
            row2, 
            text="📥 Import Vault", 
            command=self.import_vault_dialog, 
            font=self.font_bold, 
            fg_color="#9b59b6", 
            hover_color="#8e44ad", 
            width=180,
            height=45
        )
        self.import_btn.pack(side="left", padx=5)
        self.create_tooltip(self.import_btn, "Import vault from .pvgx file:\n• Restore backup\n• Receive shared vault\n• Verify signatures")
        
        # Browser Extension button
        self.browser_ext_btn = ctk.CTkButton(
            row2, 
            text="🌐 Browser Extension", 
            command=self.show_browser_extension_setup, 
            font=self.font_bold, 
            fg_color="#16a085", 
            hover_color="#138d75", 
            width=180,
            height=45
        )
        self.browser_ext_btn.pack(side="left", padx=5)
        self.create_tooltip(self.browser_ext_btn, "Setup browser autofill:\n• Copy authentication token\n• View setup instructions\n• One-time configuration")

        self.bind_all("<Control-n>", lambda e: self.open_add_window())

        # Credentials table
        table_label = ctk.CTkLabel(self, text="📋 Your Credentials", font=ctk.CTkFont(size=16, weight="bold"), anchor="w")
        table_label.pack(anchor="w", padx=25, pady=(10, 5))
        
        self.table_frame = ctk.CTkScrollableFrame(self, fg_color="#1a1a1a", corner_radius=10)
        self.table_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.render_table()
        # Wrap on_change to also bump deadline and refresh display
        def _wrapped_on_change():
            try:
                self._user_on_change()
            finally:
                self._bump_deadline()
                self._update_timer_text()
        self.on_change = _wrapped_on_change

        # Start timer updates
        self._update_timer_text()
        self._schedule_timer_tick()
    
    def _start_autofill_server(self):
        """Start the autofill API server for browser extension."""
        try:
            self.autofill_server = AutofillServer(self.credentials)
            self.autofill_server.start()
            print("[PassGuard] Autofill server started successfully")
        except Exception as e:
            print(f"[PassGuard] Failed to start autofill server: {e}")
            self.autofill_server = None
    
    def _stop_autofill_server(self):
        """Stop the autofill API server."""
        if self.autofill_server:
            try:
                self.autofill_server.stop()
                print("[PassGuard] Autofill server stopped")
            except Exception as e:
                print(f"[PassGuard] Error stopping autofill server: {e}")
    
    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget."""
        tooltip_data = {'window': None, 'after_id': None}
        
        def destroy_tooltip():
            """Safely destroy tooltip."""
            if tooltip_data['after_id']:
                try:
                    widget.after_cancel(tooltip_data['after_id'])
                except:
                    pass
                tooltip_data['after_id'] = None
            
            if tooltip_data['window']:
                try:
                    tooltip_data['window'].destroy()
                except:
                    pass
                tooltip_data['window'] = None
        
        def show_tooltip():
            """Show tooltip after delay."""
            if tooltip_data['window']:
                return
            
            try:
                # Get widget position
                x = widget.winfo_rootx() + 25
                y = widget.winfo_rooty() + widget.winfo_height() + 5
                
                # Create tooltip window
                tooltip_data['window'] = ctk.CTkToplevel(widget)
                tooltip_data['window'].wm_overrideredirect(True)
                tooltip_data['window'].wm_geometry(f"+{x}+{y}")
                
                # Make it transient to main window so it minimizes with it
                tooltip_data['window'].transient(self)
                
                label = ctk.CTkLabel(
                    tooltip_data['window'],
                    text=text,
                    font=ctk.CTkFont(size=11),
                    fg_color="#2b2b2b",
                    corner_radius=6,
                    padx=10,
                    pady=6
                )
                label.pack()
                
                # Bind leave event to tooltip itself
                tooltip_data['window'].bind("<Leave>", lambda e: destroy_tooltip())
            except:
                destroy_tooltip()
        
        def on_enter(event):
            # Destroy any existing tooltip
            destroy_tooltip()
            # Schedule tooltip to show after short delay
            tooltip_data['after_id'] = widget.after(500, show_tooltip)
        
        def on_leave(event):
            # Cancel scheduled tooltip and destroy existing one
            destroy_tooltip()
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
        
        # Also destroy tooltip when main window loses focus
        self.bind("<FocusOut>", lambda e: destroy_tooltip())
        self.bind("<Unmap>", lambda e: destroy_tooltip())
    
    def lock_vault(self, stop_api=True):
        """Lock the vault and return to unlock screen.
        
        Args:
            stop_api: If True, stops the autofill API server. 
                     If False, keeps API running for browser autofill.
        """
        try:
            self.pause_timer()
            
            # Stop autofill server if requested
            if stop_api and self.autofill_server:
                try:
                    self.autofill_server.stop()
                    print("[PassGuard] Autofill server stopped")
                except Exception as e:
                    print(f"[PassGuard] Error stopping autofill server: {e}")
            
            # Save any pending changes
            try:
                save_vault(self.password, {"credentials": self.credentials}, self.vault_path)
            except Exception as e:
                print(f"Failed to save vault on lock: {e}")
            
            # Clear all widget references to prevent tkinter errors
            try:
                if hasattr(self, 'table_frame'):
                    for widget in self.table_frame.winfo_children():
                        try:
                            widget.destroy()
                        except:
                            pass
            except Exception as e:
                print(f"[PassGuard] Error clearing widgets: {e}")
            
            # Show parent unlock dialog if it exists
            if self.parent is not None:
                self.parent.deiconify()
                try:
                    # Clear password box for security
                    self.parent.password_entry.delete(0, "end")
                except Exception:
                    pass
                # Center and raise the unlock window
                try:
                    self.parent.update_idletasks()
                    w, h = self.parent.winfo_width(), self.parent.winfo_height()
                    sw, sh = self.parent.winfo_screenwidth(), self.parent.winfo_screenheight()
                    x = (sw // 2) - (w // 2)
                    y = (sh // 2) - (h // 2)
                    self.parent.geometry(f"+{x}+{y}")
                    self.parent.attributes("-topmost", True)
                    self.parent.after(200, lambda: self.parent.attributes("-topmost", False))
                except Exception:
                    pass
            
            # Destroy this window last
            try:
                # Cancel timer updates before destroy
                if self._timer_after_id is not None:
                    self.after_cancel(self._timer_after_id)
                self.destroy()
            except Exception as e:
                print(f"[PassGuard] Error destroying window: {e}")
                
        except Exception as e:
            print(f"[PassGuard] Error in lock_vault: {e}")

    def _format_remaining(self, seconds: int) -> str:
        m, s = divmod(max(0, seconds), 60)
        return f"{m:02d}:{s:02d}"

    def _bump_deadline(self):
        self.change_deadline = time.time() + self.change_inactivity_limit

    def _update_timer_text(self):
        try:
            if not self.winfo_exists():
                return
            if self._timer_paused:
                self.timer_label.configure(text="Timer paused")
            else:
                remaining = int(self.change_deadline - time.time())
                self.timer_label.configure(text=f"Auto-lock in {self._format_remaining(remaining)}")
        except Exception:
            pass

    def _schedule_timer_tick(self):
        try:
            self._timer_after_id = self.after(1000, self._tick_timer)
        except Exception:
            self._timer_after_id = None

    def _tick_timer(self):
        try:
            self._update_timer_text()
            self._schedule_timer_tick()
        except Exception:
            pass
    
    def pause_timer(self):
        """Pause the inactivity timer (e.g., during security test)."""
        try:
            self._timer_paused = True
            self._update_timer_text()
        except Exception:
            pass
    
    def resume_timer(self):
        """Resume the inactivity timer and reset deadline."""
        try:
            if not self.winfo_exists():
                return
            self._timer_paused = False
            self.change_deadline = time.time() + self.change_inactivity_limit
            self._update_timer_text()
        except Exception:
            pass

    def render_table(self):
        for widget in self.table_frame.winfo_children():
            widget.destroy()

        # Headers aligned with content
        headers = ["🌐 Website", "👤 Username / Email", "🔑 Password", "", "", "", ""]
        header_frame = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, columnspan=7, sticky="ew", padx=5, pady=(5, 8))
        
        # Position headers to align with row content
        header_labels = [
            ("🌐 Website", 0, 200),
            ("👤 Username / Email", 1, 250),
            ("🔑 Password", 2, 120),
        ]
        
        for text, col, width in header_labels:
            header = ctk.CTkLabel(header_frame, text=text, font=ctk.CTkFont(size=13, weight="bold"), text_color="#3498db", width=width, anchor="w")
            header.grid(row=0, column=col, padx=15, pady=8, sticky="w")

        query = self.search_var.get().lower()
        filtered = [cred for cred in self.credentials if query in cred['website'].lower() or query in cred['username'].lower()]

        for row, cred in enumerate(filtered, start=1):
            # Create row frame for better visual separation
            row_frame = ctk.CTkFrame(self.table_frame, fg_color="#252525", corner_radius=6)
            row_frame.grid(row=row, column=0, columnspan=7, sticky="ew", padx=5, pady=3)
            
            website = ctk.CTkLabel(row_frame, text=cred['website'], font=self.font_body, width=200, anchor="w")
            username = ctk.CTkLabel(row_frame, text=cred['username'], font=self.font_body, width=250, anchor="w")
            password = ctk.CTkLabel(row_frame, text="••••••••", font=self.font_body, width=120, anchor="w")

            website.grid(row=0, column=0, padx=15, pady=10, sticky="w")
            username.grid(row=0, column=1, padx=15, pady=10, sticky="w")
            password.grid(row=0, column=2, padx=15, pady=10, sticky="w")

            # Action buttons inside row frame
            reveal_btn = ctk.CTkButton(row_frame, text="👁", width=45, height=35, font=ctk.CTkFont(size=18), fg_color="#34495e", hover_color="#2c3e50", anchor="center")
            reveal_btn.grid(row=0, column=3, padx=5, pady=10)
            reveal_btn.bind("<ButtonPress-1>", lambda e, l=password, p=cred['password']: l.configure(text=p))
            reveal_btn.bind("<ButtonRelease-1>", lambda e, l=password: l.configure(text="••••••••"))
            reveal_btn.bind("<ButtonPress-3>", lambda e, l=password, p=cred['password']: l.configure(text=p))
            reveal_btn.bind("<ButtonRelease-3>", lambda e, l=password: l.configure(text="••••••••"))
            self.create_tooltip(reveal_btn, "Hold to reveal password")

            copy_btn = ctk.CTkButton(row_frame, text="📋 Copy", width=80, height=35, fg_color="#27ae60",
                                     hover_color="#229954", command=lambda pw=cred['password']: self.copy_to_clipboard(pw), font=self.font_bold)
            copy_btn.grid(row=0, column=4, padx=5, pady=10)

            edit_btn = ctk.CTkButton(row_frame, text="✏️ Edit", width=80, height=35, fg_color="#f39c12",
                                     hover_color="#e67e22", command=lambda idx=self.credentials.index(cred): self.edit_credential(idx), font=self.font_bold)
            edit_btn.grid(row=0, column=5, padx=5, pady=10)

            del_btn = ctk.CTkButton(row_frame, text="🗑️ Delete", width=90, height=35, fg_color="#e74c3c",
                                     hover_color="#c0392b", command=lambda idx=self.credentials.index(cred): self.delete_credential(idx), font=self.font_bold)
            del_btn.grid(row=0, column=6, padx=5, pady=10)

    def generate_password(self, length=16):
        safe_symbols = '!@#%&*_-+='
        chars = string.ascii_letters + string.digits + safe_symbols
        while True:
            password = ''.join(random.choices(chars, k=length))
            if (any(c.islower() for c in password) and
                any(c.isupper() for c in password) and
                any(c.isdigit() for c in password) and
                any(c in safe_symbols for c in password)):
                return password

    def copy_to_clipboard(self, password):
        pyperclip.copy(password)
        self.show_splash("Password copied to clipboard \u2714")
        threading.Thread(target=self.clear_clipboard_after_delay, daemon=True).start()

    def show_splash(self, text):
        splash = ctk.CTkLabel(
            self,
            text=text,
            text_color="white",
            fg_color="green",
            font=ctk.CTkFont(size=16, weight="bold"),
            corner_radius=10,
            padx=15,
            pady=5
        )
        splash.place(relx=0.5, rely=0.95, anchor="center")
        self.after(2000, splash.destroy)

    def clear_clipboard_after_delay(self):
        time.sleep(15)
        if pyperclip.paste() != "":
            pyperclip.copy("")

    def delete_credential(self, index):
        if messagebox.askyesno("Delete", "Are you sure you want to delete this credential?"):
            self.credentials.pop(index)
            save_vault(self.password, {"credentials": self.credentials}, self.vault_path)
            self.render_table()
            try:
                self.on_change()
            except Exception:
                pass

    def set_window_icon(self, win):
        try:
            if sys.platform.startswith("win"):
                from ctypes import windll
                icon_path = os.path.abspath(os.path.join("assets", "icon.ico"))
                if os.path.exists(icon_path):
                    win.iconbitmap(default=icon_path)
                    hwnd = windll.user32.GetParent(win.winfo_id())
                    windll.shell32.SetCurrentProcessExplicitAppUserModelID("passguard.vault")
                    windll.user32.SendMessageW(hwnd, 0x80, 1, icon_path)
        except Exception as e:
            print(f"Could not set icon: {e}")

    def edit_credential(self, index):
        # Handle both index (int) and credential dict
        if isinstance(index, dict):
            # Called from breach check dialog with credential dict
            cred = index
            # Find the actual index in credentials list
            try:
                index = self.credentials.index(cred)
            except ValueError:
                messagebox.showerror("Error", "Credential not found in vault")
                return
        else:
            # Called normally with index
            cred = self.credentials[index]
        
        # Pause timer during edit
        self.pause_timer()
        
        win = ctk.CTkToplevel(self)
        win.configure(bg=ctk.ThemeManager.theme["CTkFrame"]["fg_color"][1])
        self.set_window_icon(win)
        win.title("Edit Credential")
        win.geometry("380x450")
        win.resizable(False, False)
        win.lift()
        win.focus_force()
        win.grab_set()
        
        # Resume timer when dialog closes
        def on_close():
            self.resume_timer()
            win.destroy()
        
        win.protocol("WM_DELETE_WINDOW", on_close)

        ctk.CTkLabel(win, text="Website", font=self.font_body).pack(pady=5)
        website_entry = ctk.CTkEntry(win, font=self.font_body)
        website_entry.insert(0, cred["website"])
        website_entry.pack()
        win.after(100, lambda: website_entry.focus())

        ctk.CTkLabel(win, text="Username / Email", font=self.font_body).pack(pady=5)
        username_entry = ctk.CTkEntry(win, font=self.font_body, width=280)
        username_entry.insert(0, cred["username"])
        username_entry.pack()

        ctk.CTkLabel(win, text="Password", font=self.font_body).pack(pady=5)
        password_entry = ctk.CTkEntry(win, show="\u2022", font=self.font_body, width=280)
        password_entry.insert(0, cred["password"])
        password_entry.pack()
        
        # Strength bar (non-blocking)
        strength_frame = ctk.CTkFrame(win, fg_color="transparent")
        strength_frame.pack(pady=5)
        
        # Header with info button
        header_frame = ctk.CTkFrame(strength_frame, fg_color="transparent")
        header_frame.pack(anchor="w", fill="x")
        
        ctk.CTkLabel(header_frame, text="Strength:", font=ctk.CTkFont(size=9)).pack(side="left")
        
        # Info button with tooltip
        info_btn = ctk.CTkButton(header_frame, text="ℹ", width=20, height=20, font=ctk.CTkFont(size=12, weight="bold"), fg_color="#3498db", hover_color="#2980b9", corner_radius=10)
        info_btn.pack(side="left", padx=5)
        
        # Tooltip (initially hidden)
        tooltip = ctk.CTkFrame(win, fg_color="#2c3e50", corner_radius=8, border_width=1, border_color="#3498db")
        ctk.CTkLabel(tooltip, text="Strong Password Tips:\n✓ 12+ characters\n✓ Mix uppercase & lowercase\n✓ Include numbers (0-9)\n✓ Add symbols (!@#$%...)\n✓ Avoid personal info\n✓ Use password generator", font=ctk.CTkFont(size=10), justify="left", text_color="white").pack(padx=10, pady=8)
        
        def show_tooltip(e=None):
            tooltip.place(x=50, y=280, anchor="w")
        def hide_tooltip(e=None):
            tooltip.place_forget()
        
        info_btn.bind("<Enter>", show_tooltip)
        info_btn.bind("<Leave>", hide_tooltip)
        info_btn.configure(command=lambda: None)
        
        bar_container = ctk.CTkFrame(strength_frame, fg_color="#2b2b2b", height=16, width=280, corner_radius=8)
        bar_container.pack(pady=3)
        bar_container.pack_propagate(False)
        
        segments = []
        segment_frame = ctk.CTkFrame(bar_container, fg_color="transparent")
        segment_frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        for i in range(5):
            seg = ctk.CTkFrame(segment_frame, fg_color="#1a1a1a", corner_radius=5)
            seg.pack(side="left", fill="both", expand=True, padx=1)
            segments.append(seg)
        
        strength_label = ctk.CTkLabel(strength_frame, text="", font=ctk.CTkFont(size=10))
        strength_label.pack()
        
        def update_strength(event=None):
            pw = password_entry.get()
            if not pw:
                for seg in segments:
                    seg.configure(fg_color="#1a1a1a")
                strength_label.configure(text="")
                return
            
            result = classify_strength(pw, require_strong=False)
            
            # Update segments - all filled segments use the strength color
            strength_colors = {
                0: '#e74c3c',  # Very Weak - Red
                1: '#e67e22',  # Weak - Orange
                2: '#f39c12',  # Medium - Yellow
                3: '#27ae60',  # Strong - Green
                4: '#16a085'   # Very Strong - Teal
            }
            
            filled = result['score'] + 1
            fill_color = strength_colors[result['score']]
            
            for i, seg in enumerate(segments):
                if i < filled:
                    seg.configure(fg_color=fill_color)
                else:
                    seg.configure(fg_color="#1a1a1a")
            
            # Update label
            strength_label.configure(
                text=f"{result['label']} - {result['entropy']} bits",
                text_color=result['color']
            )
        
        password_entry.bind("<KeyRelease>", update_strength)
        update_strength()  # Initial check

        gen_btn = ctk.CTkButton(win, text="Generate Secure Password", command=lambda: self.copy_generated(password_entry), font=self.font_bold)
        gen_btn.pack(pady=5)
        
        # Ensure tooltip stays on top
        tooltip.lift()

        website_entry.bind("<Down>", lambda e: username_entry.focus())
        username_entry.bind("<Up>", lambda e: website_entry.focus())
        username_entry.bind("<Down>", lambda e: password_entry.focus())
        password_entry.bind("<Up>", lambda e: username_entry.focus())

        website_entry.bind("<Return>", lambda e: username_entry.focus())
        username_entry.bind("<Return>", lambda e: password_entry.focus())
        password_entry.bind("<Return>", lambda e: save())

        def save():
            self.credentials[index] = {
                "website": website_entry.get().strip(),
                "username": username_entry.get().strip(),
                "password": password_entry.get().strip()
            }
            save_vault(self.password, {"credentials": self.credentials}, self.vault_path)
            self.render_table()
            win.destroy()
            try:
                self.on_change()
            except Exception:
                pass
            self.resume_timer()

        win.bind("<Return>", lambda e: save())
        ctk.CTkButton(win, text="Save", command=save, font=self.font_bold).pack(pady=10)

    def open_add_window(self):
        # Pause timer during add
        self.pause_timer()
        
        win = ctk.CTkToplevel(self)
        win.configure(bg=ctk.ThemeManager.theme["CTkFrame"]["fg_color"][1])
        self.set_window_icon(win)
        win.title("Add Credential")
        win.geometry("380x450")
        win.resizable(False, False)
        win.lift()
        win.focus_force()
        win.grab_set()
        
        # Resume timer when dialog closes
        def on_close():
            self.resume_timer()
            win.destroy()
        
        win.protocol("WM_DELETE_WINDOW", on_close)

        ctk.CTkLabel(win, text="Website", font=self.font_body).pack(pady=5)
        website_entry = ctk.CTkEntry(win, font=self.font_body)
        website_entry.pack()
        win.after(100, lambda: website_entry.focus())

        ctk.CTkLabel(win, text="Username / Email", font=self.font_body).pack(pady=5)
        username_entry = ctk.CTkEntry(win, font=self.font_body, width=280)
        username_entry.pack()

        ctk.CTkLabel(win, text="Password", font=self.font_body).pack(pady=5)
        password_entry = ctk.CTkEntry(win, show="\u2022", font=self.font_body, width=280)
        password_entry.pack()
        
        # Strength bar (non-blocking)
        strength_frame = ctk.CTkFrame(win, fg_color="transparent")
        strength_frame.pack(pady=5)
        
        # Header with info button
        header_frame = ctk.CTkFrame(strength_frame, fg_color="transparent")
        header_frame.pack(anchor="w", fill="x")
        
        ctk.CTkLabel(header_frame, text="Strength:", font=ctk.CTkFont(size=9)).pack(side="left")
        
        # Info button with tooltip
        info_btn = ctk.CTkButton(header_frame, text="ℹ", width=20, height=20, font=ctk.CTkFont(size=12, weight="bold"), fg_color="#3498db", hover_color="#2980b9", corner_radius=10)
        info_btn.pack(side="left", padx=5)
        
        # Tooltip (initially hidden)
        tooltip = ctk.CTkFrame(win, fg_color="#2c3e50", corner_radius=8, border_width=1, border_color="#3498db")
        ctk.CTkLabel(tooltip, text="Strong Password Tips:\n✓ 12+ characters\n✓ Mix uppercase & lowercase\n✓ Include numbers (0-9)\n✓ Add symbols (!@#$%...)\n✓ Avoid personal info\n✓ Use password generator", font=ctk.CTkFont(size=10), justify="left", text_color="white").pack(padx=10, pady=8)
        
        def show_tooltip(e=None):
            tooltip.place(x=50, y=280, anchor="w")
        def hide_tooltip(e=None):
            tooltip.place_forget()
        
        info_btn.bind("<Enter>", show_tooltip)
        info_btn.bind("<Leave>", hide_tooltip)
        info_btn.configure(command=lambda: None)
        
        bar_container = ctk.CTkFrame(strength_frame, fg_color="#2b2b2b", height=16, width=280, corner_radius=8)
        bar_container.pack(pady=3)
        bar_container.pack_propagate(False)
        
        segments = []
        segment_frame = ctk.CTkFrame(bar_container, fg_color="transparent")
        segment_frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        for i in range(5):
            seg = ctk.CTkFrame(segment_frame, fg_color="#1a1a1a", corner_radius=5)
            seg.pack(side="left", fill="both", expand=True, padx=1)
            segments.append(seg)
        
        strength_label = ctk.CTkLabel(strength_frame, text="", font=ctk.CTkFont(size=10))
        strength_label.pack()
        
        def update_strength(event=None):
            pw = password_entry.get()
            if not pw:
                for seg in segments:
                    seg.configure(fg_color="#1a1a1a")
                strength_label.configure(text="")
                return
            
            result = classify_strength(pw, require_strong=False)
            
            # Update segments - all filled segments use the strength color
            strength_colors = {
                0: '#e74c3c',  # Very Weak - Red
                1: '#e67e22',  # Weak - Orange
                2: '#f39c12',  # Medium - Yellow
                3: '#27ae60',  # Strong - Green
                4: '#16a085'   # Very Strong - Teal
            }
            
            filled = result['score'] + 1
            fill_color = strength_colors[result['score']]
            
            for i, seg in enumerate(segments):
                if i < filled:
                    seg.configure(fg_color=fill_color)
                else:
                    seg.configure(fg_color="#1a1a1a")
            
            # Update label
            strength_label.configure(
                text=f"{result['label']} - {result['entropy']} bits",
                text_color=result['color']
            )
        
        password_entry.bind("<KeyRelease>", update_strength)

        gen_btn = ctk.CTkButton(win, text="Generate Secure Password", command=lambda: self.copy_generated(password_entry), font=self.font_bold)
        gen_btn.pack(pady=5)
        
        # Ensure tooltip stays on top
        tooltip.lift()

        website_entry.bind("<Down>", lambda e: username_entry.focus())
        username_entry.bind("<Up>", lambda e: website_entry.focus())
        username_entry.bind("<Down>", lambda e: password_entry.focus())
        password_entry.bind("<Up>", lambda e: username_entry.focus())

        website_entry.bind("<Return>", lambda e: username_entry.focus())
        username_entry.bind("<Return>", lambda e: password_entry.focus())
        password_entry.bind("<Return>", lambda e: save())

        def save():
            site = website_entry.get().strip()
            user = username_entry.get().strip()
            pw = password_entry.get().strip()

            if not site or not user or not pw:
                messagebox.showerror("Error", "All fields are required.")
                return

            self.credentials.append({
                "website": site,
                "username": user,
                "password": pw
            })
            save_vault(self.password, {"credentials": self.credentials}, self.vault_path)
            self.render_table()
            win.destroy()
            try:
                self.on_change()
            except Exception:
                pass
            self.resume_timer()

        win.bind("<Return>", lambda e: save())
        ctk.CTkButton(win, text="Save", command=save).pack(pady=10)

    def copy_generated(self, entry):
        password = self.generate_password()
        entry.delete(0, "end")
        entry.insert(0, password)
        pyperclip.copy(password)
        self.show_splash("Secure password copied to clipboard \u2714")

    def run_security_test(self):
        """Run security audit on current vault credentials."""
        # Pause inactivity timer during security test
        self.pause_timer()
        
        try:
            # Ask for report name
            dialog = ctk.CTkInputDialog(text="Enter a name for this security report (optional):", title="Security Test")
            report_name = dialog.get_input()
            if report_name is None:  # User cancelled
                self.resume_timer()
                return
            if not report_name:
                report_name = "Security Audit"
            
            # Ask if user wants to provide personal info for PII detection
            response = messagebox.askyesno(
                "Personal Information",
                "Would you like to provide personal information for enhanced security checks?\n\n"
                "This will check if your passwords contain personal data like your name, birthdate, etc.\n\n"
                "This information is only used for scanning and is never saved."
            )
            
            user_info = None
            if response:
                user_info = self.collect_user_info()
                if user_info is None:  # User cancelled
                    self.resume_timer()
                    return
            
            # Run audit in background
            self.show_progress_dialog(report_name, user_info)
        except Exception as e:
            self.resume_timer()
            raise e
    
    def collect_user_info(self):
        """Collect optional user info for PII detection."""
        dialog = ctk.CTkToplevel(self)
        self.set_window_icon(dialog)
        dialog.title("Personal Information (Optional)")
        dialog.geometry("400x420")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.lift()
        dialog.focus_force()
        
        ctk.CTkLabel(dialog, text="Provide information to check for in passwords:", font=self.font_bold).pack(pady=10)
        ctk.CTkLabel(dialog, text="(All fields optional - leave blank to skip)", font=self.font_body, text_color="gray").pack()
        
        ctk.CTkLabel(dialog, text="Full Name:", font=self.font_body).pack(pady=(10, 2))
        name_entry = ctk.CTkEntry(dialog, width=300, font=self.font_body)
        name_entry.pack()
        
        ctk.CTkLabel(dialog, text="Date of Birth (YYYY-MM-DD):", font=self.font_body).pack(pady=(10, 2))
        dob_entry = ctk.CTkEntry(dialog, width=300, font=self.font_body, placeholder_text="1990-01-15")
        dob_entry.pack()
        
        # Auto-format DOB with dashes
        last_formatted = [""]
        
        def format_dob(event):
            # Ignore navigation keys
            if event.keysym in ['Left', 'Right', 'Up', 'Down', 'Home', 'End', 'Tab', 'Shift_L', 'Shift_R', 'Control_L', 'Control_R', 'BackSpace', 'Delete']:
                return
            
            current_text = dob_entry.get()
            
            # Remove all non-digit characters
            digits_only = ''.join(c for c in current_text if c.isdigit())
            
            # Limit to 8 digits
            if len(digits_only) > 8:
                digits_only = digits_only[:8]
            
            # Format as YYYY-MM-DD
            formatted = ""
            if len(digits_only) >= 1:
                formatted = digits_only[:4]
            if len(digits_only) >= 5:
                formatted += "-" + digits_only[4:6]
            if len(digits_only) >= 7:
                formatted += "-" + digits_only[6:8]
            
            # Only update if different from last formatted value
            if formatted != last_formatted[0]:
                last_formatted[0] = formatted
                dob_entry.delete(0, "end")
                dob_entry.insert(0, formatted)
                dob_entry.icursor(len(formatted))
        
        dob_entry.bind("<KeyRelease>", format_dob)
        
        ctk.CTkLabel(dialog, text="Email:", font=self.font_body).pack(pady=(10, 2))
        email_entry = ctk.CTkEntry(dialog, width=300, font=self.font_body)
        email_entry.pack()
        
        ctk.CTkLabel(dialog, text="Phone:", font=self.font_body).pack(pady=(10, 2))
        phone_entry = ctk.CTkEntry(dialog, width=300, font=self.font_body)
        phone_entry.pack()
        
        result = {}
        
        def submit():
            result['name'] = name_entry.get().strip()
            result['dob'] = dob_entry.get().strip()
            result['email'] = email_entry.get().strip()
            result['phone'] = phone_entry.get().strip()
            dialog.destroy()
        
        def cancel():
            result['cancelled'] = True
            dialog.destroy()
        
        # Arrow key navigation
        name_entry.bind("<Down>", lambda e: dob_entry.focus())
        name_entry.bind("<Return>", lambda e: dob_entry.focus())
        
        dob_entry.bind("<Up>", lambda e: name_entry.focus())
        dob_entry.bind("<Down>", lambda e: email_entry.focus())
        dob_entry.bind("<Return>", lambda e: email_entry.focus())
        
        email_entry.bind("<Up>", lambda e: dob_entry.focus())
        email_entry.bind("<Down>", lambda e: phone_entry.focus())
        email_entry.bind("<Return>", lambda e: phone_entry.focus())
        
        phone_entry.bind("<Up>", lambda e: email_entry.focus())
        phone_entry.bind("<Down>", lambda e: submit())
        phone_entry.bind("<Return>", lambda e: submit())
        
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="Submit", command=submit, font=self.font_bold, fg_color="green", hover_color="#006600").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", command=cancel, font=self.font_bold).pack(side="left", padx=5)
        
        dialog.wait_window()
        
        if result.get('cancelled'):
            return None
        
        # Filter out empty fields
        user_info = {k: v for k, v in result.items() if v and k != 'cancelled'}
        return user_info if user_info else None
    
    def show_progress_dialog(self, report_name, user_info):
        """Show progress dialog while running security audit."""
        progress_dialog = ctk.CTkToplevel(self)
        self.set_window_icon(progress_dialog)
        progress_dialog.title("Running Security Test")
        progress_dialog.geometry("400x200")
        progress_dialog.resizable(False, False)
        progress_dialog.grab_set()
        progress_dialog.lift()
        
        ctk.CTkLabel(progress_dialog, text="Analyzing vault security...", font=self.font_title).pack(pady=20)
        
        progress_bar = ctk.CTkProgressBar(progress_dialog, width=300)
        progress_bar.pack(pady=10)
        progress_bar.set(0)
        
        status_label = ctk.CTkLabel(progress_dialog, text="Starting scan...", font=self.font_body)
        status_label.pack(pady=10)
        
        report_result = {}
        
        def run_audit():
            try:
                # Simulate progress updates
                progress_dialog.after(100, lambda: progress_bar.set(0.2))
                progress_dialog.after(200, lambda: status_label.configure(text="Checking for reused passwords..."))
                
                progress_dialog.after(400, lambda: progress_bar.set(0.4))
                progress_dialog.after(500, lambda: status_label.configure(text="Analyzing password strength..."))
                
                progress_dialog.after(700, lambda: progress_bar.set(0.6))
                progress_dialog.after(800, lambda: status_label.configure(text="Detecting personal information..."))
                
                progress_dialog.after(1000, lambda: progress_bar.set(0.8))
                progress_dialog.after(1100, lambda: status_label.configure(text="Finding similar passwords..."))
                
                # Run actual audit
                report = run_security_audit(self.credentials, user_info, report_name)
                report_result['report'] = report
                
                progress_dialog.after(1300, lambda: progress_bar.set(1.0))
                progress_dialog.after(1400, lambda: status_label.configure(text="Complete!"))
                progress_dialog.after(1600, lambda: self.show_report_dialog(report, progress_dialog))
                
            except Exception as e:
                progress_dialog.after(0, lambda: messagebox.showerror("Error", f"Security test failed: {e}"))
                progress_dialog.after(100, lambda: progress_dialog.destroy())
        
        threading.Thread(target=run_audit, daemon=True).start()
    
    def show_report_dialog(self, report, progress_dialog):
        """Show security report summary and save options."""
        progress_dialog.destroy()
        
        # Resume timer after security test completes
        self.resume_timer()
        
        dialog = ctk.CTkToplevel(self)
        self.set_window_icon(dialog)
        dialog.title("Security Test Results")
        dialog.geometry("650x650")
        dialog.resizable(True, True)
        dialog.grab_set()
        dialog.lift()
        
        # Title
        ctk.CTkLabel(dialog, text=f"🔒 {report['report_name']}", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
        # Summary frame
        summary_frame = ctk.CTkFrame(dialog)
        summary_frame.pack(fill="x", padx=20, pady=10)
        
        stats = report['stats']
        ctk.CTkLabel(summary_frame, text="Summary", font=self.font_bold).pack(pady=5)
        ctk.CTkLabel(summary_frame, text=f"Total Credentials: {stats['total_credentials']}", font=self.font_body).pack()
        ctk.CTkLabel(summary_frame, text=f"Reused Passwords: {stats['reused_passwords']}", font=self.font_body, text_color="#FF6B35" if stats['reused_passwords'] > 0 else "white").pack()
        ctk.CTkLabel(summary_frame, text=f"Weak Passwords: {stats['weak_passwords']}", font=self.font_body, text_color="#FF6B35" if stats['weak_passwords'] > 0 else "white").pack()
        ctk.CTkLabel(summary_frame, text=f"PII Matches: {stats['pii_matches']}", font=self.font_body, text_color="#FFA500" if stats['pii_matches'] > 0 else "white").pack()
        ctk.CTkLabel(summary_frame, text=f"Similar Password Groups: {stats['similarity_groups']}", font=self.font_body).pack()
        
        # Recommendations with details
        rec_frame = ctk.CTkScrollableFrame(dialog, height=200)
        rec_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        ctk.CTkLabel(rec_frame, text="Recommendations", font=self.font_bold).pack(pady=5, anchor="w")
        
        # Show detailed recommendations with website names
        findings = report['findings']
        
        # Critical weak passwords
        critical_weak = [w for w in findings['weak_passwords'] if w['strength'] == 'critical']
        if critical_weak:
            ctk.CTkLabel(rec_frame, text="🔴 CRITICAL - Change Immediately:", font=self.font_bold, text_color="#FF4444").pack(anchor="w", pady=(5, 2))
            for item in critical_weak[:5]:
                ctk.CTkLabel(rec_frame, text=f"  • {item['website']} - {', '.join(item['issues'][:2])}", font=self.font_body, wraplength=520, justify="left").pack(anchor="w", padx=10)
        
        # Reused passwords
        if findings['reused_passwords']:
            ctk.CTkLabel(rec_frame, text="🔴 HIGH - Reused Passwords:", font=self.font_bold, text_color="#FF6B35").pack(anchor="w", pady=(5, 2))
            for item in findings['reused_passwords'][:3]:
                sites_str = ", ".join(item['sites'][:3])
                if len(item['sites']) > 3:
                    sites_str += f" (+{len(item['sites'])-3} more)"
                ctk.CTkLabel(rec_frame, text=f"  • Same password on: {sites_str}", font=self.font_body, wraplength=520, justify="left").pack(anchor="w", padx=10)
        
        # PII matches
        if findings['pii_matches']:
            ctk.CTkLabel(rec_frame, text="🟠 HIGH - Contains Personal Info:", font=self.font_bold, text_color="#FFA500").pack(anchor="w", pady=(5, 2))
            for item in findings['pii_matches'][:3]:
                ctk.CTkLabel(rec_frame, text=f"  • {item['website']} - {item['matched_fields'][0] if item['matched_fields'] else 'PII detected'}", font=self.font_body, wraplength=520, justify="left").pack(anchor="w", padx=10)
        
        # Weak passwords (non-critical)
        weak_only = [w for w in findings['weak_passwords'] if w['strength'] == 'weak']
        if weak_only:
            ctk.CTkLabel(rec_frame, text="🟡 MEDIUM - Weak Passwords:", font=self.font_bold, text_color="#FFD700").pack(anchor="w", pady=(5, 2))
            for item in weak_only[:3]:
                ctk.CTkLabel(rec_frame, text=f"  • {item['website']} - Entropy: {item['entropy']} bits", font=self.font_body, wraplength=520, justify="left").pack(anchor="w", padx=10)
        
        # Similar passwords
        if findings['similarity_groups']:
            ctk.CTkLabel(rec_frame, text="🟡 MEDIUM - Similar Passwords:", font=self.font_bold, text_color="#FFD700").pack(anchor="w", pady=(5, 2))
            for item in findings['similarity_groups'][:2]:
                sites_str = ", ".join(item['sites'][:3])
                ctk.CTkLabel(rec_frame, text=f"  • {sites_str}", font=self.font_body, wraplength=520, justify="left").pack(anchor="w", padx=10)
        
        # Strong passwords
        strong_passwords = [w for w in findings['weak_passwords'] if w['strength'] == 'strong'] if 'weak_passwords' in findings else []
        # Also check all credentials for strong ones not in weak list
        all_strong = []
        for cred in self.credentials:
            pw = cred.get('password', '')
            if pw:
                from core.security_audit import classify_password_strength
                strength, entropy, _ = classify_password_strength(pw)
                if strength == 'strong':
                    all_strong.append({'website': cred.get('website', 'Unknown'), 'entropy': round(entropy, 2)})
        
        if all_strong:
            ctk.CTkLabel(rec_frame, text="🟢 GOOD - Strong Passwords:", font=self.font_bold, text_color="#00FF00").pack(anchor="w", pady=(5, 2))
            for item in all_strong[:5]:
                ctk.CTkLabel(rec_frame, text=f"  • {item['website']} - Entropy: {item['entropy']} bits", font=self.font_body, wraplength=520, justify="left").pack(anchor="w", padx=10)
        
        # If no issues
        if not any([critical_weak, findings['reused_passwords'], findings['pii_matches'], weak_only, findings['similarity_groups']]):
            ctk.CTkLabel(rec_frame, text="✅ No major security issues detected!", font=self.font_bold, text_color="#00FF00").pack(anchor="w", pady=5)
        
        # Warning
        warning_frame = ctk.CTkFrame(dialog, fg_color="#3d3d3d")
        warning_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(warning_frame, text="⚠️ Reports may contain sensitive information. Store securely.", font=self.font_body, text_color="#FFA500").pack(pady=5)
        
        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        def save_pdf():
            filepath = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                initialfile=f"PassGuard_Security_Report_{report['report_name'].replace(' ', '_')}.pdf"
            )
            if filepath:
                try:
                    save_report_pdf(report, filepath)
                    messagebox.showinfo("Success", f"PDF report saved to:\n{filepath}\n\nThe report includes:\n• Executive summary\n• Detailed findings\n• Priority recommendations\n• PassGuard watermark")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save PDF report: {e}\n\nMake sure reportlab is installed:\npip install reportlab")
        
        ctk.CTkButton(btn_frame, text="💾 Save Report (PDF)", command=save_pdf, font=self.font_bold, fg_color="#2ecc71", hover_color="#27ae60", width=180).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Close", command=dialog.destroy, font=self.font_bold, width=100).pack(side="left", padx=5)
    
    def show_browser_extension_setup(self):
        """Show browser extension setup dialog with token copy."""
        self.pause_timer()
        
        dialog = ctk.CTkToplevel(self)
        self.set_window_icon(dialog)
        dialog.title("Browser Extension Setup")
        dialog.geometry("600x650")
        dialog.resizable(False, False)
        dialog.grab_set()
        
        # Header
        header = ctk.CTkFrame(dialog, fg_color="#1a1a1a", corner_radius=12)
        header.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(
            header,
            text="🌐 Browser Autofill Setup",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#16a085"
        ).pack(pady=15)
        
        # Content
        content = ctk.CTkFrame(dialog, fg_color="#1e1e1e", corner_radius=12)
        content.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        
        # Token section
        token_frame = ctk.CTkFrame(content, fg_color="#2b2b2b", corner_radius=10)
        token_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(
            token_frame,
            text="🔑 Step 1: Copy Authentication Token",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))
        
        ctk.CTkLabel(
            token_frame,
            text="This token allows your browser to securely access credentials.\nIt's generated once and stored safely.",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        ).pack(anchor="w", padx=15, pady=(0, 10))
        
        # Copy token button
        def copy_token():
            if self.autofill_server:
                token = self.autofill_server.get_token()
                pyperclip.copy(token)
                copy_btn.configure(text="✓ Token Copied!", fg_color="#27ae60")
                dialog.after(2000, lambda: copy_btn.configure(text="📋 Copy Token", fg_color="#16a085"))
                messagebox.showinfo("Token Copied", "Authentication token copied to clipboard!\n\nPaste it in the browser extension popup.")
            else:
                messagebox.showerror("Error", "Autofill server not running")
        
        copy_btn = ctk.CTkButton(
            token_frame,
            text="📋 Copy Token",
            command=copy_token,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#16a085",
            hover_color="#138d75",
            width=500,
            height=50
        )
        copy_btn.pack(padx=15, pady=(0, 15))
        
        # Instructions
        inst_frame = ctk.CTkFrame(content, fg_color="#2b2b2b", corner_radius=10)
        inst_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        ctk.CTkLabel(
            inst_frame,
            text="📋 Step 2: Install & Configure Extension",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))
        
        instructions = [
            "1️⃣ Open Chrome/Edge and go to chrome://extensions/",
            "2️⃣ Enable 'Developer mode' (toggle in top-right)",
            "3️⃣ Click 'Load unpacked' and select browser_extension folder",
            "4️⃣ Click the PassGuard extension icon in your toolbar",
            "5️⃣ Paste the token you copied and click 'Save Token'",
            "6️⃣ Status should turn green ✅",
            "",
            "✨ Step 3: Use Autofill",
            "• Visit any login page (e.g., reddit.com, gmail.com)",
            "• Look for '🔐 Fill with PassGuard' button",
            "• Click it to autofill your credentials",
            "• Done! No need to configure again"
        ]
        
        for inst in instructions:
            if inst.startswith("✨"):
                ctk.CTkLabel(
                    inst_frame,
                    text=inst,
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color="#16a085"
                ).pack(anchor="w", padx=15, pady=(10, 5))
            elif inst == "":
                ctk.CTkLabel(inst_frame, text="").pack(pady=5)
            else:
                ctk.CTkLabel(
                    inst_frame,
                    text=inst,
                    font=ctk.CTkFont(size=12),
                    text_color="white" if inst.startswith("•") else "#e0e0e0"
                ).pack(anchor="w", padx=20 if inst.startswith("•") else 15, pady=2)
        
        # Close button
        ctk.CTkButton(
            content,
            text="Close",
            command=lambda: [dialog.destroy(), self.resume_timer()],
            font=ctk.CTkFont(size=14, weight="bold"),
            width=200,
            height=40
        ).pack(pady=(0, 15))
        
        dialog.protocol("WM_DELETE_WINDOW", lambda: [dialog.destroy(), self.resume_timer()])
    
    def export_vault_dialog(self):
        """Open dialog to export current vault."""
        self.pause_timer()
        
        dialog = ctk.CTkToplevel(self)
        self.set_window_icon(dialog)
        dialog.title("Export Vault")
        dialog.geometry("500x400")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.lift()
        dialog.focus_force()
        
        def on_close():
            self.resume_timer()
            dialog.destroy()
        
        dialog.protocol("WM_DELETE_WINDOW", on_close)
        
        ctk.CTkLabel(dialog, text="📤 Export Vault", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=15)
        
        # Check if keypair exists
        if not keypair_exists():
            ctk.CTkLabel(dialog, text="⚠️ No encryption keypair found", font=ctk.CTkFont(size=13, weight="bold"), text_color="#e67e22").pack(pady=10)
            ctk.CTkLabel(dialog, text="A keypair will be generated to secure your exports.\nThis is a one-time setup.", wraplength=400).pack(pady=5)
            
            def generate_keys():
                try:
                    save_keypair(self.password)
                    messagebox.showinfo("Success", "Encryption keypair generated successfully!")
                    dialog.destroy()
                    self.export_vault_dialog()  # Reopen dialog
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to generate keypair: {e}")
            
            ctk.CTkButton(dialog, text="Generate Keypair", command=generate_keys, font=self.font_bold, width=200).pack(pady=15)
            ctk.CTkButton(dialog, text="Cancel", command=on_close, font=self.font_bold, width=100).pack(pady=5)
            return
        
        # Show fingerprint
        fingerprint = get_public_key_fingerprint()
        ctk.CTkLabel(dialog, text=f"Your Key ID: {fingerprint}", font=ctk.CTkFont(size=10), text_color="gray").pack()
        
        # Export options
        info_frame = ctk.CTkFrame(dialog, fg_color="#2b2b2b", corner_radius=10)
        info_frame.pack(padx=20, pady=15, fill="x")
        
        ctk.CTkLabel(info_frame, text="Export Options:", font=self.font_bold).pack(anchor="w", padx=15, pady=(10, 5))
        
        export_type = ctk.StringVar(value="self")
        
        ctk.CTkRadioButton(info_frame, text="Backup for myself (encrypted with my key)", variable=export_type, value="self", font=self.font_body).pack(anchor="w", padx=30, pady=5)
        ctk.CTkRadioButton(info_frame, text="Share with another user (requires their public key)", variable=export_type, value="other", font=self.font_body).pack(anchor="w", padx=30, pady=5)
        
        info_frame.pack_configure(pady=(10, 15))
        
        # Recipient key selection
        recipient_key_path = [None]
        recipient_label = ctk.CTkLabel(dialog, text="", font=ctk.CTkFont(size=10), text_color="gray")
        recipient_label.pack()
        
        def select_recipient_key():
            path = filedialog.askopenfilename(
                title="Select Recipient's Public Key",
                filetypes=[("PEM files", "*.pem"), ("All files", "*.*")]
            )
            if path:
                recipient_key_path[0] = path
                recipient_label.configure(text=f"Recipient: {os.path.basename(path)}")
        
        select_key_btn = ctk.CTkButton(dialog, text="📁 Select Recipient's Public Key", command=select_recipient_key, font=self.font_body, width=250)
        
        def update_ui(*args):
            if export_type.get() == "other":
                select_key_btn.pack(pady=5)
                recipient_label.pack()
            else:
                select_key_btn.pack_forget()
                recipient_label.pack_forget()
                recipient_key_path[0] = None
        
        export_type.trace_add("write", update_ui)
        update_ui()
        
        # Export button
        def do_export():
            try:
                if export_type.get() == "other" and not recipient_key_path[0]:
                    messagebox.showerror("Error", "Please select recipient's public key")
                    return
                
                vault_data = {"credentials": self.credentials}
                vault_label = os.path.basename(self.vault_path).replace('.dat', '')
                
                export_path = export_vault(
                    vault_data,
                    self.password,
                    vault_label,
                    recipient_key_path[0]
                )
                
                recipient_name = "yourself" if export_type.get() == "self" else os.path.basename(recipient_key_path[0]).replace('.pem', '')
                
                messagebox.showinfo(
                    "Export Successful",
                    f"Vault successfully exported!\n\n"
                    f"File: {os.path.basename(export_path)}\n"
                    f"Location: {os.path.dirname(export_path)}\n"
                    f"Encrypted for: {recipient_name}\n\n"
                    f"This file can only be decrypted by the recipient's private key."
                )
                on_close()
                
            except Exception as e:
                messagebox.showerror("Export Failed", f"Failed to export vault:\n{e}")
        
        ctk.CTkButton(dialog, text="📤 Export Vault", command=do_export, font=self.font_bold, fg_color="#3498db", hover_color="#2980b9", width=200, height=40).pack(pady=20)
        ctk.CTkButton(dialog, text="Cancel", command=on_close, font=self.font_body, width=100).pack()
    
    def import_vault_dialog(self):
        """Open dialog to import a vault from .pvgx file."""
        self.pause_timer()
        
        # Select import file
        import_file = filedialog.askopenfilename(
            title="Select Vault Export File",
            filetypes=[("PassGuard Export", "*.pvgx"), ("All files", "*.*")]
        )
        
        if not import_file:
            self.resume_timer()
            return
        
        dialog = ctk.CTkToplevel(self)
        self.set_window_icon(dialog)
        dialog.title("Import Vault")
        dialog.geometry("450x350")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.lift()
        dialog.focus_force()
        
        def on_close():
            self.resume_timer()
            dialog.destroy()
        
        dialog.protocol("WM_DELETE_WINDOW", on_close)
        
        ctk.CTkLabel(dialog, text="📥 Import Vault", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=15)
        ctk.CTkLabel(dialog, text=f"File: {os.path.basename(import_file)}", font=ctk.CTkFont(size=10), text_color="gray").pack()
        
        # Signature verification option
        verify_frame = ctk.CTkFrame(dialog, fg_color="#2b2b2b", corner_radius=10)
        verify_frame.pack(padx=20, pady=15, fill="x")
        
        ctk.CTkLabel(verify_frame, text="Signature Verification (Optional):", font=self.font_bold).pack(anchor="w", padx=15, pady=(10, 5))
        ctk.CTkLabel(verify_frame, text="Verify sender's identity by selecting their public key", font=ctk.CTkFont(size=10), text_color="gray", wraplength=380).pack(anchor="w", padx=15)
        
        sender_key_path = [None]
        sender_label = ctk.CTkLabel(verify_frame, text="No verification", font=ctk.CTkFont(size=10), text_color="gray")
        sender_label.pack(padx=15, pady=5)
        
        def select_sender_key():
            path = filedialog.askopenfilename(
                title="Select Sender's Public Key",
                filetypes=[("PEM files", "*.pem"), ("All files", "*.*")]
            )
            if path:
                sender_key_path[0] = path
                sender_label.configure(text=f"Verify with: {os.path.basename(path)}", text_color="white")
        
        ctk.CTkButton(verify_frame, text="📁 Select Sender's Public Key", command=select_sender_key, font=self.font_body, width=220).pack(pady=5, padx=15)
        verify_frame.pack_configure(pady=(10, 15))
        
        # Import button
        def do_import():
            try:
                vault_data, vault_label = import_vault(import_file, self.password, sender_key_path[0])
                
                # Save imported vault
                from core.vault import create_vault, save_vault_label
                import uuid
                
                rand_name = uuid.uuid4().hex[:10] + ".dat"
                new_vault_path = os.path.join("vaults", rand_name)
                
                # Prompt for new label
                label_dialog = ctk.CTkInputDialog(text=f"Enter label for imported vault:", title="Vault Label")
                label_dialog.geometry("400x150")
                new_label = label_dialog.get_input()
                
                if not new_label:
                    new_label = vault_label + "_imported"
                
                # Save vault
                save_vault(self.password, vault_data, new_vault_path)
                save_vault_label(rand_name, new_label)
                
                # Refresh parent unlock dialog if it exists
                if self.parent and hasattr(self.parent, 'refresh_dropdown'):
                    self.parent.refresh_dropdown()
                
                messagebox.showinfo(
                    "Import Successful",
                    f"Vault '{new_label}' imported successfully!\n\n"
                    f"Credentials: {len(vault_data.get('credentials', []))}\n\n"
                    f"The vault is now available in your vault list."
                )
                
                on_close()
                
            except ValueError as e:
                messagebox.showerror("Import Failed", f"Failed to import vault:\n{e}")
            except Exception as e:
                messagebox.showerror("Import Failed", f"Unexpected error during import:\n{e}")
        
        ctk.CTkButton(dialog, text="📥 Import Vault", command=do_import, font=self.font_bold, fg_color="#9b59b6", hover_color="#8e44ad", width=200, height=40).pack(pady=20)
        ctk.CTkButton(dialog, text="Cancel", command=on_close, font=self.font_body, width=100).pack()
    
    def open_breach_check(self):
        """Open HIBP breach check dialog."""
        self.pause_timer()
        
        try:
            dialog = SecurityCheckDialog(
                self,
                self.credentials,
                self.password,
                on_edit_callback=self.edit_credential
            )
            dialog.grab_set()
            dialog.lift()
            dialog.focus_force()
            
            # Resume timer when dialog closes
            def on_close():
                self.resume_timer()
                try:
                    dialog.destroy()
                except:
                    pass
            
            dialog.protocol("WM_DELETE_WINDOW", on_close)
            
        except Exception as e:
            self.resume_timer()
            messagebox.showerror("Error", f"Failed to open breach check:\n{e}")
    
    def _minimize_to_tray(self):
        """Minimize window to system tray"""
        try:
            self.withdraw()
            if self.parent:
                self.parent.withdraw()
        except Exception as e:
            print(f"[MainWindow] Failed to minimize to tray: {e}")
        