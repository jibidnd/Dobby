# Setup

## Windows

1. Install [OpenCode](https://opencode.ai).
2. Download or clone the dobby folder.
3. Open PowerShell in that folder and run `opencode`.
4. Say `set up dobby`.

The guided setup detects Python, Node, OpenCode, and the plugin dependency. If Python is not on your PATH, it asks for an existing `python.exe` location and shows examples of valid paths. You can instead choose the guided Python install.

It then asks you to choose a permission level and model provider. These steps require your approval because they control what dobby can do and where your prompts are sent.

Restart OpenCode when setup finishes.

## macOS and Linux

Install Python 3.10+, Node.js, and OpenCode using your platform's normal package manager or the official installers. Then open a terminal in the dobby folder, run `opencode`, and say `set up dobby`. The same guided configuration handles the rest.

## Connect Services

During guided setup, choose **Connect Composio** to enable optional service connections. Composio is the bridge for Google services such as Gmail, Calendar, and Drive, plus services such as Dropbox and GitHub. You authenticate in your browser and approve services individually. Choosing not to connect anything leaves dobby fully local.

## Private Files

The setup process creates private files and folders only when needed. `memory/`, `knowledge/`, `dobby.local.md`, and `.mcp.json` are ignored by Git. Keep them in a location and backup system you trust.
