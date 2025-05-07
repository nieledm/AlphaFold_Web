import sqlite3

# Conecta ao banco existente
conn = sqlite3.connect('D:/CQMED/AFweb/database.db')
cursor = conn.cursor()

cursor.execute(
    """CREATE TABLE uploads(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    file_name TEXT,
    base_name TEXT,
    status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )"""
)

conn.commit()
conn.close()