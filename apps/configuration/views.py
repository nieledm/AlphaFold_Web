from flask import Blueprint, render_template, request, flash, redirect, url_for, session
import os
from dotenv import dotenv_values, set_key

config_bp = Blueprint('config', __name__)

ENV_PATH = os.path.join(os.getcwd(), ".env")

def get_env_description(key):
    """Retorna a descrição para cada variável de ambiente"""
    descriptions = {
        'SECRET_KEY': 'Chave secreta para segurança da aplicação Flask. Deve ser uma string longa e aleatória.',
        'ALPHAFOLD_SSH_HOST': 'Endereço do servidor SSH onde o AlphaFold está instalado.',
        'ALPHAFOLD_SSH_PORT': 'Porta SSH do servidor (padrão: 22).',
        'ALPHAFOLD_SSH_USER': 'Usuário para conexão SSH com o servidor.',
        'ALPHAFOLD_INPUT_BASE': 'Diretório base no servidor para arquivos de entrada do AlphaFold.',
        'ALPHAFOLD_OUTPUT_BASE': 'Diretório base no servidor para arquivos de saída do AlphaFold.',
        'ALPHAFOLD_PARAMS': 'Caminho para os parâmetros e modelos do AlphaFold.',
        'ALPHAFOLD_DB': 'Caminho para os bancos de dados do AlphaFold.',
        'ALPHAFOLD_PREDICTION': 'Configurações específicas para predições do AlphaFold.',
        'EMAIL_SENDER': 'Endereço de email para envio de notificações.',
        'EMAIL_PASSWORD': 'Senha do email para autenticação SMTP.',
        'BASE_URL': 'URL base da aplicação para links em emails e notificações.',
        'DATABASE_URL': 'URL de conexão com o banco de dados.',
        'DEBUG': 'Modo de desenvolvimento (True/False). Em produção deve ser False.',
        'LOG_LEVEL': 'Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL).',
    }
    return descriptions.get(key, 'Variável de configuração do sistema.')

def get_env_variables():
    """Retorna todas as variáveis do .env como dicionário"""
    return dotenv_values(ENV_PATH)

def update_env_variable(key, value):
    """Atualiza ou adiciona uma variável no .env"""
    set_key(ENV_PATH, key, value)

@config_bp.route('/admin/settings', methods=['GET', 'POST'])
def settings():
    if not session.get('is_admin'):
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('users.dashboard'))
    if request.method == 'POST': 
        # Lógica para salvar as variáveis
        env_vars = get_env_variables()
        for key in env_vars.keys():
            new_value = request.form.get(key)
            if new_value is not None:
                update_env_variable(key, new_value)
        
        flash('Configurações salvas com sucesso!', 'success')
        return redirect(url_for('config.settings'))
    
    # Método GET - mostrar as configurações
    env_vars = get_env_variables()
    
    return render_template('settings.html',
                            titulo='Configurações do Sistema',
                            active_page='settings',
                            nome_usuario=session.get('user_name', 'Usuário'),
                            env_vars=env_vars,
                            get_env_description=get_env_description)

