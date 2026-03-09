import sqlite3

conn = sqlite3.connect("database.db")
c = conn.cursor()

# Add sold column if not exists
try:
    c.execute("ALTER TABLE tickets ADD COLUMN sold INTEGER DEFAULT 0")
    print("sold column added!")
except Exception as e:
    print(f"Column already exists: {e}")

# Mark all existing tickets as sold=1
c.execute("UPDATE tickets SET sold=1 WHERE sold=0 OR sold IS NULL")
print(f"Updated {c.rowcount} tickets to sold=1")

conn.commit()
conn.close()
print("Done! ✅")







