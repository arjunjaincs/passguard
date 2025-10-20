# 🌐 Browser Autofill - Quick Guide

## ⚡ One-Time Setup

1. **Unlock PassGuard vault**
2. **Click "🌐 Browser Extension" button**
3. **Click "📋 Copy Token"**
4. **Install extension:**
   - Open `chrome://extensions/`
   - Enable Developer mode
   - Load unpacked → select `browser_extension` folder
5. **Paste token in extension popup**
6. **Done!** Never configure again ✅

---

## 🎯 How to Use

Visit any login page → **Floating button appears** → Click it → **Credentials filled!**

```
┌─────────────────────────────────────┐
│  Login Page                         │
│  ┌───────────────────────────────┐ │
│  │ Username: [____________]      │ │
│  │ Password: [____________]      │ │
│  └───────────────────────────────┘ │
│                                     │
│              [🔐 Fill with PassGuard] ← Floating button
└─────────────────────────────────────┘
```

---

## 🔐 Smart Auto-Lock

```
┌────────────────────────────────────────────────────┐
│  UNLOCK VAULT                                      │
│  ↓                                                 │
│  ├─ UI Active ✅ (view/edit passwords)            │
│  └─ API Active ✅ (browser autofill)              │
│                                                    │
│  ⏱️ AFTER 3 MINUTES (auto-lock)                   │
│  ├─ UI Locks ❌ (need password to view)           │
│  └─ API Running ✅ (autofill still works!)        │
│                                                    │
│  🔒 CLICK "LOCK VAULT" (manual)                   │
│  ├─ UI Locks ❌                                    │
│  └─ API Stops ❌ (full security)                  │
│                                                    │
│  🔌 USB REMOVED (emergency)                       │
│  ├─ UI Locks ❌                                    │
│  └─ API Stops ❌ (instant protection)             │
└────────────────────────────────────────────────────┘
```

**Why this is smart:**
- **Secure:** Password list locks quickly (3 min)
- **Convenient:** Browser autofill works all day
- **Safe:** Manual lock for when you leave
- **Protected:** USB removal = instant full lock

---

## 🛡️ Security

✅ **Localhost only** - No external access  
✅ **Token auth** - 32-byte random (impossible to guess)  
✅ **Persistent token** - Configure once, works forever  
✅ **UI locks fast** - Can't view passwords without unlock  
✅ **Manual lock** - Full control when needed  

---

## 🎨 Features

- **🎯 Floating Button** - Always visible, easy to click
- **🔍 Auto-Detection** - Finds login forms automatically
- **⚡ One-Click Fill** - Instant credential filling
- **✨ Smooth Animations** - Beautiful gradient effects
- **📱 Smart Notifications** - Success/error messages
- **🔄 Dynamic Loading** - Works with SPAs (React, Vue, etc.)

---

## 🐛 Troubleshooting

**Button not appearing?**
1. Check console (F12) for `[PassGuard] Found X login form(s)`
2. Reload extension at `chrome://extensions/`
3. Verify PassGuard is running and unlocked
4. Test API: Visit `http://127.0.0.1:5777/health`

**"No credentials found"?**
- Add credentials in PassGuard for this website
- Domain should match (e.g., "reddit.com")

**Extension shows red dot?**
- Unlock PassGuard vault
- Copy token again if needed

---

## 📊 Architecture

```
┌──────────┐    Token Auth    ┌──────────┐    Encrypted    ┌──────────┐
│ Browser  │ ←─────────────→ │   API    │ ←────────────→ │  Vault   │
│Extension │   localhost:5777 │  Server  │   AES-256-GCM  │  (Locked)│
└──────────┘                  └──────────┘                 └──────────┘
```

**Data Flow:**
1. Extension detects login form
2. Requests credentials from API (with token)
3. API verifies token + decrypts vault
4. Returns username/password
5. Extension fills form fields
6. **No data stored in browser**

---

## 💡 Pro Tips

**Daily Workflow:**
- Unlock vault once in morning
- Browse all day with autofill
- UI auto-locks (secure)
- Autofill keeps working (convenient)
- Manual lock when leaving computer

**Maximum Security:**
- Store vault on USB drive
- Auto-locks everything if USB removed
- Manual lock every time you step away

**Best Practice:**
- Use strong master password
- Enable USB auto-lock
- Manual lock when leaving desk
- Keep token secure (never share)

---

## ✨ What Makes This Special

Unlike other password managers:
- ✅ **Fully offline** - No cloud, no sync, no tracking
- ✅ **Local API** - Everything on your computer
- ✅ **Smart locking** - UI locks, autofill works
- ✅ **One-time setup** - Configure once, use forever
- ✅ **Visual feedback** - Beautiful floating button
- ✅ **Open source** - Audit the code yourself

---

**Setup time:** 2 minutes  
**Daily friction:** Zero  
**Security:** Maximum  
**Convenience:** Maximum  

🎉 **Perfect balance!**
