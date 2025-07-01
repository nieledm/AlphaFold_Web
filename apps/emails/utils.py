from flask import url_for
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from smtplib import SMTP_SSL
from database import get_db_connection

from apps.logs.utils import log_action

from config import EMAIL_SENDER, EMAIL_PASSWORD

from flask import Blueprint
emails_bp = Blueprint('emails', __name__, template_folder='../../templates')

# ==============================================================
# FUNÇÕES DE E-MAIL
# ==============================================================
def send_email(to_email, subject, html_content):
    """Função genérica para enviar e-mails"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = to_email
    msg.attach(MIMEText(html_content, "html"))
    
    try:
        with SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, to_email, msg.as_string())
            log_action('', 'Envio de email', 'Sucesso no envio')

        return True
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")
        log_action('', 'Envio de email', 'Erro no envio')
        return False

def send_verification_email(name, email, token):
    """Envia e-mail de verificação para novo usuário"""
    verification_url = url_for('aut.confirm_email', token=token, _external=True)
    html = f"""
    <html>
        <body>
            <p>Olá {name},</p>
            <p>Por favor, confirme seu e-mail clicando no link abaixo:</p>
            <p><a href="{verification_url}">Confirmar e-mail</a></p>
        </body>
    </html>
    """
    send_email(email, "Confirme seu e-mail", html)

def send_admin_notification(name, email):
    """Notifica administradores sobre novo usuário pendente"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT email FROM users WHERE is_admin = 1')
        admins = c.fetchall()
    
    html = f"""
    <html>
        <body>
            <p>Olá,</p>
            <p>O usuário {name} ({email}) confirmou o seu e-mail para usar o AlphaFold e aguarda aprovação.</p>
            <p>Por favor, acesse o painel de administração para aprovar ou rejeitar a solicitação.</p>
        </body>
    </html>
    """
    
    for admin in admins:
        send_email(admin[0], "Novo usuário aguardando aprovação no AlphaFold", html)

def send_activation_email(user_email, user_name):
    """Envia e-mail de confirmação de ativação da conta"""
    html = f"""
    <html>
        <body>
            <p>Olá {user_name},</p>
            <p>Sua conta foi ativada com sucesso!</p>
            <p>Agora você pode acessar o sistema.</p>
        </body>
    </html>
    """
    send_email(user_email, "Sua conta no AlphaFold foi ativada", html)

def send_processing_complete_email(user_name, user_email, base_name, user_id):
    """Envia e-mail ao usuário informando que o processamento foi concluído"""
    try:
        download_url = url_for('apf.download_result', base_name=base_name, _external=True)
    except Exception as e:
        print(f"[ERRO] Falha ao gerar link de download: {e}")
        download_url = "[Erro ao gerar link]"

    html = f"""
    <html>
        <body>
            <p>Olá {user_name},</p>
            <p>Seu processamento com o AlphaFold foi concluído com sucesso.</p>
            <p>Você pode baixar o resultado indo ao seu dashboard ou clicando no link abaixo:</p>
            <p><a href="{download_url}">Download do resultado</a></p>
            <p>Obrigado por usar o sistema AlphaFold!</p>
        </body>
    </html>
    """
    send_email(user_email, "AlphaFold: Resultado disponível", html)