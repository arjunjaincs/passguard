from core.vault import save_vault
from tkinter import messagebox, Menu
import threading
import time
import customtkinter as ctk
import tkinter as tk
import pyperclip
import string
import random
import os
import sys

class MainWindow(ctk.CTk):
    def __init__(self, credentials: list, password: str, vault_path: str, label: str):
        super().__init__()
        self.title("PassGuard Vault")
        self.geometry("600x540")
        self.credentials = credentials
        self.password = password
        self.vault_path = vault_path
        icon_path = os.path.join("assets", "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(default=icon_path)
            except Exception as e:
                print(f"Failed to set main icon: {e}")

        self.label = ctk.CTkLabel(self, text=f"Vault: {label}", font=ctk.CTkFont(size=20, weight="bold"))
        self.label.pack(pady=10)

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.render_table())
        self.search_entry = ctk.CTkEntry(self, placeholder_text="Search by website / username", textvariable=self.search_var, width=300)
        self.search_entry.pack(pady=5)

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(pady=5)
        self.add_btn = ctk.CTkButton(container, text="Add Credential (Ctrl+N)", command=self.open_add_window)
        self.add_btn.pack(side="left", padx=(0, 10))

        self.lock_btn = ctk.CTkButton(container, text="Lock Vault", command=self.lock_vault)
        self.lock_btn.pack(side="left")

        self.bind_all("<Control-n>", lambda e: self.open_add_window())

        self.table_frame = ctk.CTkScrollableFrame(self)
        self.table_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.render_table()

    def lock_vault(self):
        os.execl(sys.executable, sys.executable, *sys.argv)

    def render_table(self):
        for widget in self.table_frame.winfo_children():
            widget.destroy()

        headers = ["Website", "Username / Email", "Password", "", "", ""]
        for i, text in enumerate(headers):
            header = ctk.CTkLabel(self.table_frame, text=text, font=ctk.CTkFont(weight="bold"))
            header.grid(row=0, column=i, padx=10, pady=5, sticky="w")

        query = self.search_var.get().lower()
        filtered = [cred for cred in self.credentials if query in cred['website'].lower() or query in cred['username'].lower()]

        for row, cred in enumerate(filtered, start=1):
            website = ctk.CTkLabel(self.table_frame, text=cred['website'])
            username = ctk.CTkLabel(self.table_frame, text=cred['username'])
            password = ctk.CTkLabel(self.table_frame, text="\u2022\u2022\u2022\u2022\u2022\u2022")

            website.grid(row=row, column=0, padx=10, pady=3, sticky="w")
            username.grid(row=row, column=1, padx=10, pady=3, sticky="w")
            password.grid(row=row, column=2, padx=10, pady=3, sticky="w")

            reveal_btn = ctk.CTkButton(self.table_frame, text="\ud83d\udc41", width=30)
            reveal_btn.grid(row=row, column=3, padx=2)
            reveal_btn.bind("<ButtonPress-1>", lambda e, l=password, p=cred['password']: l.configure(text=p))
            reveal_btn.bind("<ButtonRelease-1>", lambda e, l=password: l.configure(text="\u2022\u2022\u2022\u2022\u2022\u2022"))
            reveal_btn.bind("<ButtonPress-3>", lambda e, l=password, p=cred['password']: l.configure(text=p))
            reveal_btn.bind("<ButtonRelease-3>", lambda e, l=password: l.configure(text="\u2022\u2022\u2022\u2022\u2022\u2022"))

            copy_btn = ctk.CTkButton(self.table_frame, text="Copy", width=50, fg_color="green",
                                     hover_color="#118811", command=lambda pw=cred['password']: self.copy_to_clipboard(pw))
            copy_btn.grid(row=row, column=4, padx=2)

            edit_btn = ctk.CTkButton(self.table_frame, text="Edit", width=50, fg_color="goldenrod",
                                     hover_color="#c49000", command=lambda idx=self.credentials.index(cred): self.edit_credential(idx))
            edit_btn.grid(row=row, column=5, padx=2)

            del_btn = ctk.CTkButton(self.table_frame, text="Del", width=50, fg_color="red",
                                     hover_color="#990000", command=lambda idx=self.credentials.index(cred): self.delete_credential(idx))
            del_btn.grid(row=row, column=6, padx=2)

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
        cred = self.credentials[index]
        win = ctk.CTkToplevel(self)
        win.configure(bg=ctk.ThemeManager.theme["CTkFrame"]["fg_color"][1])
        self.set_window_icon(win)
        win.title("Edit Credential")
        win.geometry("300x300")
        win.resizable(False, False)
        win.lift()
        win.focus_force()
        self.set_window_icon(win)
        win.grab_set()

        ctk.CTkLabel(win, text="Website").pack(pady=5)
        website_entry = ctk.CTkEntry(win)
        website_entry.insert(0, cred["website"])
        website_entry.pack()
        win.after(100, lambda: website_entry.focus())

        ctk.CTkLabel(win, text="Username").pack(pady=5)
        username_entry = ctk.CTkEntry(win)
        username_entry.insert(0, cred["username"])
        username_entry.pack()

        ctk.CTkLabel(win, text="Password").pack(pady=5)
        password_entry = ctk.CTkEntry(win, show="\u2022")
        password_entry.insert(0, cred["password"])
        password_entry.pack()

        gen_btn = ctk.CTkButton(win, text="Generate Secure Password", command=lambda: self.copy_generated(password_entry))
        gen_btn.pack(pady=10)

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

        win.bind("<Return>", lambda e: save())
        ctk.CTkButton(win, text="Save", command=save).pack(pady=10)

    def open_add_window(self):
        win = ctk.CTkToplevel(self)
        win.configure(bg=ctk.ThemeManager.theme["CTkFrame"]["fg_color"][1])
        self.set_window_icon(win)
        win.title("Add Credential")
        win.geometry("300x300")
        win.resizable(False, False)
        win.lift()
        win.focus_force()
        self.set_window_icon(win)
        win.grab_set()

        ctk.CTkLabel(win, text="Website").pack(pady=5)
        website_entry = ctk.CTkEntry(win)
        website_entry.pack()
        win.after(100, lambda: website_entry.focus())

        ctk.CTkLabel(win, text="Username").pack(pady=5)
        username_entry = ctk.CTkEntry(win)
        username_entry.pack()

        ctk.CTkLabel(win, text="Password").pack(pady=5)
        password_entry = ctk.CTkEntry(win, show="\u2022")
        password_entry.pack()

        gen_btn = ctk.CTkButton(win, text="Generate Secure Password", command=lambda: self.copy_generated(password_entry))
        gen_btn.pack(pady=10)

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

        win.bind("<Return>", lambda e: save())
        ctk.CTkButton(win, text="Save", command=save).pack(pady=10)

    def copy_generated(self, entry):
        password = self.generate_password()
        entry.delete(0, "end")
        entry.insert(0, password)
        pyperclip.copy(password)
        self.show_splash("Secure password copied to clipboard \u2714")