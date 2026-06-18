import os, sqlite3
db = os.path.join(os.environ["LOCALAPPDATA"], "PassSimple", "vault.db")
conn = sqlite3.connect(db)
row = conn.execute("SELECT value FROM vault_meta WHERE key='schema_version'").fetchone()
print("schema_version:", int(row[0]))
cols = [r[1] for r in conn.execute("PRAGMA table_info(entries)").fetchall()]
print("columns:", cols)
