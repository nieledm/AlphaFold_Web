import eventlet
eventlet.monkey_patch()  # SEMPRE EM PRIMEIRO

import os, sys
from flask import Flask, request, g, jsonify
from flask_socketio import SocketIO
from itsdangerous import URLSafeTimedSerializer
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# -------------------------------------------------------------
# 🔍 Verificação de variáveis obrigatórias do .env
# -------------------------------------------------------------

REQUIRED_VARS = [
    "SECRET_KEY",
    "ALPHAFOLD_SSH_HOST",
    "ALPHAFOLD_SSH_PORT",
    "ALPHAFOLD_SSH_USER",
    "ALPHAFOLD_INPUT_BASE",
    "ALPHAFOLD_OUTPUT_BASE",
    "ALPHAFOLD_PARAMS",
    "ALPHAFOLD_DB",
    "EMAIL_SENDER",
    "EMAIL_PASSWORD",
]

missing_vars = [var for var in REQUIRED_VARS if not os.getenv(var)]

if missing_vars:
    print("❌ Erro: variáveis obrigatórias ausentes no .env:")
    for var in missing_vars:
        print(f"   - {var}")
    print("\nCorrija o arquivo .env antes de iniciar o aplicativo.")
    sys.exit(1)
else:
    print("✅ Todas as variáveis obrigatórias foram carregadas com sucesso.")

# -------------------------------------------------------------
# 🔧 Configuração do app Flask
# -------------------------------------------------------------

app = Flask(__name__)
SECRET_KEY = os.getenv('SECRET_KEY')
app.secret_key = SECRET_KEY

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Configurações AlphaFold
ALPHAFOLD_SSH_HOST = os.getenv("ALPHAFOLD_SSH_HOST")
ALPHAFOLD_SSH_PORT = int(os.getenv("ALPHAFOLD_SSH_PORT", 22))
ALPHAFOLD_SSH_USER = os.getenv("ALPHAFOLD_SSH_USER")

ALPHAFOLD_INPUT_BASE = os.getenv("ALPHAFOLD_INPUT_BASE")
ALPHAFOLD_OUTPUT_BASE = os.getenv("ALPHAFOLD_OUTPUT_BASE")
ALPHAFOLD_PARAMS = os.getenv("ALPHAFOLD_PARAMS")
ALPHAFOLD_DB = os.getenv("ALPHAFOLD_DB")


ALPHAFOLD_PREDICTION=os.getenv("ALPHAFOLD_PREDICTION") # Diretório padrão para salvar predições

# Configurações de e-mail
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

serializer = URLSafeTimedSerializer(app.secret_key)

# URL base para download
BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")