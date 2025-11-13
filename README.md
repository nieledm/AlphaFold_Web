# AlphaFold_Web

Aplicação web para gestão de jobs do AlphaFold com painel administrativo, uploads em JSON, geração de inputs e atualizações em tempo real via Socket.IO.

Este repositório contém uma aplicação Flask com suporte a WebSocket (Flask-SocketIO), clientes JS para atualização em tempo real nas páginas de Status, Dashboard e Logs, além de utilitários para gerar arquivos JSON de entrada para o AlphaFold.

## Sumário

- Sobre
- Pré-requisitos
- Instalação
- Configuração
- Arquitetura e principais arquivos
- Como rodar (desenvolvimento)
- Como funciona a atualização em tempo real (Socket.IO)
- Personalizações úteis
- Depuração e troubleshooting
- Contribuindo
- Licença

## Sobre

O sistema permite que usuários façam upload de um arquivo JSON (gerado no builder), acompanhem o status do processamento (jobs) e que administradores visualizem logs e números de uso do servidor (CPU/GPU/Memória). A comunicação em tempo real é feita com Socket.IO para evitar reloads manuais.

## Pré-requisitos

- Python 3.8+ (recomendado 3.10+)
- virtualenv ou outro gerenciador de ambiente
- Node/npm não é obrigatório para rodar (os assets já estão no projeto).
- Acesso a um servidor onde o AlphaFold é executado (opcional, para monitoramento remoto via SSH)

## Instalação

1. Clone o repositório e entre na pasta do projeto:

```powershell
cd D:\CQMED\AFweb
```

2. Crie e ative um ambiente virtual (Windows PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Instale dependências:

```powershell
pip install -r requirements.txt
```

Observação: se faltar algum pacote (por exemplo `python-dotenv`), instale manualmente:

```powershell
pip install python-dotenv flask-socketio
```

## Configuração

As variáveis de configuração ficam em `config.py` (e podem ser carregadas de `.env` caso você use `python-dotenv`). Variáveis importantes:

- `ALPHAFOLD_SSH_HOST` - host SSH para coletar métricas (se usar monitoramento remoto)
- `ALPHAFOLD_SSH_PORT` - porta SSH
- `ALPHAFOLD_SSH_USER` - usuário SSH
- Variáveis de DB/paths: `ALPHAFOLD_DB`, `ALPHAFOLD_INPUT_BASE`, `ALPHAFOLD_OUTPUT_BASE` etc.

Se quiser usar `.env`, crie um arquivo na raiz com as variáveis de ambiente (exemplo mínimo):

```
FLASK_ENV=development
SECRET_KEY=uma_chave_secreta_aqui
ALPHAFOLD_SSH_HOST=server.example.com
ALPHAFOLD_SSH_PORT=22
ALPHAFOLD_SSH_USER=user
# ... outras variáveis necessárias
```

Depois, confirme que `config.py` lê essas variáveis (o projeto já usa `python-dotenv` por padrão).

## Arquitetura e principais arquivos

- `app.py` - ponto de entrada da aplicação; cria o `Flask` app, registra blueprints e inicializa `SocketIO`.
- `config.py` - configurações da aplicação (paths, SSH, keys)
- `database.py` - conexão com SQLite (função `get_db_connection()`)
- `apps/` - módulos organizados por responsabilidade:
  - `monitor/` - views do painel, utilitários e os eventos Socket.IO (`apps/monitor/socket_events.py`)
  - `alphafold/` - builder e views específicas do AlphaFold
  - `logs/` - visualização e filtros de logs
  - `autentication/`, `users_rotas/`, `admin_rotas/` - autenticação e rotas relacionadas aos usuários
- `static/js/` - clientes Socket.IO e scripts da interface
  - `socket_status_client.js` - atualizações da página de status
  - `socket_dashboard_client.js` - atualizações do dashboard (jobs)
  - `socket_logs_client.js` - atualizações da página de logs
- `templates/` - arquivos HTML Jinja2 (status_page.html, dashboard.html, logs.html, builder_json_form.html, etc.)

### Padrões

- Updates em tempo real:
  - Status: 5s
  - Dashboard (jobs): 3s
  - Logs: 4s

Esses intervalos são definidos pelo servidor nos handlers em `apps/monitor/socket_events.py` (funções que emitem periodicamente em threads background). O cliente apenas inicia/parar as atualizações na carga/saída da página.

## Como rodar (desenvolvimento)

1. Ative o virtualenv (veja seção Instalação).
2. Configure `config.py` / `.env` com as variáveis necessárias.
3. Inicie a aplicação:

```powershell
python app.py
```

Observações:

- `app.py` cria a instância `socketio = SocketIO(app, cors_allowed_origins="*")` e registra os handlers do módulo `apps.monitor.socket_events`.
- Se mudar código Python, reinicie o servidor.

## Como funciona a atualização em tempo real (Socket.IO)

Fluxo resumido:

1. O cliente inclui o script `https://cdn.socket.io/4.5.4/socket.io.min.js` e um dos arquivos `static/js/socket_*_client.js` na página.
2. Ao carregar a página, o cliente conecta-se ao servidor Socket.IO (`const socket = io();`) e pede uma atualização inicial.
3. O servidor, implementado em `apps/monitor/socket_events.py`, registra handlers que:
   - Respondem requisições pontuais (`request_status_update`, `request_user_jobs_update`, `request_logs_update`)
   - Iniciam threads que emitem periodicamente para a sessão/cliente (`start_live_updates`, `start_jobs_live_updates`, `start_logs_live_updates`).
4. Cada emissão contém um payload JSON com os dados necessários. Exemplo (status):

```json
{
  "status": { /* cpu, mem, gpu, disk */ },
  "running_count": 2,
  "pending_count": 5,
  "timestamp": 169...
}
```

No cliente, os handlers atualizam o DOM (barras, tabelas e badges). O projeto foi ajustado para não mostrar mais o relógio de "última atualização" — as atualizações ocorrem silenciosamente.

### Observações sobre implementação

- O código do servidor usa threads por sessão com *stop flags* para controlar o ciclo de emissão. Isso evita que threads órfãs continuem após o cliente desconectar.
- Os handlers são registrados de forma programática (função `register_socketio_handlers(socketio)`), para garantir que `socketio` esteja inicializado antes de aplicar os decoradores.
- Broadcasts direcionados usam `socketio.emit(..., to=session_id)` para enviar apenas ao cliente alvo.

## Personalizações úteis

- Ajustar intervalos: em `apps/monitor/socket_events.py`, altere os `time.sleep()` dentro das funções das threads (5s, 3s, 4s).
- Limitar volume de logs: a query de logs já usa `LIMIT 100`; ajuste conforme necessidade.
- Paginação de logs: para muitos registros, adicione paginação (offset/limit) no query e no cliente.
- Namespaces/rooms: se quiser separar tráfego entre páginas, considere usar namespaces `socketio = SocketIO(..., ...)` e `socket.on('event', namespace='/status')`.

## Depuração e troubleshooting

- Erros comuns ao iniciar:
  - ModuleNotFoundError (ex: dotenv): ative o virtualenv e rode `pip install -r requirements.txt`.
  - ImportError related to socketio being None: isso indicava registros de handlers antes de criar a instância; a versão atual registra via `register_socketio_handlers()` do `apps/monitor/socket_events.py` a partir de `app.py`.

- Verificar logs do servidor: execute `python app.py` e observe a saída no console. Mensagens e exceptions do Socket.IO são printadas lá.

- Verificar conexão no browser: abra DevTools (F12) > aba Network > filter `ws` (WebSocket) para confirmar handshake com `socket.io/?EIO=4...` e assinar eventos na aba Console (o cliente já faz console.log nas conexões e updates).

- Se o cliente não receber atualizações:
  - Confirme que `socketio` está inicializado e `register_socketio_handlers()` foi chamado em `app.py`.
  - Verifique se a sessão (cookie) é preservada e contém `session_id` ou `user_id` usados para direcionamento.

## Testes rápidos (smoke tests)

1. Inicie a aplicação localmente.
2. Acesse `/status`, verifique que as barras de CPU/Mem/GPU aparecem e que o console do browser mostra `Status atualizado` logs.
3. Acesse `/dashboard` logado com um usuário; crie/ponha um job e veja se aparece/atualiza no dashboard.
4. Acesse `/logs` como admin, aplique um filtro e veja novas linhas aparecendo quando ações são geradas.

## Segurança

- As rotas de logs e certas ações administrativas devem ser restritas a usuários admin; o código usa `session.get('is_admin')` para validar.
- Sanitize de filenames e inputs é aplicado no builder e nos handlers; confirme sempre se aceita apenas os caracteres esperados.

## Contribuindo

1. Faça um fork e crie uma branch para sua feature/fix.
2. Abra um pull request descrevendo as mudanças. Inclua comandos para reproduzir as alterações localmente.

## Observações finais e próximos passos sugeridos

- Melhorar controle de threads com `asyncio`/`eventlet`/`gevent` para escalabilidade.
- Adicionar paginação de logs e métricas históricas (prometheus/grafana).
- Migrar o backend Socket.IO para namespaces ou salas para reduzir ruído entre páginas.

---

Se quiser, eu adapto o README com instruções específicas do seu ambiente (ex.: caminhos do AlphaFold, autenticação SSH, exemplos de `.env`) — diga o que prefere que eu adicione.
