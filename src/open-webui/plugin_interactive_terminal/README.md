# Interactive Terminal Tool for Open WebUI
📋 Overview
The Interactive Terminal Tool provides a powerful, browser-based terminal interface that enables LLMs (Large Language Models) to interact with your host system's command line. This tool creates a bidirectional communication channel where both you and the AI can execute commands, view outputs in real-time, and collaborate on system administration tasks.
[link desta documentação](https://openwebui.com/t/aotto/interactive_terminal)

Key Features
 🖥️ Browser-Based Terminal - Full xterm.js terminal accessible via web browser
 🤖 LLM Command Execution - AI can execute commands and see real-time output
 👤 User Interaction - Type commands directly in the browser terminal
 🔄 Background Jobs - Long-running commands execute asynchronously in parallel
 📊 Complete History Tracking - All commands (user and AI) are logged with outputs ⏱️ Smart Timeout Handling - Intelligent polling and graceful timeout management 🔗 Session Management - Multiple terminal sessions with auto-expiration 🌐 Docker-to-Host Communication - Execute commands on host from containerized Open WebUI

🏗️ Architecture
Components

┌─────────────────────────────────────────────────────────────┐
│                        Open WebUI (Docker)                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  LLM + Interactive Terminal Tool (Python)              │
│  │  - Sends commands via HTTP API                         │
│  │  - Polls for job status                                │
│  │  - Retrieves command history                           │
│  └─────────────────────┬──────────────────────────────────┘ │
└────────────────────────┼────────────────────────────────────┘
                         │ HTTP/WebSocket
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              Host Terminal Server (Python + Flask)           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Flask-SocketIO Server (Port 7681)                     │
│  │  - WebSocket for browser terminal                      │
│  │  - REST API for command execution                      │
│  │  - Job queue for async commands                        │
│  │  - Session management                                  │
│  └─────────────────────┬──────────────────────────────────┘ │
│                        ↓                                     │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  PTY (Pseudo-Terminal)                                 │
│  │  - Spawns /bin/bash processes                          │
│  │  - Captures stdin/stdout/stderr                        │
│  │  - Manages terminal sessions                           │
│  └─────────────────────┬──────────────────────────────────┘ │
└────────────────────────┼────────────────────────────────────┘
                         ↓
                    Host System
                (Commands execute here)

Communication Flow
 1. LLM → Host Server: HTTP POST to /api/send_async_command
 2. Server → PTY: Write command to pseudo-terminal file descriptor
 3. PTY → Bash: Command executes in real bash session
 4. Bash → PTY: Output captured via PTY
 5. PTY → Server: Output queued and stored
 6. Server → LLM: Job status and output returned via polling
 7. Server → Browser: Real-time output via WebSocket to xterm.js

📦 Installation
Prerequisites
 Python 3.8+
 Open WebUI running in Docker
 Host machine running macOS or Linux

Step 1: Install Dependencies on Host

pip install flask flask-socketio python-socketio eventlet

Step 2: Download the Files
Save these two files on your host machine:

 1. host_terminal_server.py - The terminal server
 2. interactive_terminal_tool.py - The Open WebUI tool

Step 3: Configure Docker
Add host networking to your Open WebUI Docker configuration:

For docker-compose.yml:

services:
  open-webui:
    # ... other config ...
    extra_hosts:
      - "host.docker.internal:host-gateway"

For docker run:

docker run --add-host=host.docker.internal:host-gateway \
  # ... other flags ...
  ghcr.io/open-webui/open-webui:main

For Linux hosts, you may need to use the bridge IP instead:

extra_hosts:
  - "host.docker.internal:172.17.0.1"

Step 4: Start the Terminal Server

python3 host_terminal_server.py

You should see:

============================================================
Terminal Server with Parallel Job Execution
============================================================
Session timeout: 30 minutes
Jobs run in parallel threads for concurrent execution
============================================================

Ready to accept terminal sessions

Step 5: Add Tool to Open WebUI

 1. Go to Open WebUI → Settings → Tools
 2. Click "Add Tool"
 3. Paste the contents of interactive_terminal_tool.py
 4. Save and enable the tool

🚀 Usage Guide
Basic Commands

1. Open a Terminal Session

# LLM calls
open_terminal()

Output:

============================================================
Interactive Terminal Session Created
============================================================
Session ID: <SESSION_ID>
Web Terminal URL: http://host.docker.internal:7681/terminal/<SESSION_ID>
============================================================

You can now:
- Open the URL in your browser to use the terminal interactively
- Use the tool to send commands programmatically

2. Run a Command Asynchronously

run_async_command("ls -la")

Output:

============================================================
Command Submitted
============================================================
Job ID: <JOB_ID>
Status: pending
============================================================

3. Poll Command Status

get_job_status("<JOB_ID>")

Example Output (running):

============================================================
Job Status
============================================================
Job ID: <JOB_ID>
Status: running
Last Output Chunk:
<partial command output here>
============================================================

Example Output (completed):

============================================================
Job Status
============================================================
Job ID: <JOB_ID>
Status: completed
Exit Code: 0
Full Output:
<full command output here>
============================================================

4. List Command History

get_command_history()

Example Output:

============================================================
Command History
============================================================
[1] Job ID: 001
    Command: ls -la
    Status: completed
    Exit Code: 0

[2] Job ID: 002
    Command: ping -c 4 google.com
    Status: running

[3] Job ID: 003
    Command: df -h
    Status: completed
    Exit Code: 0
============================================================

5. Close a Session

close_terminal_session("<SESSION_ID>")

Output:

============================================================
Session Closed
============================================================
Session ID: <SESSION_ID>
All associated jobs terminated
============================================================

🧠 Best Practices for LLM Usage

 1. Always check job status instead of assuming completion.
 2. Prefer short, idempotent commands.
 3. Use explicit paths to avoid ambiguity.
 4. Avoid destructive commands unless explicitly instructed by the user.
 5. Log important outputs and summarize them for the user.
 6. Use history to provide context and continuity across interactions.

🔐 Security Considerations

 - Restrict access to the terminal server to trusted networks.
 - Run the terminal server under a non-root user when possible.
 - Use firewalls to limit which hosts can connect.
 - Regularly audit command history for misuse.
 - Consider containerizing sensitive workloads separately.

⚙️ Configuration Options

Environment Variables

HOST_TERMINAL_SERVER_URL
  - Description: Base URL of the host terminal server
  - Example: http://host.docker.internal:7681

SESSION_TIMEOUT_MINUTES
  - Description: Inactivity timeout for terminal sessions
  - Default: 30

MAX_PARALLEL_JOBS
  - Description: Maximum number of concurrent jobs per session
  - Default: 5

LOG_LEVEL
  - Description: Verbosity of server logging
  - Values: DEBUG, INFO, WARNING, ERROR
  - Default: INFO

🧩 Example LLM Prompt Templates

1. System Administration

"Use the interactive terminal to:
1. Check disk usage with `df -h`
2. List the 10 largest directories in /var
3. Summarize which paths are consuming the most space

Use asynchronous commands and provide a concise summary of findings."

2. Diagnostics

"Open a terminal session and:
1. Run `top -b -n 1` to capture current CPU usage
2. Run `free -m` to check memory usage
3. Run `df -h` to inspect disk usage

Then, analyze whether the system is under resource pressure and explain your reasoning."

3. Log Analysis

"Using the interactive terminal:
1. Tail the last 100 lines of /var/log/syslog
2. Search for occurrences of the word 'error'
3. Summarize any critical or recurring issues you find."

🛠️ Troubleshooting

1. Browser Terminal Not Connecting
 - Symptom: Web terminal page does not load or connect.
 - Checks:
   - Ensure the host terminal server is running.
   - Verify that port 7681 is accessible from the Open WebUI container and your browser.
   - Confirm that host.docker.internal is correctly mapped in Docker.

2. Commands Not Executing
 - Symptom: Jobs stay in "pending" state.
 - Checks:
   - Check terminal server logs for errors.
   - Ensure there are available job slots (MAX_PARALLEL_JOBS).
   - Verify that the PTY process is running and responsive.

3. Session Timeout Issues
 - Symptom: Sessions close sooner than expected.
 - Checks:
   - Verify SESSION_TIMEOUT_MINUTES configuration.
   - Ensure there is no reverse proxy cutting idle connections prematurely.

4. High Resource Usage
 - Symptom: Host system shows high CPU or memory from terminal sessions.
 - Recommendations:
   - Limit MAX_PARALLEL_JOBS.
   - Implement job runtime limits.
   - Regularly close inactive sessions via the tool or server admin API.

📚 Summary

The Interactive Terminal Tool for Open WebUI bridges the gap between conversational AI and real-world system administration by providing:

 - A full-featured browser-based terminal
 - Asynchronous, parallel job execution
 - Comprehensive command history tracking
 - Robust session and timeout management
 - Flexible integration with Dockerized Open WebUI deployments

This enables powerful workflows where LLMs can not only suggest commands but also execute them, observe real-time output, and iteratively refine actions—all under the user's supervision and control.
