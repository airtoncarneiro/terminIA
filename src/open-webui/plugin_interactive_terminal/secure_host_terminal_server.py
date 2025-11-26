"""
Servidor Terminal Seguro para Open WebUI
Versão: 1.1 (Correção de autenticação)
"""

import os
import uuid
import asyncio
from datetime import datetime
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

API_KEY = os.getenv("TERMINAL_API_KEY")
if not API_KEY:
    raise RuntimeError("TERMINAL_API_KEY environment variable is required")

PORT = int(os.getenv("TERMINAL_PORT", "7681"))
HOST = os.getenv("TERMINAL_HOST", "0.0.0.0")

# ============================================================================
# MODELOS
# ============================================================================


class CreateSessionRequest(BaseModel):
    session_id: str


class SendCommandRequest(BaseModel):
    session_id: str
    command: str
    estimated_duration: int = 30

# ============================================================================
# ARMAZENAMENTO EM MEMÓRIA
# ============================================================================


sessions: Dict[str, dict] = {}
jobs: Dict[str, dict] = {}
command_history: Dict[str, list] = {}

# ============================================================================
# APLICAÇÃO FASTAPI
# ============================================================================

app = FastAPI(
    title="Secure Terminal Server",
    description="Servidor terminal seguro para Open WebUI",
    version="1.1.0"
)

# ============================================================================
# AUTENTICAÇÃO CORRIGIDA
# ============================================================================


def verify_api_key(authorization: str = Header(None)):
    """Verifica se a API key é válida."""
    if not authorization:
        raise HTTPException(
            status_code=401, detail="Authorization header missing")

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Invalid authorization format")

    token = authorization.replace("Bearer ", "")

    if token != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return True

# ============================================================================
# ENDPOINTS
# ============================================================================


@app.get("/")
async def root():
    """Página inicial."""
    return {"status": "running", "service": "secure-terminal-server"}


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/api/create_session")
async def create_session(
    request: CreateSessionRequest,
    authenticated: bool = Depends(verify_api_key)
):
    """Cria uma nova sessão de terminal."""
    session_id = request.session_id

    sessions[session_id] = {
        "id": session_id,
        "created_at": datetime.now().isoformat(),
        "active": True
    }

    command_history[session_id] = []

    print(f"✅ Session created: {session_id}")

    return {
        "success": True,
        "session_id": session_id,
        "message": "Terminal session created"
    }


@app.post("/api/send_async_command")
async def send_async_command(
    request: SendCommandRequest,
    authenticated: bool = Depends(verify_api_key)
):
    """Envia comando para execução assíncrona."""
    session_id = request.session_id
    command = request.command

    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    # Criar job
    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "job_id": job_id,
        "session_id": session_id,
        "command": command,
        "status": "running",
        "output": "",
        "error": None,
        "started_at": datetime.now().isoformat()
    }

    # Executar comando em background
    asyncio.create_task(execute_command(job_id, command, session_id))

    print(f"🚀 Command started: {command} (job: {job_id[:8]}...)")

    return {
        "success": True,
        "job_id": job_id,
        "status": "running",
        "risk_level": "low"
    }


async def execute_command(job_id: str, command: str, session_id: str):
    """Executa comando no terminal."""
    try:
        # Executar comando
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        output = stdout.decode() if stdout else ""
        error = stderr.decode() if stderr else ""

        # Calcular elapsed time
        started = datetime.fromisoformat(jobs[job_id]["started_at"])
        elapsed = (datetime.now() - started).total_seconds()

        # Atualizar job
        jobs[job_id]["status"] = "completed" if process.returncode == 0 else "failed"
        jobs[job_id]["output"] = output
        jobs[job_id]["error"] = error if error else None
        jobs[job_id]["return_code"] = process.returncode
        jobs[job_id]["completed_at"] = datetime.now().isoformat()
        jobs[job_id]["elapsed_seconds"] = elapsed

        # Adicionar ao histórico
        command_history[session_id].append({
            "command": command,
            "output": output,
            "error": error,
            "return_code": process.returncode,
            "timestamp": datetime.now().isoformat(),
            "source": "llm_async",
            "risk_level": "low"
        })

        print(f"✅ Command completed: {command[:50]}... (job: {job_id[:8]}...)")

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["completed_at"] = datetime.now().isoformat()
        print(f"❌ Command failed: {str(e)}")


@app.get("/api/job/{job_id}")
async def get_job(
    job_id: str,
    authenticated: bool = Depends(verify_api_key)
):
    """Obtém status de um job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id].copy()

    # Calcular elapsed time se ainda não tiver
    if "elapsed_seconds" not in job and job["status"] == "running":
        started = datetime.fromisoformat(job["started_at"])
        job["elapsed_seconds"] = (datetime.now() - started).total_seconds()

    return job


@app.get("/api/command_history/{session_id}")
async def get_command_history(
    session_id: str,
    authenticated: bool = Depends(verify_api_key)
):
    """Obtém histórico de comandos de uma sessão."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    history = command_history.get(session_id, [])

    return {
        "session_id": session_id,
        "history": history,
        "count": len(history)
    }


@app.post("/api/close_session/{session_id}")
async def close_session(
    session_id: str,
    authenticated: bool = Depends(verify_api_key)
):
    """Fecha uma sessão."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    sessions[session_id]["active"] = False
    sessions[session_id]["closed_at"] = datetime.now().isoformat()

    print(f"🔒 Session closed: {session_id}")

    return {
        "success": True,
        "message": f"Session {session_id} closed"
    }


@app.get("/terminal/{session_id}")
async def terminal_page(session_id: str):
    """Página do terminal (visualização web)."""
    if session_id not in sessions:
        return HTMLResponse(
            content="<h1>Session not found</h1>",
            status_code=404
        )

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Terminal - {session_id[:8]}</title>
        <style>
            body {{
                background: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Courier New', monospace;
                padding: 20px;
            }}
            h1 {{
                color: #4ec9b0;
            }}
            .session-info {{
                background: #252526;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            }}
            .command-history {{
                background: #1e1e1e;
                border: 1px solid #3c3c3c;
                padding: 15px;
                border-radius: 5px;
                max-height: 600px;
                overflow-y: auto;
            }}
            .command {{
                margin-bottom: 20px;
                padding: 10px;
                background: #252526;
                border-left: 3px solid #4ec9b0;
            }}
            .command-text {{
                color: #569cd6;
                font-weight: bold;
            }}
            .output {{
                color: #ce9178;
                white-space: pre-wrap;
                margin-top: 10px;
            }}
            .timestamp {{
                color: #6a9955;
                font-size: 0.9em;
            }}
        </style>
    </head>
    <body>
        <h1>🖥️ Secure Terminal Session</h1>
        <div class="session-info">
            <strong>Session ID:</strong> {session_id}<br>
            <strong>Status:</strong> Active<br>
            <strong>Created:</strong> {sessions[session_id]['created_at']}
        </div>
        
        <h2>Command History</h2>
        <div class="command-history" id="history">
            <p>No commands executed yet. Waiting for LLM to send commands...</p>
        </div>
        
        <script>
            // Auto-refresh history every 2 seconds
            setInterval(async () => {{
                try {{
                    const response = await fetch('/api/command_history/{session_id}', {{
                        headers: {{
                            'Authorization': 'Bearer {API_KEY}'
                        }}
                    }});
                    const data = await response.json();
                    
                    const historyDiv = document.getElementById('history');
                    if (data.history.length === 0) {{
                        historyDiv.innerHTML = '<p>No commands executed yet.</p>';
                    }} else {{
                        historyDiv.innerHTML = data.history.map(cmd => `
                            <div class="command">
                                <span class="timestamp">${{cmd.timestamp}}</span><br>
                                <span class="command-text">$ ${{cmd.command}}</span>
                                <div class="output">${{cmd.output || '(no output)'}}</div>
                            </div>
                        `).reverse().join('');
                    }}
                }} catch (e) {{
                    console.error('Error fetching history:', e);
                }}
            }}, 2000);
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════════════════════╗
║   🔒 Secure Terminal Server                             ║
╠══════════════════════════════════════════════════════════╣
║   Port: {PORT}                                              ║
║   Host: {HOST}                                         ║
║   API Key: {'✓ Configured' if API_KEY else '✗ Missing'}                                    ║
╚══════════════════════════════════════════════════════════╝

Server starting...
    """)

    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level="info"
    )
