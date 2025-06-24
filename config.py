from flask import Flask, url_for
from itsdangerous import URLSafeTimedSerializer

app = Flask(__name__)
app.secret_key = '#!Alph@3!'

# Configuração conexão Horizon
ALPHAFOLD_SSH_HOST = '143.106.4.186'
ALPHAFOLD_SSH_PORT = 2323
ALPHAFOLD_SSH_USER = 'alphaFoldWeb'

# Configurações AlphaFold
ALPHAFOLD_INPUT_BASE = '/str1/projects/AI-DD/alphafold3/alphafold3_input'
ALPHAFOLD_OUTPUT_BASE = '/str1/projects/AI-DD/alphafold3/alphafold3_output'
ALPHAFOLD_PARAMS = '/str1/projects/AI-DD/alphafold3/alphafold3_params'
ALPHAFOLD_DB = '/str1/projects/AI-DD/alphafold3/alphafold3_DB'

# Configurações de e-mail
EMAIL_SENDER = 'nieledm@gmail.com'
EMAIL_PASSWORD = 'zlde qbxb zvif bfpg'
serializer = URLSafeTimedSerializer(app.secret_key)