import sqlite3
import uuid

DB_PATH = "app.db"

def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns

def run_migration():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Add `quote_id` if missing
    if not column_exists(cursor, "quotes", "quote_id"):
        cursor.execute("ALTER TABLE quotes ADD COLUMN quote_id TEXT")
        print("✅ Added 'quote_id' column.")

    # 2. Add `weight_method` if missing
    if not column_exists(cursor, "quotes", "weight_method"):
        cursor.execute("ALTER TABLE quotes ADD COLUMN weight_method TEXT")
        print("✅ Added 'weight_method' column.")

    # 3. Populate missing quote_ids and set default weight method
    cursor.execute("SELECT id, quote_id, weight_method FROM quotes")
    updates = []
    for row in cursor.fetchall():
        quote_id = row[1]
        weight_method = row[2]
        if not quote_id or quote_id.strip() == "":
            new_id = str(uuid.uuid4())
            updates.append((new_id, row[0]))
        if not weight_method:
            cursor.execute("UPDATE quotes SET weight_method = ? WHERE id = ?", ("actual", row[0]))

    for qid, row_id in updates:
        cursor.execute("UPDATE quotes SET quote_id = ? WHERE id = ?", (qid, row_id))

    conn.commit()
    conn.close()
    print(f"✅ Migrated {len(updates)} quotes with new UUIDs.")
    print("✅ Migration complete.")

if __name__ == "__main__":
    run_migration()
