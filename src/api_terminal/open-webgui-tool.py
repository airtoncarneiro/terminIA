"""
title: Terminal Executor Tool
author: open-webui
author_url: https://github.com/open-webui
funding_url: https://github.com/open-webui
version: 1.0.2
"""

from typing import Callable, Any
import requests
import json
import asyncio
import shlex


class Tools:
    """
    Ferramenta para execução de comandos no terminal via API local.
    Permite ao LLM interagir com o sistema operacional de forma controlada.
    """

    def __init__(self):
        self.valves = self.Valves()

    class Valves:
        """
        Configurações da ferramenta (editáveis via interface do Open-WebUI).
        """

        def __init__(self):
            # self.API_BASE_URL: str = "http://localhost:8000"
            self.API_BASE_URL: str = "http://host.docker.internal:8000"
            self.TIMEOUT: int = 300
            self.MAX_OUTPUT_LENGTH: int = 4000

    async def execute_terminal_command(
        self,
        binary: str,
        args: list[str] = None,
        timeout: int = None,
        __user__: dict = None,
        __event_emitter__: Callable[[dict], Any] = None
    ) -> str:
        """
        Executa um comando no terminal através da API local.

        Args:
            binary: Nome do binário/comando a ser executado (ex: 'ls', 'docker', 'sudo')
            args: Lista de argumentos do comando (ex: ['-la', '/home'])
            timeout: Timeout em segundos (opcional, usa valor padrão se não informado)
            __user__: Informações do usuário (injetado automaticamente pelo Open-WebUI)
            __event_emitter__: Emitter para enviar eventos de status (injetado automaticamente)

        Returns:
            String com o resultado da execução (stdout, stderr e returncode)
        """
        if args is None:
            args = []

        if timeout is None:
            timeout = self.valves.TIMEOUT

        # 🔧 FIX: Se o binary contém espaços, parsear como comando completo
        if " " in binary:
            parsed = shlex.split(binary)
            binary = parsed[0]
            args = parsed[1:] + args

        # Emite evento de status inicial
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"Executando comando: {binary} {' '.join(args)}",
                        "done": False
                    }
                }
            )

        try:
            # Monta o payload
            payload = {
                "binary": binary,
                "args": args,
                "timeout": timeout
            }

            # Realiza a chamada à API
            response = requests.post(
                f"{self.valves.API_BASE_URL}/run",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=timeout + 5
            )

            # Valida resposta
            response.raise_for_status()
            result = response.json()

            # Formata o output
            command_executed = result.get(
                "command", f"{binary} {' '.join(args)}")
            stdout = result.get("stdout", "")
            stderr = result.get("stderr", "")
            returncode = result.get("returncode", -1)
            environment = result.get("environment", "unknown")

            # Trunca output se necessário
            if len(stdout) > self.valves.MAX_OUTPUT_LENGTH:
                stdout = stdout[:self.valves.MAX_OUTPUT_LENGTH] + \
                    "\n... (truncado)"
            if len(stderr) > self.valves.MAX_OUTPUT_LENGTH:
                stderr = stderr[:self.valves.MAX_OUTPUT_LENGTH] + \
                    "\n... (truncado)"

            # Monta resposta formatada
            output_parts = [
                f"🖥️ **Comando executado:** `{command_executed}`",
                f"🌍 **Ambiente:** {environment}",
                f"📊 **Return Code:** {returncode}",
            ]

            if stdout:
                output_parts.append(f"\n**📤 STDOUT:**\n```\n{stdout}\n```")

            if stderr:
                output_parts.append(f"\n**⚠️ STDERR:**\n```\n{stderr}\n```")

            result_message = "\n".join(output_parts)

            # Emite evento de conclusão
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f"Comando executado com sucesso (rc={returncode})",
                            "done": True
                        }
                    }
                )

            return result_message

        except requests.exceptions.Timeout:
            error_msg = f"⏱️ **Erro:** Timeout ao executar comando '{binary}'"
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "Timeout na execução do comando",
                            "done": True
                        }
                    }
                )
            return error_msg

        except requests.exceptions.RequestException as e:
            error_msg = f"🚨 **Erro de comunicação com a API:** {str(e)}"
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f"Erro: {str(e)}",
                            "done": True
                        }
                    }
                )
            return error_msg

        except Exception as e:
            error_msg = f"❌ **Erro inesperado:** {str(e)}"
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f"Erro crítico: {str(e)}",
                            "done": True
                        }
                    }
                )
            return error_msg
