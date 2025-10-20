# PassGuard Icon Setup Guide

## ✅ What's Been Done

All icons have been configured to use your new logo from `assets/icon.ico`

### 📍 Icons Are Now Used In:

#### Main Application Windows
- ✅ **UnlockDialog** (main login window)
- ✅ **MainWindow** (vault window)
- ✅ **System Tray Icon**

#### All Dialog Boxes
- ✅ Create New Vault dialog
- ✅ Delete Vault confirmation
- ✅ Edit Credential dialog
- ✅ Add Credential dialog
- ✅ Personal Information dialog (security audit)
- ✅ Security Test Progress dialog
- ✅ Security Test Results dialog
- ✅ Browser Extension Setup dialog
- ✅ Export Vault dialog
- ✅ Import Vault dialog
- ✅ Security Check Dialog (HIBP)

#### Browser Extension
- ✅ Extension icon (16x16, 48x48, 128x128)
- ✅ Popup window
- ✅ Toolbar icon

---

## 🔧 How to Update Icons

### Step 1: Place Your New Logo
Put your new logo file as:
```
assets/icon.ico
```

### Step 2: Resize for Browser Extension
Run the resize script:
```bash
python resize_icons.py
```

This will automatically create:
- `browser_extension/icons/icon16.png` (16x16)
- `browser_extension/icons/icon48.png` (48x48)
- `browser_extension/icons/icon128.png` (128x128)

### Step 3: Done!
All windows and dialogs will automatically use the new icon.

---

## 📝 Technical Details

### Icon Formats
- **Main App**: `.ico` file (Windows icon format)
- **Browser Extension**: `.png` files (16, 48, 128 pixels)

### Where Icons Are Set

**File: `ui/main_window.py`**
- Method: `set_window_icon(win)` - Sets icon for all dialogs
- Called for every CTkToplevel dialog

**File: `ui/unlock_dialog.py`**
- Method: `set_window_icon(win)` - Sets icon for create/delete dialogs
- Main window icon set in `__init__`

**File: `ui/security_check_dialog.py`**
- Method: `set_window_icon()` - Sets icon for HIBP dialog
- Called in `__init__`

**File: `main.py`**
- Method: `create_icon_image()` - Loads icon for system tray
- Uses PIL to load `assets/icon.ico`

**File: `browser_extension/manifest.json`**
```json
"icons": {
  "16": "icons/icon16.png",
  "48": "icons/icon48.png",
  "128": "icons/icon128.png"
}
```

---

## 🎨 Icon Requirements

### For `assets/icon.ico`:
- Format: ICO (Windows Icon)
- Recommended sizes: 16x16, 32x32, 48x48, 256x256 (multi-size ICO)
- Transparency: Supported
- Color depth: 32-bit recommended

### For Browser Extension:
- Format: PNG
- Sizes: Exactly 16x16, 48x48, 128x128 pixels
- Transparency: Supported
- Color depth: 32-bit RGBA

---

## 🚀 Quick Start

1. **Replace** `assets/icon.ico` with your new logo
2. **Run** `python resize_icons.py`
3. **Test** by running `python main.py`
4. **Reload** browser extension (chrome://extensions → reload)

---

## ✨ All Set!

Your new logo is now used everywhere in PassGuard:
- 🪟 All application windows
- 💬 All dialog boxes
- 🌐 Browser extension
- 📱 System tray

No more default icons! 🎉
