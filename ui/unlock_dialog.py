import customtkinter as ctk
import os
import sys
import uuid
from core.vault import VAULT_PATH, create_vault, load_vault_labels, save_vault_label, delete_vault_label
from core.strength import classify_strength, get_strength_requirements


class UnlockDialog(ctk.CTk):
    def __init__(self, unlock_callback, create_callback, app=None):
        super().__init__()
        self.unlock_callback = unlock_callback
        self.create_callback = create_callback
        self.app = app  # Reference to main app for tray integration
        self._focus_after_id = None

        self.title("PassGuard - Vault Login")
        self.geometry("500x600")
        self.resizable(False, False)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Set window icon
        icon_path = os.path.join("assets", "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(default=icon_path)
            except Exception as e:
                print(f"Failed to set unlock window icon: {e}")

        self.create_widgets()
        
        # Handle close button for tray
        if self.app and hasattr(self.app, 'tray_app') and self.app.tray_app:
            self.protocol("WM_DELETE_WINDOW", self._minimize_to_tray)
    
    def set_window_icon(self, win):
        """Set window icon for dialog boxes."""
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
    
    def _minimize_to_tray(self):
        """Minimize to system tray instead of closing"""
        try:
            self.withdraw()
        except Exception as e:
            print(f"[UnlockDialog] Failed to minimize to tray: {e}")

    def create_widgets(self):
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=15)
        header_frame.pack(fill="x", padx=25, pady=20)
        
        ctk.CTkLabel(
            header_frame,
            text="🔐 PassGuard",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color="#3498db"
        ).pack(pady=20)
        
        ctk.CTkLabel(
            header_frame,
            text="Secure Password Manager",
            font=ctk.CTkFont(size=13),
            text_color="gray"
        ).pack(pady=(0, 15))

        # Main content frame
        content_frame = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=15)
        content_frame.pack(fill="both", expand=True, padx=25, pady=(0, 20))
        
        # Vault selection
        ctk.CTkLabel(
            content_frame,
            text="📁 Select Vault",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        ).pack(anchor="w", padx=25, pady=(25, 8))
        
        self.vault_labels = load_vault_labels()
        self.vault_list = list(self.vault_labels.values())
        self.label_to_filename = {v: k for k, v in self.vault_labels.items()}

        self.dropdown = ctk.CTkOptionMenu(
            content_frame,
            values=["Select Profile"] + self.vault_list,
            command=self.select_vault,
            width=400,
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color="#2b2b2b",
            button_color="#3498db",
            button_hover_color="#2980b9"
        )
        self.dropdown.pack(padx=25, pady=(0, 20))
        self.dropdown.set("Select Profile")
        self.selected_vault = ""

        # Password entry
        ctk.CTkLabel(
            content_frame,
            text="🔑 Master Password",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        ).pack(anchor="w", padx=25, pady=(0, 8))

        self.password_entry = ctk.CTkEntry(
            content_frame,
            show="•",
            width=400,
            height=40,
            font=ctk.CTkFont(size=13),
            placeholder_text="Enter your master password..."
        )
        self.password_entry.pack(padx=25, pady=(0, 20))
        self._focus_after_id = self.after(100, lambda: self.password_entry.focus())

        # Unlock button
        self.unlock_btn = ctk.CTkButton(
            content_frame,
            text="🔓 Unlock Vault",
            command=self.try_unlock,
            width=400,
            height=50,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#2ecc71",
            hover_color="#27ae60"
        )
        self.unlock_btn.pack(padx=25, pady=(0, 15))

        # Divider
        ctk.CTkLabel(
            content_frame,
            text="────────── or ──────────",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        ).pack(pady=15)

        # Action buttons
        button_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        button_frame.pack(pady=(0, 20))
        
        self.create_vault_btn = ctk.CTkButton(
            button_frame,
            text="➕ Create New Vault",
            command=self.open_create_window,
            width=190,
            height=45,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#3498db",
            hover_color="#2980b9"
        )
        self.create_vault_btn.pack(side="left", padx=5)
        
        self.delete_vault_btn = ctk.CTkButton(
            button_frame,
            text="🗑️ Delete Vault",
            command=self.open_delete_window,
            width=190,
            height=45,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#e74c3c",
            hover_color="#c0392b"
        )
        self.delete_vault_btn.pack(side="left", padx=5)

        # Status label
        self.status_label = ctk.CTkLabel(
            content_frame,
            text="",
            text_color="#e74c3c",
            wraplength=400,
            justify="center",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(pady=(0, 15))

        self.bind("<Return>", lambda e: self.try_unlock())

    def select_vault(self, label):
        self.selected_vault = self.label_to_filename.get(label, "")

    def try_unlock(self):
        password = self.password_entry.get().strip()
        if password and self.selected_vault:
            path = os.path.join("vaults", self.selected_vault)
            self.unlock_callback(password, self.status_label, path)

    def open_create_window(self):
        win = ctk.CTkToplevel(self)
        self.set_window_icon(win)
        win.title("Create New Vault")
        win.geometry("550x750")
        win.resizable(False, False)
        win.grab_set()
        win.lift()
        win.focus_force()
        
        # Header
        header = ctk.CTkFrame(win, fg_color="#1a1a1a", corner_radius=12)
        header.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(
            header,
            text="➕ Create New Vault",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#3498db"
        ).pack(pady=15)
        
        # Content frame
        content = ctk.CTkFrame(win, fg_color="#1e1e1e", corner_radius=12)
        content.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        # Vault name
        ctk.CTkLabel(
            content,
            text="📝 Vault Name",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        ).pack(anchor="w", padx=20, pady=(20, 5))
        
        name_entry = ctk.CTkEntry(
            content,
            width=480,
            height=40,
            font=ctk.CTkFont(size=13),
            placeholder_text="Enter a name for your vault..."
        )
        name_entry.pack(padx=20, pady=(0, 15))
        win.after(100, lambda: name_entry.focus())

        # Master password
        ctk.CTkLabel(
            content,
            text="🔑 Master Password",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        ).pack(anchor="w", padx=20, pady=(0, 5))
        
        pass1_entry = ctk.CTkEntry(
            content,
            show="•",
            width=480,
            height=40,
            font=ctk.CTkFont(size=13),
            placeholder_text="Create a strong master password..."
        )
        pass1_entry.pack(padx=20, pady=(0, 10))

        # Strength bar with gradient effect
        strength_frame = ctk.CTkFrame(content, fg_color="transparent")
        strength_frame.pack(pady=5, padx=20, fill="x")
        
        ctk.CTkLabel(
            strength_frame,
            text="Password Strength:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", pady=(0, 5))
        
        # Multi-segment strength bar
        bar_container = ctk.CTkFrame(strength_frame, fg_color="#2b2b2b", height=24, corner_radius=12)
        bar_container.pack(fill="x", pady=5)
        bar_container.pack_propagate(False)
        
        # Create 5 segments for visual appeal
        segments = []
        segment_frame = ctk.CTkFrame(bar_container, fg_color="transparent")
        segment_frame.pack(fill="both", expand=True, padx=3, pady=3)
        
        for i in range(5):
            seg = ctk.CTkFrame(segment_frame, fg_color="#1a1a1a", corner_radius=8)
            seg.pack(side="left", fill="both", expand=True, padx=1)
            segments.append(seg)
        
        strength_label = ctk.CTkLabel(
            strength_frame,
            text="",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        strength_label.pack(pady=3)
        
        entropy_label = ctk.CTkLabel(
            strength_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        entropy_label.pack()

        # Requirements checklist
        req_frame = ctk.CTkFrame(content, fg_color="#2b2b2b", corner_radius=10)
        req_frame.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(
            req_frame,
            text="✓ Requirements:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        req_labels = {}
        requirements = [
            ("length", "✗ At least 8 characters (12+ recommended)"),
            ("classes", "✗ At least 3 character types"),
            ("entropy", "✗ Minimum 60 bits entropy"),
            ("no_personal", "✗ No personal information")
        ]
        
        for key, text in requirements:
            lbl = ctk.CTkLabel(
                req_frame,
                text=text,
                font=ctk.CTkFont(size=11),
                text_color="#e74c3c"
            )
            lbl.pack(anchor="w", padx=20, pady=3)
            req_labels[key] = lbl
        
        ctk.CTkLabel(req_frame, text="").pack(pady=3)  # Spacer

        # Confirm password
        ctk.CTkLabel(
            content,
            text="🔒 Confirm Password",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        ).pack(anchor="w", padx=20, pady=(10, 5))
        
        pass2_entry = ctk.CTkEntry(
            content,
            show="•",
            width=480,
            height=40,
            font=ctk.CTkFont(size=13),
            placeholder_text="Re-enter your master password..."
        )
        pass2_entry.pack(padx=20, pady=(0, 10))

        status = ctk.CTkLabel(
            content,
            text="",
            text_color="#e74c3c",
            wraplength=450,
            font=ctk.CTkFont(size=12)
        )
        status.pack(pady=5)
        
        create_btn = ctk.CTkButton(
            content,
            text="✨ Create Vault",
            state="disabled",
            width=480,
            height=50,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#2ecc71",
            hover_color="#27ae60"
        )
        
        # Live strength checker
        def update_strength(event=None):
            password = pass1_entry.get()
            confirm = pass2_entry.get()
            
            if not password:
                for seg in segments:
                    seg.configure(fg_color="#1a1a1a")
                strength_label.configure(text="")
                entropy_label.configure(text="")
                for lbl in req_labels.values():
                    lbl.configure(text_color="#e74c3c")
                create_btn.configure(state="disabled")
                return
            
            # Get user info for personal data check
            name = name_entry.get().strip()
            user_hints = [name] if name else None
            
            result = classify_strength(password, user_hints, require_strong=True)
            
            # Update strength bar segments - all filled segments use the strength color
            strength_colors = {
                0: '#e74c3c',  # Very Weak - Red
                1: '#e67e22',  # Weak - Orange
                2: '#f39c12',  # Medium - Yellow
                3: '#27ae60',  # Strong - Green
                4: '#16a085'   # Very Strong - Teal
            }
            
            filled_segments = result['score'] + 1  # 0-4 score -> 1-5 segments
            fill_color = strength_colors[result['score']]
            
            for i, seg in enumerate(segments):
                if i < filled_segments:
                    seg.configure(fg_color=fill_color)
                else:
                    seg.configure(fg_color="#1a1a1a")
            
            # Update label
            strength_label.configure(
                text=f"{result['label']}",
                text_color=result['color']
            )
            
            # Update entropy
            entropy_label.configure(text=f"Entropy: {result['entropy']} bits (60+ recommended)")
            
            # Update requirements checklist
            req_labels['length'].configure(
                text=f"{'✓' if result['length'] >= 8 else '✗'} At least 8 characters (12+ recommended)",
                text_color="#27ae60" if result['length'] >= 8 else "#e74c3c"
            )
            
            req_labels['classes'].configure(
                text=f"{'✓' if result['char_classes'] >= 3 else '✗'} At least 3 character types",
                text_color="#27ae60" if result['char_classes'] >= 3 else "#e74c3c"
            )
            
            req_labels['entropy'].configure(
                text=f"{'✓' if result['entropy'] >= 60 else '✗'} Minimum 60 bits entropy",
                text_color="#27ae60" if result['entropy'] >= 60 else "#e74c3c"
            )
            
            req_labels['no_personal'].configure(
                text=f"{'✓' if not result['has_personal_info'] else '✗'} No personal information",
                text_color="#27ae60" if not result['has_personal_info'] else "#e74c3c"
            )
            
            # Enable/disable create button
            passwords_match = password == confirm and confirm != ""
            if result['meets_minimum'] and passwords_match:
                create_btn.configure(state="normal")
                status.configure(text="✓ Ready to create vault", text_color="#27ae60")
            elif not result['meets_minimum']:
                create_btn.configure(state="disabled")
                status.configure(text="Password does not meet minimum requirements", text_color="#e74c3c")
            elif not passwords_match:
                create_btn.configure(state="disabled")
                if confirm:
                    status.configure(text="Passwords do not match", text_color="#e74c3c")
                else:
                    status.configure(text="Please confirm password", text_color="gray")
        
        pass1_entry.bind("<KeyRelease>", update_strength)
        pass2_entry.bind("<KeyRelease>", update_strength)
        name_entry.bind("<KeyRelease>", update_strength)

        def validate_and_create():
            name = name_entry.get().strip()
            p1 = pass1_entry.get()
            p2 = pass2_entry.get()

            if not name or not p1 or not p2:
                status.configure(text="All fields are required.", text_color="#e74c3c")
                return
            
            # Final validation
            result = classify_strength(p1, [name], require_strong=True)
            
            if not result['meets_minimum']:
                status.configure(text="Password does not meet minimum requirements.", text_color="#e74c3c")
                return
            
            if p1 != p2:
                status.configure(text="Passwords do not match.", text_color="#e74c3c")
                return

            rand_name = uuid.uuid4().hex[:10] + ".dat"
            path = os.path.join("vaults", rand_name)
            save_vault_label(rand_name, name)

            create_vault(p1, path)
            self.refresh_dropdown()
            self.dropdown.set("Select Profile")
            self.selected_vault = "" 
            win.destroy()

        def _on_vault_created(label):
            self.refresh_dropdown()
            self.dropdown.set(label)
            self.select_vault(label)

        create_btn.configure(command=validate_and_create)
        create_btn.pack(pady=15)

        name_entry.bind("<Return>", lambda e: pass1_entry.focus())
        name_entry.bind("<Down>", lambda e: pass1_entry.focus())

        pass1_entry.bind("<Return>", lambda e: pass2_entry.focus())
        pass1_entry.bind("<Down>", lambda e: pass2_entry.focus())
        pass1_entry.bind("<Up>", lambda e: name_entry.focus())

        def try_submit(e=None):
            # Only submit if button is enabled
            if create_btn.cget("state") == "normal":
                validate_and_create()
        
        pass2_entry.bind("<Return>", try_submit)
        pass2_entry.bind("<Down>", try_submit)
        pass2_entry.bind("<Up>", lambda e: pass1_entry.focus())
        
        # Also allow Enter from anywhere in the dialog when button is enabled
        win.bind("<Return>", try_submit)

    def open_delete_window(self):
        """Open dialog to delete a vault with password confirmation."""
        from tkinter import messagebox
        from core.vault import unlock_vault
        
        if not self.selected_vault:
            messagebox.showerror("Error", "Please select a vault to delete.")
            return
        
        # Get vault label for display
        vault_label = self.vault_labels.get(self.selected_vault, "Unknown")
        
        # Confirmation dialog
        win = ctk.CTkToplevel(self)
        self.set_window_icon(win)
        win.title("Delete Vault")
        win.geometry("400x300")
        win.resizable(False, False)
        win.grab_set()
        win.lift()
        win.focus_force()
        
        # Warning
        ctk.CTkLabel(
            win,
            text="⚠️ WARNING ⚠️",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#e74c3c"
        ).pack(pady=(20, 10))
        
        ctk.CTkLabel(
            win,
            text=f"You are about to delete vault:\n\"{vault_label}\"",
            font=ctk.CTkFont(size=13, weight="bold"),
            wraplength=350
        ).pack(pady=5)
        
        ctk.CTkLabel(
            win,
            text="This action CANNOT be undone!\nAll credentials will be permanently deleted.",
            font=ctk.CTkFont(size=11),
            text_color="#e67e22",
            wraplength=350
        ).pack(pady=10)
        
        ctk.CTkLabel(
            win,
            text="Enter master password to confirm:",
            font=ctk.CTkFont(size=11, weight="bold")
        ).pack(pady=(15, 5))
        
        password_entry = ctk.CTkEntry(win, show="•", width=250)
        password_entry.pack(pady=5)
        win.after(100, lambda: password_entry.focus())
        
        status_label = ctk.CTkLabel(win, text="", text_color="#e74c3c")
        status_label.pack(pady=5)
        
        def confirm_delete():
            password = password_entry.get()
            if not password:
                status_label.configure(text="Password required")
                return
            
            # Verify password
            vault_path = os.path.join("vaults", self.selected_vault)
            try:
                unlock_vault(password, vault_path)
                # Password correct, delete vault
                try:
                    # Delete vault file
                    os.remove(vault_path)
                    
                    # Remove from labels using core function
                    delete_vault_label(self.selected_vault)
                    
                    # Close dialog and refresh
                    win.destroy()
                    self.selected_vault = ""
                    self.refresh_dropdown()
                    messagebox.showinfo("Success", f"Vault \"{vault_label}\" has been permanently deleted.")
                except Exception as e:
                    status_label.configure(text=f"Error deleting vault: {e}")
            except:
                status_label.configure(text="Incorrect password")
        
        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(pady=15)
        
        ctk.CTkButton(
            btn_frame,
            text="Delete Vault",
            command=confirm_delete,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=150
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=win.destroy,
            font=ctk.CTkFont(size=12, weight="bold"),
            width=100
        ).pack(side="left", padx=5)
        
        password_entry.bind("<Return>", lambda e: confirm_delete())
    
    def refresh_dropdown(self):
        self.vault_labels = load_vault_labels()
        self.vault_list = list(self.vault_labels.values())
        self.label_to_filename = {v: k for k, v in self.vault_labels.items()}

        values = ["Select Profile"] + self.vault_list
        self.dropdown.configure(values=values)
        self.dropdown.set("Select Profile")
        self.selected_vault = ""