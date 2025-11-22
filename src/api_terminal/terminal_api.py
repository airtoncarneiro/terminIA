from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import subprocess
import shlex
import os

# 🔧 Ambiente: dev (default) ou prod
ENVIRONMENT = os.getenv("APP_ENV", "dev")

# 🔐 API key obrigatória (sem default inseguro)
API_KEY = os.getenv("TERMINAL_API_KEY")
if API_KEY is None:
    raise RuntimeError(
        "Variável de ambiente TERMINAL_API_KEY não definida. "
        "Defina TERMINAL_API_KEY antes de subir a API."
    )

# Lista de binários permitidos (apenas para ambiente dev)
ALLOWED_BINARIES = [
    "ls", "pwd", "whoami", "id", "cat", "grep", "find",
    "docker",  # mantenha só se quiser permitir comandos docker
    "python3", "python"
]


class CommandRequest(BaseModel):
    binary: str          # ex: "ls"
    args: list[str] = []  # ex: ["-la", "/"]


class CommandResponse(BaseModel):
    command: str
    stdout: str
    stderr: str
    returncode: int
    environment: str     # dev ou prod


def is_binary_allowed(binary: str) -> bool:
    """
    Em dev: checa se o binário está na whitelist.
    Em prod: sempre permite.
    """
    if ENVIRONMENT == "prod":
        # 🚨 Sem restrição de binário em prod (por sua conta e risco)
        return True
    return binary in ALLOWED_BINARIES


app = FastAPI(title=f"Terminal API ({ENVIRONMENT})")


@app.post("/run", response_model=CommandResponse)
def run_command(
    req: CommandRequest,
    x_api_key: str = Header(None, alias="X-API-Key")
):
    # 🔐 Autenticação via API key
    # if x_api_key != API_KEY:
    #     raise HTTPException(
    #         status_code=401, detail="API key inválida ou ausente.")

    import logging
    logging.basicConfig(level=logging.INFO)

    # 🔍 LOG: Comando recebido
    print(f"📥 Comando recebido: binary={req.binary}, args={req.args}")

    # ✅ Política de comandos
    allowed = is_binary_allowed(req.binary)
    print(f"🔐 Comando permitido? {allowed}")

    if not allowed:
        print(f"🚫 Comando BLOQUEADO: {req.binary}")
        raise HTTPException(
            status_code=400,
            detail="Comando não permitido pela política de segurança (ambiente dev)."
        )

    # Monta a lista final
    cmd_list = [req.binary] + (req.args or [])
    print(f"🔧 Comando completo: {cmd_list}")

    try:
        result = subprocess.run(
            cmd_list,
            shell=False,
            capture_output=True,
            text=True,
            timeout=30
        )

        print(f"✅ Executado! Return code: {result.returncode}")
        print(f"📤 STDOUT (primeiros 200 chars): {result.stdout[:200]}")
        print(f"📤 STDERR (primeiros 200 chars): {result.stderr[:200]}")

    except subprocess.TimeoutExpired as e:
        print(f"⏱️ TIMEOUT: {e}")
        raise HTTPException(
            status_code=500, detail="Comando demorou demais e foi interrompido.")
    except Exception as e:
        print(f"❌ ERRO INESPERADO: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")

    command_str = " ".join(shlex.quote(part) for part in cmd_list)

    return CommandResponse(
        command=command_str,
        stdout=result.stdout,
        stderr=result.stderr,
        returncode=result.returncode,
        environment=ENVIRONMENT
    )


# if __name__ == "__main__":
#     req = CommandRequest(binary="ls", args=["-a"])
#     run_command(req)
