import customtkinter as ctk
import os
import uuid
from core.vault import VAULT_PATH, create_vault, load_vault_labels, save_vault_label


class UnlockDialog(ctk.CTk):
    def __init__(self, unlock_callback, create_callback):
        super().__init__()
        self.unlock_callback = unlock_callback
        self.create_callback = create_callback
        self._focus_after_id = None

        self.title("PassGuard - Vault Login")
        self.geometry("320x400")
        self.resizable(True, True)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.create_widgets()

    def create_widgets(self):
        self.label = ctk.CTkLabel(self, text="Select or Create Vault")
        self.label.pack(pady=(10, 4))

        self.vault_labels = load_vault_labels()
        self.vault_list = list(self.vault_labels.values())
        self.label_to_filename = {v: k for k, v in self.vault_labels.items()}

        self.dropdown = ctk.CTkOptionMenu(
            self, 
            values=["Select Profile"] + self.vault_list,
            command=self.select_vault
        )
        self.dropdown.pack(pady=(0, 10))
        self.dropdown.set("Select Profile")
        self.selected_vault = ""

        self.pass_label = ctk.CTkLabel(self, text="Enter Master Password")
        self.pass_label.pack(pady=(0, 5))

        self.password_entry = ctk.CTkEntry(self, show="•", width=200)
        self.password_entry.pack()
        self._focus_after_id = self.after(100, lambda: self.password_entry.focus())

        self.unlock_btn = ctk.CTkButton(self, text="Unlock Vault", command=self.try_unlock)
        self.unlock_btn.pack(pady=(10, 15))

        self.or_label = ctk.CTkLabel(self, text="— or —")
        self.or_label.pack(pady=5)

        self.create_vault_btn = ctk.CTkButton(self, text="Create New Vault", command=self.open_create_window)
        self.create_vault_btn.pack(pady=5)

        self.status_label = ctk.CTkLabel(self, text="", text_color="red", wraplength=250, justify="center")
        self.status_label.pack(pady=10)

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
        win.title("Create New Vault")
        win.geometry("320x380")
        win.resizable(False, False)
        win.grab_set()
        win.lift()
        win.focus_force()

        ctk.CTkLabel(win, text="Vault Name (Label)").pack(pady=(15, 2))
        name_entry = ctk.CTkEntry(win)
        name_entry.pack()
        win.after(100, lambda: name_entry.focus())

        ctk.CTkLabel(win, text="Master Password").pack(pady=(10, 2))
        pass1_entry = ctk.CTkEntry(win, show="•")
        pass1_entry.pack()

        ctk.CTkLabel(win, text="Confirm Password").pack(pady=(10, 2))
        pass2_entry = ctk.CTkEntry(win, show="•")
        pass2_entry.pack()

        rules = [
            "At least 6 characters",
            "At least one uppercase & lowercase",
            "At least one number",
            "At least one symbol (!@#$%)"
        ]
        for rule in rules:
            ctk.CTkLabel(win, text=f"• {rule}", text_color="gray").pack(anchor="w", padx=20)

        status = ctk.CTkLabel(win, text="", text_color="red")
        status.pack(pady=5)

        def validate_and_create():
            name = name_entry.get().strip()
            p1 = pass1_entry.get()
            p2 = pass2_entry.get()

            if not name or not p1 or not p2:
                status.configure(text="All fields are required.")
                return
            if p1 != p2:
                status.configure(text="Passwords do not match.")
                return
            if len(p1) < 6 or not any(c.islower() for c in p1) or not any(c.isupper() for c in p1) \
                or not any(c.isdigit() for c in p1) or not any(c in '!@#$%^&*()-_=+[]{}|;:,.<>?/~`' for c in p1):
                status.configure(text="Password too weak.")
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

        ctk.CTkButton(win, text="Create Vault", command=validate_and_create).pack(pady=15)

        name_entry.bind("<Return>", lambda e: pass1_entry.focus())
        name_entry.bind("<Down>", lambda e: pass1_entry.focus())

        pass1_entry.bind("<Return>", lambda e: pass2_entry.focus())
        pass1_entry.bind("<Down>", lambda e: pass2_entry.focus())
        pass1_entry.bind("<Up>", lambda e: name_entry.focus())

        pass2_entry.bind("<Return>", lambda e: validate_and_create())
        pass2_entry.bind("<Down>", lambda e: validate_and_create())
        pass2_entry.bind("<Up>", lambda e: pass1_entry.focus())

    def refresh_dropdown(self):
        self.vault_labels = load_vault_labels()
        self.vault_list = list(self.vault_labels.values())
        self.label_to_filename = {v: k for k, v in self.vault_labels.items()}

        values = ["Select Profile"] + self.vault_list
        self.dropdown.configure(values=values)
        self.dropdown.set("Select Profile")
        self.selected_vault = ""