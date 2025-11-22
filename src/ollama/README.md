# 🐳 Executando Ollama dentro de um Container Docker

Este guia explica como instalar, buildar e executar o **Ollama** dentro
de um container Docker, permitindo que você use modelos LLM através da
API local em `http://localhost:11434`.

------------------------------------------------------------------------

## 📌 Requisitos

-   Docker instalado\
-   (Opcional) Docker Compose instalado\
-   Sistema operacional: Linux, macOS ou Windows

------------------------------------------------------------------------

# 🚀 1. Clonar ou criar o diretório do projeto

``` bash
mkdir ollama-docker
cd ollama-docker
```

------------------------------------------------------------------------

# 🚀 2. Criar os arquivos

Crie os arquivos abaixo:

### **Dockerfile**

``` dockerfile
FROM ollama/ollama:latest

RUN mkdir -p /root/.ollama

EXPOSE 11434

CMD ["serve"]
```

### **docker-compose.yml (opcional)**

``` yaml
version: '3.9'

services:
  ollama:
    build: .
    container_name: ollama
    restart: unless-stopped
    ports:
      - "11434:11434"
    volumes:
      - ollama_models:/root/.ollama

volumes:
  ollama_models:
```

------------------------------------------------------------------------

# 🏗️ 3. Build da imagem

### Usando Docker diretamente:

``` bash
docker build -t my-ollama .
```

### Usando Docker Compose:

``` bash
docker compose build
```

------------------------------------------------------------------------

# ▶️ 4. Executar o servidor Ollama

### Via Docker:

``` bash
docker run -d --name ollama \
  -p 11434:11434 \
  -v ollama_models:/root/.ollama \
  my-ollama
```

### Via Docker Compose:

``` bash
docker compose up -d
```

------------------------------------------------------------------------

# 🔍 5. Testar se o servidor está funcionando

``` bash
curl http://localhost:11434/api/version
```

Resposta esperada:

``` json
{"version":"0.3.x"}
```

------------------------------------------------------------------------

# 📥 6. Baixar um modelo dentro do container

``` bash
docker exec -it ollama ollama pull phi3:mini

docker exec -it ollama run deepseek-r1:1.5b
```

## para listar os modelos baixados
``` bash
docker exec -it ollama ollama list
```

## para remover um modelo
``` bash
docker exec -it ollama rm qwen2.5:4b
```

------------------------------------------------------------------------

# 🤖 7. Usar um modelo

``` bash
curl http://localhost:11434/api/generate -d '{
  "model": "phi3:mini",
  "prompt": "Explique buffer overflow."
}'
```

------------------------------------------------------------------------

# 🛑 8. Parar e remover o container

### Via docker:

``` bash
docker stop ollama
docker rm ollama
```

### Via docker-compose:

``` bash
docker compose down
```

------------------------------------------------------------------------

# 💾 Onde ficam os modelos?

Eles são salvos dentro do volume Docker:

    ollama_models:/root/.ollama

Isso garante persistência mesmo após remover ou rebuildar o container.

------------------------------------------------------------------------

# 🎯 Conclusão

Agora você tem:

✔ Ollama containerizado\
✔ Persistência dos modelos\
✔ API exposta em `localhost:11434`\
✔ Pronto para integrar com qualquer app (Python, JS, PHP, Postman etc.)

Se quiser, posso gerar também:

-   exemplo de consumo via **PHP**\
-   exemplo via **Python**\
-   versão **com GPU (NVIDIA)** usando `--gpus all`\
-   versão **pronta para deploy em VPS**\
-   versão **com túnel Cloudflare para acesso remoto**

# Executar o LMStudio: `/Downloads/LM-Studio-0.3.32-2-x64.AppImage --no-sandbox`