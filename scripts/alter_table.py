import sqlite3

# Conecta ao banco existente
conn = sqlite3.connect('D:/CQMED/AFweb/database.db')
cursor = conn.cursor()

cursor.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 0;")

conn.commit()
print("Usuário admin criado com sucesso!")

conn.close()