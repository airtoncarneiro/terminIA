## Containerize a aplicação
docker build -t terminal-api .

## Execute o container
docker run --rm \
  -e TERMINAL_API_KEY="sua-chave" \
  -p 8000:8000 \
  --name terminal-api \
  terminal-api

### Liberando o terminal (detach)
docker run -d --rm \
  -e TERMINAL_API_KEY="sua-chave" \
  -p 8000:8000 \
  --name terminal-api \
  terminal-api

## Executar a API do Terminal em uma Máquina Local
uvicorn terminal_api:app --host 0.0.0.0 --port 8000

## Expôr a porta via NGROK:
ngrok http 8000

curl -X POST https://8508a903fd1f.ngrok-free.app/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: uma-chave-bem-grande-e-secreta" \
  -d '{"binary": "whoami", "args": []}'

## Testar com:
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: uma-chave-bem-grande-e-secreta" \
  -d '{"binary": "ls", "args": ["-la", "/"]}'

curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: uma-chave-bem-grande-e-secreta" \
  -d '{"binary": "python3", "args": ["-c", "print(\"oi\")"]}'

curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: uma-chave-bem-grande-e-secreta" \
  -d '{"binary": "whoami", "args": []}'

