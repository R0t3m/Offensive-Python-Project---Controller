# Python Multi-Client C2 & Remote Administration Tool

A lightweight, multi-threaded command and control (C2) framework and payload builder written in Python.

## Features

- **Multi-Client Architecture** – Handles multiple concurrent agent sessions from a centralized server panel.
- **Integrated HTTP Server** – Built-in lightweight HTTP server for automatic payload delivery and staging.
- **Interactive Shell** – Execute native shell commands.
- **Built-in Modules**:
  - **Keylogger** – Real-time keystroke capturing and buffer dumping (`pynput`).
  - **Screen Capture** – Remote screenshot utility saved directly to the server side (`pyautogui`).
  - **System Monitoring** – Live process tracking and idle time detection (`GetLastInputInfo` on Windows, `tty` on Linux).
  - **File Transfer** – Built-in upload and download capabilities for exfiltration and deployment.

## Requirements

- Python 3.x

The scripts automatically install any required third-party modules on first run.

## Usage

### 1. Start the Server / Listener

Run the central server script, specifying your local listening IP and port:

```bash
python control.py <LHOST> <LPORT>
```

From the interactive server panel, you can use the following core commands:

- sessions – List all active connected agent sessions
- interact <ID> – Switch control to a specific agent session
- quit – Shutdown the server and close all connections

2. Generate and Compile Payloads
Use the builder script to compile a target-specific executable payload (Windows or Linux):
```bash
python builder.py <LHOST> <LPORT> <windows/linux> <payload_name>
```

## Disclaimer
This tool is created strictly for educational purposes, authorized security testing, and administrative management of systems you own or have explicit legal permission to access. The author assumes no liability for misuse.
