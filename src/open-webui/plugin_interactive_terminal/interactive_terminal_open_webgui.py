"""
title: Secure Interactive Terminal
author: Alexander Otto
version: 5.0
description: Secure interactive terminal for Agnet-Human co-pilot.
required_open_webui_version: 0.3.9

*Requires seperate script to be running on local system to connect to terminal*
"""

import uuid
import requests
from typing import Callable, Any
from datetime import datetime
import time
import os


class Tools:
    """High-level helper for interacting with a secure terminal server.

    Manages session creation, command dispatch, job polling, and simple history
    queries. Most public methods optionally accept an ``__event_emitter__`` callback
    to push rich status messages back to the OpenWebUI frontend.

    Environment
    -----------
    Expects the environment variable ``TERMINAL_API_KEY`` to be set before
    instantiation. If absent, initialization fails.
    """

    def __init__(self):
        """
        Initialize the tool, configure hosts, read API key, and set state.

        :raises RuntimeError: If the environment variable ``TERMINAL_API_KEY`` is not set.
        """
        self.terminal_host_internal = "http://host.docker.internal:7681"
        self.terminal_host_external = "http://localhost:7681"

        # API key for authentication - SET THIS IN ENVIRONMENT VARIABLE IN OPENWEBUI CONTAINER
        self.api_key = key = os.environ.get("TERMINAL_API_KEY")
        if not key:
            raise RuntimeError("TERMINAL_API_KEY is required")

        self.current_session_id = None
        self.active_jobs = {}
        self.pending_confirmations = {}

    def _make_request(self, method, endpoint, data=None, timeout=10):
        """
        Make an authenticated request to the terminal server.

        :param method: HTTP method to use. Supported values are ``"GET"`` and ``"POST"``.
        :type method: str
        :param endpoint: API path appended to ``self.terminal_host_internal`` to form the full URL
                         (e.g., ``"/api/create_session"``). Typically begins with a leading slash.
        :type endpoint: str
        :param data: JSON-serializable payload for ``POST`` requests. Ignored for ``GET``.
        :type data: dict | list | str | int | float | bool | None
        :param timeout: Maximum number of seconds to wait for a server response.
        :type timeout: int | float

        :returns: A ``requests.Response`` on success, or ``None`` if connection error, timeout, or other exception occurs.
        :rtype: requests.Response | None
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        url = f"{self.terminal_host_internal}{endpoint}"

        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == "POST":
                response = requests.post(
                    url, headers=headers, json=data, timeout=timeout
                )
            else:
                raise ValueError(f"Unsupported method: {method}")

            return response
        except requests.exceptions.ConnectionError:
            return None
        except requests.exceptions.Timeout:
            return None
        except Exception as e:
            return None

    def open_terminal(self, __event_emitter__: Callable[[dict], Any] = None) - &gt; str:
        """
        Open a secure interactive terminal session.

        :param __event_emitter__: Optional callback to stream UI messages back to OpenWebUI.
                                  It is called with a dict payload like
                                  ``{"type": "message", "data": {"content": "..."} }``.
        :type __event_emitter__: Callable[[dict], Any] | None

        :returns: Status string indicating success or an error message. Also emits a message
                  containing the browser link to the terminal when an emitter is provided.
        :rtype: str
        """
        session_id = str(uuid.uuid4())

        try:
            response = self._make_request(
                "POST", "/api/create_session", {"session_id": session_id}
            )

            if response is None:
                error = "❌ Cannot connect to terminal server. Make sure secure_host_terminal_server.py is running."
                if __event_emitter__:
                    __event_emitter__(
                        {"type": "message", "data": {"content": error}})
                return f"ERROR: {error}"

            if response.status_code != 200:
                error = f"Failed to create terminal session: {response.json().get('error', 'Unknown error')}"
                if __event_emitter__:
                    __event_emitter__(
                        {"type": "message", "data": {"content": f"❌ {error}"}}
                    )
                return f"ERROR: {error}"

            self.current_session_id = session_id

            terminal_url = f"{self.terminal_host_external}/terminal/{session_id}"

            user_message = f"""
            🖥️ **Secure Terminal Session Created**

            **🌐 OPEN TERMINAL HERE:**
            {terminal_url}
            
            **Session ID:** `{session_id}`
            
            **🔒 Security Features Active:**
            - ✓ Command validation and risk assessment
            - ✓ Dangerous commands are blocked automatically
            - ✓ High/medium risk commands require your approval
            - ✓ All activity is logged
            
            I can now execute commands. You'll be prompted to approve any potentially risky operations.
            """

            if __event_emitter__:
                __event_emitter__(
                    {"type": "message", "data": {"content": user_message}}
                )

            return f"{user_message}"

        except Exception as e:
            error = f"Error creating terminal: {str(e)}"
            if __event_emitter__:
                __event_emitter__(
                    {"type": "message", "data": {"content": f"❌ {error}"}}
                )
            return f"ERROR: {error}"

    def send_terminal_command(self, command: str, session_id: str = None, estimated_duration: int = 30, __event_emitter__: Callable[[dict], Any] = None) - &gt; str:
        """
        Send a command to the terminal with security validation.

        The server will validate the command and either block it, require
        confirmation, or accept and run it.

        :param command: Shell command to execute.
        :type command: str
        :param session_id: Existing session to use. If ``None``, uses ``self.current_session_id``.
        :type session_id: str | None
        :param estimated_duration: Best-effort estimate (seconds) for how long the command may take.
                                   Forwarded to the server for UX purposes.
        :type estimated_duration: int
        :param __event_emitter__: Optional callback to stream status/UX messages to the UI.
        :type __event_emitter__: Callable[[dict], Any] | None

        :returns: Status string indicating whether the command was blocked, queued, running,
                  completed, or if an error occurred. When a confirmation is required,
                  returns a message indicating pending confirmation.
        :rtype: str
        """
        if session_id is None:
            if self.current_session_id is None:
                error = "No active terminal. Call open_terminal() first."
                if __event_emitter__:
                    __event_emitter__(
                        {"type": "message", "data": {"content": f"❌ {error}"}}
                    )
                return f"ERROR: {error}"
            session_id = self.current_session_id

        terminal_url = f"{self.terminal_host_external}/terminal/{session_id}"

        try:
            # Send command (will be validated by server)
            response = self._make_request(
                "POST",
                "/api/send_async_command",
                {
                    "session_id": session_id,
                    "command": command,
                    "estimated_duration": estimated_duration,
                },
                timeout=15
            )

            if response is None:
                error = "Cannot connect to terminal server"
                if __event_emitter__:
                    __event_emitter__(
                        {"type": "message", "data": {"content": f"❌ {error}"}}
                    )
                return f"ERROR: {error}"

            result = response.json()

            # Handle blocked commands
            if response.status_code == 403:
                blocked_msg = f"""
                🚫 **Command Blocked for Security**

                **Command:** `{command}`
                
                **Reason:** {result.get('reason', 'Security policy violation')}
                
                This command has been blocked to protect your system. It cannot be executed.
                
                **💻 [Terminal]({terminal_url})**
                """

                if __event_emitter__:
                    __event_emitter__(
                        {"type": "message", "data": {"content": blocked_msg}}
                    )

                return f"BLOCKED: {result.get('reason', 'Security violation')}"

            # Handle confirmation required
            if result.get("status") == "pending_confirmation":
                confirmation_id = result.get("confirmation_id")
                risk_level = result.get("risk_level", "unknown")
                risk_reason = result.get("risk_reason", "Requires approval")

                # Track confirmation
                self.pending_confirmations[confirmation_id] = {
                    "command": command,
                    "session_id": session_id,
                    "risk_level": risk_level,
                }

                risk_emoji = "🔴" if risk_level == "high" else "🟡"

                confirmation_msg = f"""
                {risk_emoji} **User Confirmation Required**

                **Risk Level:** {risk_level.upper()}
                **Command:** `{command}`
                
                **Why confirmation is needed:**
                {risk_reason}
                
                **What's happening:**
                I've sent this command for your approval. Please check the terminal window to approve or deny it.
                
                **💻 [Open terminal to approve/deny]({terminal_url})**
                
                I'll check back to see if you've approved it...
                """

                if __event_emitter__:
                    __event_emitter__(
                        {"type": "message", "data": {"content": confirmation_msg}}
                    )

                # Poll for confirmation with smart backoff
                return self._wait_for_confirmation(
                    confirmation_id, command, terminal_url, __event_emitter__
                )

            # Command accepted and running
            if result.get("success"):
                job_id = result.get("job_id")
                risk_level = result.get("risk_level", "low")

                if job_id:
                    self.active_jobs[job_id] = {
                        "command": command,
                        "session_id": session_id,
                    }

                    start_msg = f"""
                    ✅ **Command Started**

                    **Command:** `{command}`
                    **Risk Level:** {risk_level}
                    **Job ID:** `{job_id[:8]}...`
                    
                    The command is now executing.
                    
                    **💻 [Watch live]({terminal_url})**
                    """

                    if __event_emitter__:
                        __event_emitter__(
                            {"type": "message", "data": {"content": start_msg}}
                        )

                    # Poll for completion
                    return self._poll_job_with_backoff(
                        job_id, command, terminal_url, __event_emitter__
                    )
                else:
                    return f"Command sent: {command}"

            error = result.get("error", "Unknown error")
            if __event_emitter__:
                __event_emitter__(
                    {"type": "message", "data": {"content": f"❌ {error}"}}
                )
            return f"ERROR: {error}"

        except Exception as e:
            error = f"Error: {str(e)}"
            if __event_emitter__:
                __event_emitter__(
                    {"type": "message", "data": {"content": f"❌ {error}"}}
                )
            return f"ERROR: {error}"

    def _wait_for_confirmation(self, confirmation_id, command, terminal_url, __event_emitter__):
        """
        Wait for user to approve or deny a pending command.

        Polls the confirmation endpoint with a short backoff schedule until the user acts
        or the polling window is exhausted.

        :param confirmation_id: Server-issued identifier for the pending confirmation.
        :type confirmation_id: str
        :param command: The original command awaiting approval.
        :type command: str
        :param terminal_url: Browser URL for the associated terminal session (used in messages).
        :type terminal_url: str
        :param __event_emitter__: Optional callback to stream status messages to the UI.
        :type __event_emitter__: Callable[[dict], Any] | None

        :returns: Human-readable status message describing the outcome (approved, denied,
                  expired, or still waiting).
        :rtype: str
        """
        # Poll: 2s, 5s, 10s, 15s, 20s (total 52s)
        poll_intervals = [2, 3, 5, 5, 5]

        for i, wait_time in enumerate(poll_intervals):
            time.sleep(wait_time)

            response = self._make_request(
                "GET", f"/api/confirmation_status/{confirmation_id}"
            )

            if response and response.status_code == 200:
                status_data = response.json()
                status = status_data.get("status")

                if status == "approved":
                    # Command approved, now wait for it to execute
                    if __event_emitter__:
                        __event_emitter__(
                            {
                                "type": "message",
                                "data": {
                                    "content": f"✅ **Command Approved by User**\n\nExecuting: `{command}`\n\n**💻 [Terminal]({terminal_url})**"
                                },
                            }
                        )

                    # Wait a moment for job to be created
                    time.sleep(2)

                    # Try to find the job (server creates it after approval)
                    return f"Command approved and executing: {command}"

                elif status == "denied":
                    if __event_emitter__:
                        __event_emitter__(
                            {
                                "type": "message",
                                "data": {
                                    "content": f"❌ **Command Denied by User**\n\nThe command was not executed: `{command}`"
                                },
                            }
                        )

                    if confirmation_id in self.pending_confirmations:
                        del self.pending_confirmations[confirmation_id]

                    return f"Command denied by user: {command}"

                elif status == "expired":
                    if __event_emitter__:
                        __event_emitter__(
                            {
                                "type": "message",
                                "data": {
                                    "content": f"⏰ **Confirmation Expired**\n\nYou didn't approve or deny the command in time: `{command}`"
                                },
                            }
                        )

                    if confirmation_id in self.pending_confirmations:
                        del self.pending_confirmations[confirmation_id]

                    return f"Confirmation expired: {command}"

        # After all polling, still pending
        final_msg = f"""
        ⏰ **Still Waiting for Confirmation**

        **Command:** `{command}`
        
        I've checked multiple times but you haven't approved or denied this command yet.
        
        **What to do:**
        1. **Open the terminal:** {terminal_url}
        2. **Click Approve or Deny** in the confirmation dialog
        3. **Tell me** "check if command was approved" and I'll continue
        
        **Confirmation ID:** `{confirmation_id[:8]}...`
        """

        if __event_emitter__:
            __event_emitter__(
                {"type": "message", "data": {"content": final_msg}})

        return f"Awaiting user confirmation for: {command}. Session: {terminal_url}. Confirmation ID: {confirmation_id}"

    def _poll_job_with_backoff(self, job_id, command, terminal_url, __event_emitter__):
        """
        Poll a job's status with progressive backoff.

        Checks job status several times with increasing delays, reporting completion
        output, failure reason, or continued execution.

        :param job_id: Unique identifier of the job created by the server.
        :type job_id: str
        :param command: The command associated with the job (for display/logging).
        :type command: str
        :param terminal_url: Browser URL for the associated terminal session (used in messages).
        :type terminal_url: str
        :param __event_emitter__: Optional callback to stream status messages to the UI.
        :type __event_emitter__: Callable[[dict], Any] | None

        :returns: Human-readable message describing the job outcome or that it is still running.
        :rtype: str
        """
        poll_intervals = [0, 2, 5, 10, 20]

        for i, wait_time in enumerate(poll_intervals):
            if wait_time & gt; 0:
                time.sleep(wait_time)

            response = self._make_request("GET", f"/api/job/{job_id}")

            if response and response.status_code == 200:
                job = response.json()
                status = job.get("status")

                if status == "completed":
                    output = job.get("output", "").strip()
                    elapsed = job.get("elapsed_seconds", 0)

                    msg = f"""
                    ✅ **Command Completed**

                    **Command:** `{command}`
                    **Duration:** {elapsed:.1f} seconds
                    
                    **Output:**
                    {output if output else '(no output)'}
                    
                    **💻 [View in terminal]({terminal_url})**
                    """

                    if __event_emitter__:
                        __event_emitter__(
                            {"type": "message", "data": {"content": msg}})

                    if job_id in self.active_jobs:
                        del self.active_jobs[job_id]

                    return f"Command completed. Output: {output}"

                elif status == "failed":
                    error = job.get("error", "Unknown error")

                    msg = f"""
                    ❌ **Command Failed**

                    **Command:** `{command}`
                    **Error:** {error}
                    
                    **💻 [Terminal]({terminal_url})**
                    """

                    if __event_emitter__:
                        __event_emitter__(
                            {"type": "message", "data": {"content": msg}})

                    if job_id in self.active_jobs:
                        del self.active_jobs[job_id]

                    return f"Command failed: {error}"

        # Still running after all polls
        final_msg = f"""
        ⏰ **Command Still Running**

        **Command:** `{command}`
        
        I've checked {len(poll_intervals)} times but the command is still executing.
        
        **What to do:**
        1. **Watch it live:** {terminal_url}
        2. **When done, tell me:** "check job {job_id[:8]}" or "show recent commands"
        
        I'll retrieve and analyze the results when you're ready!
        """

        if __event_emitter__:
            __event_emitter__(
                {"type": "message", "data": {"content": final_msg}})

        return f"{final_msg}"

    def check_job(self, job_id: str, __event_emitter__: Callable[[dict], Any] = None) - &gt; str:
        """
        Check the status and results of a background job.

        Accepts partial job IDs and resolves to a single match from
        ``self.active_jobs`` when possible.

        :param job_id: The job ID to check. If shorter than 36 characters, a unique prefix is allowed.
        :type job_id: str
        :param __event_emitter__: Optional callback to stream status messages to the UI.
        :type __event_emitter__: Callable[[dict], Any] | None

        :returns: Human-readable message describing job state (completed/running/failed/queued) or an error.
        :rtype: str
        """
        # If partial job_id, try to find match
        if len(job_id) & lt; 36:
            matching = [
                jid for jid in self.active_jobs.keys() if jid.startswith(job_id)
            ]
            if len(matching) == 1:
                job_id = matching[0]
            elif len(matching) & gt; 1:
                error = f"Multiple jobs match '{job_id}'"
                if __event_emitter__:
                    __event_emitter__(
                        {"type": "message", "data": {"content": f"❌ {error}"}}
                    )
                return f"ERROR: {error}"

        try:
            response = self._make_request("GET", f"/api/job/{job_id}")

            if response is None:
                error = "Cannot connect to terminal server"
                if __event_emitter__:
                    __event_emitter__(
                        {"type": "message", "data": {"content": f"❌ {error}"}}
                    )
                return f"ERROR: {error}"

            if response.status_code == 200:
                job = response.json()
                status = job.get("status")
                command = job.get("command")
                session_id = job.get("session_id")
                terminal_url = f"{self.terminal_host_external}/terminal/{session_id}"

                if status == "completed":
                    output = job.get("output", "").strip()
                    elapsed = job.get("elapsed_seconds", 0)

                    msg = f"""
                    ✅ **Job Completed**

                    **Command:** `{command}`
                    **Duration:** {elapsed:.1f} seconds
                    
                    **Output:**
                    {output if output else '(no output)'}
                    
                    **💻 [Terminal]({terminal_url})**
                    """

                    if __event_emitter__:
                        __event_emitter__(
                            {"type": "message", "data": {"content": msg}})

                    return f"{msg}"

                elif status == "running":
                    elapsed = job.get("elapsed_seconds", 0)
                    remaining = job.get("estimated_remaining", 0)

                    msg = f"""
                    ⚙️ **Job Running**

                    **Command:** `{command}`
                    **Elapsed:** {elapsed:.0f} seconds
                    **Estimated remaining:** ~{remaining:.0f} seconds
                    
                    **💻 [Watch live]({terminal_url})**
                    """

                    if __event_emitter__:
                        __event_emitter__(
                            {"type": "message", "data": {"content": msg}})

                    return f"{msg}"

                elif status == "failed":
                    error = job.get("error", "Unknown error")

                    msg = f"""
                    ❌ **Job Failed**

                    **Command:** `{command}`
                    **Error:** {error}
                    
                    **💻 [Terminal]({terminal_url})**
                    """

                    if __event_emitter__:
                        __event_emitter__(
                            {"type": "message", "data": {"content": msg}})

                    return f"Job failed: {error}"

                else:  # queued
                    msg = f"""
                    ⏳ **Job Queued**

                    **Command:** `{command}`
                    
                    The job is waiting to execute.
                    
                    **💻 [Terminal]({terminal_url})**
                    """

                    if __event_emitter__:
                        __event_emitter__(
                            {"type": "message", "data": {"content": msg}})

                    return f"{msg}"

            elif response.status_code == 404:
                error = "Job not found or expired"
                if __event_emitter__:
                    __event_emitter__(
                        {"type": "message", "data": {"content": f"❌ {error}"}}
                    )
                return f"ERROR: {error}"

            else:
                error = "Failed to fetch job status"
                if __event_emitter__:
                    __event_emitter__(
                        {"type": "message", "data": {"content": f"❌ {error}"}}
                    )
                return f"ERROR: {error}"

        except Exception as e:
            error = f"Error: {str(e)}"
            if __event_emitter__:
                __event_emitter__(
                    {"type": "message", "data": {"content": f"❌ {error}"}}
                )
            return f"ERROR: {error}"

    def get_last_command(self, session_id: str = None, __event_emitter__: Callable[[dict], Any] = None) - &gt; str:
        """
        Get the most recent command executed in a session and its output.

        :param session_id: Session to inspect. If ``None``, uses ``self.current_session_id``.
        :type session_id: str | None
        :param __event_emitter__: Optional callback to stream a formatted summary to the UI.
        :type __event_emitter__: Callable[[dict], Any] | None

        :returns: Summary string with the last command and output, or an error message.
        :rtype: str
        """
        if session_id is None:
            session_id = self.current_session_id

        if session_id is None:
            error = "No active session"
            if __event_emitter__:
                __event_emitter__(
                    {"type": "message", "data": {"content": f"❌ {error}"}}
                )
            return f"ERROR: {error}"

        terminal_url = f"{self.terminal_host_external}/terminal/{session_id}"

        try:
            response = self._make_request(
                "GET", f"/api/command_history/{session_id}")

            if response is None:
                error = "Cannot connect to terminal server"
                if __event_emitter__:
                    __event_emitter__(
                        {"type": "message", "data": {"content": f"❌ {error}"}}
                    )
                return f"ERROR: {error}"

            if response.status_code == 200:
                result = response.json()
                history = result.get("history", [])

                if not history:
                    msg = f"No commands executed yet.\n\n**💻 [Terminal]({terminal_url})**"
                    if __event_emitter__:
                        __event_emitter__(
                            {"type": "message", "data": {"content": msg}})
                    return msg

                last_cmd = history[-1]
                ts = datetime.fromisoformat(
                    last_cmd["timestamp"]).strftime("%H:%M:%S")

                source_map = {
                    "llm": ("🤖", "Assistant"),
                    "llm_async": ("🔄", "Assistant (async)"),
                    "user": ("👤", "User"),
                }
                source_icon, source_label = source_map.get(
                    last_cmd["source"], ("❓", "Unknown")
                )

                output = last_cmd.get("output", "").strip()
                risk_level = last_cmd.get("risk_level", "unknown")

                user_msg = f"""
                **📋 Last Command**

                **{source_icon} Source:** {source_label}
                **Time:** {ts}
                **Command:** `{last_cmd['command']}`
                **Risk Level:** {risk_level}
                
                **Output:**
                {output if output else '(no output captured)'}
                
                **💻 [Terminal]({terminal_url})**
                """

                if __event_emitter__:
                    __event_emitter__(
                        {"type": "message", "data": {"content": user_msg}}
                    )

                return f"Last command: {last_cmd['command']}. Output: {output if output else '(no output)'}"

            else:
                error = "Failed to fetch command history"
                if __event_emitter__:
                    __event_emitter__(
                        {"type": "message", "data": {"content": f"❌ {error}"}}
                    )
                return f"ERROR: {error}"

        except Exception as e:
            error = f"Error: {str(e)}"
            if __event_emitter__:
                __event_emitter__(
                    {"type": "message", "data": {"content": f"❌ {error}"}}
                )
            return f"ERROR: {error}"

    def get_recent_commands(self, count: int = 5, session_id: str = None, __event_emitter__: Callable[[dict], Any] = None) - &gt; str:
        """
        Get the last N commands (with truncated outputs) for a session.

        :param count: Maximum number of most-recent commands to return.
        :type count: int
        :param session_id: Session to inspect. If ``None``, uses ``self.current_session_id``.
        :type session_id: str | None
        :param __event_emitter__: Optional callback to stream a formatted list to the UI.
        :type __event_emitter__: Callable[[dict], Any] | None

        :returns: Text summary of recent commands, or an error message.
        :rtype: str
        """
        if session_id is None:
            session_id = self.current_session_id

        if session_id is None:
            error = "No active session"
            if __event_emitter__:
                __event_emitter__(
                    {"type": "message", "data": {"content": f"❌ {error}"}}
                )
            return f"ERROR: {error}"

        terminal_url = f"{self.terminal_host_external}/terminal/{session_id}"

        try:
            response = self._make_request(
                "GET", f"/api/command_history/{session_id}")

            if response is None or response.status_code != 200:
                error = "Failed to fetch command history"
                if __event_emitter__:
                    __event_emitter__(
                        {"type": "message", "data": {"content": f"❌ {error}"}}
                    )
                return f"ERROR: {error}"

            result = response.json()
            history = result.get("history", [])

            if not history:
                msg = f"No commands executed yet.\n\n**💻 [Terminal]({terminal_url})**"
                if __event_emitter__:
                    __event_emitter__(
                        {"type": "message", "data": {"content": msg}})
                return msg

            recent = history[-count:] if len(history) & gt
            = count else history

            user_msg = f"""
            **📋 Recent Commands** (Last {len(recent)} of {len(history)} total)

            **💻 [Terminal]({terminal_url})**            
            """

            llm_response = f"Last {len(recent)} commands:\n\n"

            source_map = {"llm": "🤖", "llm_async": "🔄", "user": "👤"}

            for i, cmd in enumerate(recent, 1):
                ts = datetime.fromisoformat(
                    cmd["timestamp"]).strftime("%H:%M:%S")
                icon = source_map.get(cmd["source"], "❓")
                output = cmd.get("output", "").strip()
                risk = cmd.get("risk_level", "unknown")

                user_msg += f"**{i}. {icon}** {ts} - Risk: {risk}\n"
                user_msg += f"**Command:** `{cmd['command']}`\n"
                if output:
                    display = output[:200] + "..." if len(output) & gt
                    200 else output
                    user_msg += f"**Output:**\n```\n{display}\n```\n"
                else:
                    user_msg += "*No output*\n"
                user_msg += "\n"

                llm_response += f"{i}. {cmd['command']}\n"
                llm_response += f"   Output: {output if output else '(none)'}\n\n"

            if __event_emitter__:
                __event_emitter__(
                    {"type": "message", "data": {"content": user_msg}})

            return llm_response

        except Exception as e:
            error = f"Error: {str(e)}"
            if __event_emitter__:
                __event_emitter__(
                    {"type": "message", "data": {"content": f"❌ {error}"}}
                )
            return f"ERROR: {error}"

    def get_terminal_link(self, session_id: str = None, __event_emitter__: Callable[[dict], Any] = None) - &gt; str:
        """
        Get the browser link for the current or specified terminal session.

        :param session_id: Session to link to. If ``None``, uses ``self.current_session_id``.
        :type session_id: str | None
        :param __event_emitter__: Optional callback to stream a formatted link card to the UI.
        :type __event_emitter__: Callable[[dict], Any] | None

        :returns: The terminal URL as a plain string (also emitted when an emitter is provided).
        :rtype: str
        """
        if session_id is None:
            session_id = self.current_session_id

        if session_id is None:
            error = "No active terminal session"
            if __event_emitter__:
                __event_emitter__(
                    {"type": "message", "data": {"content": f"❌ {error}"}}
                )
            return f"ERROR: {error}"

        terminal_url = f"{self.terminal_host_external}/terminal/{session_id}"

        msg = f"""
        **🖥️ Secure Terminal Link**

        {terminal_url}
        
        **Session ID:** `{session_id}`
        """

        if __event_emitter__:
            __event_emitter__({"type": "message", "data": {"content": msg}})

        return terminal_url

    def close_terminal(self, session_id: str = None, __event_emitter__: Callable[[dict], Any] = None) - &gt; str:
        """
        Close a terminal session.

        :param session_id: Session to close. If ``None``, uses ``self.current_session_id``.
        :type session_id: str | None
        :param __event_emitter__: Optional callback to stream a success/error message to the UI.
        :type __event_emitter__: Callable[[dict], Any] | None

        :returns: A short status string indicating success or an error message.
        :rtype: str
        """
        if session_id is None:
            session_id = self.current_session_id

        if session_id is None:
            error = "No active session to close"
            if __event_emitter__:
                __event_emitter__(
                    {"type": "message", "data": {"content": f"❌ {error}"}}
                )
            return f"ERROR: {error}"

        try:
            response = self._make_request(
                "POST", f"/api/close_session/{session_id}")

            if response and response.status_code == 200:
                msg = f"✓ Closed terminal session `{session_id[:8]}...`"
                if __event_emitter__:
                    __event_emitter__(
                        {"type": "message", "data": {"content": msg}})

                if self.current_session_id == session_id:
                    self.current_session_id = None

                return msg
            else:
                error = "Failed to close session"
                if __event_emitter__:
                    __event_emitter__(
                        {"type": "message", "data": {"content": f"❌ {error}"}}
                    )
                return f"ERROR: {error}"

        except Exception as e:
            error = f"Error: {str(e)}"
            if __event_emitter__:
                __event_emitter__(
                    {"type": "message", "data": {"content": f"❌ {error}"}}
                )
            return f"ERROR: {error}"
