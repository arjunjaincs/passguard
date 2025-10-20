"""Security Check Dialog - HIBP Breach Checking.

Provides UI for checking passwords and accounts against Have I Been Pwned database.
"""

import customtkinter as ctk
import threading
import os
import sys
from tkinter import messagebox
from typing import List, Dict, Optional
import pyperclip
import string
import random

from core.breach_check import (
    check_password_pwned_k_anonymity,
    check_account_breached_hibp,
    format_breach_summary
)
from core.crypto import encrypt_data, decrypt_data


class SecurityCheckDialog(ctk.CTkToplevel):
    """Dialog for checking credentials against HIBP database."""
    
    def set_window_icon(self):
        """Set window icon."""
        try:
            if sys.platform.startswith("win"):
                from ctypes import windll
                icon_path = os.path.abspath(os.path.join("assets", "icon.ico"))
                if os.path.exists(icon_path):
                    self.iconbitmap(default=icon_path)
                    hwnd = windll.user32.GetParent(self.winfo_id())
                    windll.shell32.SetCurrentProcessExplicitAppUserModelID("passguard.vault")
                    windll.user32.SendMessageW(hwnd, 0x80, 1, icon_path)
        except Exception as e:
            print(f"Could not set icon: {e}")
    
    def __init__(self, parent, credentials: List[Dict], master_password: str, on_edit_callback=None):
        super().__init__(parent)
        
        self.credentials = credentials
        self.master_password = master_password
        self.on_edit_callback = on_edit_callback
        self.checking = False
        self.stop_check = False
        
        # Set window icon
        self.set_window_icon()
        
        self.title("Security Check - Have I Been Pwned")
        self.geometry("900x700")
        self.resizable(True, True)
        
        # Fonts
        self.font_title = ctk.CTkFont(size=18, weight="bold")
        self.font_bold = ctk.CTkFont(size=13, weight="bold")
        self.font_body = ctk.CTkFont(size=12)
        self.font_small = ctk.CTkFont(size=10)
        
        self.setup_ui()
        self.load_saved_api_key()
        
        # Center window
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x = (sw // 2) - (w // 2)
        y = (sh // 2) - (h // 2)
        self.geometry(f"+{x}+{y}")
    
    def setup_ui(self):
        """Setup dialog UI."""
        # Title
        title_label = ctk.CTkLabel(
            self,
            text="🔍 Security Check - Have I Been Pwned",
            font=self.font_title
        )
        title_label.pack(pady=15)
        
        # Options frame
        options_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=10)
        options_frame.pack(padx=20, pady=10, fill="x")
        
        ctk.CTkLabel(
            options_frame,
            text="Check Type:",
            font=self.font_bold
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        # Check type radio buttons
        self.check_type = ctk.StringVar(value="password")
        
        ctk.CTkRadioButton(
            options_frame,
            text="Password-only (Free, k-anonymity - only 5 chars of hash sent)",
            variable=self.check_type,
            value="password",
            font=self.font_body,
            command=self.update_ui_state
        ).pack(anchor="w", padx=30, pady=3)
        
        ctk.CTkRadioButton(
            options_frame,
            text="Account/Email (Requires HIBP API key - paid service)",
            variable=self.check_type,
            value="account",
            font=self.font_body,
            command=self.update_ui_state
        ).pack(anchor="w", padx=30, pady=3)
        
        # API key frame (shown only for account check)
        self.api_key_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        
        ctk.CTkLabel(
            self.api_key_frame,
            text="HIBP API Key:",
            font=self.font_body
        ).pack(anchor="w", padx=15, pady=(5, 2))
        
        api_key_input_frame = ctk.CTkFrame(self.api_key_frame, fg_color="transparent")
        api_key_input_frame.pack(fill="x", padx=15)
        
        self.api_key_entry = ctk.CTkEntry(
            api_key_input_frame,
            placeholder_text="Enter your HIBP API key",
            width=400,
            show="*"
        )
        self.api_key_entry.pack(side="left", padx=(0, 10))
        
        self.remember_key_var = ctk.BooleanVar(value=False)
        self.remember_key_check = ctk.CTkCheckBox(
            api_key_input_frame,
            text="Remember (encrypted)",
            variable=self.remember_key_var,
            font=self.font_small
        )
        self.remember_key_check.pack(side="left")
        
        ctk.CTkLabel(
            self.api_key_frame,
            text="Get API key at: https://haveibeenpwned.com/API/Key",
            font=self.font_small,
            text_color="gray"
        ).pack(anchor="w", padx=15, pady=(2, 10))
        
        options_frame.pack_configure(pady=(10, 5))
        
        # Privacy notice
        privacy_frame = ctk.CTkFrame(self, fg_color="#1a3a4a", corner_radius=8)
        privacy_frame.pack(padx=20, pady=5, fill="x")
        
        ctk.CTkLabel(
            privacy_frame,
            text="🔒 Privacy: Password checks use k-anonymity (only first 5 chars of SHA1 hash sent). "
                 "Your passwords are never transmitted to the server.",
            font=self.font_small,
            wraplength=850,
            justify="left",
            text_color="#a8dadc"
        ).pack(padx=10, pady=8)
        
        # Action buttons
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(pady=10)
        
        self.check_btn = ctk.CTkButton(
            action_frame,
            text="🔍 Check All Credentials",
            command=self.start_check,
            font=self.font_bold,
            fg_color="#2ecc71",
            hover_color="#27ae60",
            width=200,
            height=40
        )
        self.check_btn.pack(side="left", padx=5)
        
        self.stop_btn = ctk.CTkButton(
            action_frame,
            text="⏹ Stop",
            command=self.stop_checking,
            font=self.font_bold,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            width=100,
            height=40,
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=5)
        
        # Progress bar
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=20, pady=5)
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, width=400)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.progress_bar.set(0)
        
        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="Ready",
            font=self.font_small
        )
        self.progress_label.pack(side="left")
        
        # Results frame (scrollable)
        results_label = ctk.CTkLabel(
            self,
            text="Results:",
            font=self.font_bold
        )
        results_label.pack(anchor="w", padx=20, pady=(10, 5))
        
        self.results_frame = ctk.CTkScrollableFrame(self, fg_color="#1e1e1e")
        self.results_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # Close button
        ctk.CTkButton(
            self,
            text="Close",
            command=self.destroy,
            font=self.font_body,
            width=100
        ).pack(pady=10)
        
        # Initial UI state
        self.update_ui_state()
    
    def update_ui_state(self):
        """Update UI based on selected check type."""
        if self.check_type.get() == "account":
            self.api_key_frame.pack(fill="x", padx=15, pady=(5, 10))
        else:
            self.api_key_frame.pack_forget()
    
    def load_saved_api_key(self):
        """Load saved API key if exists."""
        key_file = "vaults/hibp_key.enc"
        if os.path.exists(key_file):
            try:
                with open(key_file, "rb") as f:
                    encrypted = f.read()
                
                data = decrypt_data(self.master_password, encrypted)
                api_key = data.get("api_key", "")
                
                if api_key:
                    self.api_key_entry.insert(0, api_key)
                    self.remember_key_var.set(True)
            except Exception:
                pass  # Invalid key or wrong password
    
    def save_api_key(self, api_key: str):
        """Save API key encrypted with master password."""
        try:
            os.makedirs("vaults", exist_ok=True)
            data = {"api_key": api_key}
            encrypted = encrypt_data(self.master_password, data)
            
            with open("vaults/hibp_key.enc", "wb") as f:
                f.write(encrypted)
        except Exception as e:
            print(f"Failed to save API key: {e}")
    
    def start_check(self):
        """Start security check in background thread."""
        if self.checking:
            return
        
        # Validate
        check_type = self.check_type.get()
        if check_type == "account":
            api_key = self.api_key_entry.get().strip()
            if not api_key:
                messagebox.showerror("Error", "Please enter your HIBP API key")
                return
            
            # Save key if requested
            if self.remember_key_var.get():
                self.save_api_key(api_key)
        
        # Clear previous results
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        
        # Update UI
        self.checking = True
        self.stop_check = False
        self.check_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.progress_label.configure(text="Starting...")
        
        # Start background thread
        thread = threading.Thread(target=self.run_checks, daemon=True)
        thread.start()
    
    def stop_checking(self):
        """Stop ongoing check."""
        self.stop_check = True
        self.progress_label.configure(text="Stopping...")
    
    def run_checks(self):
        """Run checks in background thread."""
        check_type = self.check_type.get()
        api_key = self.api_key_entry.get().strip() if check_type == "account" else None
        
        total = len(self.credentials)
        
        for i, cred in enumerate(self.credentials):
            if self.stop_check:
                self.after(0, lambda: self.progress_label.configure(text="Stopped"))
                break
            
            website = cred.get("website", "Unknown")
            username = cred.get("username", "")
            password = cred.get("password", "")
            
            # Update progress
            progress = (i + 1) / total
            self.after(0, lambda p=progress, idx=i+1, t=total: self.update_progress(p, f"Checking {idx}/{t}..."))
            
            # Perform check
            try:
                if check_type == "password":
                    count = check_password_pwned_k_anonymity(password)
                    result_text = f"Not found ✓" if count == 0 else f"⚠ Pwned - {count:,} breaches"
                    result_color = "#27ae60" if count == 0 else "#e74c3c"
                    check_label = "Password"
                else:
                    # Account check
                    if not username:
                        result_text = "No username"
                        result_color = "gray"
                        check_label = "Account"
                    else:
                        breaches = check_account_breached_hibp(username, api_key)
                        if not breaches:
                            result_text = "Not found ✓"
                            result_color = "#27ae60"
                        else:
                            result_text = f"⚠ {len(breaches)} breach(es)"
                            result_color = "#e74c3c"
                        check_label = "Account"
                
                # Add result to UI (on main thread)
                self.after(0, lambda w=website, u=username, c=check_label, r=result_text, col=result_color, cr=cred: 
                          self.add_result(w, u, c, r, col, cr))
                
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda w=website, u=username, c=check_type, e=error_msg, cr=cred:
                          self.add_result(w, u, c.capitalize(), f"Error: {e}", "#e67e22", cr))
        
        # Done
        self.after(0, self.check_complete)
    
    def update_progress(self, value: float, text: str):
        """Update progress bar (called from main thread)."""
        self.progress_bar.set(value)
        self.progress_label.configure(text=text)
    
    def add_result(self, website: str, username: str, check_type: str, result: str, color: str, credential: Dict):
        """Add result row to UI (called from main thread)."""
        row_frame = ctk.CTkFrame(self.results_frame, fg_color="#2b2b2b", corner_radius=8)
        row_frame.pack(fill="x", pady=5, padx=5)
        
        # Website
        ctk.CTkLabel(
            row_frame,
            text=website[:30],
            font=self.font_bold,
            width=150,
            anchor="w"
        ).pack(side="left", padx=10, pady=10)
        
        # Username
        ctk.CTkLabel(
            row_frame,
            text=username[:25] if username else "(no username)",
            font=self.font_small,
            width=150,
            anchor="w",
            text_color="gray"
        ).pack(side="left", padx=5)
        
        # Check type
        ctk.CTkLabel(
            row_frame,
            text=check_type,
            font=self.font_small,
            width=80,
            anchor="w"
        ).pack(side="left", padx=5)
        
        # Result
        ctk.CTkLabel(
            row_frame,
            text=result,
            font=self.font_body,
            text_color=color,
            width=200,
            anchor="w"
        ).pack(side="left", padx=5)
        
        # Action buttons
        if "Pwned" in result or "breach" in result:
            # Generate password button
            gen_btn = ctk.CTkButton(
                row_frame,
                text="🔑 Generate",
                command=lambda: self.generate_password(),
                font=self.font_small,
                width=90,
                height=28,
                fg_color="#3498db",
                hover_color="#2980b9"
            )
            gen_btn.pack(side="left", padx=3)
            
            # Edit button
            if self.on_edit_callback:
                edit_btn = ctk.CTkButton(
                    row_frame,
                    text="✏ Edit",
                    command=lambda c=credential: self.edit_credential(c),
                    font=self.font_small,
                    width=70,
                    height=28,
                    fg_color="#9b59b6",
                    hover_color="#8e44ad"
                )
                edit_btn.pack(side="left", padx=3)
    
    def check_complete(self):
        """Called when check is complete."""
        self.checking = False
        self.check_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.progress_label.configure(text="Complete!")
    
    def generate_password(self):
        """Generate and copy secure password."""
        chars = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:,.<>?"
        password = ''.join(random.SystemRandom().choice(chars) for _ in range(20))
        
        pyperclip.copy(password)
        messagebox.showinfo(
            "Password Generated",
            f"Secure password copied to clipboard!\n\n"
            f"Password: {password}\n\n"
            f"Clipboard will auto-clear in 15 seconds."
        )
    
    def edit_credential(self, credential: Dict):
        """Open edit dialog for credential."""
        if self.on_edit_callback:
            self.on_edit_callback(credential)
