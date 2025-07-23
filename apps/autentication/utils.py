from flask import session, redirect, url_for, flash
from functools import wraps
import re

# ==============================================================
# DECORADORES DE AUTENTICAÇÃO E AUTORIZAÇÃO
# ==============================================================

def login_required(f):
    """
    Decorador para rotas que exigem que o usuário esteja logado.
    Redireciona para a página de login se o usuário não estiver na sessão.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Você precisa estar logado para acessar esta página.', 'warning')
            return redirect(url_for('aut.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """
    Decorador para rotas que exigem que o usuário seja um administrador.
    Redireciona para o dashboard ou página de login se não for admin.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Você precisa estar logado para acessar esta página.', 'warning')
            return redirect(url_for('aut.login'))
        if not session.get('is_admin'):
            flash('Acesso não autorizado. Apenas administradores podem acessar esta página.', 'danger')
            return redirect(url_for('users.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def validar_nome(nome):
    return len(nome.strip().split()) >= 2

def validar_email(email):
    dominios = ['unicamp', 'unesp', 'usp', 'fatec', 'unifesp', 'unb', 'ufrj', 'ufmg', 'ufrgs', 'unc.edu']
    return any(d in email.lower() for d in dominios)

def validar_senha(senha):
    regex = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$')
    return regex.match(senha)