"""Build-time metadata injected by build.ps1 before PyInstaller runs.

In development (default state) COMMIT_HASH is 'dev' and BUILD_DATE is empty.
build.ps1 overwrites this file with the real values before bundling, then
restores the defaults so the working tree stays clean between builds.
Do NOT add this file to .gitignore -- the defaults must be committed.
"""

COMMIT_HASH: str = "dev"
BUILD_DATE: str = ""
