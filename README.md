# dobby

*Dobby is here to help.*

Your private personal-assistant runtime. It runs in [OpenCode](https://opencode.ai), remembers the context you choose to keep, and can help with planning, writing, learning, research, and software work.

## Start Here

1. Install [OpenCode](https://opencode.ai).
2. Download or clone this folder somewhere you control.
3. Open a terminal in the folder and run:

   ```powershell
   opencode
   ```

4. In the chat, say **`set up dobby`**.

That is all the setup you need to begin. The guided setup checks your machine, installs the small plugin dependency, asks how you want permissions handled, helps you sign in to a model provider, and verifies the result. If Python is not found, it will ask for an existing `python.exe` path or offer to install it.

You will need to restart OpenCode once after setup so it can load the plugin.

## Optional Connections

dobby works without access to any other service. During setup it offers **Composio**, which is how you can connect Gmail, Google Calendar, Google Drive, Dropbox, GitHub, and other services. You choose whether to enable it and separately approve each service in your browser.

## Privacy

Your personal memory, knowledge notes, local preferences, and tool connections remain on your machine and are ignored by Git:

- `memory/` — active context and tasks
- `knowledge/` — durable notes you create
- `dobby.local.md` — preferences and paths
- `.mcp.json` — local service connections

Back up those private files using a method you trust. The repository contains only dobby's code, skills, and documentation.

## Everyday Use

Just talk to dobby. Try `good morning`, `plan my day`, `jot this`, `remember this`, or `critic this draft`. Run `configure-dobby` any time you want to repair or change setup.

## More Help

- [Setup details](docs/setup.md)
- [Hosting dobby](docs/hosting.md)
- [Product design](BLUEPRINT.md)

Developers can run `python scripts/verify.py` to check the repository.
