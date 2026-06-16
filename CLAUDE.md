# PassSimple — Project Context

## Overview
Local-only password manager for Windows. Single-user. Encrypted via Windows DPAPI
bound to the current user account. **No master password** — DPAPI handles the
key protection. No cloud, no telemetry, no network calls. Ever.

## Tech Stack
- Python 3.12+
- PySide6 (GUI, Qt 6)
- sqlite3 (builtin) — local storage
- cryptography (AES-GCM)
- pywin32 (DPAPI via `win32crypt`)
- pytest (tests)
- PyInstaller (build to single-file `.exe`)

## Project Layout
```
PassSimple/
├── CLAUDE.md
├── README.md
├── pyproject.toml
├── .gitignore
├── assets/
│   ├── icon.ico            # Multi-res: 16, 32, 48, 256
│   └── icon.png            # Source for icon generation
├── src/
│   ├── __init__.py
│   ├── app.py              # Entry point
│   ├── crypto.py           # DPAPI wrapper + AES-GCM
│   ├── db.py               # SQLite schema, migrations, CRUD
│   ├── models.py           # Entry, Tag dataclasses
│   ├── importer.py         # CSV import (Chromium browsers)
│   ├── generator.py        # Password generator (secrets module)
│   └── gui/
│       ├── __init__.py
│       ├── main_window.py
│       ├── entry_dialog.py
│       ├── settings_dialog.py
│       └── styles.qss      # Qt stylesheet
├── tests/
│   ├── test_crypto.py
│   ├── test_db.py
│   ├── test_importer.py
│   └── test_generator.py
└── build/
    └── passsimple.spec     # PyInstaller config
```

Runtime data location: `%LOCALAPPDATA%\PassSimple\vault.db`
(not the project folder — Windows convention)

## Security Requirements — READ CAREFULLY

### Key management
1. On first launch: generate a random 32-byte master key with `os.urandom(32)`.
2. Encrypt that master key with **DPAPI in user scope**
   (`win32crypt.CryptProtectData(key, None, None, None, None, 0)` — no
   `CRYPTPROTECT_LOCAL_MACHINE` flag).
3. Store the encrypted master key in a dedicated `vault_meta` table.
4. On every subsequent launch: load and decrypt via DPAPI. The master key only
   exists in memory while the app runs.

### Per-entry encryption
- Algorithm: **AES-GCM**, 256-bit key.
- Generate a **fresh 12-byte nonce per encrypt operation** with `os.urandom(12)`.
  Never reuse a nonce with the same key.
- Store `nonce || ciphertext || tag` (or use the cryptography library's built-in
  format) alongside the entry. The nonce is not secret but must be unique.
- Associated data (AAD) optional — if used, bind to entry ID.

### Operational rules
- Passwords are stored **encrypted at rest only**. Decrypt on demand, hold in
  memory only as long as needed.
- Clipboard: when user copies a password, auto-clear after **30 seconds**.
- No logging of plaintext passwords or decrypted content. Ever. Not even on
  ERROR level. Not even during development.
- No network imports (`requests`, `urllib3`, `httpx`, sockets). The app must
  function fully offline. CI should fail if these appear.
- No telemetry, no analytics, no auto-update calls.
- No master password fallback. DPAPI-only by design — if the user's Windows
  account is lost, the vault is lost. Document this clearly in the README.

### Memory hygiene (best-effort)
Python strings are immutable, so true zeroing is not possible. Instead:
- Minimize lifetime of decrypted values.
- Don't hold full vault decrypted in memory; decrypt entries on demand.
- Don't print/repr password fields. Override `__repr__` on the Entry model.

## DB Schema (initial)

```sql
CREATE TABLE vault_meta (
    key TEXT PRIMARY KEY,
    value BLOB NOT NULL
);
-- Stores the DPAPI-encrypted master key under key='master_key'

CREATE TABLE entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    username TEXT,
    password_ct BLOB NOT NULL,   -- ciphertext (nonce + ct + tag)
    url TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,    -- ISO 8601
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_entries_title ON entries(title);

CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE entry_tags (
    entry_id INTEGER REFERENCES entries(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (entry_id, tag_id)
);
```

Use parameterised queries everywhere. **Never** build SQL with f-strings or
`+` concatenation. SQL injection in a password manager is unacceptable.

## Features (MVP)
- [ ] Create / read / update / delete entries
- [ ] Search by title / username (live filter in sidebar)
- [ ] Password generator (see below)
- [ ] Copy password to clipboard with 30s auto-clear
- [ ] CSV import (Chromium browsers: Edge, Chrome, Brave)
- [ ] CSV export (plaintext, with a clear warning dialog)
- [ ] Tags + filter by tag
- [ ] Dark mode (default) + light mode toggle
- [ ] Custom app icon (window + taskbar + .exe)

Out of scope for v1: browser auto-fill, mobile, multi-vault, sync, 2FA storage,
Firefox import (different format, requires NSS).

## Password Generator

- **CSPRNG required**: use Python's `secrets` module, never `random`.
- **Length**: 16–64 characters, default 20.
- **Character classes** (each toggleable in UI, all on by default):
  - lowercase `a-z`
  - uppercase `A-Z`
  - digits `0-9`
  - symbols `!@#$%^&*()-_=+[]{};:,.<>?`
- **Optional toggle**: "exclude ambiguous characters" → removes `0`, `O`, `o`,
  `1`, `l`, `I`, `|`, `` ` ``.
- **Guarantee**: at least 1 character from each enabled class. Implementation:
  pick one per class, fill the rest from the union, shuffle with
  `secrets.SystemRandom().shuffle()`.
- **No biased modulo**: use `secrets.choice(alphabet)`, not `secrets.randbelow(len) % ...`.
- Show entropy estimate in the UI (`log2(alphabet_size) * length` bits).

## CSV Import

All three target browsers (Edge, Chrome, Brave) are Chromium-based and export
the **same CSV format**:

```csv
name,url,username,password,note
```

So: one parser, no per-browser branches. Implementation notes:
- Use `csv.DictReader` with `utf-8-sig` encoding (handles BOM from Excel-saved files).
- Validate required columns (`name`, `url`, `username`, `password`) on first row.
- Map: `name` → `title`, others 1:1. Empty `note` → `NULL` in DB.
- Show a preview table before committing the import.
- On error in a row: skip + log row number to import-report dialog, don't abort
  the whole import.
- After successful import: **prompt user to delete the source CSV file**
  (it contains plaintext passwords).

## App Icon

- Format: `.ico` with embedded sizes 16, 32, 48, 256 px.
- Source: keep a high-res `assets/icon.png` (1024×1024) in the repo, generate
  `.ico` from it. Tool: ImageMagick (`magick icon.png -define icon:auto-resize=256,48,32,16 icon.ico`)
  or online converter.
- Runtime (PySide6):
  ```python
  app.setWindowIcon(QIcon("assets/icon.ico"))
  ```
- Build (PyInstaller): `--icon=assets/icon.ico` flag in the `.spec` file.
- Style direction: minimal, monochrome or two-tone, recognisable at 16px.

## UI Direction
- PySide6 with a QSS stylesheet in `src/gui/styles.qss`.
- Dark mode default. Colors: background `#1e1e2e`, surface `#313244`,
  accent `#89b4fa`, text `#cdd6f4` (Catppuccin Mocha-ish palette).
- Rounded corners (8px) on cards and buttons.
- Layout: left sidebar (search + entry list) ~280px, main pane (entry detail).
- Font: Segoe UI Variable on Windows, fallback sans-serif.
- No emojis in UI text.

## Coding Standards
- Type hints on every function signature.
- Docstrings on every public function (one-line is fine).
- `pathlib.Path` for all filesystem paths, never raw strings.
- f-strings for formatting (except SQL — see above).
- Black formatting, line length 100.
- Imports sorted (isort-compatible).

## Testing Priorities
Critical path first:
1. **`test_crypto.py`** — encrypt/decrypt roundtrip, wrong-key failure,
   tampered-ciphertext detection (GCM tag), nonce uniqueness check.
2. **`test_generator.py`** — length bounds, charset inclusion guarantee,
   uses `secrets` (no `random` import).
3. **`test_db.py`** — schema creation, CRUD, foreign keys, migration safety.
4. **`test_importer.py`** — Chromium CSV parsing, malformed input handling,
   empty fields, special characters, BOM handling.

GUI is not unit-tested — manual test plan in README.

## What NOT to do
- Do not add cloud sync, even as an option.
- Do not log passwords or decrypted content.
- Do not call external services for password strength checks (no HIBP API).
  If needed, implement zxcvbn-python locally.
- Do not use `eval` or `exec` anywhere.
- Do not store the master key in plaintext on disk, ever.
- Do not silently swallow exceptions in the crypto module.
- Do not use `random` module for any password-related randomness — `secrets` only.

## How to talk to me (Luca)
- German is fine, English is fine.
- Explain crypto-related decisions in comments. I want to learn this.
- Before generating a new file, check this CLAUDE.md and confirm the
  approach fits.
- For any change touching `crypto.py`, write or update the corresponding test
  in the same commit.
