import sqlite3

# Conecta ao banco existente
conn = sqlite3.connect('D:/CQMED/AFweb/database.db')
cursor = conn.cursor()

cursor.execute(
    """CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        is_admin INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 0
    );"""
)

cursor.execute(
    """CREATE TABLE uploads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        file_name TEXT NOT NULL,
        base_name TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        priority INTEGER DEFAULT 0,
        job_id VARCHAR(20),
        updated_at DATETIME,
        details TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );"""
)

cursor.execute(
   """ CREATE TABLE logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        details TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );"""
)

cursor.execute(
    """CREATE TABLE config (
        key TEXT PRIMARY KEY,
        value TEXT
    );"""
)

cursor.execute(
    """CREATE TABLE sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        session_token TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );"""
)

conn.commit()
conn.close()