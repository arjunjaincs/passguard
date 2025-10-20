# PassGuard - Features

## 🔐 Security
- **AES-256-GCM** encryption + **Argon2id** key derivation
- **Zero-knowledge** architecture (data never leaves device)
- **Real-time breach detection** (HIBP k-anonymity)
- **Password strength analysis** (entropy calculation)
- **USB auto-lock** (instant protection on removal)
- **Clipboard auto-clear** (security after copy)
- **Smart timeout** (UI locks, autofill works)

## 🌐 Browser Autofill
- **One-click autofill** on any website
- **Floating button** (always visible)
- **Local API** (localhost only, token auth)
- **Encrypted token** storage
- **Works offline** (no internet needed)
- **Chrome/Edge/Brave** support

## 🔍 Security Audit
- **Weak password detection**
- **Reuse & similarity analysis**
- **PII exposure warnings**
- **Breach count tracking**
- **PDF reports** with recommendations
- **Risk scoring** (Critical/High/Medium/Low)

## 📤 Vault Sharing
- **RSA-4096 encryption** for secure sharing
- **Digital signatures** (authenticity verification)
- **Self-backup** or **share with others**
- **`.pvgx` export format**
- **Cross-device transfer** (no password exposure)

## 🎨 User Experience
- **Modern dark UI** (CustomTkinter)
- **Hold-to-reveal** passwords (secure by default)
- **One-click copy** (auto-clear after 15s)
- **Keyboard shortcuts** (Ctrl+N for add)
- **Visual feedback** (colors, icons, animations)
- **Responsive design** (scrollable tables)

## 🔑 Credential Management
- **Add/Edit/Delete** credentials
- **Password generator** (customizable length/complexity)
- **Search & filter** (instant results)
- **Notes field** (optional metadata)
- **Bulk operations** (export, audit)

## 🔧 Advanced
- **Failed attempt protection** (3 strikes → lock, 4th → suspend)
- **Brute-force protection**
- **Memory wiping** on lock
- **No plaintext storage** (everything encrypted)
- **Session-only memory** (cleared on lock)
- **Secure deletion** (overwrite before remove)
- **HTTPS-only** API calls (HIBP)
- **Background threading** (non-blocking UI)
- **Low memory** (< 100 MB)
- **Fast search** (< 50ms for 1000 credentials)

## 🌐 Platform Support
- **Windows** ✅ (Full USB auto-lock)
- **Linux** ✅ (Path polling)
- **macOS** ✅ (Path polling)

## 📊 Tech Stack
- **Python 3.8+**
- **CustomTkinter** (Modern UI)
- **AES-256-GCM** + **Argon2id** + **RSA-4096**
- **Flask** (Local API)
- **HIBP API** (Breach detection)
- **ReportLab** (PDF reports)

---

**Total Features:** 50+  
**Lines of Code:** ~5,000  
**Dependencies:** 6 core libraries  
**Platform:** Cross-platform (Windows/Linux/macOS)

### User Guides
- `README.md` - Quick start & overview
- `EXPORT_IMPORT_DEMO.md` - Visual export/import guide
- `USB_AUTO_LOCK.md` - USB auto-lock documentation
- `FEATURE_LIST.md` - This document

### Developer Docs
- Inline docstrings (all functions)
- Type hints (Python 3.8+)
- Code comments (complex logic)
- Test files (unit tests)

---

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run PassGuard
python main.py

# Create vault → Add credentials → Lock vault
# Export → Import → Breach check → Security audit
```

---

## 📈 Project Stats

- **Lines of Code**: ~6,500+
- **Files**: 15+ Python modules
- **Features**: 50+ implemented
- **Security Audits**: 7 categories
- **Encryption Algorithms**: 3 (AES, RSA, Argon2)
- **API Integrations**: 1 (HIBP)
- **Supported Platforms**: 3 (Windows, Linux, macOS)

---

## 🎓 Key Differentiators

### vs. LastPass/1Password
- ✅ **100% offline** (no cloud dependency)
- ✅ **Open source** (auditable code)
- ✅ **Zero subscription** (free forever)
- ✅ **USB auto-lock** (physical security)
- ✅ **Binary vault format** (obfuscated)

### vs. KeePass
- ✅ **Modern UI** (CustomTkinter)
- ✅ **Breach checking** (HIBP integration)
- ✅ **RSA export/import** (secure sharing)
- ✅ **PDF reports** (professional audits)
- ✅ **Real-time strength** (instant feedback)

### vs. Bitwarden
- ✅ **Fully offline** (no server required)
- ✅ **USB auto-lock** (removable drive protection)
- ✅ **Binary encryption** (not JSON)
- ✅ **Argon2id** (stronger than PBKDF2)
- ✅ **Python-based** (easy to audit)

---

## 🏆 Feature Highlights

**Most Unique Features:**
1. 🔌 **USB Auto-Lock** - Instant lock on drive removal
2. 📤 **RSA Export/Import** - Share without password exposure
3. 🔍 **HIBP Breach Check** - k-anonymity password checking
4. 📊 **PDF Security Reports** - Professional audit deliverables
5. 🔐 **Binary Vault Format** - Random-looking encrypted files

**Best Security Features:**
1. Argon2id KDF (128 MiB memory)
2. AES-256-GCM authenticated encryption
3. RSA-4096 asymmetric encryption
4. Zero-knowledge architecture
5. Secure memory wiping

**Best UX Features:**
1. Hold-to-reveal passwords
2. Real-time strength checker
3. One-click password generator
4. Auto-clear clipboard
5. Visual countdown timer

---

## 💡 Future Enhancements (Roadmap)

- 🔐 **TOTP/2FA** support (time-based codes)
- 🌐 **Browser extension** (auto-fill)
- 📱 **Mobile app** (Android/iOS)
- 🔄 **Auto-backup** (scheduled exports)
- 🎨 **Themes** (light mode, custom colors)
- 🔍 **Advanced search** (regex, tags)
- 📊 **Dashboard** (statistics, charts)
- 🔔 **Notifications** (breach alerts)

---

**PassGuard** - *Enterprise security, personal control.*

**Version**: 2.0  
**License**: MIT  
**Author**: Arjun  
**Status**: Production Ready ✅
