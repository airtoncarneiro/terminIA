FROM python:3.12-slim

# Diretório de trabalho dentro do container
WORKDIR /app

# Copia só o arquivo de dependências primeiro (melhora cache de build)
COPY requirements.txt .

# Instala dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia o resto dos arquivos da aplicação
COPY terminal_api.py .

# Variável só para logs ficarem imediatos
ENV PYTHONUNBUFFERED=1

# Comando padrão: subir o uvicorn na porta 8000
CMD ["uvicorn", "terminal_api:app", "--host", "0.0.0.0", "--port", "8000"]
