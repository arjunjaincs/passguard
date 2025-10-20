# 🔐 PassGuard

**Enterprise-grade password manager with military-grade encryption and zero-knowledge architecture.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Security: Argon2id](https://img.shields.io/badge/Security-Argon2id-green.svg)](https://en.wikipedia.org/wiki/Argon2)

---

## ✨ Features

### 🔒 **Military-Grade Security**
- **AES-256-GCM** encryption for vault data
- **Argon2id** key derivation (OWASP recommended)
- **RSA-4096** for secure vault sharing
- **Zero-knowledge architecture** - your master password never leaves your device
- **Auto-lock** on inactivity and USB drive removal

### 🛡️ **Security Auditing**
- **Password strength analyzer** with real-time feedback
- **Breach detection** via Have I Been Pwned API (k-anonymity)
- **Security audit reports** (PDF export)
- Detects weak, reused, and similar passwords
- Personal information exposure detection

### 🌐 **Browser Integration**
- **Chrome/Edge extension** for one-click autofill
- Secure local API with token authentication
- Works offline - no cloud dependency

### 📤 **Vault Management**
- **Secure export/import** with RSA encryption
- **Multiple vaults** with custom labels
- **Digital signatures** for authenticity verification
- Cross-device vault sharing

### 🎨 **Modern UI**
- Dark mode interface with CustomTkinter
- Real-time password strength visualization
- Hold-to-reveal password protection
- Auto-clearing clipboard (15s timeout)
- System tray integration

---

## 🚀 Quick Start

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/passguard.git
cd passguard
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Run PassGuard:**
```bash
python main.py
```

### First-Time Setup

1. **Create your first vault:**
   - Click "Create New Vault"
   - Enter a vault name
   - Create a strong master password (12+ characters recommended)

2. **Add credentials:**
   - Click "Add Credential"
   - Enter website, username, and password
   - Use the password generator for strong passwords

3. **Optional - Setup browser extension:**
   - Click "Browser Extension" button
   - Copy the authentication token
   - Load the extension in Chrome/Edge
   - Paste the token in the extension popup

---

## 📋 Requirements

- **Python 3.8+**
- **Windows/Linux/macOS**
- **Dependencies:** See `requirements.txt`

### Core Dependencies
- `customtkinter` - Modern UI framework
- `pycryptodome` - AES encryption
- `argon2-cffi` - Key derivation
- `cryptography` - RSA encryption
- `requests` - HIBP API integration
- `flask` - Browser extension API

---

## 🔐 Security Architecture

### Encryption Stack
```
Master Password
    ↓
Argon2id (3 iterations, 64MB memory)
    ↓
256-bit AES-GCM Key
    ↓
Encrypted Vault Data
```

### Zero-Knowledge Design
- Master password **never stored** anywhere
- Vault encrypted locally before any storage
- Browser extension uses **one-time tokens**
- HIBP checks use **k-anonymity** (only 5 chars of hash sent)

### Auto-Lock Protection
- Locks after **3 minutes** of inactivity
- Locks when **USB drive removed** (if vault on USB)
- Clears clipboard after **15 seconds**
- Suspends app after **4 failed unlock attempts**

---

## 📖 Usage

### Password Management
- **Add:** Click "Add Credential" or press `Ctrl+N`
- **Edit:** Click "Edit" button on any credential
- **Delete:** Click "Delete" button (requires confirmation)
- **Copy:** Click "Copy" to copy password (auto-clears in 15s)
- **Reveal:** Hold the eye icon to temporarily reveal password

### Security Audit
1. Click "Security Audit" button
2. Optionally provide personal info for PII detection
3. Review findings and recommendations
4. Export report as PDF

### Breach Check
1. Click "Breach Check" button
2. Select check type (password-only or account)
3. For account checks, enter HIBP API key
4. Review results and update compromised passwords

### Vault Export/Import
**Export:**
1. Click "Export Vault"
2. Choose backup (self) or share (other user)
3. For sharing, select recipient's public key
4. Save the `.pvgx` file

**Import:**
1. Click "Import Vault"
2. Select `.pvgx` file
3. Optionally verify sender's signature
4. Enter vault label

---

## 🌐 Browser Extension Setup

1. **In PassGuard:**
   - Open vault
   - Click "Browser Extension"
   - Copy the authentication token

2. **In Chrome/Edge:**
   - Go to `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked"
   - Select `browser_extension` folder

3. **Configure Extension:**
   - Click PassGuard extension icon
   - Paste authentication token
   - Click "Save Token"
   - Status should turn green ✅

4. **Use Autofill:**
   - Visit any login page
   - Click "🔐 Fill with PassGuard" button
   - Credentials auto-filled!

---

## 🛠️ Development

### Project Structure
```
passguard/
├── main.py                 # Application entry point
├── core/
│   ├── crypto.py          # Encryption/decryption
│   ├── vault.py           # Vault management
│   ├── strength.py        # Password strength analysis
│   ├── security_audit.py  # Security auditing
│   ├── breach_check.py    # HIBP integration
│   ├── export_import.py   # RSA vault sharing
│   └── autofill_server.py # Browser extension API
├── ui/
│   ├── unlock_dialog.py   # Login screen
│   ├── main_window.py     # Main vault window
│   └── security_check_dialog.py  # Breach check UI
├── browser_extension/     # Chrome/Edge extension
└── assets/
    └── icon.ico          # Application icon
```

### Building Executable
```bash
# Install PyInstaller
pip install pyinstaller

# Build (Windows)
pyinstaller --onefile --windowed --icon=assets/icon.ico main.py

# Output in dist/main.exe
```

---

## 🔒 Security Best Practices

### Master Password
- ✅ Use **12+ characters**
- ✅ Mix uppercase, lowercase, digits, symbols
- ✅ Avoid personal information
- ✅ Use a unique password (not used elsewhere)
- ❌ Never share your master password

### Vault Management
- ✅ Regular security audits
- ✅ Update weak/breached passwords immediately
- ✅ Use unique passwords for each site
- ✅ Enable auto-lock features
- ✅ Store vault backups securely

### Browser Extension
- ✅ Only use on trusted devices
- ✅ Regenerate token if compromised
- ✅ Lock vault when not in use

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Have I Been Pwned** - Breach detection API
- **CustomTkinter** - Modern UI framework
- **OWASP** - Security guidelines

---

## 📧 Support

For issues, questions, or feature requests, please open an issue on GitHub.

---

**PassGuard** - *Enterprise security, personal control.* 🔐
