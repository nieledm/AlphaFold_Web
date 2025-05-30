import sqlite3

# Conecta ao banco existente
conn = sqlite3.connect('D:/CQMED/AFweb/database.db')
cursor = conn.cursor()

# Verifica se já existe algum admin
cursor.execute("SELECT * FROM users WHERE is_admin = 1")
admin = cursor.fetchone()

if admin:
    print("Já existe um admin cadastrado:", admin)
else:
    # Insere um usuário admin
    cursor.execute("""
        INSERT INTO users (name, email, password, is_admin, is_active)
        VALUES (?, ?, ?, ?, ?)
    """, ("Niele", "nieledm@gmail.com", "123", 1, 1))

    conn.commit()
    print("Usuário admin criado com sucesso!")

conn.close()