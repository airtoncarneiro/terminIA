# terminIA

Plataforma experimental para orquestrar um agente de IA com duas partes principais:
1. **API de Terminal** (FastAPI + Docker) que executa comandos no host/container.
2. **Infra de LLM local** (Ollama + opcional Open WebUI) para interface humana/LLM sem depender de provedores externos.

> Use de forma responsável. A API de terminal pode executar comandos do sistema e acessar o Docker host via `docker.sock`.

## Estrutura do repositório
- `docker/api_terminal/` — API de terminal (FastAPI) que expõe `POST /run`.
- `docker/ollama/` — Infra Docker/Compose para rodar Ollama e, opcionalmente, Open WebUI.
- `__pycache__/` — artefatos de execução em Python (pode ser ignorado).

## Visão geral da arquitetura
- Um cliente (UI/LLM) envia comandos para a **API de Terminal**.
- A API valida (whitelist em dev, liberado em prod), executa via `subprocess` e retorna stdout/stderr/código de saída.
- Em paralelo, você pode rodar **Ollama** para servir modelos locais e usar o **Open WebUI** como front-end de chat.

## API de Terminal (`docker/api_terminal`)
- **Arquivo principal:** `terminal_api.py`
- **Endpoint:** `POST /run`
- **Payload:**
  ```json
  {
    "binary": "ls",
    "args": ["-la", "/"]
  }
  ```
- **Headers:** `X-API-Key: <sua-chave>` (a validação está comentada no código; descomente em produção).
- **Resposta:** comando executado, stdout, stderr, returncode, environment.

### Segurança e ambientes
- Variáveis:
  - `TERMINAL_API_KEY` (obrigatória).
  - `APP_ENV` (`dev` | `prod`), default `dev`.
- Em `dev`: só executa binários da whitelist (`ALLOWED_BINARIES`).
- Em `prod`: não há restrição de binários (use com cautela).
- Timeout padrão: 30s.

### Build e execução (Docker)
```bash
cd docker/api_terminal
docker build -t terminal-api .
docker run --rm \
  -e TERMINAL_API_KEY="sua-chave" \
  -p 8000:8000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --name terminal-api \
  terminal-api
```

Rodar em background:
```bash
docker run -d --rm \
  -e TERMINAL_API_KEY="sua-chave" \
  -p 8000:8000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --name terminal-api \
  terminal-api
```

Executar local (sem Docker):
```bash
cd docker/api_terminal
export TERMINAL_API_KEY="sua-chave"
export APP_ENV=dev  # ou prod
uvicorn terminal_api:app --host 0.0.0.0 --port 8000
```

### Testes rápidos
```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sua-chave" \
  -d '{"binary": "ls", "args": ["-la", "/"]}'
```

## Infra de LLM (`docker/ollama`)
- **Dockerfile** mínimo para usar `ollama/ollama:latest` na porta 11434.
- **Compose** opcional com dois serviços:
  - `ollama` (API em `http://localhost:11434`)
  - `openwebui` (UI em `http://localhost:3000`, com `OLLAMA_BASE_URL=http://ollama:11434`)

### Subir com Docker direto
```bash
cd docker/ollama
docker build -t my-ollama .
docker run -d --name ollama \
  -p 11434:11434 \
  -v ollama_models:/root/.ollama \
  my-ollama
```

### Subir com Docker Compose
```bash
cd docker/ollama
docker compose up -d
# UI em http://localhost:3000 (Open WebUI)
```

### Testar Ollama
```bash
curl http://localhost:11434/api/version
docker exec -it ollama ollama pull phi3:mini
docker exec -it ollama ollama run deepseek-r1:1.5b
```

## Fluxo sugerido (agente)
1. Suba a API de terminal e Ollama.
2. Use a UI/LLM (ex.: Open WebUI) para gerar comandos.
3. Encaminhe comandos via `POST /run` para execução controlada.
4. Valide outputs e registre logs para auditoria.

## Pontos de atenção
- Proteja o `TERMINAL_API_KEY` e considere restringir IPs/outras camadas de rede.
- Só monte `docker.sock` se precisar de controle total do host.
- Revise a whitelist em `ALLOWED_BINARIES` para o modo `dev`.
- Avalie monitoração/logging adicional antes de expor publicamente.

## Próximos passos
- Descomentar a validação de `X-API-Key` em `docker/api_terminal/terminal_api.py`.
- Adicionar testes automatizados para a API (ex.: `pytest` + `httpx`).
- Implementar auditoria de comandos executados e limites de taxa.
- Integrar um cliente UI (Open WebUI ou outro) chamando `POST /run` para fechar o loop do agente.
