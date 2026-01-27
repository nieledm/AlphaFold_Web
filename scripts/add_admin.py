import sqlite3
import bcrypt

DB_PATH = 'database.db' 

def create_admin():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Verifica se já existe admin
    cursor.execute("SELECT * FROM users WHERE is_admin = 1")
    admin = cursor.fetchone()

    if admin:
        print(f"Já existe um admin cadastrado: {admin[2]} (ID: {admin[0]})")
    else:
        # DADOS DO USUÁRIO
        email = "admin@aplhafold3"
        raw_password = "@Dmin514"
        
        hashed_password = bcrypt.hashpw(raw_password.encode('utf-8'), bcrypt.gensalt())

        # Insere o usuário com a senha criptografada
        cursor.execute("""
            INSERT INTO users (name, email, password, is_admin, is_active)
            VALUES (?, ?, ?, ?, ?)
        """, ("admin", email, hashed_password, 1, 1))

        conn.commit()
        print(f"Sucesso! Usuário '{email}' criado com hash seguro.")

    conn.close()

if __name__ == "__main__":
    create_admin()