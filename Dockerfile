FROM python:3.11-slim

# Evitar arquivos .pyc e buffer de logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    libgfortran5 \
    openssh-client \
    git \
    && rm -rf /var/lib/apt/lists/*

# Criar um usuário não-root
RUN useradd -m -u 1003 alphaFoldWeb

# --- Configuração do VENV ---
ENV ALPHAFOLD_ENV=/opt/venv
RUN python3 -m venv $ALPHAFOLD_ENV
ENV PATH="$ALPHAFOLD_ENV/bin:$PATH"

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- Configuração da Aplicação ---
WORKDIR /app

# 1. Copia o código
COPY . /app

# 2. Permissão para o usuário não-root ser dono dos arquivos
RUN chown -R alphaFoldWeb:alphaFoldWeb /app

# Muda para o usuário
USER alphaFoldWeb

# Expõe a porta correta
EXPOSE 5055

# 3. CRÍTICO: 
# - Usa a porta 5055 (para bater com o expose)
# - Usa worker eventlet (para o SocketIO funcionar)
# - Apenas 1 worker é recomendado para SocketIO (a não ser que use Redis)
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "-b", "0.0.0.0:5055", "app:app"]