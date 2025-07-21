import customtkinter as ctk
import os
import sys
import threading
import time
from ui.unlock_dialog import UnlockDialog
from ui.main_window import MainWindow
from core.vault import unlock_vault, create_vault, load_vault_labels

main_window = None
last_activity_time = time.time()
INACTIVITY_LIMIT = 5 * 60
selected_vault_path = ""
selected_vault_label = ""

ICON_PATH = os.path.join("assets", "icon.ico")

def reset_timer(event=None):
    global last_activity_time
    last_activity_time = time.time()

def monitor_inactivity():
    def check():
        while True:
            time.sleep(10)
            if time.time() - last_activity_time > INACTIVITY_LIMIT:
                try:
                    main_window.after(0, lock_app)
                    break
                except Exception:
                    pass
    threading.Thread(target=check, daemon=True).start()

def lock_app():
    global main_window
    if main_window:
        main_window.destroy()
        relaunch_unlock()

def relaunch_unlock():
    global unlock_ui
    unlock_ui = UnlockDialog(handle_unlock, handle_create)
    if os.path.exists(ICON_PATH):
        try:
            unlock_ui.iconbitmap(ICON_PATH)
        except Exception:
            pass
    unlock_ui.mainloop()

def launch_main_window(credentials, password, label):
    global main_window
    main_window = MainWindow(credentials, password, selected_vault_path, label)
    if os.path.exists(ICON_PATH):
        try:
            main_window.iconbitmap(ICON_PATH)
        except Exception:
            pass

    for event in ["<Motion>", "<Key>", "<Button>"]:
        main_window.bind_all(event, reset_timer)

    monitor_inactivity()
    main_window.mainloop()

def handle_unlock(password, status_label, vault_path):
    global selected_vault_path, selected_vault_label
    try:
        if not vault_path or not os.path.exists(vault_path):
            status_label.configure(text="Please select a vault.")
            return
        selected_vault_path = vault_path
        labels = load_vault_labels()
        filename = os.path.basename(vault_path)
        selected_vault_label = labels.get(filename, "Unknown")

        vault = unlock_vault(password, selected_vault_path)
        status_label.configure(text="Vault unlocked ✔")
        status_label.after(500, lambda: open_main(vault["credentials"], password))
    except FileNotFoundError:
        status_label.configure(text="Vault not found.")
    except Exception as e:
        status_label.configure(text=f"Invalid password ❌ ({e})")

def handle_create(name, password, path, status_label, refresh_callback):
    try:
        create_vault(password, path)
        status_label.configure(text="Vault created ✔")
        status_label.after(800, refresh_callback)
    except Exception as e:
        status_label.configure(text=f"Error: {e}")

def open_main(credentials, password):
    try:
        unlock_ui.after_cancel(unlock_ui._focus_after_id)
    except Exception:
        pass

    unlock_ui.withdraw()
    unlock_ui.update()
    unlock_ui.destroy()

    launch_main_window(credentials, password, selected_vault_label)

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    unlock_ui = UnlockDialog(handle_unlock, handle_create)
    if os.path.exists(ICON_PATH):
        try:
            unlock_ui.iconbitmap(ICON_PATH)
        except Exception:
            pass
    unlock_ui.mainloop()