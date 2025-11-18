from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import subprocess
import shlex
import os

app = FastAPI()

# 🔐 Agora a API key vem só da variável de ambiente, sem default inseguro
API_KEY = os.getenv("TERMINAL_API_KEY")
if API_KEY is None:
    raise RuntimeError(
        "Variável de ambiente TERMINAL_API_KEY não definida. "
        "Defina antes de subir a API."
    )

# Lista de binários permitidos (ajuste conforme seu lab)
ALLOWED_BINARIES = [
    "ls", "pwd", "whoami", "id", "cat", "grep", "find",
    "docker",  # mantenha só se quiser permitir comandos docker
    "python3", "python"
]


class CommandRequest(BaseModel):
    binary: str        # ex: "ls"
    args: list[str] = []  # ex: ["-la", "/"]


class CommandResponse(BaseModel):
    command: str
    stdout: str
    stderr: str
    returncode: int


def is_binary_allowed(binary: str) -> bool:
    """
    Checa se o binário está na whitelist.
    """
    return binary in ALLOWED_BINARIES


@app.post("/run", response_model=CommandResponse)
def run_command(
    req: CommandRequest,
    x_api_key: str = Header(None, alias="X-API-Key")
):
    # 🔐 Autenticação via API key
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=401, detail="API key inválida ou ausente.")

    # ✅ Política de comandos permitidos (somente pelo binário)
    if not is_binary_allowed(req.binary):
        raise HTTPException(
            status_code=400, detail="Comando não permitido pela política de segurança.")

    # Monta a lista final: ["ls", "-la", "/"]
    cmd_list = [req.binary] + (req.args or [])

    try:
        result = subprocess.run(
            cmd_list,
            shell=False,           # 🔒 sem shell agora
            capture_output=True,
            text=True,
            timeout=30
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=500, detail="Comando demorou demais e foi interrompido.")

    # Monta uma string “bonita” só para devolver no JSON
    command_str = " ".join(shlex.quote(part) for part in cmd_list)

    return CommandResponse(
        command=command_str,
        stdout=result.stdout,
        stderr=result.stderr,
        returncode=result.returncode
    )
