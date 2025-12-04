import sqlite3
import os

DATABASE = 'database.db'

def configure_sqlite(conn):
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute("PRAGMA temp_store=MEMORY;")
    cursor.execute("PRAGMA locking_mode=NORMAL;")
    cursor.execute("PRAGMA busy_timeout=5000;")
    cursor.close()

# def get_db_connection():
#     """Retorna uma conexão com o banco de dados"""
#     conn = sqlite3.connect(DATABASE)
#     conn.row_factory = sqlite3.Row
#     return conn

def get_db_connection():
    """Retorna uma conexão com o banco de dados"""
    conn = sqlite3.connect(
        DATABASE,
        check_same_thread=False,
        timeout=10
    )
    conn.row_factory = sqlite3.Row

    configure_sqlite(conn)  # <- IMPORTANTE PARA NÃO TER PROBLEMAS DE CONCORRÊNCIA NO SQLITE

    return conn


def init_db():
    """Inicializa o banco de dados com as tabelas necessárias"""
    db_dir = os.path.dirname(DATABASE)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)

    conn = get_db_connection()
    c = conn.cursor()

    # Verifica e cria a tabela users se não existir
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 0
        )
    ''')

    # Verifica e cria a tabela uploads se não existir
    c.execute('''
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            file_name TEXT NOT NULL,
            base_name TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            priority INTEGER DEFAULT 0,
            details TEXT,
            job_id VARCHAR(20),
            updated_at DATETIME,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Verifica e cria a tabela logs se não existir
    c.execute('''
    CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            details TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Verifica e cria a tabela config se não existir
    c.execute('''
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    conn.commit()
    conn.close()
    
def get_user_by_email(email):
    """Busca um usuário pelo e-mail"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email = ?', (email,))
        return c.fetchone()