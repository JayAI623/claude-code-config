---
name: wechat-decrypt
description: Extract encryption keys from WeChat macOS process memory, decrypt SQLCipher databases, and export chat messages with ZSTD decompression support.
---

# WeChat macOS Database Decryption & Message Export

Extract SQLCipher encryption keys from WeChat 4.x on macOS, decrypt databases, and export chat messages.

## Prerequisites

```bash
brew install llvm sqlcipher
pip3 install zstandard pycryptodome
```

SIP (System Integrity Protection) must be **temporarily disabled** to read WeChat process memory via `task_for_pid`.

## Important: WeChat Version Compatibility

**WeChat 4.1+ changed key storage** — the memory scanner cannot find keys in 4.1+.
You must use **WeChat 4.0.3.x** (last compatible version) to extract keys.

### Download Old WeChat (v4.0.3.61)

The old version is available from the Wayback Machine:

```
https://web.archive.org/web/20250405144350/https://dldir1.qq.com/weixin/Universal/Mac/WeChatMac.dmg
```

This DMG is Tencent-signed and Apple-notarized (verified with `codesign -dv` and `spctl -a`).

### Install Old Version Temporarily

```bash
# Back up current WeChat (optional)
cp -R /Applications/WeChat.app /Applications/WeChat_backup.app

# Remove current version
rm -rf /Applications/WeChat.app

# Mount and install old DMG
open WeChatMac_old.dmg
# Drag WeChat.app to /Applications

# Verify version (should show 4.0.x)
mdls -name kMDItemVersion /Applications/WeChat.app
```

## Step-by-Step Workflow

### 1. Disable SIP (one-time, reboot required)

1. Restart Mac, hold **Power** button → Recovery Mode
2. Terminal → `csrutil disable`
3. Restart

### 2. Extract Encryption Keys

Login to old WeChat (4.0.3.x), then run the C scanner:

```bash
cd ~/.claude/skills/wechat-decrypt

# Compile (if needed)
cc -O2 -o find_all_keys_macos find_all_keys_macos.c -framework Foundation

# Run (must be root)
sudo ./find_all_keys_macos
```

This scans WeChat process memory for `x'<64hex_key><32hex_salt>'` patterns and outputs `all_keys.json`.

### 3. Restore New WeChat Version

```bash
rm -rf /Applications/WeChat.app
# Install latest WeChat from Mac App Store or official site
```

The extracted keys remain valid — they are per-database, not per-version.

### 4. Re-enable SIP

1. Restart Mac → Recovery Mode
2. Terminal → `csrutil enable`
3. Restart

### 5. Configure & Decrypt Databases

Create `config.json` in the working directory:

```json
{
    "db_dir": "~/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/<your_wxid>/db_storage",
    "keys_file": "all_keys.json",
    "decrypted_dir": "decrypted",
    "wechat_process": "WeChat"
}
```

Then decrypt:

```bash
python3 decrypt_db.py
```

### 6. Export Messages

```bash
# List all conversations
python3 export_messages.py

# Export specific chat (supports fuzzy name matching)
python3 export_messages.py -c "群名称"

# Export with ZSTD decompression for rich media
python3 export_messages.py -c "群名称" -n 100

# Search across all chats
python3 export_messages.py -s "keyword"

# Export all conversations
python3 export_messages.py --all
```

### 7. ZSTD Message Decompression

WeChat 4.x compresses rich media messages (quotes, links, files) with ZSTD (magic bytes `28b52ffd`). To decode inline:

```python
import zstandard
dctx = zstandard.ZstdDecompressor()

if isinstance(content, bytes) and content[:4] == b'\x28\xb5\x2f\xfd':
    decoded = dctx.decompress(content).decode("utf-8", errors="replace")
```

## Technical Details

- **Encryption**: SQLCipher 4, AES-256-CBC, HMAC-SHA512, PBKDF2 (256,000 iterations), page_size=4096, reserve=80
- **Key format in memory**: `x'<64hex_enc_key><32hex_salt>'` cached by WCDB
- **Message table naming**: `Msg_{md5(username)}` — tables are MD5-hashed from username/chatroom ID
- **Message types**: 1=text, 3=image, 34=voice, 43=video, 47=emoji, 10000=system, 49=link/file
- **Group message format**: `"wxid_xxx:\ncontent"` with sender prefix separated by `:\n`

## Files in This Skill

| File | Description |
|------|-------------|
| `find_all_keys_macos.c` | C memory scanner (Mach VM API) |
| `find_all_keys_macos` | Compiled binary (ARM64) |
| `decrypt_db.py` | SQLCipher database decryptor |
| `export_messages.py` | Message exporter with fuzzy matching |
| `config.py` | Configuration loader |
| `key_scan_common.py` | Shared HMAC verification logic |
| `key_utils.py` | Key path utilities |
