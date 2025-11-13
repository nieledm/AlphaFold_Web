from dotenv import dotenv_values, set_key
import os

ENV_PATH = os.path.join(os.getcwd(), ".env")

def get_env_variables():
    """Retorna todas as variáveis do .env como dicionário"""
    return dotenv_values(ENV_PATH)

def update_env_variable(key, value):
    """Atualiza ou adiciona uma variável no .env"""
    set_key(ENV_PATH, key, value)