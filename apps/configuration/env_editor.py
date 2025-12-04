from dotenv import dotenv_values, set_key
import os

ENV_PATH = os.path.join(os.getcwd(), ".env")

def get_env_variables():
    """Retorna todas as variáveis do .env como dicionário"""
    return dotenv_values(ENV_PATH)

def update_env_variable(key, value):
    """Atualiza ou adiciona uma variável no .env"""
    set_key(ENV_PATH, key, value)

def remote_join(*parts):
    cleaned = []
    for p in parts:
        if not p:
            continue
        # remove only trailing slashes
        cleaned.append(str(p).rstrip("/"))
    result = "/".join(cleaned)
    # ensure leading slash if original first part had it
    if str(parts[0]).startswith("/"):
        result = "/" + result.lstrip("/")
    return result