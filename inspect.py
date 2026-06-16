import os, sqlite3
db = os.path.join(os.environ["LOCALAPPDATA"], "PassSimple", "vault.db")
conn = sqlite3.connect(db)
rows = conn.execute("SELECT id, title, username, url, length(password_ct), length(notes), created_at FROM entries").fetchall()
print(f"{'id':>3} | {'title':<20} | {'username':<20} | {'url':<25} | pwlen | nlen | created")
print("-" * 120)
for r in rows:
    print(f"{r[0]:>3} | {str(r[1])[:20]:<20} | {str(r[2])[:20]:<20} | {str(r[3])[:25]:<25} | {r[4]:>5} | {r[5] if r[5] else '-':>4} | {r[6]}")
