from flask import Flask
from itsdangerous import URLSafeTimedSerializer
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = '#!Alph@3!'

# Configurações AlphaFold
ALPHAFOLD_SSH_HOST = os.getenv("ALPHAFOLD_SSH_HOST")
ALPHAFOLD_SSH_PORT = int(os.getenv("ALPHAFOLD_SSH_PORT", 22))
ALPHAFOLD_SSH_USER = os.getenv("ALPHAFOLD_SSH_USER")

ALPHAFOLD_INPUT_BASE = os.getenv("ALPHAFOLD_INPUT_BASE")
ALPHAFOLD_OUTPUT_BASE = os.getenv("ALPHAFOLD_OUTPUT_BASE")
ALPHAFOLD_PARAMS = os.getenv("ALPHAFOLD_PARAMS")
ALPHAFOLD_DB = os.getenv("ALPHAFOLD_DB")

# Configurações de e-mail
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

serializer = URLSafeTimedSerializer(app.secret_key)

# URL base para download
BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")