# PassSimple

Local-only password manager for Windows.

## Features
- AES-256-GCM encryption per entry
- Master key protected by Windows DPAPI (no master password to remember)
- Fully offline — no network, no telemetry, no cloud sync
- CSV import from Chromium-based browsers (Chrome, Edge, Brave)
- Password generator with configurable character classes and entropy estimate
- Dark mode (Catppuccin Mocha palette) with optional light mode
- Auto-clears clipboard after 30 seconds

## Requirements
- Windows 10/11
- Python 3.12+

## Installation

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Running

```powershell
python -m src.app
```

## Running Tests

```powershell
pytest
```

## Building the Executable

```powershell
pyinstaller build/passsimple.spec
```

The output `.exe` will be in `dist/`.

## Vault Location

The vault is stored at:

```
%LOCALAPPDATA%\PassSimple\vault.db
```

## Security Model

PassSimple uses **Windows DPAPI** (Data Protection API) to encrypt the
AES-256 master key. DPAPI binds protection to your **Windows user account** —
no separate master password is needed or stored.

> **Important:** If your Windows user account is lost, corrupted, or
> migrated to a new machine without a proper profile export, **the vault
> cannot be decrypted**. There is no recovery path by design.
> Back up your passwords before reinstalling Windows or changing accounts.

Each entry's password is encrypted individually with AES-256-GCM using a
unique random nonce. Only the encrypted blob is written to disk; plaintext
exists in memory only for the brief moment it is displayed or copied.

## License

MIT — see [LICENSE](LICENSE) for details.
